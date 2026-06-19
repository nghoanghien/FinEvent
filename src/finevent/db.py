"""Database helpers for optional PostgreSQL-backed workflows."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from finevent.config import load_config


@lru_cache(maxsize=1)
def get_database_url() -> str:
    return os.getenv("POSTGRES_DSN") or load_config().storage.postgres_dsn


@lru_cache(maxsize=1)
def get_sqlalchemy_engine() -> Any:
    try:
        from sqlalchemy import create_engine
    except ImportError as exc:
        raise RuntimeError(
            "SQLAlchemy is required for database-backed dictionary operations. "
            "Install the ingestion or api extra first."
        ) from exc
    return create_engine(get_database_url(), pool_pre_ping=True)
