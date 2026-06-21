"""Metric computation for event extraction evaluation."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable

from finevent.evaluation.models import EventMatch, GoldRecord, PredictionRecord
from finevent.types import JsonDict

ERROR_NO_EVENT_FALSE_POSITIVE = "E_NO_EVENT_FALSE_POSITIVE"
ERROR_MISSED_EVENT = "E_MISSED_EVENT"
ERROR_EXTRA_EVENT = "E_EXTRA_EVENT"
ERROR_WRONG_TICKER = "E_WRONG_TICKER"
ERROR_WRONG_EVENT_TYPE = "E_WRONG_EVENT_TYPE"
ERROR_WRONG_IMPACT = "E_WRONG_IMPACT"
ERROR_UNSUPPORTED_ARGUMENT = "E_UNSUPPORTED_ARGUMENT"
ERROR_BAD_EVIDENCE = "E_BAD_EVIDENCE"
ERROR_INVALID_JSON = "E_INVALID_JSON"
ERROR_SCHEMA_VIOLATION = "E_SCHEMA_VIOLATION"

MATCH_THRESHOLD = 0.25


def evaluate_prediction_group(
    *,
    config_name: str,
    gold_records: dict[str, GoldRecord],
    predictions: list[PredictionRecord],
) -> JsonDict:
    prediction_by_article = _best_prediction_by_article(predictions)
    article_ids = sorted(set(gold_records) | set(prediction_by_article))

    detailed_rows: list[JsonDict] = []
    error_rows: list[JsonDict] = []
    all_matches: list[EventMatch] = []
    gold_events: list[JsonDict] = []
    pred_events: list[JsonDict] = []
    event_type_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    impact_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    binary_counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    ticker_correct = 0
    ticker_total = 0
    subtype_correct = 0
    subtype_total = 0
    slot_counts = {"tp": 0, "fp": 0, "fn": 0}
    json_valid_count = 0
    schema_valid_count = 0
    prediction_count = 0

    for article_id in article_ids:
        gold = gold_records.get(article_id) or _empty_gold(article_id)
        prediction = prediction_by_article.get(article_id) or _missing_prediction(
            article_id,
            config_name,
        )
        prediction_count += 1
        json_valid_count += int(prediction.json_valid)
        schema_valid_count += int(prediction.schema_valid)

        gold_has_event = _has_event(gold.document_label, gold.events)
        pred_has_event = _has_event(prediction.document_label, prediction.events)
        _update_binary_counts(binary_counts, gold_has_event, pred_has_event)

        matches, unmatched_gold, unmatched_pred = match_events(gold.events, prediction.events)
        all_matches.extend(matches)
        gold_events.extend(gold.events)
        pred_events.extend(prediction.events)

        _update_class_counts(
            event_type_counts,
            gold.events,
            prediction.events,
            matches,
            "event_type",
        )
        _update_class_counts(
            impact_counts,
            gold.events,
            prediction.events,
            matches,
            "impact_sentiment",
        )
        ticker_result = _ticker_accuracy(matches)
        ticker_correct += ticker_result["correct"]
        ticker_total += ticker_result["total"]
        subtype_result = _subtype_accuracy(matches)
        subtype_correct += subtype_result["correct"]
        subtype_total += subtype_result["total"]
        slot_result = _slot_counts(matches)
        for key in slot_counts:
            slot_counts[key] += slot_result[key]

        error_rows.extend(
            build_article_errors(
                gold=gold,
                prediction=prediction,
                matches=matches,
                unmatched_gold=unmatched_gold,
                unmatched_pred=unmatched_pred,
            )
        )
        detailed_rows.append(
            {
                "config_name": config_name,
                "article_id": article_id,
                "gold_document_label": gold.document_label,
                "pred_document_label": prediction.document_label,
                "gold_event_count": len(gold.events),
                "pred_event_count": len(prediction.events),
                "matched_event_count": len(matches),
                "json_valid": int(prediction.json_valid),
                "schema_valid": int(prediction.schema_valid),
            }
        )

    detection = _binary_metrics(binary_counts)
    slot_metrics = _prf(slot_counts["tp"], slot_counts["fp"], slot_counts["fn"])
    metrics = {
        "event_detection_accuracy": detection["accuracy"],
        "event_detection_precision": detection["precision"],
        "event_detection_recall": detection["recall"],
        "event_detection_f1": detection["f1"],
        "event_type_macro_f1": _macro_f1(event_type_counts),
        "event_type_micro_f1": _micro_f1(event_type_counts),
        "impact_sentiment_macro_f1": _macro_f1(impact_counts),
        "impact_sentiment_micro_f1": _micro_f1(impact_counts),
        "ticker_accuracy": _safe_divide(ticker_correct, ticker_total),
        "event_subtype_accuracy": _safe_divide(subtype_correct, subtype_total),
        "slot_precision": slot_metrics["precision"],
        "slot_recall": slot_metrics["recall"],
        "slot_f1": slot_metrics["f1"],
        "json_validity_rate": _safe_divide(json_valid_count, prediction_count),
        "schema_compliance_rate": _safe_divide(schema_valid_count, prediction_count),
    }
    return {
        "metrics": metrics,
        "matches": all_matches,
        "per_event_type_rows": _per_class_rows(event_type_counts, label_field="event_type"),
        "error_rows": error_rows,
        "detailed_rows": detailed_rows,
        "article_count": len(article_ids),
        "gold_event_count": len(gold_events),
        "predicted_event_count": len(pred_events),
        "matched_event_count": len(all_matches),
        "hallucination_row": aggregate_hallucination_metrics(config_name, predictions),
    }


def match_events(
    gold_events: list[JsonDict],
    predicted_events: list[JsonDict],
    *,
    threshold: float = MATCH_THRESHOLD,
) -> tuple[list[EventMatch], list[JsonDict], list[JsonDict]]:
    candidate_pairs: list[EventMatch] = []
    for gold_index, gold_event in enumerate(gold_events):
        for pred_index, pred_event in enumerate(predicted_events):
            score, breakdown = event_match_score(gold_event, pred_event)
            if score >= threshold:
                candidate_pairs.append(
                    EventMatch(
                        gold_index=gold_index,
                        pred_index=pred_index,
                        gold_event=gold_event,
                        pred_event=pred_event,
                        score=score,
                        score_breakdown=breakdown,
                    )
                )
    matches: list[EventMatch] = []
    used_gold: set[int] = set()
    used_pred: set[int] = set()
    for candidate in sorted(candidate_pairs, key=lambda item: item.score, reverse=True):
        if candidate.gold_index in used_gold or candidate.pred_index in used_pred:
            continue
        used_gold.add(candidate.gold_index)
        used_pred.add(candidate.pred_index)
        matches.append(candidate)
    unmatched_gold = [
        event for index, event in enumerate(gold_events) if index not in used_gold
    ]
    unmatched_pred = [
        event for index, event in enumerate(predicted_events) if index not in used_pred
    ]
    return matches, unmatched_gold, unmatched_pred


def event_match_score(gold_event: JsonDict, pred_event: JsonDict) -> tuple[float, JsonDict]:
    ticker_or_company = max(
        _exact_match(gold_event.get("ticker"), pred_event.get("ticker")),
        _company_match(gold_event.get("company_name"), pred_event.get("company_name")),
    )
    event_type = _exact_match(gold_event.get("event_type"), pred_event.get("event_type"))
    evidence_overlap = max(
        _text_overlap(gold_event.get("evidence_span"), pred_event.get("evidence_span")),
        _text_overlap(gold_event.get("event_summary"), pred_event.get("event_summary")),
    )
    argument_overlap = _argument_overlap(
        gold_event.get("event_arguments"),
        pred_event.get("event_arguments"),
    )
    score = (
        0.35 * ticker_or_company
        + 0.35 * event_type
        + 0.20 * evidence_overlap
        + 0.10 * argument_overlap
    )
    breakdown = {
        "ticker_or_company": ticker_or_company,
        "event_type": event_type,
        "evidence_overlap": evidence_overlap,
        "argument_overlap": argument_overlap,
    }
    return round(score, 6), breakdown


def build_article_errors(
    *,
    gold: GoldRecord,
    prediction: PredictionRecord,
    matches: list[EventMatch],
    unmatched_gold: list[JsonDict],
    unmatched_pred: list[JsonDict],
) -> list[JsonDict]:
    errors: list[JsonDict] = []
    if not prediction.json_valid:
        errors.append(_error_row(prediction, gold.article_id, ERROR_INVALID_JSON))
    if not prediction.schema_valid:
        errors.append(_error_row(prediction, gold.article_id, ERROR_SCHEMA_VIOLATION))

    if not _has_event(gold.document_label, gold.events) and _has_event(
        prediction.document_label,
        prediction.events,
    ):
        errors.append(_error_row(prediction, gold.article_id, ERROR_NO_EVENT_FALSE_POSITIVE))

    for event in unmatched_gold:
        errors.append(
            _error_row(
                prediction,
                gold.article_id,
                ERROR_MISSED_EVENT,
                event_id=str(event.get("event_id") or ""),
                gold_event_type=str(event.get("event_type") or ""),
            )
        )
    for event in unmatched_pred:
        error_code = (
            ERROR_NO_EVENT_FALSE_POSITIVE
            if not _has_event(gold.document_label, gold.events)
            else ERROR_EXTRA_EVENT
        )
        errors.append(
            _error_row(
                prediction,
                gold.article_id,
                error_code,
                pred_event_type=str(event.get("event_type") or ""),
            )
        )

    for match in matches:
        gold_event = match.gold_event
        pred_event = match.pred_event
        if _normalize(gold_event.get("ticker")) and not _exact_match(
            gold_event.get("ticker"),
            pred_event.get("ticker"),
        ):
            errors.append(
                _error_row(
                    prediction,
                    gold.article_id,
                    ERROR_WRONG_TICKER,
                    event_id=str(gold_event.get("event_id") or ""),
                    gold_event_type=str(gold_event.get("event_type") or ""),
                    pred_event_type=str(pred_event.get("event_type") or ""),
                )
            )
        if not _exact_match(gold_event.get("event_type"), pred_event.get("event_type")):
            errors.append(
                _error_row(
                    prediction,
                    gold.article_id,
                    ERROR_WRONG_EVENT_TYPE,
                    event_id=str(gold_event.get("event_id") or ""),
                    gold_event_type=str(gold_event.get("event_type") or ""),
                    pred_event_type=str(pred_event.get("event_type") or ""),
                )
            )
        if not _exact_match(gold_event.get("impact_sentiment"), pred_event.get("impact_sentiment")):
            errors.append(
                _error_row(
                    prediction,
                    gold.article_id,
                    ERROR_WRONG_IMPACT,
                    event_id=str(gold_event.get("event_id") or ""),
                    gold_event_type=str(gold_event.get("event_type") or ""),
                    pred_event_type=str(pred_event.get("event_type") or ""),
                )
            )
        if match.score_breakdown.get("evidence_overlap", 0.0) <= 0.0:
            errors.append(
                _error_row(
                    prediction,
                    gold.article_id,
                    ERROR_BAD_EVIDENCE,
                    event_id=str(gold_event.get("event_id") or ""),
                    gold_event_type=str(gold_event.get("event_type") or ""),
                    pred_event_type=str(pred_event.get("event_type") or ""),
                )
            )

    for unsupported in _verification_unsupported_fields(prediction):
        errors.append(
            _error_row(
                prediction,
                gold.article_id,
                ERROR_UNSUPPORTED_ARGUMENT,
                event_id=str(unsupported.get("event_id") or ""),
                details=str(unsupported.get("field") or ""),
            )
        )
    return errors


def aggregate_error_rows(error_rows: list[JsonDict]) -> list[JsonDict]:
    counts = Counter(str(row.get("error_code") or "") for row in error_rows)
    return [
        {"error_code": error_code, "count": count}
        for error_code, count in sorted(counts.items())
    ]


def aggregate_hallucination_metrics(
    config_name: str,
    predictions: list[PredictionRecord],
) -> JsonDict:
    metric_rows = []
    for prediction in predictions:
        metrics = dict(prediction.hallucination_metrics or {})
        report_metrics = prediction.verification_report.get("metrics")
        if isinstance(report_metrics, dict):
            metrics = {**report_metrics, **metrics}
        if metrics:
            metric_rows.append(metrics)
    return {
        "config_name": config_name,
        "run_count": len(predictions),
        "run_count_with_verification": len(metric_rows),
        "pre_verification_hallucination_rate": _mean(
            _float(row.get("unsupported_field_rate")) for row in metric_rows
        ),
        "post_verification_hallucination_rate": _mean(
            _post_verification_rate(row) for row in metric_rows
        ),
        "evidence_coverage": _mean(_float(row.get("evidence_coverage")) for row in metric_rows),
        "unsupported_event_rate": _mean(
            _float(row.get("unsupported_event_rate")) for row in metric_rows
        ),
        "groundedness_score": _mean(
            _float(row.get("groundedness_score")) for row in metric_rows
        ),
    }


def group_predictions_by_config(
    predictions: list[PredictionRecord],
) -> dict[str, list[PredictionRecord]]:
    grouped: dict[str, list[PredictionRecord]] = defaultdict(list)
    for prediction in predictions:
        grouped[prediction.config_name].append(prediction)
    return dict(grouped)


def choose_best_config(rows: list[JsonDict]) -> JsonDict | None:
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: (
            _float(row.get("event_type_macro_f1")),
            _float(row.get("slot_f1")),
            _float(row.get("groundedness_score")),
            _float(row.get("event_detection_f1")),
        ),
    )


def _best_prediction_by_article(
    predictions: list[PredictionRecord],
) -> dict[str, PredictionRecord]:
    selected: dict[str, PredictionRecord] = {}
    for prediction in predictions:
        existing = selected.get(prediction.article_id)
        if existing is None or _prediction_quality_key(prediction) > _prediction_quality_key(
            existing
        ):
            selected[prediction.article_id] = prediction
    return selected


def _prediction_quality_key(prediction: PredictionRecord) -> tuple[int, int, int]:
    return (
        int(prediction.json_valid),
        int(prediction.schema_valid),
        len(prediction.events),
    )


def _empty_gold(article_id: str) -> GoldRecord:
    return GoldRecord(
        article_id=article_id,
        label={
            "article_id": article_id,
            "document_label": "NO_EVENT",
            "events": [],
            "warnings": ["prediction_without_gold"],
            "model_info": {},
        },
    )


def _missing_prediction(article_id: str, config_name: str) -> PredictionRecord:
    return PredictionRecord(
        article_id=article_id,
        config_name=config_name,
        prediction={
            "article_id": article_id,
            "document_label": "NO_EVENT",
            "events": [],
            "warnings": ["missing_prediction"],
            "model_info": {},
        },
    )


def _update_binary_counts(counts: dict[str, int], gold_has: bool, pred_has: bool) -> None:
    if gold_has and pred_has:
        counts["tp"] += 1
    elif not gold_has and pred_has:
        counts["fp"] += 1
    elif gold_has and not pred_has:
        counts["fn"] += 1
    else:
        counts["tn"] += 1


def _binary_metrics(counts: dict[str, int]) -> JsonDict:
    tp = counts["tp"]
    fp = counts["fp"]
    fn = counts["fn"]
    tn = counts["tn"]
    prf = _prf(tp, fp, fn)
    return {
        **prf,
        "accuracy": _safe_divide(tp + tn, tp + fp + fn + tn),
    }


def _update_class_counts(
    class_counts: dict[str, dict[str, int]],
    gold_events: list[JsonDict],
    predicted_events: list[JsonDict],
    matches: list[EventMatch],
    field_name: str,
) -> None:
    matched_gold = {match.gold_index for match in matches}
    matched_pred = {match.pred_index for match in matches}
    for match in matches:
        gold_label = str(match.gold_event.get(field_name) or "")
        pred_label = str(match.pred_event.get(field_name) or "")
        if gold_label and pred_label and gold_label == pred_label:
            class_counts[gold_label]["tp"] += 1
        else:
            if gold_label:
                class_counts[gold_label]["fn"] += 1
            if pred_label:
                class_counts[pred_label]["fp"] += 1
    for index, event in enumerate(gold_events):
        if index not in matched_gold:
            label = str(event.get(field_name) or "")
            if label:
                class_counts[label]["fn"] += 1
    for index, event in enumerate(predicted_events):
        if index not in matched_pred:
            label = str(event.get(field_name) or "")
            if label:
                class_counts[label]["fp"] += 1


def _per_class_rows(
    class_counts: dict[str, dict[str, int]],
    *,
    label_field: str,
) -> list[JsonDict]:
    rows: list[JsonDict] = []
    for label, counts in sorted(class_counts.items()):
        prf = _prf(counts["tp"], counts["fp"], counts["fn"])
        rows.append(
            {
                label_field: label,
                "tp": counts["tp"],
                "fp": counts["fp"],
                "fn": counts["fn"],
                "precision": prf["precision"],
                "recall": prf["recall"],
                "f1": prf["f1"],
            }
        )
    return rows


def _ticker_accuracy(matches: list[EventMatch]) -> dict[str, int]:
    correct = 0
    total = 0
    for match in matches:
        gold_ticker = _normalize(match.gold_event.get("ticker"))
        if not gold_ticker:
            continue
        total += 1
        correct += int(gold_ticker == _normalize(match.pred_event.get("ticker")))
    return {"correct": correct, "total": total}


def _subtype_accuracy(matches: list[EventMatch]) -> dict[str, int]:
    correct = 0
    total = 0
    for match in matches:
        gold_subtype = _normalize(match.gold_event.get("event_subtype"))
        if not gold_subtype:
            continue
        total += 1
        correct += int(gold_subtype == _normalize(match.pred_event.get("event_subtype")))
    return {"correct": correct, "total": total}


def _slot_counts(matches: list[EventMatch]) -> dict[str, int]:
    counts = {"tp": 0, "fp": 0, "fn": 0}
    for match in matches:
        gold_slots = _normalized_slots(match.gold_event.get("event_arguments"))
        pred_slots = _normalized_slots(match.pred_event.get("event_arguments"))
        matched_pred_keys: set[str] = set()
        for key, gold_value in gold_slots.items():
            pred_value = pred_slots.get(key)
            if pred_value and _slot_value_match(gold_value, pred_value):
                counts["tp"] += 1
                matched_pred_keys.add(key)
            else:
                counts["fn"] += 1
        for key in pred_slots:
            if key not in matched_pred_keys and key not in gold_slots:
                counts["fp"] += 1
            elif key in gold_slots and key not in matched_pred_keys:
                counts["fp"] += 1
    return counts


def _normalized_slots(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    slots: dict[str, str] = {}
    for key, raw_value in value.items():
        if raw_value is None or raw_value == "":
            continue
        normalized = _normalize_value(raw_value)
        if normalized:
            slots[str(key)] = normalized
    return slots


def _slot_value_match(gold_value: str, pred_value: str) -> bool:
    if gold_value == pred_value:
        return True
    return _text_overlap(gold_value, pred_value) >= 0.75


def _argument_overlap(gold_value: object, pred_value: object) -> float:
    gold_slots = _normalized_slots(gold_value)
    pred_slots = _normalized_slots(pred_value)
    if not gold_slots and not pred_slots:
        return 0.0
    if not gold_slots or not pred_slots:
        return 0.0
    matches = sum(
        1
        for key, value in gold_slots.items()
        if key in pred_slots and _slot_value_match(value, pred_slots[key])
    )
    return _safe_divide(matches, len(set(gold_slots) | set(pred_slots)))


def _exact_match(left: object, right: object) -> float:
    left_norm = _normalize(left)
    right_norm = _normalize(right)
    return 1.0 if left_norm and right_norm and left_norm == right_norm else 0.0


def _company_match(left: object, right: object) -> float:
    left_norm = _normalize(left)
    right_norm = _normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    if left_norm in right_norm or right_norm in left_norm:
        return 0.8
    return _text_overlap(left_norm, right_norm)


def _text_overlap(left: object, right: object) -> float:
    left_tokens = set(_tokens(left))
    right_tokens = set(_tokens(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return _safe_divide(len(left_tokens & right_tokens), len(left_tokens | right_tokens))


def _tokens(value: object) -> list[str]:
    return re.findall(r"[a-z0-9]+", _normalize(value))


def _normalize_value(value: object) -> str:
    if isinstance(value, list):
        return " ".join(_normalize_value(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_normalize_value(item) for item in value.values())
    return _normalize(value)


def _normalize(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace("đ", "d").replace("Đ", "d")
    text = "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", text).strip()


def _has_event(document_label: str, events: list[JsonDict]) -> bool:
    return document_label == "HAS_EVENT" and bool(events)


def _prf(tp: int, fp: int, fn: int) -> JsonDict:
    precision = _safe_divide(tp, tp + fp)
    recall = _safe_divide(tp, tp + fn)
    return {
        "precision": precision,
        "recall": recall,
        "f1": _safe_divide(2 * precision * recall, precision + recall),
    }


def _macro_f1(class_counts: dict[str, dict[str, int]]) -> float:
    if not class_counts:
        return 0.0
    return _mean(
        _prf(counts["tp"], counts["fp"], counts["fn"])["f1"]
        for counts in class_counts.values()
    )


def _micro_f1(class_counts: dict[str, dict[str, int]]) -> float:
    tp = sum(counts["tp"] for counts in class_counts.values())
    fp = sum(counts["fp"] for counts in class_counts.values())
    fn = sum(counts["fn"] for counts in class_counts.values())
    return _prf(tp, fp, fn)["f1"]


def _verification_unsupported_fields(prediction: PredictionRecord) -> list[JsonDict]:
    value = prediction.verification_report.get("unsupported_fields")
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _post_verification_rate(row: JsonDict) -> float:
    unsupported_event_rate = _float(row.get("unsupported_event_rate"))
    unsupported_field_rate = _float(row.get("unsupported_field_rate"))
    if unsupported_event_rate > 0 or unsupported_field_rate > 0:
        return 0.0
    return 0.0


def _error_row(
    prediction: PredictionRecord,
    article_id: str,
    error_code: str,
    *,
    event_id: str = "",
    gold_event_type: str = "",
    pred_event_type: str = "",
    details: str = "",
) -> JsonDict:
    return {
        "config_name": prediction.config_name,
        "run_id": prediction.run_id,
        "article_id": article_id,
        "event_id": event_id,
        "error_code": error_code,
        "gold_event_type": gold_event_type,
        "pred_event_type": pred_event_type,
        "details": details,
    }


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    value = numerator / denominator
    if math.isnan(value) or math.isinf(value):
        return 0.0
    return round(value, 6)


def _mean(values: Iterable[float]) -> float:
    collected = [value for value in values if not math.isnan(value)]
    return round(sum(collected) / len(collected), 6) if collected else 0.0


def _float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
