"""Evidence verification and hallucination reduction for extraction outputs."""

from __future__ import annotations

import copy
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from typing import Any

from finevent.ingestion.text import normalize_text
from finevent.schema.taxonomy import EventTaxonomy, load_event_taxonomy
from finevent.schema.validation import (
    EVENT_KEYS,
    TOP_LEVEL_KEYS,
    ValidationIssue,
    validate_label_document,
)
from finevent.types import JsonDict

SUPPORTED = "SUPPORTED"
PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
UNSUPPORTED = "UNSUPPORTED"


CORE_ARGUMENT_GROUPS: dict[str, tuple[tuple[str, ...], ...]] = {
    "MA": (("buyer", "seller", "target_company", "stake_percentage", "transaction_value"),),
    "CONTRACT": (("partner", "project", "product", "package_name", "contract_value"),),
    "CAPITAL": (("share_volume", "issue_price", "capital_before", "capital_after", "bond_value"),),
    "LEADERSHIP": (("person", "role", "action"),),
    "EXPANSION": (("project", "location", "investment_value", "capacity", "market"),),
    "LEGAL_RISK": (("legal_authority", "violation", "case_name", "penalty_value"),),
    "PARTNERSHIP": (("partner", "agreement_type", "partnership_scope", "project"),),
    "LICENSE_APPROVAL": (("legal_authority", "approval_type", "project", "license_id"),),
    "BUSINESS_RESULT": (("period", "revenue", "profit", "growth_rate", "cause"),),
    "ASSET_TRANSACTION": (("asset_name", "asset_type", "buyer", "seller", "transaction_value"),),
    "DEBT_CREDIT": (("lender", "borrower", "loan_value", "credit_limit", "bond_code"),),
    "DIVIDEND_SHAREHOLDER": (("dividend_type", "dividend_rate", "record_date", "payment_date"),),
    "PRODUCT_SERVICE": (("product", "launch_date", "market", "price_change"),),
    "MARKET_LISTING": (("exchange", "ticker", "listing_date", "status", "reason"),),
    "ESG_OPERATIONAL_RISK": (("incident_type", "location", "impact_scope", "legal_authority"),),
}


@dataclass(frozen=True)
class VerificationConfig:
    evidence_match_threshold: float = 0.82
    argument_match_threshold: float = 0.78
    drop_unsupported_events: bool = True
    null_unsupported_arguments: bool = True
    verification_version: str = "m07_verification_v1"


@dataclass(frozen=True)
class EvidenceMatch:
    support: str
    source: str | None = None
    source_id: str | None = None
    score: float = 0.0
    matched_text: str | None = None
    match_type: str | None = None

    @property
    def is_supported(self) -> bool:
        return self.support in {SUPPORTED, PARTIALLY_SUPPORTED}

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class VerificationResult:
    verified_output: JsonDict
    report: JsonDict

    @property
    def metrics(self) -> JsonDict:
        metrics = self.report.get("metrics")
        return metrics if isinstance(metrics, dict) else {}

    def to_dict(self) -> JsonDict:
        return {"verified_output": self.verified_output, "verification_report": self.report}


@dataclass
class _VerificationAccumulator:
    event_checks: list[JsonDict] = field(default_factory=list)
    field_checks: list[JsonDict] = field(default_factory=list)
    unsupported_fields: list[JsonDict] = field(default_factory=list)
    dropped_events: list[JsonDict] = field(default_factory=list)
    repairs: list[JsonDict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def verify_extraction_output(
    draft_output: JsonDict,
    *,
    article: JsonDict,
    retrieved_contexts: list[JsonDict] | None = None,
    taxonomy: EventTaxonomy | None = None,
    config: VerificationConfig | None = None,
) -> VerificationResult:
    """Verify a normalized extraction output against article/context evidence.

    The verifier is intentionally conservative. It never creates new facts; it
    can only drop unsupported events, null unsupported arguments, strip
    out-of-schema fields, and report consistency warnings.
    """
    taxonomy = taxonomy or load_event_taxonomy()
    config = config or VerificationConfig()
    contexts = retrieved_contexts or []
    accumulator = _VerificationAccumulator()

    pre_schema = validate_label_document(draft_output, article, taxonomy=taxonomy)
    sanitized = _sanitize_document(draft_output, accumulator)
    draft_events = sanitized.get("events") if isinstance(sanitized.get("events"), list) else []
    verified_events: list[JsonDict] = []

    for index, raw_event in enumerate(draft_events):
        if not isinstance(raw_event, dict):
            accumulator.dropped_events.append(
                {
                    "event_index": index,
                    "event_id": None,
                    "reason": "event_not_object",
                    "action": "drop_event",
                }
            )
            continue

        event = _sanitize_event(raw_event, index, taxonomy, accumulator)
        event_id = str(event.get("event_id") or f"event_{index + 1:02d}")
        event_type = event.get("event_type")

        if event_type not in taxonomy.event_types:
            accumulator.dropped_events.append(
                {
                    "event_index": index,
                    "event_id": event_id,
                    "reason": "invalid_event_type",
                    "action": "drop_event",
                }
            )
            continue

        evidence_match = find_evidence_support(
            str(event.get("evidence_span") or ""),
            article=article,
            retrieved_contexts=contexts,
            threshold=config.evidence_match_threshold,
        )
        accumulator.event_checks.append(
            {
                "event_index": index,
                "event_id": event_id,
                "event_type": event_type,
                "evidence": evidence_match.to_dict(),
            }
        )
        accumulator.field_checks.append(
            {
                "event_id": event_id,
                "field": "evidence_span",
                "value": event.get("evidence_span"),
                "support": evidence_match.support,
                "evidence": evidence_match.to_dict(),
            }
        )

        if not evidence_match.is_supported and config.drop_unsupported_events:
            accumulator.dropped_events.append(
                {
                    "event_index": index,
                    "event_id": event_id,
                    "reason": "evidence_span_unsupported",
                    "action": "drop_event",
                    "evidence_span": event.get("evidence_span"),
                }
            )
            continue

        if evidence_match.matched_text and evidence_match.match_type == "fuzzy":
            event["evidence_span"] = evidence_match.matched_text
            accumulator.repairs.append(
                {
                    "event_id": event_id,
                    "field": "evidence_span",
                    "action": "replace_with_matched_evidence",
                    "source": evidence_match.source,
                    "score": evidence_match.score,
                }
            )

        _verify_arguments(event, article, contexts, config, accumulator)
        _check_taxonomy_consistency(event, taxonomy, accumulator)
        verified_events.append(event)

    sanitized["events"] = verified_events
    sanitized["document_label"] = _verified_document_label(sanitized, verified_events)
    _append_verification_warnings(sanitized, accumulator)

    final_schema = validate_label_document(sanitized, article, taxonomy=taxonomy)
    report = _build_report(
        draft_output=draft_output,
        verified_output=sanitized,
        pre_schema_issues=pre_schema.issues,
        final_schema_issues=final_schema.issues,
        accumulator=accumulator,
        config=config,
    )
    return VerificationResult(verified_output=sanitized, report=report)


def find_evidence_support(
    evidence_span: str,
    *,
    article: JsonDict,
    retrieved_contexts: list[JsonDict] | None = None,
    threshold: float = 0.82,
) -> EvidenceMatch:
    """Find exact or fuzzy support for an evidence span in article/context text."""
    contexts = retrieved_contexts or []
    query = normalize_text(evidence_span)
    if not query:
        return EvidenceMatch(support=UNSUPPORTED, score=0.0)

    article_text = _article_text(article)
    article_match = _find_text_match(
        query,
        article_text,
        source="article",
        source_id=str(article.get("article_id") or ""),
        threshold=threshold,
    )
    if article_match.is_supported:
        return article_match

    best_context_match = EvidenceMatch(support=UNSUPPORTED, score=article_match.score)
    for context in contexts:
        context_text = _context_text(context)
        context_match = _find_text_match(
            query,
            context_text,
            source="retrieved_context",
            source_id=str(context.get("chunk_id") or context.get("article_id") or ""),
            threshold=threshold,
        )
        if context_match.score > best_context_match.score:
            best_context_match = context_match
        if context_match.is_supported:
            return context_match
    return best_context_match


def build_self_verification_prompt(
    *,
    article: JsonDict,
    draft_output: JsonDict,
    retrieved_contexts: list[JsonDict] | None = None,
) -> str:
    """Build the optional LLM self-verification prompt for later experiments."""
    contexts = retrieved_contexts or []
    context_blocks = []
    for index, context in enumerate(contexts, start=1):
        context_blocks.append(
            f"[context_{index}]\n"
            f"title: {context.get('title') or ''}\n"
            f"text: {_truncate(_context_text(context), 1200)}"
        )
    return "\n\n".join(
        [
            "You are verifying a Vietnamese financial event extraction result.",
            "Use only the article and retrieved contexts. Do not introduce new facts.",
            "For each event field, return SUPPORTED, PARTIALLY_SUPPORTED, or UNSUPPORTED.",
            "If a field is unsupported, recommend set_null, drop_field, or drop_event.",
            "Return JSON only.",
            "[article]",
            f"title: {article.get('title') or ''}",
            f"text: {_truncate(str(article.get('text') or ''), 4000)}",
            "[retrieved_contexts]",
            "\n\n".join(context_blocks) if context_blocks else "[]",
            "[draft_output_json]",
            str(draft_output),
        ]
    )


def _sanitize_document(draft_output: JsonDict, accumulator: _VerificationAccumulator) -> JsonDict:
    sanitized = copy.deepcopy(draft_output)
    extra_keys = sorted(set(sanitized) - TOP_LEVEL_KEYS)
    for key in extra_keys:
        sanitized.pop(key, None)
        accumulator.repairs.append(
            {"field": key, "path": "$", "action": "drop_unexpected_top_level_field"}
        )
    warnings = sanitized.get("warnings")
    if not isinstance(warnings, list):
        sanitized["warnings"] = []
        accumulator.repairs.append({"field": "warnings", "path": "$", "action": "reset_warnings"})
    return sanitized


def _sanitize_event(
    raw_event: JsonDict,
    index: int,
    taxonomy: EventTaxonomy,
    accumulator: _VerificationAccumulator,
) -> JsonDict:
    event = copy.deepcopy(raw_event)
    event_id = str(event.get("event_id") or f"event_{index + 1:02d}")
    extra_keys = sorted(set(event) - EVENT_KEYS)
    for key in extra_keys:
        event.pop(key, None)
        accumulator.repairs.append(
            {
                "event_id": event_id,
                "field": key,
                "path": f"events[{index}]",
                "action": "drop_unexpected_event_field",
            }
        )

    event_type = event.get("event_type")
    subtype = event.get("event_subtype")
    if isinstance(event_type, str):
        event["event_type"] = event_type.strip().upper()
        event_type = event["event_type"]
    if isinstance(subtype, str):
        subtype = subtype.strip().upper() or None
        event["event_subtype"] = subtype
    if (
        isinstance(event_type, str)
        and subtype is not None
        and subtype not in taxonomy.allowed_subtypes(event_type)
    ):
        event["event_subtype"] = None
        accumulator.repairs.append(
            {
                "event_id": event_id,
                "field": "event_subtype",
                "action": "set_null_invalid_subtype_for_type",
                "old_value": subtype,
            }
        )
    arguments = event.get("event_arguments")
    if not isinstance(arguments, dict):
        event["event_arguments"] = {}
        accumulator.repairs.append(
            {
                "event_id": event_id,
                "field": "event_arguments",
                "action": "reset_non_object_arguments",
            }
        )
    return event


def _verify_arguments(
    event: JsonDict,
    article: JsonDict,
    contexts: list[JsonDict],
    config: VerificationConfig,
    accumulator: _VerificationAccumulator,
) -> None:
    event_id = str(event.get("event_id") or "")
    arguments = event.get("event_arguments")
    if not isinstance(arguments, dict):
        return

    evidence_texts = [str(event.get("evidence_span") or ""), _article_text(article)]
    evidence_texts.extend(_context_text(context) for context in contexts)

    for key, value in list(arguments.items()):
        if _is_empty_value(value):
            continue
        value_strings = _value_strings(value)
        if not value_strings:
            continue
        match = _best_value_match(
            value_strings,
            evidence_texts,
            threshold=config.argument_match_threshold,
        )
        accumulator.field_checks.append(
            {
                "event_id": event_id,
                "field": f"event_arguments.{key}",
                "value": value,
                "support": match.support,
                "evidence": match.to_dict(),
            }
        )
        if match.is_supported:
            continue

        action = "set_null" if config.null_unsupported_arguments else "drop_field"
        if config.null_unsupported_arguments:
            arguments[key] = None
        else:
            arguments.pop(key, None)
        _cap_event_confidence(event, 0.7)
        accumulator.unsupported_fields.append(
            {
                "event_id": event_id,
                "field": f"event_arguments.{key}",
                "value": value,
                "reason": "argument_value_not_grounded",
                "action": action,
                "best_match": match.to_dict(),
            }
        )


def _check_taxonomy_consistency(
    event: JsonDict,
    taxonomy: EventTaxonomy,
    accumulator: _VerificationAccumulator,
) -> None:
    event_id = str(event.get("event_id") or "")
    event_type = event.get("event_type")
    if not isinstance(event_type, str) or event_type not in taxonomy.event_types:
        return

    arguments = (
        event.get("event_arguments")
        if isinstance(event.get("event_arguments"), dict)
        else {}
    )
    core_groups = CORE_ARGUMENT_GROUPS.get(event_type, ())
    for group in core_groups:
        if not any(not _is_empty_value(arguments.get(field)) for field in group):
            accumulator.warnings.append(
                f"{event_id}:missing_core_argument_for_{event_type.lower()}"
            )
            _cap_event_confidence(event, 0.75)
            break

    sentiment = event.get("impact_sentiment")
    if event_type == "LEGAL_RISK" and sentiment == "POSITIVE":
        accumulator.warnings.append(f"{event_id}:legal_risk_positive_sentiment_needs_review")
        _cap_event_confidence(event, 0.65)
    if event_type in {"CONTRACT", "EXPANSION", "PARTNERSHIP"} and sentiment == "NEGATIVE":
        accumulator.warnings.append(f"{event_id}:negative_growth_event_needs_strong_evidence")
        _cap_event_confidence(event, 0.7)


def _build_report(
    *,
    draft_output: JsonDict,
    verified_output: JsonDict,
    pre_schema_issues: list[ValidationIssue],
    final_schema_issues: list[ValidationIssue],
    accumulator: _VerificationAccumulator,
    config: VerificationConfig,
) -> JsonDict:
    draft_events = (
        draft_output.get("events") if isinstance(draft_output.get("events"), list) else []
    )
    verified_events = (
        verified_output.get("events") if isinstance(verified_output.get("events"), list) else []
    )
    metrics = _compute_metrics(
        draft_event_count=len(draft_events),
        verified_event_count=len(verified_events),
        field_checks=accumulator.field_checks,
        dropped_events=accumulator.dropped_events,
        repairs=accumulator.repairs,
    )
    return {
        "verification_version": config.verification_version,
        "schema_valid_before_verification": not any(
            issue.severity == "error" for issue in pre_schema_issues
        ),
        "schema_valid_after_verification": not any(
            issue.severity == "error" for issue in final_schema_issues
        ),
        "schema_issues_before_verification": [issue.to_dict() for issue in pre_schema_issues],
        "schema_issues_after_verification": [issue.to_dict() for issue in final_schema_issues],
        "draft_event_count": len(draft_events),
        "verified_event_count": len(verified_events),
        "event_checks": accumulator.event_checks,
        "field_checks": accumulator.field_checks,
        "unsupported_fields": accumulator.unsupported_fields,
        "dropped_events": accumulator.dropped_events,
        "repairs": accumulator.repairs,
        "warnings": accumulator.warnings,
        "metrics": metrics,
    }


def _compute_metrics(
    *,
    draft_event_count: int,
    verified_event_count: int,
    field_checks: list[JsonDict],
    dropped_events: list[JsonDict],
    repairs: list[JsonDict],
) -> JsonDict:
    evidence_checks = [check for check in field_checks if check.get("field") == "evidence_span"]
    supported_evidence = [
        check
        for check in evidence_checks
        if check.get("support") in {SUPPORTED, PARTIALLY_SUPPORTED}
    ]
    unsupported_checks = [check for check in field_checks if check.get("support") == UNSUPPORTED]
    supported_checks = [check for check in field_checks if check.get("support") == SUPPORTED]
    partial_checks = [
        check for check in field_checks if check.get("support") == PARTIALLY_SUPPORTED
    ]
    denominator = len(field_checks) or 1
    return {
        "evidence_coverage": _ratio(len(supported_evidence), len(evidence_checks)),
        "unsupported_field_rate": _ratio(len(unsupported_checks), len(field_checks)),
        "unsupported_event_rate": _ratio(len(dropped_events), draft_event_count),
        "verified_event_retention_rate": _ratio(verified_event_count, draft_event_count),
        "schema_repair_count": len(repairs),
        "repair_success_rate": 1.0 if repairs else 0.0,
        "groundedness_score": round(
            (len(supported_checks) + 0.5 * len(partial_checks)) / denominator,
            6,
        ),
    }


def _find_text_match(
    query: str,
    text: str,
    *,
    source: str,
    source_id: str,
    threshold: float,
) -> EvidenceMatch:
    query_norm = _fold(query)
    text_norm = _fold(text)
    if not query_norm or not text_norm:
        return EvidenceMatch(support=UNSUPPORTED, source=source, source_id=source_id)
    if query_norm in text_norm:
        return EvidenceMatch(
            support=SUPPORTED,
            source=source,
            source_id=source_id,
            score=1.0,
            matched_text=query,
            match_type="exact",
        )

    best_score = 0.0
    best_text: str | None = None
    for candidate in _candidate_windows(text, query):
        score = SequenceMatcher(None, query_norm, _fold(candidate)).ratio()
        if score > best_score:
            best_score = score
            best_text = candidate
    if best_score >= threshold:
        support = SUPPORTED if best_score >= 0.92 else PARTIALLY_SUPPORTED
        return EvidenceMatch(
            support=support,
            source=source,
            source_id=source_id,
            score=round(best_score, 6),
            matched_text=best_text,
            match_type="fuzzy",
        )
    return EvidenceMatch(
        support=UNSUPPORTED,
        source=source,
        source_id=source_id,
        score=round(best_score, 6),
        matched_text=best_text,
        match_type="fuzzy",
    )


def _best_value_match(
    value_strings: list[str],
    texts: list[str],
    *,
    threshold: float,
) -> EvidenceMatch:
    best = EvidenceMatch(support=UNSUPPORTED)
    for value in value_strings:
        for index, text in enumerate(texts):
            match = _find_text_match(
                value,
                text,
                source="evidence_text" if index == 0 else "article_or_context",
                source_id=str(index),
                threshold=threshold,
            )
            if match.score > best.score:
                best = match
            if match.is_supported:
                return match
    return best


def _candidate_windows(text: str, query: str) -> list[str]:
    sentences = _split_sentences(text)
    query_tokens = _fold(query).split()
    if not query_tokens:
        return sentences
    windows: list[str] = []
    target = len(query_tokens)
    for sentence in sentences:
        windows.append(sentence)
        tokens = sentence.split()
        if len(tokens) <= 2:
            continue
        min_size = max(2, target - 3)
        max_size = min(len(tokens), target + 5)
        for size in range(min_size, max_size + 1):
            for start in range(0, len(tokens) - size + 1):
                windows.append(" ".join(tokens[start : start + size]))
    return windows


def _value_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [str(value)]
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(_value_strings(item))
        return values
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(_value_strings(item))
        return values
    return []


def _is_empty_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _verified_document_label(document: JsonDict, verified_events: list[JsonDict]) -> str:
    original = document.get("document_label")
    if verified_events:
        return "HAS_EVENT"
    if original == "UNCERTAIN":
        return "UNCERTAIN"
    return "NO_EVENT"


def _append_verification_warnings(
    document: JsonDict,
    accumulator: _VerificationAccumulator,
) -> None:
    warnings = document.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
        document["warnings"] = warnings
    if accumulator.dropped_events:
        warnings.append("verification_dropped_unsupported_events")
    if accumulator.unsupported_fields:
        warnings.append("verification_nullified_unsupported_arguments")
    warnings.extend(accumulator.warnings)


def _cap_event_confidence(event: JsonDict, cap: float) -> None:
    confidence = event.get("confidence")
    if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
        event["confidence"] = round(min(float(confidence), cap), 6)


def _article_text(article: JsonDict) -> str:
    return "\n".join(
        str(value)
        for value in (article.get("title"), article.get("text"))
        if isinstance(value, str) and value.strip()
    )


def _context_text(context: JsonDict) -> str:
    return "\n".join(
        str(value)
        for value in (context.get("title"), context.get("text"))
        if isinstance(value, str) and value.strip()
    )


def _split_sentences(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [
        sentence.strip()
        for sentence in re.split(r"[\n\r]+|(?<=[.!?;:])\s+", normalized)
        if sentence.strip()
    ]


def _fold(text: str) -> str:
    normalized = normalize_text(str(text)).lower()
    normalized = normalized.replace("đ", "d").replace("Đ", "d")
    ascii_text = "".join(
        char
        for char in unicodedata.normalize("NFKD", normalized)
        if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", ascii_text).strip()


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 6)


def _truncate(text: Any, max_chars: int) -> str:
    value = str(text or "")
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3] + "..."
