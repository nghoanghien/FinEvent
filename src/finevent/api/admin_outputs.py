"""Admin structured extraction output endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from finevent.api.artifacts import (
    artifact_relative_path,
    get_workspace_root,
    load_json_file,
    resolve_artifact_path,
)
from finevent.api.errors import api_error
from finevent.api.serialization import to_jsonable
from finevent.database import schema
from finevent.db import get_sqlalchemy_engine

router = APIRouter(prefix="/admin/outputs", tags=["admin-outputs"])


@router.get("")
def list_outputs(
    article_id: str | None = Query(default=None),
    source: str = Query(default="auto", pattern="^(auto|postgres|filesystem)$"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    db_items = (
        _list_outputs_from_db(article_id=article_id, limit=limit, offset=offset)
        if source in {"auto", "postgres"}
        else None
    )
    if db_items is not None:
        return db_items
    if source == "postgres":
        raise api_error(
            503,
            "DATABASE_OUTPUTS_UNAVAILABLE",
            "PostgreSQL extraction outputs are unavailable.",
        )
    items = _list_output_files(article_id=article_id)
    return {
        "source": "filesystem",
        "items": items[offset : offset + limit],
        "limit": limit,
        "offset": offset,
        "total": len(items),
    }


@router.get("/{run_id}")
def get_output(run_id: str) -> dict[str, Any]:
    db_output = _get_output_from_db(run_id)
    if db_output is not None:
        return db_output
    result_path = _result_path_for_run_id(run_id)
    if result_path is None:
        raise api_error(
            404,
            "OUTPUT_NOT_FOUND",
            "Extraction output does not exist.",
            details={"run_id": run_id},
        )
    return {
        "source": "filesystem",
        "path": artifact_relative_path(result_path),
        "output": load_json_file(result_path),
    }


@router.get("/by-article/{article_id}")
def get_output_by_article(article_id: str) -> dict[str, Any]:
    db_run_id = _latest_db_run_id_for_article(article_id)
    if db_run_id:
        return get_output(db_run_id)
    matches = _list_output_files(article_id=article_id)
    if not matches:
        raise api_error(
            404,
            "OUTPUT_NOT_FOUND",
            "No extraction output exists for this article.",
            details={"article_id": article_id},
        )
    return get_output(str(matches[0]["run_id"]))


def _list_outputs_from_db(
    *,
    article_id: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any] | None:
    statement = select(
        schema.extraction_runs.c.run_id,
        schema.extraction_runs.c.article_id,
        schema.extraction_runs.c.document_label,
        schema.extraction_runs.c.model_name,
        schema.extraction_runs.c.retrieval_config,
        schema.extraction_runs.c.run_dir,
        schema.extraction_runs.c.created_at,
        schema.extraction_runs.c.completed_at,
    )
    count_statement = select(func.count()).select_from(schema.extraction_runs)
    if article_id:
        statement = statement.where(schema.extraction_runs.c.article_id == article_id)
        count_statement = count_statement.where(schema.extraction_runs.c.article_id == article_id)
    statement = (
        statement.order_by(schema.extraction_runs.c.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    try:
        with get_sqlalchemy_engine().begin() as connection:
            total = int(connection.execute(count_statement).scalar() or 0)
            rows = [dict(row) for row in connection.execute(statement).mappings().all()]
    except Exception:  # noqa: BLE001 - filesystem outputs remain valid without DB.
        return None
    return {
        "source": "postgres",
        "items": to_jsonable(rows),
        "limit": limit,
        "offset": offset,
        "total": total,
    }


def _get_output_from_db(run_id: str) -> dict[str, Any] | None:
    run_statement = select(schema.extraction_runs).where(schema.extraction_runs.c.run_id == run_id)
    trace_statement = (
        select(schema.extraction_node_traces)
        .where(schema.extraction_node_traces.c.run_id == run_id)
        .order_by(schema.extraction_node_traces.c.trace_id.asc())
    )
    try:
        with get_sqlalchemy_engine().begin() as connection:
            run_row = connection.execute(run_statement).mappings().first()
            if run_row is None:
                return None
            trace_rows = [dict(row) for row in connection.execute(trace_statement).mappings().all()]
    except Exception:  # noqa: BLE001 - filesystem output remains valid without DB.
        return None
    run = dict(run_row)
    return {
        "source": "postgres",
        "run_id": run_id,
        "article_id": run.get("article_id"),
        "prediction": run.get("final_output") or {},
        "draft_output": run.get("draft_output") or {},
        "validation_issues": run.get("validation_issues") or [],
        "verification_report": run.get("verification_report") or {},
        "hallucination_metrics": run.get("hallucination_metrics") or {},
        "node_traces": to_jsonable(trace_rows),
        "run": to_jsonable(run),
    }


def _latest_db_run_id_for_article(article_id: str) -> str | None:
    statement = (
        select(schema.extraction_runs.c.run_id)
        .where(schema.extraction_runs.c.article_id == article_id)
        .order_by(schema.extraction_runs.c.created_at.desc())
        .limit(1)
    )
    try:
        with get_sqlalchemy_engine().begin() as connection:
            value = connection.execute(statement).scalar()
    except Exception:  # noqa: BLE001 - filesystem output remains valid without DB.
        return None
    return str(value) if value else None


def _list_output_files(*, article_id: str | None) -> list[dict[str, Any]]:
    runs_root = resolve_artifact_path("runs/extraction", must_exist=False)
    if not runs_root.exists():
        return []
    items: list[dict[str, Any]] = []
    for result_path in sorted(runs_root.glob("*/result.json"), reverse=True):
        payload = load_json_file(result_path)
        if article_id and str(payload.get("article_id") or "") != article_id:
            continue
        run_dir = result_path.parent
        stat = result_path.stat()
        items.append(
            {
                "run_id": run_dir.name,
                "article_id": payload.get("article_id"),
                "document_label": payload.get("document_label"),
                "event_count": len(payload.get("events") or []),
                "path": artifact_relative_path(result_path),
                "run_dir": artifact_relative_path(run_dir),
                "updated_at": stat.st_mtime,
            }
        )
    return to_jsonable(items)


def _result_path_for_run_id(run_id: str) -> Path | None:
    safe_root = get_workspace_root() / "runs" / "extraction"
    candidate = (safe_root / run_id / "result.json").resolve()
    if candidate.exists() and candidate.is_relative_to(safe_root.resolve()):
        return candidate
    return None
