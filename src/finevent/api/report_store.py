"""Database-backed workflow report registry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from finevent.api.artifacts import artifact_kind, get_workspace_root

MAX_REPORT_SNAPSHOT_BYTES = 2_000_000
TEXT_REPORT_SUFFIXES = {".csv", ".json", ".jsonl", ".log", ".md", ".txt"}
JSON_REPORT_SUFFIXES = {".json"}


def register_workflow_reports(
    engine: Any,
    *,
    run_id: str,
    workflow_name: str,
    step_id: str,
    artifact_paths: list[str],
) -> int:
    reports = [_report_payload(run_id, workflow_name, step_id, path) for path in artifact_paths]
    reports = [report for report in reports if report is not None]
    if not reports:
        return 0
    sql = _sqlalchemy_text()
    with engine.begin() as connection:
        for report in reports:
            connection.execute(
                sql(
                    """
                    INSERT INTO workflow_reports (
                        report_id,
                        run_id,
                        workflow_name,
                        step_id,
                        path,
                        name,
                        kind,
                        size_bytes,
                        content_text,
                        content_json,
                        content_truncated,
                        metadata,
                        updated_at
                    )
                    VALUES (
                        :report_id,
                        :run_id,
                        :workflow_name,
                        :step_id,
                        :path,
                        :name,
                        :kind,
                        :size_bytes,
                        :content_text,
                        CAST(:content_json AS JSONB),
                        :content_truncated,
                        CAST(:metadata AS JSONB),
                        NOW()
                    )
                    ON CONFLICT (report_id)
                    DO UPDATE SET
                        workflow_name = EXCLUDED.workflow_name,
                        step_id = EXCLUDED.step_id,
                        path = EXCLUDED.path,
                        name = EXCLUDED.name,
                        kind = EXCLUDED.kind,
                        size_bytes = EXCLUDED.size_bytes,
                        content_text = EXCLUDED.content_text,
                        content_json = EXCLUDED.content_json,
                        content_truncated = EXCLUDED.content_truncated,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """
                ),
                report,
            )
    return len(reports)


def list_workflow_reports(engine: Any, *, kind: str | None = None) -> list[dict[str, Any]]:
    sql = _sqlalchemy_text()
    query = """
        SELECT
            report_id,
            run_id,
            workflow_name,
            step_id,
            path,
            name,
            kind,
            size_bytes,
            content_truncated,
            metadata,
            updated_at
        FROM workflow_reports
    """
    params: dict[str, Any] = {}
    if kind:
        query += " WHERE kind = :kind"
        params["kind"] = kind
    query += " ORDER BY updated_at DESC"
    with engine.begin() as connection:
        rows = connection.execute(sql(query), params).mappings().all()
    return [
        {
            **dict(row),
            "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
            "source": "database",
        }
        for row in rows
    ]


def _report_payload(
    run_id: str,
    workflow_name: str,
    step_id: str,
    path: str,
) -> dict[str, Any] | None:
    if not path.startswith("reports/"):
        return None
    report_path = _resolve_report_path(path)
    if report_path is None or not report_path.is_file():
        return None
    stat = report_path.stat()
    content_text, content_json, truncated = _read_report_snapshot(report_path)
    return {
        "report_id": _report_id(run_id, step_id, path),
        "run_id": run_id,
        "workflow_name": workflow_name,
        "step_id": step_id,
        "path": path,
        "name": report_path.name,
        "kind": artifact_kind(report_path),
        "size_bytes": stat.st_size,
        "content_text": content_text,
        "content_json": json.dumps(content_json, ensure_ascii=False),
        "content_truncated": truncated,
        "metadata": json.dumps({"source": "admin_workflow_runner"}, ensure_ascii=False),
    }


def _resolve_report_path(path: str) -> Path | None:
    raw_path = Path(path)
    if raw_path.is_absolute() or not raw_path.parts or raw_path.parts[0] != "reports":
        return None
    workspace_root = get_workspace_root().resolve()
    resolved = (workspace_root / raw_path).resolve()
    if not resolved.is_relative_to(workspace_root):
        return None
    return resolved


def _read_report_snapshot(path: Path) -> tuple[str | None, object | None, bool]:
    suffix = path.suffix.lower()
    if suffix not in TEXT_REPORT_SUFFIXES:
        return None, None, False
    size = path.stat().st_size
    truncated = size > MAX_REPORT_SNAPSHOT_BYTES
    with path.open("rb") as file:
        raw = file.read(MAX_REPORT_SNAPSHOT_BYTES + 1)
    if len(raw) > MAX_REPORT_SNAPSHOT_BYTES:
        raw = raw[:MAX_REPORT_SNAPSHOT_BYTES]
        truncated = True
    text = raw.decode("utf-8", errors="replace")
    if suffix in JSON_REPORT_SUFFIXES and not truncated:
        try:
            return None, json.loads(text), False
        except json.JSONDecodeError:
            return text, None, False
    return text, None, truncated


def _report_id(run_id: str, step_id: str, path: str) -> str:
    digest = hashlib.sha1(f"{run_id}:{step_id}:{path}".encode()).hexdigest()
    return f"workflow_report_{digest[:20]}"


def _sqlalchemy_text() -> Any:
    try:
        from sqlalchemy import text
    except ImportError as exc:
        raise RuntimeError("SQLAlchemy is required for workflow report storage.") from exc
    return text
