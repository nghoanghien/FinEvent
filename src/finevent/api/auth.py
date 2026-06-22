"""Admin API authentication middleware helpers."""

from __future__ import annotations

import hmac
import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse, Response

ADMIN_API_KEY_HEADER = "X-Admin-API-Key"
TRUTHY = {"1", "true", "yes", "on"}
DOTENV_LOADED = False


async def admin_auth_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if not request.url.path.startswith("/admin") or request.method == "OPTIONS":
        return await call_next(request)
    auth_error = validate_admin_request(request)
    if auth_error is not None:
        return auth_error
    return await call_next(request)


def validate_admin_request(request: Request) -> JSONResponse | None:
    _load_dotenv_once()
    if _admin_auth_disabled():
        return None
    expected_key = os.getenv("FINEVENT_ADMIN_API_KEY")
    if not expected_key:
        return _error_response(
            503,
            "ADMIN_AUTH_NOT_CONFIGURED",
            "Admin API key is required. Set FINEVENT_ADMIN_API_KEY or explicitly set "
            "FINEVENT_ADMIN_AUTH_DISABLED=true for local-only development.",
        )
    provided_key = request.headers.get(ADMIN_API_KEY_HEADER, "")
    if not provided_key or not hmac.compare_digest(provided_key, expected_key):
        return _error_response(
            401,
            "ADMIN_AUTH_REQUIRED",
            f"Admin API requires a valid {ADMIN_API_KEY_HEADER} header.",
        )
    return None


def _admin_auth_disabled() -> bool:
    return os.getenv("FINEVENT_ADMIN_AUTH_DISABLED", "").strip().lower() in TRUTHY


def _load_dotenv_once() -> None:
    global DOTENV_LOADED
    if DOTENV_LOADED:
        return
    DOTENV_LOADED = True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    workspace_root = Path(os.getenv("FINEVENT_WORKSPACE_ROOT") or Path.cwd())
    load_dotenv(workspace_root / ".env")


def _error_response(status_code: int, error_code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error_code": error_code, "message": message, "details": {}},
    )
