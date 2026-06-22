"""CORS configuration for the admin API."""

from __future__ import annotations

import os


def get_allowed_origins() -> list[str]:
    raw_value = os.getenv(
        "FINEVENT_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    return origins
