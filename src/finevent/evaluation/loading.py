"""Load gold labels and prediction artifacts for evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from finevent.evaluation.models import GoldRecord, PredictionRecord
from finevent.jsonl import read_jsonl
from finevent.schema.validation import EVENT_KEYS, MODEL_INFO_KEYS, TOP_LEVEL_KEYS
from finevent.types import JsonDict, PathLike


def load_gold_records(path: PathLike) -> dict[str, GoldRecord]:
    records: dict[str, GoldRecord] = {}
    for raw_record in read_jsonl(path):
        label = normalize_label_payload(raw_record)
        article_id = str(label.get("article_id") or raw_record.get("article_id") or "")
        if not article_id:
            continue
        records[article_id] = GoldRecord(
            article_id=article_id,
            label=label,
            source_record=raw_record,
        )
    return records


def load_prediction_records(
    *,
    predictions_path: PathLike | None = None,
    runs_dir: PathLike | None = None,
    default_config_name: str = "default",
) -> list[PredictionRecord]:
    records: list[PredictionRecord] = []
    if predictions_path is not None:
        records.extend(
            _load_prediction_file(
                predictions_path,
                default_config_name=default_config_name,
            )
        )
    if runs_dir is not None:
        records.extend(
            _load_run_result_files(
                runs_dir,
                default_config_name=default_config_name,
            )
        )
    return records


def normalize_label_payload(record: JsonDict) -> JsonDict:
    for key in ("label", "gold", "prediction", "final_output", "verified_output"):
        value = record.get(key)
        if isinstance(value, dict):
            return _schema_shaped_payload(value)
    return _schema_shaped_payload(record)


def _load_prediction_file(
    path: PathLike,
    *,
    default_config_name: str,
) -> list[PredictionRecord]:
    input_path = Path(path)
    if input_path.suffix.lower() == ".jsonl":
        raw_records = read_jsonl(input_path)
    else:
        loaded = json.loads(input_path.read_text(encoding="utf-8"))
        raw_records = loaded if isinstance(loaded, list) else [loaded]
    return [
        _prediction_from_record(
            raw_record,
            source_path=str(input_path),
            default_config_name=default_config_name,
        )
        for raw_record in raw_records
        if isinstance(raw_record, dict)
    ]


def _load_run_result_files(
    runs_dir: PathLike,
    *,
    default_config_name: str,
) -> list[PredictionRecord]:
    records: list[PredictionRecord] = []
    root = Path(runs_dir)
    if not root.exists():
        return records
    for result_path in sorted(root.glob("*/result.json")):
        try:
            loaded = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            records.append(
                PredictionRecord(
                    article_id="",
                    config_name=default_config_name,
                    prediction=_empty_prediction(""),
                    source_path=str(result_path),
                    json_valid=False,
                )
            )
            continue
        if isinstance(loaded, dict):
            records.append(
                _prediction_from_record(
                    loaded,
                    source_path=str(result_path),
                    default_config_name=default_config_name,
                )
            )
    return records


def _prediction_from_record(
    record: JsonDict,
    *,
    source_path: str,
    default_config_name: str,
) -> PredictionRecord:
    prediction = normalize_label_payload(record)
    article_id = str(
        prediction.get("article_id")
        or record.get("article_id")
        or record.get("query_article_id")
        or ""
    )
    run_id = str(record.get("run_id") or _model_info_run_id(prediction) or "")
    config_name = str(
        record.get("config_name")
        or record.get("experiment_config")
        or record.get("run_config_name")
        or record.get("ablation_config")
        or default_config_name
    )
    return PredictionRecord(
        article_id=article_id,
        config_name=config_name,
        prediction=prediction or _empty_prediction(article_id),
        run_id=run_id,
        source_path=source_path,
        validation_issues=_list_of_dicts(record.get("validation_issues")),
        verification_report=dict(record.get("verification_report") or {}),
        hallucination_metrics=dict(record.get("hallucination_metrics") or {}),
        raw_record=record,
        json_valid=True,
    )


def _schema_shaped_payload(payload: JsonDict) -> JsonDict:
    shaped: JsonDict = {}
    for key in TOP_LEVEL_KEYS:
        if key in payload:
            shaped[key] = payload[key]
    if "events" not in shaped and "events" in payload:
        shaped["events"] = payload["events"]
    article_id = payload.get("article_id")
    if article_id is not None:
        shaped["article_id"] = article_id
    events = shaped.get("events")
    if isinstance(events, list):
        shaped["events"] = [
            _schema_shaped_event(event) for event in events if isinstance(event, dict)
        ]
    else:
        shaped["events"] = []
    shaped.setdefault("document_label", "HAS_EVENT" if shaped["events"] else "NO_EVENT")
    shaped.setdefault("warnings", [])
    shaped.setdefault("model_info", _schema_shaped_model_info(payload.get("model_info")))
    return shaped


def _schema_shaped_event(event: JsonDict) -> JsonDict:
    return {key: event.get(key) for key in EVENT_KEYS if key in event}


def _schema_shaped_model_info(value: object) -> JsonDict:
    if not isinstance(value, dict):
        return {}
    return {key: value.get(key) for key in MODEL_INFO_KEYS if key in value}


def _model_info_run_id(payload: JsonDict) -> str:
    model_info = payload.get("model_info")
    if isinstance(model_info, dict):
        return str(model_info.get("run_id") or "")
    return ""


def _list_of_dicts(value: object) -> list[JsonDict]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _empty_prediction(article_id: str) -> JsonDict:
    return {
        "article_id": article_id,
        "document_label": "NO_EVENT",
        "events": [],
        "warnings": ["missing_prediction"],
        "model_info": {},
    }
