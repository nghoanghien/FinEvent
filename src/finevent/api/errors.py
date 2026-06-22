"""Shared API error helpers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def api_error(
    status_code: int,
    error_code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": error_code,
            "message": message,
            "details": details or {},
        },
    )
