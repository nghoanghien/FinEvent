"""Configuration helper functions for node builders."""

from __future__ import annotations

from typing import Any


def str_config(config: dict[str, Any], key: str, default: str) -> str:
    value = config.get(key)
    if value is None or value == "":
        return default
    return str(value)


def optional_str_config(config: dict[str, Any], key: str) -> str | None:
    value = config.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def int_config(config: dict[str, Any], key: str, default: int) -> int:
    value = config.get(key)
    if value is None or value == "":
        return default
    return int(value)


def float_config(config: dict[str, Any], key: str, default: float) -> float:
    value = config.get(key)
    if value is None or value == "":
        return default
    return float(value)


def bool_config(config: dict[str, Any], key: str, default: bool) -> bool:
    value = config.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def extend_optional_int(
    command: list[str],
    flag: str,
    config: dict[str, Any],
    key: str,
) -> None:
    value = config.get(key)
    if value is not None and value != "":
        command.extend([flag, str(int(value))])
