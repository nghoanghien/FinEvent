"""PostgreSQL sync helpers for online retrieval runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from finevent.jsonl import read_jsonl
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class RetrievalRunSyncResult:
    run_count: int
    context_count: int


def sync_retrieval_runs_jsonl(
    engine: Any,
    *,
    retrieval_results_path: PathLike = "data/retrieval/online_contexts.jsonl",
) -> RetrievalRunSyncResult:
    records = read_jsonl(retrieval_results_path)
    sql = _sqlalchemy_text()
    context_count = 0
    with engine.begin() as connection:
        for record in records:
            if not isinstance(record, dict):
                continue
            retrieval_run_id = str(record.get("retrieval_run_id") or "")
            if not retrieval_run_id:
                continue
            contexts = [
                context for context in record.get("contexts", []) if isinstance(context, dict)
            ]
            _upsert_run(connection, sql, record, retrieval_results_path)
            connection.execute(
                sql("DELETE FROM retrieval_run_contexts WHERE retrieval_run_id = :run_id"),
                {"run_id": retrieval_run_id},
            )
            for context in contexts:
                _insert_context(connection, sql, retrieval_run_id, context)
                context_count += 1
    return RetrievalRunSyncResult(run_count=len(records), context_count=context_count)


def _upsert_run(
    connection: Any,
    sql: Any,
    record: JsonDict,
    retrieval_results_path: PathLike,
) -> None:
    connection.execute(
        sql(
            """
            INSERT INTO retrieval_runs (
                retrieval_run_id,
                article_id,
                retrieval_config,
                query_plan,
                metrics,
                warnings,
                source_path,
                output_path
            )
            VALUES (
                :retrieval_run_id,
                :article_id,
                :retrieval_config,
                CAST(:query_plan AS JSONB),
                CAST(:metrics AS JSONB),
                CAST(:warnings AS JSONB),
                :source_path,
                :output_path
            )
            ON CONFLICT (retrieval_run_id)
            DO UPDATE SET
                article_id = EXCLUDED.article_id,
                retrieval_config = EXCLUDED.retrieval_config,
                query_plan = EXCLUDED.query_plan,
                metrics = EXCLUDED.metrics,
                warnings = EXCLUDED.warnings,
                source_path = EXCLUDED.source_path,
                output_path = EXCLUDED.output_path
            """
        ),
        {
            "retrieval_run_id": record["retrieval_run_id"],
            "article_id": record.get("article_id"),
            "retrieval_config": record.get("retrieval_config") or "unknown",
            "query_plan": _json(record.get("queries", [])),
            "metrics": _json(record.get("metrics", [])),
            "warnings": _json(record.get("warnings", [])),
            "source_path": str(Path(retrieval_results_path)),
            "output_path": str(Path(retrieval_results_path)),
        },
    )


def _insert_context(
    connection: Any,
    sql: Any,
    retrieval_run_id: str,
    context: JsonDict,
) -> None:
        raw_metadata = context.get("metadata")
        metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
        connection.execute(
        sql(
            """
            INSERT INTO retrieval_run_contexts (
                retrieval_run_id,
                rank,
                chunk_id,
                article_id,
                score,
                score_breakdown,
                context,
                pattern_refs
            )
            VALUES (
                :retrieval_run_id,
                :rank,
                :chunk_id,
                :article_id,
                :score,
                CAST(:score_breakdown AS JSONB),
                CAST(:context AS JSONB),
                CAST(:pattern_refs AS JSONB)
            )
            """
        ),
        {
            "retrieval_run_id": retrieval_run_id,
            "rank": int(context.get("rank") or 0),
            "chunk_id": str(context.get("chunk_id") or ""),
            "article_id": str(context.get("article_id") or ""),
            "score": float(context.get("score") or 0.0),
            "score_breakdown": _json(context.get("score_breakdown", {})),
            "context": _json(context),
            "pattern_refs": _json(metadata.get("pattern_refs", [])),
        },
    )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _sqlalchemy_text() -> Any:
    try:
        from sqlalchemy import text
    except ImportError as exc:
        raise RuntimeError("SQLAlchemy is required for retrieval run sync.") from exc
    return text
