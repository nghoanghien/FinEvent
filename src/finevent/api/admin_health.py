"""Admin health endpoints."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from finevent.api.artifacts import get_workspace_root
from finevent.db import get_sqlalchemy_engine

router = APIRouter(prefix="/admin", tags=["admin-health"])


@router.get("/health")
def admin_health() -> dict[str, Any]:
    workspace_root = get_workspace_root()
    postgres_status, pgvector_status = _database_status()
    return {
        "api": "ok",
        "postgres": postgres_status,
        "pgvector": pgvector_status,
        "teacher_llm": _env_status("OPENAI_API_KEY", "TEACHER_LLM_API_KEY"),
        "student_llm": _env_status("STUDENT_LLM_API_KEY"),
        "embedding": _env_status("EMBEDDING_API_KEY", "STUDENT_LLM_API_KEY"),
        "artifacts": {
            "workspace_root": str(workspace_root),
            "data_dir": (workspace_root / "data").exists(),
            "reports_dir": (workspace_root / "reports").exists(),
            "runs_dir": (workspace_root / "runs").exists(),
        },
    }


def _database_status() -> tuple[str, str]:
    try:
        engine = get_sqlalchemy_engine()
        with engine.begin() as connection:
            connection.execute(text("SELECT 1"))
            has_vector = connection.execute(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            ).scalar()
    except Exception as exc:  # noqa: BLE001 - status endpoint must not crash.
        return f"error:{exc.__class__.__name__}", "unknown"
    return "ok", "ok" if has_vector else "missing"


def _env_status(*keys: str) -> str:
    return "configured" if any(os.getenv(key) for key in keys) else "unconfigured"
