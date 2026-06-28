"""PostgreSQL sync helpers for validated event labels."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from finevent.jsonl import read_jsonl
from finevent.logging_utils import create_run_id
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class EventLabelSyncResult:
    labeling_run_id: str
    gold_documents: int
    gold_events: int
    rejected_documents: int


def sync_event_labels_jsonl(
    engine: Any,
    *,
    gold_path: PathLike = "data/labels/events_gold.jsonl",
    rejected_path: PathLike | None = "data/labels/events_rejected.jsonl",
    source_path: str | None = None,
) -> EventLabelSyncResult:
    gold_records = read_jsonl(gold_path)
    rejected_records = read_jsonl(rejected_path) if rejected_path else []
    labeling_run_id = _infer_run_id(gold_records, rejected_records)
    teacher_model = (
        _first_non_empty(gold_records, rejected_records, "teacher_model") or "unknown_teacher"
    )
    prompt_version = (
        _first_non_empty(gold_records, rejected_records, "prompt_version") or "unknown_prompt"
    )
    schema_version = _first_non_empty(
        gold_records,
        rejected_records,
        "label_schema_version",
    ) or "event_schema_v1"
    sql = _sqlalchemy_text()
    gold_events = 0

    with engine.begin() as connection:
        connection.execute(
            sql(
                """
                INSERT INTO event_labeling_runs (
                    labeling_run_id,
                    label_schema_version,
                    teacher_model,
                    prompt_version,
                    source_path,
                    status
                )
                VALUES (
                    :labeling_run_id,
                    :label_schema_version,
                    :teacher_model,
                    :prompt_version,
                    :source_path,
                    'RUNNING'
                )
                ON CONFLICT (labeling_run_id)
                DO UPDATE SET
                    label_schema_version = EXCLUDED.label_schema_version,
                    teacher_model = EXCLUDED.teacher_model,
                    prompt_version = EXCLUDED.prompt_version,
                    source_path = EXCLUDED.source_path,
                    status = 'RUNNING'
                """
            ),
            {
                "labeling_run_id": labeling_run_id,
                "label_schema_version": schema_version,
                "teacher_model": teacher_model,
                "prompt_version": prompt_version,
                "source_path": source_path or str(Path(gold_path)),
            },
        )

        for record in gold_records:
            label = record.get("label") or {}
            if not isinstance(label, dict):
                continue
            _upsert_gold_document(connection, sql, record, label, labeling_run_id)
            connection.execute(
                sql("DELETE FROM events_gold WHERE article_id = :article_id"),
                {"article_id": label["article_id"]},
            )
            for event in label.get("events", []):
                if not isinstance(event, dict):
                    continue
                _insert_gold_event(connection, sql, record, label, event, labeling_run_id)
                gold_events += 1

        for record in rejected_records:
            _insert_rejection(connection, sql, record, labeling_run_id)

        connection.execute(
            sql(
                """
                UPDATE event_labeling_runs
                SET
                    gold_count = :gold_count,
                    rejected_count = :rejected_count,
                    completed_at = NOW(),
                    status = 'SUCCESS'
                WHERE labeling_run_id = :labeling_run_id
                """
            ),
            {
                "labeling_run_id": labeling_run_id,
                "gold_count": len(gold_records),
                "rejected_count": len(rejected_records),
            },
        )

    return EventLabelSyncResult(
        labeling_run_id=labeling_run_id,
        gold_documents=len(gold_records),
        gold_events=gold_events,
        rejected_documents=len(rejected_records),
    )


def _upsert_gold_document(
    connection: Any,
    sql: Any,
    record: JsonDict,
    label: JsonDict,
    labeling_run_id: str,
) -> None:
    validation_warnings = [
        issue for issue in record.get("validation_errors", []) if issue.get("severity") == "warning"
    ]
    connection.execute(
        sql(
            """
            INSERT INTO event_label_documents_gold (
                article_id,
                document_label,
                label_reason,
                label_schema_version,
                label_source,
                teacher_model,
                prompt_version,
                labeling_run_id,
                warnings,
                model_info,
                validation_warnings,
                raw_label,
                updated_at
            )
            VALUES (
                :article_id,
                :document_label,
                :label_reason,
                :label_schema_version,
                :label_source,
                :teacher_model,
                :prompt_version,
                :labeling_run_id,
                CAST(:warnings AS JSONB),
                CAST(:model_info AS JSONB),
                CAST(:validation_warnings AS JSONB),
                CAST(:raw_label AS JSONB),
                NOW()
            )
            ON CONFLICT (article_id)
            DO UPDATE SET
                document_label = EXCLUDED.document_label,
                label_reason = EXCLUDED.label_reason,
                label_schema_version = EXCLUDED.label_schema_version,
                label_source = EXCLUDED.label_source,
                teacher_model = EXCLUDED.teacher_model,
                prompt_version = EXCLUDED.prompt_version,
                labeling_run_id = EXCLUDED.labeling_run_id,
                warnings = EXCLUDED.warnings,
                model_info = EXCLUDED.model_info,
                validation_warnings = EXCLUDED.validation_warnings,
                raw_label = EXCLUDED.raw_label,
                updated_at = NOW()
            """
        ),
        {
            "article_id": label["article_id"],
            "document_label": label["document_label"],
            "label_reason": label.get("label_reason") or "",
            "label_schema_version": record["label_schema_version"],
            "label_source": record["label_source"],
            "teacher_model": record["teacher_model"],
            "prompt_version": record["prompt_version"],
            "labeling_run_id": labeling_run_id,
            "warnings": json.dumps(label.get("warnings", []), ensure_ascii=False),
            "model_info": json.dumps(label.get("model_info", {}), ensure_ascii=False),
            "validation_warnings": json.dumps(validation_warnings, ensure_ascii=False),
            "raw_label": json.dumps(label, ensure_ascii=False),
        },
    )


def _insert_gold_event(
    connection: Any,
    sql: Any,
    record: JsonDict,
    label: JsonDict,
    event: JsonDict,
    labeling_run_id: str,
) -> None:
    connection.execute(
        sql(
            """
            INSERT INTO events_gold (
                event_id,
                article_id,
                ticker,
                company_name,
                event_type,
                event_subtype,
                event_summary,
                event_reason,
                event_arguments,
                impact_sentiment,
                evidence_span,
                source_url,
                published_at,
                confidence,
                label_schema_version,
                label_source,
                teacher_model,
                prompt_version,
                labeling_run_id,
                updated_at
            )
            VALUES (
                :event_id,
                :article_id,
                :ticker,
                :company_name,
                :event_type,
                :event_subtype,
                :event_summary,
                :event_reason,
                CAST(:event_arguments AS JSONB),
                :impact_sentiment,
                :evidence_span,
                :source_url,
                CAST(:published_at AS TIMESTAMPTZ),
                :confidence,
                :label_schema_version,
                :label_source,
                :teacher_model,
                :prompt_version,
                :labeling_run_id,
                NOW()
            )
            ON CONFLICT (event_id)
            DO UPDATE SET
                article_id = EXCLUDED.article_id,
                ticker = EXCLUDED.ticker,
                company_name = EXCLUDED.company_name,
                event_type = EXCLUDED.event_type,
                event_subtype = EXCLUDED.event_subtype,
                event_summary = EXCLUDED.event_summary,
                event_reason = EXCLUDED.event_reason,
                event_arguments = EXCLUDED.event_arguments,
                impact_sentiment = EXCLUDED.impact_sentiment,
                evidence_span = EXCLUDED.evidence_span,
                source_url = EXCLUDED.source_url,
                published_at = EXCLUDED.published_at,
                confidence = EXCLUDED.confidence,
                label_schema_version = EXCLUDED.label_schema_version,
                label_source = EXCLUDED.label_source,
                teacher_model = EXCLUDED.teacher_model,
                prompt_version = EXCLUDED.prompt_version,
                labeling_run_id = EXCLUDED.labeling_run_id,
                updated_at = NOW()
            """
        ),
        {
            "event_id": event["event_id"],
            "article_id": label["article_id"],
            "ticker": event.get("ticker"),
            "company_name": event.get("company_name"),
            "event_type": event["event_type"],
            "event_subtype": event.get("event_subtype"),
            "event_summary": event["event_summary"],
            "event_reason": event.get("event_reason") or "",
            "event_arguments": json.dumps(event.get("event_arguments", {}), ensure_ascii=False),
            "impact_sentiment": event["impact_sentiment"],
            "evidence_span": event["evidence_span"],
            "source_url": event["source_url"],
            "published_at": event.get("published_at"),
            "confidence": float(event["confidence"]),
            "label_schema_version": record["label_schema_version"],
            "label_source": record["label_source"],
            "teacher_model": record["teacher_model"],
            "prompt_version": record["prompt_version"],
            "labeling_run_id": labeling_run_id,
        },
    )


def _insert_rejection(connection: Any, sql: Any, record: JsonDict, labeling_run_id: str) -> None:
    connection.execute(
        sql(
            """
            INSERT INTO event_label_rejections (
                article_id,
                label_schema_version,
                teacher_model,
                prompt_version,
                labeling_run_id,
                validation_errors,
                raw_output
            )
            VALUES (
                :article_id,
                :label_schema_version,
                :teacher_model,
                :prompt_version,
                :labeling_run_id,
                CAST(:validation_errors AS JSONB),
                CAST(:raw_output AS JSONB)
            )
            """
        ),
        {
            "article_id": record.get("article_id"),
            "label_schema_version": record.get("label_schema_version") or "event_schema_v1",
            "teacher_model": record.get("teacher_model") or "unknown_teacher",
            "prompt_version": record.get("prompt_version") or "unknown_prompt",
            "labeling_run_id": labeling_run_id,
            "validation_errors": json.dumps(
                record.get("validation_errors", []),
                ensure_ascii=False,
            ),
            "raw_output": json.dumps(record.get("raw_output"), ensure_ascii=False),
        },
    )


def _infer_run_id(gold_records: list[JsonDict], rejected_records: list[JsonDict]) -> str:
    for record in [*gold_records, *rejected_records]:
        run_id = record.get("labeling_run_id")
        if run_id:
            return str(run_id)
    return create_run_id("event_label")


def _first_non_empty(
    gold_records: list[JsonDict],
    rejected_records: list[JsonDict],
    key: str,
) -> str | None:
    for record in [*gold_records, *rejected_records]:
        value = record.get(key)
        if value:
            return str(value)
    return None


def _sqlalchemy_text() -> Any:
    try:
        from sqlalchemy import text
    except ImportError as exc:
        raise RuntimeError(
            "SQLAlchemy is required for event label sync. Install the ingestion or api extra first."
        ) from exc
    return text
