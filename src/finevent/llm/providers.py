"""Provider factories for live LLM and OpenAI-compatible embedding runs.

Secrets are read from environment variables only. This module must never print
raw API keys; notebook and CLI callers should log `redacted_dict()`.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, cast


class MissingProviderConfigError(RuntimeError):
    """Raised when a required live-provider environment variable is missing."""


@dataclass(frozen=True)
class ProviderRuntimeConfig:
    teacher_api_key: str | None
    teacher_model: str | None
    teacher_base_url: str | None
    student_api_key: str | None
    student_model: str | None
    student_base_url: str | None
    embedding_api_key: str | None
    embedding_model: str | None
    embedding_base_url: str | None

    def redacted_dict(self) -> dict[str, str | None]:
        data = asdict(self)
        for key in list(data):
            if key.endswith("_api_key"):
                data[key] = redact_secret(data[key])
        return data


def load_provider_runtime_config() -> ProviderRuntimeConfig:
    """Load provider settings from environment variables.

    Supported aliases keep compatibility with earlier docs:
    `TEACHER_LLM_API_KEY` may be used instead of `OPENAI_API_KEY`, and
    `STUDENT_LLM_ENDPOINT` may be used instead of `STUDENT_LLM_BASE_URL`.
    """
    return ProviderRuntimeConfig(
        teacher_api_key=os.getenv("OPENAI_API_KEY") or os.getenv("TEACHER_LLM_API_KEY"),
        teacher_model=os.getenv("TEACHER_LLM_MODEL"),
        teacher_base_url=os.getenv("TEACHER_LLM_BASE_URL"),
        student_api_key=os.getenv("STUDENT_LLM_API_KEY"),
        student_model=os.getenv("STUDENT_LLM_MODEL"),
        student_base_url=os.getenv("STUDENT_LLM_BASE_URL") or os.getenv("STUDENT_LLM_ENDPOINT"),
        embedding_api_key=os.getenv("EMBEDDING_API_KEY") or os.getenv("STUDENT_LLM_API_KEY"),
        embedding_model=os.getenv("EMBEDDING_MODEL"),
        embedding_base_url=(
            os.getenv("EMBEDDING_BASE_URL")
            or os.getenv("STUDENT_LLM_BASE_URL")
            or os.getenv("STUDENT_LLM_ENDPOINT")
        ),
    )


def build_teacher_chat_model_from_env(**overrides: Any) -> object:
    config = load_provider_runtime_config()
    _require("OPENAI_API_KEY or TEACHER_LLM_API_KEY", config.teacher_api_key)
    _require("TEACHER_LLM_MODEL", config.teacher_model)
    return _build_chat_openai(
        api_key=_override_str(overrides, "api_key", config.teacher_api_key),
        model=_override_str(overrides, "model", config.teacher_model),
        base_url=_override_optional_str(overrides, "base_url", config.teacher_base_url),
        temperature=_override_float(overrides, "temperature", 0.0),
        timeout=_override_float(overrides, "timeout", 120.0),
    )


def build_student_chat_model_from_env(**overrides: Any) -> object:
    config = load_provider_runtime_config()
    _require("STUDENT_LLM_API_KEY", config.student_api_key)
    _require("STUDENT_LLM_MODEL", config.student_model)
    _require("STUDENT_LLM_BASE_URL", config.student_base_url)
    return _build_chat_openai(
        api_key=_override_str(overrides, "api_key", config.student_api_key),
        model=_override_str(overrides, "model", config.student_model),
        base_url=_override_optional_str(overrides, "base_url", config.student_base_url),
        temperature=_override_float(overrides, "temperature", 0.0),
        timeout=_override_float(overrides, "timeout", 120.0),
    )


def build_openai_compatible_embeddings_from_env(**overrides: Any) -> object:
    config = load_provider_runtime_config()
    _require("EMBEDDING_API_KEY or STUDENT_LLM_API_KEY", config.embedding_api_key)
    _require("EMBEDDING_MODEL", config.embedding_model)
    _require("EMBEDDING_BASE_URL or STUDENT_LLM_BASE_URL", config.embedding_base_url)
    try:
        from langchain_openai import OpenAIEmbeddings as OpenAIEmbeddingsClass
    except ImportError as exc:
        raise RuntimeError("Install the llm extra to use OpenAI-compatible embeddings.") from exc
    OpenAIEmbeddings = cast(Any, OpenAIEmbeddingsClass)
    return OpenAIEmbeddings(
        api_key=_override_str(overrides, "api_key", config.embedding_api_key),
        model=_override_str(overrides, "model", config.embedding_model),
        base_url=_override_optional_str(overrides, "base_url", config.embedding_base_url),
        timeout=_override_float(overrides, "timeout", 120.0),
    )


def redact_secret(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


def _build_chat_openai(
    *,
    api_key: str,
    model: str,
    base_url: object | None,
    temperature: float,
    timeout: float,
) -> object:
    try:
        from langchain_openai import ChatOpenAI as ChatOpenAIClass
    except ImportError as exc:
        raise RuntimeError("Install the llm extra to use LangChain OpenAI providers.") from exc
    ChatOpenAI = cast(Any, ChatOpenAIClass)
    kwargs: dict[str, Any] = {
        "api_key": api_key,
        "model": model,
        "temperature": temperature,
        "timeout": timeout,
    }
    if base_url:
        kwargs["base_url"] = str(base_url)
    return ChatOpenAI(**kwargs)


def _override_str(overrides: dict[str, Any], key: str, default: str | None) -> str:
    value = overrides.get(key)
    if value is None:
        value = default
    return str(value)


def _override_optional_str(
    overrides: dict[str, Any],
    key: str,
    default: str | None,
) -> str | None:
    value = overrides.get(key)
    if value is None:
        value = default
    return str(value) if value is not None else None


def _override_float(overrides: dict[str, Any], key: str, default: float) -> float:
    value = overrides.get(key)
    if value is None:
        value = default
    return float(value)


def _require(name: str, value: str | None) -> None:
    if not value:
        raise MissingProviderConfigError(f"Missing required provider setting: {name}")
