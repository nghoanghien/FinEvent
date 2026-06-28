"""PostgreSQL sync helpers for event pattern records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from finevent.jsonl import read_jsonl
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class PatternSyncResult:
    pattern_count: int


def sync_pattern_artifacts(
    engine: Any,
    *,
    patterns_path: PathLike = "data/patterns/patterns.jsonl",
) -> PatternSyncResult:
    patterns = read_jsonl(patterns_path)
    sql = _sqlalchemy_text()

    with engine.begin() as connection:
        for pattern in patterns:
            _upsert_pattern(connection, sql, pattern)

    return PatternSyncResult(pattern_count=len(patterns))


def _upsert_pattern(connection: Any, sql: Any, pattern: JsonDict) -> None:
    connection.execute(
        sql(
            """
            INSERT INTO event_patterns (
                pattern_id,
                article_id,
                document_label,
                pattern_kind,
                event_id,
                event_type,
                event_subtype,
                ticker,
                company_name,
                impact_sentiment,
                input_excerpt,
                gold_output,
                pattern_text,
                evidence_span,
                event_arguments,
                explanation_brief,
                source,
                url,
                published_at,
                teacher_model,
                teacher_prompt_version,
                auto_validation_status,
                validation_errors,
                metadata,
                version,
                updated_at
            )
            VALUES (
                :pattern_id,
                :article_id,
                :document_label,
                :pattern_kind,
                :event_id,
                :event_type,
                :event_subtype,
                :ticker,
                :company_name,
                :impact_sentiment,
                :input_excerpt,
                CAST(:gold_output AS JSONB),
                :pattern_text,
                :evidence_span,
                CAST(:event_arguments AS JSONB),
                :explanation_brief,
                :source,
                :url,
                CAST(:published_at AS TIMESTAMPTZ),
                :teacher_model,
                :teacher_prompt_version,
                :auto_validation_status,
                CAST(:validation_errors AS JSONB),
                CAST(:metadata AS JSONB),
                :version,
                NOW()
            )
            ON CONFLICT (pattern_id)
            DO UPDATE SET
                article_id = EXCLUDED.article_id,
                document_label = EXCLUDED.document_label,
                pattern_kind = EXCLUDED.pattern_kind,
                event_id = EXCLUDED.event_id,
                event_type = EXCLUDED.event_type,
                event_subtype = EXCLUDED.event_subtype,
                ticker = EXCLUDED.ticker,
                company_name = EXCLUDED.company_name,
                impact_sentiment = EXCLUDED.impact_sentiment,
                input_excerpt = EXCLUDED.input_excerpt,
                gold_output = EXCLUDED.gold_output,
                pattern_text = EXCLUDED.pattern_text,
                evidence_span = EXCLUDED.evidence_span,
                event_arguments = EXCLUDED.event_arguments,
                explanation_brief = EXCLUDED.explanation_brief,
                source = EXCLUDED.source,
                url = EXCLUDED.url,
                published_at = EXCLUDED.published_at,
                teacher_model = EXCLUDED.teacher_model,
                teacher_prompt_version = EXCLUDED.teacher_prompt_version,
                auto_validation_status = EXCLUDED.auto_validation_status,
                validation_errors = EXCLUDED.validation_errors,
                metadata = EXCLUDED.metadata,
                version = EXCLUDED.version,
                updated_at = NOW()
            """
        ),
        {
            "pattern_id": pattern["pattern_id"],
            "article_id": pattern["article_id"],
            "document_label": pattern["document_label"],
            "pattern_kind": pattern["pattern_kind"],
            "event_id": pattern.get("event_id"),
            "event_type": pattern.get("event_type"),
            "event_subtype": pattern.get("event_subtype"),
            "ticker": pattern.get("ticker"),
            "company_name": pattern.get("company_name"),
            "impact_sentiment": pattern.get("impact_sentiment"),
            "input_excerpt": pattern["input_excerpt"],
            "gold_output": _json(pattern.get("gold_output", {})),
            "pattern_text": pattern["pattern_text"],
            "evidence_span": pattern.get("evidence_span"),
            "event_arguments": _json(pattern.get("event_arguments", {})),
            "explanation_brief": pattern.get("explanation_brief") or "",
            "source": pattern.get("source") or "",
            "url": pattern.get("url") or "",
            "published_at": pattern.get("published_at"),
            "teacher_model": pattern.get("teacher_model") or "unknown_teacher",
            "teacher_prompt_version": pattern.get("teacher_prompt_version") or "",
            "auto_validation_status": pattern.get("auto_validation_status") or "PASS",
            "validation_errors": _json(pattern.get("validation_errors", [])),
            "metadata": _json(pattern.get("metadata", {})),
            "version": pattern.get("version") or "m05_v1",
        },
    )

def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _sqlalchemy_text() -> Any:
    try:
        from sqlalchemy import text
    except ImportError as exc:
        raise RuntimeError("SQLAlchemy is required for PostgreSQL pattern sync.") from exc
    return text
