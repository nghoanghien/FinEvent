"""Backward-compatible database helpers for optional PostgreSQL workflows."""

from __future__ import annotations

from typing import Any

from finevent.database.engine import (
    get_database_url as _get_database_url,
)
from finevent.database.engine import (
    get_sqlalchemy_engine as _get_sqlalchemy_engine,
)


def get_database_url() -> str:
    return _get_database_url()


def get_sqlalchemy_engine() -> Any:
    return _get_sqlalchemy_engine()
