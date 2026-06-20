"""Engine and session helpers for optional PostgreSQL workflows."""

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
            "SQLAlchemy is required for database-backed workflows. "
            "Install the db, ingestion, api, or rag extra first."
        ) from exc
    return create_engine(get_database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_sessionmaker() -> Any:
    try:
        from sqlalchemy.orm import sessionmaker
    except ImportError as exc:
        raise RuntimeError(
            "SQLAlchemy is required for ORM sessions. Install the db extra first."
        ) from exc
    return sessionmaker(bind=get_sqlalchemy_engine(), autoflush=False, expire_on_commit=False)
