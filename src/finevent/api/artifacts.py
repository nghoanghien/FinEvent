"""Safe filesystem artifact access for admin APIs."""

from __future__ import annotations

import csv
import json
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from finevent.api.errors import api_error
from finevent.api.serialization import to_jsonable

ALLOWED_TOP_LEVEL_DIRS = {"data", "reports", "runs"}
TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".log", ".md", ".svg", ".txt"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
REPORT_SUFFIXES = TEXT_SUFFIXES | IMAGE_SUFFIXES | {".pdf"}


@dataclass(frozen=True)
class ArtifactInfo:
    path: str
    name: str
    kind: str
    size_bytes: int
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(
            {
                "path": self.path,
                "name": self.name,
                "kind": self.kind,
                "size_bytes": self.size_bytes,
                "updated_at": self.updated_at,
            }
        )


def get_workspace_root() -> Path:
    return Path(os.getenv("FINEVENT_WORKSPACE_ROOT") or Path.cwd()).resolve()


def resolve_artifact_path(
    path: str,
    *,
    must_exist: bool = True,
    allowed_top_level_dirs: set[str] | None = None,
) -> Path:
    allowed_roots = allowed_top_level_dirs or ALLOWED_TOP_LEVEL_DIRS
    if not path or not path.strip():
        raise api_error(422, "EMPTY_PATH", "Artifact path is required.")
    raw_path = Path(path)
    if raw_path.is_absolute():
        raise api_error(
            403,
            "ABSOLUTE_PATH_NOT_ALLOWED",
            "Artifact path must be relative to the workspace root.",
            details={"path": path},
        )
    if raw_path.parts and raw_path.parts[0] not in allowed_roots:
        raise api_error(
            403,
            "ARTIFACT_ROOT_NOT_ALLOWED",
            "Artifact path must be inside data/, reports/, or runs/.",
            details={"path": path, "allowed_roots": sorted(allowed_roots)},
        )
    workspace_root = get_workspace_root()
    resolved = (workspace_root / raw_path).resolve()
    if not resolved.is_relative_to(workspace_root):
        raise api_error(
            403,
            "PATH_TRAVERSAL_BLOCKED",
            "Artifact path cannot escape the workspace root.",
            details={"path": path},
        )
    resolved_relative = resolved.relative_to(workspace_root)
    if not resolved_relative.parts or resolved_relative.parts[0] not in allowed_roots:
        raise api_error(
            403,
            "ARTIFACT_ROOT_NOT_ALLOWED",
            "Artifact path must resolve inside data/, reports/, or runs/.",
            details={"path": path, "allowed_roots": sorted(allowed_roots)},
        )
    if must_exist and not resolved.exists():
        raise api_error(
            404,
            "ARTIFACT_NOT_FOUND",
            "Artifact path does not exist.",
            details={"path": path},
        )
    return resolved


def artifact_relative_path(path: Path) -> str:
    return path.resolve().relative_to(get_workspace_root()).as_posix()


def artifact_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "markdown"
    if suffix == ".csv":
        return "csv"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix == ".json":
        return "json"
    if suffix == ".svg":
        return "svg"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".log", ".txt"}:
        return "text"
    return "binary"


def media_type_for_path(path: Path) -> str:
    if path.suffix.lower() == ".svg":
        return "image/svg+xml"
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def list_report_artifacts() -> list[ArtifactInfo]:
    reports_root = resolve_artifact_path("reports", must_exist=False)
    if not reports_root.exists():
        return []
    artifacts: list[ArtifactInfo] = []
    for path in sorted(reports_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in REPORT_SUFFIXES:
            continue
        stat = path.stat()
        artifacts.append(
            ArtifactInfo(
                path=artifact_relative_path(path),
                name=path.name,
                kind=artifact_kind(path),
                size_bytes=stat.st_size,
                updated_at=_timestamp(path.stat().st_mtime),
            )
        )
    return artifacts


def read_text_artifact(path: str, *, max_bytes: int = 2_000_000) -> dict[str, Any]:
    artifact_path = resolve_artifact_path(path)
    if artifact_path.suffix.lower() not in TEXT_SUFFIXES:
        raise api_error(
            415,
            "UNSUPPORTED_TEXT_ARTIFACT",
            "This artifact is not a supported text artifact.",
            details={"path": path},
        )
    if artifact_path.stat().st_size > max_bytes:
        raise api_error(
            413,
            "ARTIFACT_TOO_LARGE",
            "Text artifact is too large for inline response.",
            details={"path": path, "max_bytes": max_bytes},
        )
    return {
        "path": artifact_relative_path(artifact_path),
        "kind": artifact_kind(artifact_path),
        "content": artifact_path.read_text(encoding="utf-8"),
    }


def read_csv_artifact(path: str, *, limit: int, offset: int) -> dict[str, Any]:
    artifact_path = resolve_artifact_path(path)
    if artifact_path.suffix.lower() != ".csv":
        raise api_error(415, "NOT_CSV", "Artifact is not a CSV file.", details={"path": path})
    with artifact_path.open("r", encoding="utf-8", newline="") as file:
        rows = [dict(row) for row in csv.DictReader(file)]
    page = rows[offset : offset + limit]
    columns = list(rows[0].keys()) if rows else []
    return {
        "path": artifact_relative_path(artifact_path),
        "columns": columns,
        "rows": page,
        "limit": limit,
        "offset": offset,
        "total": len(rows),
    }


def read_jsonl_artifact(path: str, *, limit: int, offset: int) -> dict[str, Any]:
    artifact_path = resolve_artifact_path(path)
    if artifact_path.suffix.lower() != ".jsonl":
        raise api_error(415, "NOT_JSONL", "Artifact is not a JSONL file.", details={"path": path})
    rows: list[dict[str, Any]] = []
    parse_errors: list[dict[str, Any]] = []
    with artifact_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                loaded = json.loads(stripped)
            except json.JSONDecodeError as exc:
                parse_errors.append({"line_number": line_number, "error": str(exc)})
                continue
            if isinstance(loaded, dict):
                rows.append(loaded)
            else:
                rows.append({"value": loaded})
    return {
        "path": artifact_relative_path(artifact_path),
        "rows": rows[offset : offset + limit],
        "limit": limit,
        "offset": offset,
        "total": len(rows),
        "parse_errors": parse_errors,
    }


def load_json_file(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise api_error(
            422,
            "INVALID_JSON_ARTIFACT",
            "JSON artifact cannot be parsed.",
            details={"path": artifact_relative_path(path), "error": str(exc)},
        ) from exc
    if not isinstance(loaded, dict):
        return {"value": loaded}
    return loaded


def _timestamp(epoch_seconds: float) -> str:
    from datetime import UTC, datetime

    return datetime.fromtimestamp(epoch_seconds, tz=UTC).isoformat()
