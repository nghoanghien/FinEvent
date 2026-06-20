"""PostgreSQL sync helpers for extraction workflow runs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from finevent.extraction.workflow import build_public_result
from finevent.types import JsonDict


@dataclass(frozen=True)
class ExtractionRunSyncResult:
    run_id: str
    trace_count: int


def sync_extraction_state(engine: Any, state: object) -> ExtractionRunSyncResult:
    sql = _sqlalchemy_text()
    result = build_public_result(state)
    final_output = state.final_output or {}
    article_id = final_output.get("article_id")
    pattern_ids = [pattern.get("pattern_id") for pattern in state.selected_patterns]

    with engine.begin() as connection:
        connection.execute(
            sql(
                """
                INSERT INTO extraction_runs (
                    run_id,
                    article_id,
                    document_label,
                    workflow_config,
                    model_name,
                    prompt_version,
                    retrieval_config,
                    pattern_ids,
                    final_output,
                    validation_issues,
                    warnings,
                    errors,
                    run_dir,
                    completed_at
                )
                VALUES (
                    :run_id,
                    :article_id,
                    :document_label,
                    CAST(:workflow_config AS JSONB),
                    :model_name,
                    :prompt_version,
                    :retrieval_config,
                    CAST(:pattern_ids AS JSONB),
                    CAST(:final_output AS JSONB),
                    CAST(:validation_issues AS JSONB),
                    CAST(:warnings AS JSONB),
                    CAST(:errors AS JSONB),
                    :run_dir,
                    NOW()
                )
                ON CONFLICT (run_id)
                DO UPDATE SET
                    article_id = EXCLUDED.article_id,
                    document_label = EXCLUDED.document_label,
                    workflow_config = EXCLUDED.workflow_config,
                    model_name = EXCLUDED.model_name,
                    prompt_version = EXCLUDED.prompt_version,
                    retrieval_config = EXCLUDED.retrieval_config,
                    pattern_ids = EXCLUDED.pattern_ids,
                    final_output = EXCLUDED.final_output,
                    validation_issues = EXCLUDED.validation_issues,
                    warnings = EXCLUDED.warnings,
                    errors = EXCLUDED.errors,
                    run_dir = EXCLUDED.run_dir,
                    completed_at = NOW()
                """
            ),
            {
                "run_id": state.run_id,
                "article_id": article_id,
                "document_label": final_output.get("document_label"),
                "workflow_config": _json(state.config.to_dict()),
                "model_name": state.config.student_model,
                "prompt_version": state.config.prompt_version,
                "retrieval_config": state.config.retrieval_config,
                "pattern_ids": _json(pattern_ids),
                "final_output": _json(final_output),
                "validation_issues": _json(state.validation_issues),
                "warnings": _json(result.get("workflow_warnings", [])),
                "errors": _json(result.get("workflow_errors", [])),
                "run_dir": state.run_dir,
            },
        )
        connection.execute(
            sql("DELETE FROM extraction_node_traces WHERE run_id = :run_id"),
            {"run_id": state.run_id},
        )
        for trace in state.traces:
            _insert_trace(connection, sql, state.run_id, trace.to_dict())

    return ExtractionRunSyncResult(run_id=state.run_id, trace_count=len(state.traces))


def _insert_trace(connection: Any, sql: Any, run_id: str, trace: JsonDict) -> None:
    connection.execute(
        sql(
            """
            INSERT INTO extraction_node_traces (
                run_id,
                node,
                status,
                latency_ms,
                input_summary,
                output_summary,
                warnings,
                errors
            )
            VALUES (
                :run_id,
                :node,
                :status,
                :latency_ms,
                CAST(:input_summary AS JSONB),
                CAST(:output_summary AS JSONB),
                CAST(:warnings AS JSONB),
                CAST(:errors AS JSONB)
            )
            """
        ),
        {
            "run_id": run_id,
            "node": trace["node"],
            "status": trace["status"],
            "latency_ms": trace["latency_ms"],
            "input_summary": _json(trace.get("input_summary", {})),
            "output_summary": _json(trace.get("output_summary", {})),
            "warnings": _json(trace.get("warnings", [])),
            "errors": _json(trace.get("errors", [])),
        },
    )


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def _sqlalchemy_text() -> Any:
    try:
        from sqlalchemy import text
    except ImportError as exc:
        raise RuntimeError("SQLAlchemy is required for extraction run sync.") from exc
    return text
