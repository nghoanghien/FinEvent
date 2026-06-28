"""Provider factories for live LLM and OpenAI-compatible embedding runs.

Secrets are read from environment variables only. This module must never print
raw API keys; notebook and CLI callers should log `redacted_dict()`.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any, cast

from finevent.paths import repo_root

DEFAULT_OPENAI_COMPATIBLE_USER_AGENT = "finevent-vn/0.1 langchain-openai-compatible"


class MissingProviderConfigError(RuntimeError):
    """Raised when a required live-provider environment variable is missing."""


@dataclass(frozen=True)
class ProviderRuntimeConfig:
    teacher_provider: str | None
    teacher_api_key: str | None
    teacher_model: str | None
    teacher_base_url: str | None
    student_provider: str | None
    student_api_key: str | None
    student_model: str | None
    student_base_url: str | None
    student_disable_thinking: bool
    student_max_tokens: int | None
    embedding_provider: str | None
    embedding_api_key: str | None
    embedding_model: str | None
    embedding_base_url: str | None
    embedding_batch_size: int
    openai_compatible_user_agent: str

    def redacted_dict(self) -> dict[str, object]:
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
    _load_dotenv_if_available()
    return ProviderRuntimeConfig(
        teacher_provider=os.getenv("TEACHER_LLM_PROVIDER") or "langchain_openai",
        teacher_api_key=os.getenv("OPENAI_API_KEY") or os.getenv("TEACHER_LLM_API_KEY"),
        teacher_model=os.getenv("TEACHER_LLM_MODEL"),
        teacher_base_url=os.getenv("TEACHER_LLM_BASE_URL"),
        student_provider=os.getenv("STUDENT_LLM_PROVIDER") or "langchain_openai",
        student_api_key=os.getenv("STUDENT_LLM_API_KEY"),
        student_model=os.getenv("STUDENT_LLM_MODEL"),
        student_base_url=os.getenv("STUDENT_LLM_BASE_URL") or os.getenv("STUDENT_LLM_ENDPOINT"),
        student_disable_thinking=_env_bool("STUDENT_LLM_DISABLE_THINKING", default=True),
        student_max_tokens=_env_optional_positive_int("STUDENT_LLM_MAX_TOKENS"),
        embedding_provider=os.getenv("EMBEDDING_PROVIDER") or "langchain_openai",
        embedding_api_key=os.getenv("EMBEDDING_API_KEY") or os.getenv("STUDENT_LLM_API_KEY"),
        embedding_model=os.getenv("EMBEDDING_MODEL"),
        embedding_base_url=(
            os.getenv("EMBEDDING_BASE_URL")
            or os.getenv("STUDENT_LLM_BASE_URL")
            or os.getenv("STUDENT_LLM_ENDPOINT")
        ),
        embedding_batch_size=_env_int("EMBEDDING_BATCH_SIZE", default=16),
        openai_compatible_user_agent=(
            os.getenv("OPENAI_COMPATIBLE_USER_AGENT") or DEFAULT_OPENAI_COMPATIBLE_USER_AGENT
        ),
    )


def build_teacher_chat_model_from_env(**overrides: Any) -> object:
    config = load_provider_runtime_config()
    _require("OPENAI_API_KEY or TEACHER_LLM_API_KEY", config.teacher_api_key)
    _require("TEACHER_LLM_MODEL", config.teacher_model)
    provider = str(overrides.get("provider") or config.teacher_provider or "langchain_openai")
    if provider not in {"langchain_openai", "openai"}:
        raise MissingProviderConfigError(
            "Teacher LLM currently supports TEACHER_LLM_PROVIDER=langchain_openai only."
        )
    return _build_chat_openai(
        api_key=_override_str(overrides, "api_key", config.teacher_api_key),
        model=_override_str(overrides, "model", config.teacher_model),
        base_url=_override_optional_str(overrides, "base_url", config.teacher_base_url),
        temperature=_override_float(overrides, "temperature", 0.0),
        timeout=_override_float(overrides, "timeout", 120.0),
        default_headers=_self_host_default_headers(
            base_url=_override_optional_str(overrides, "base_url", config.teacher_base_url),
            user_agent=config.openai_compatible_user_agent,
        ),
    )


def build_student_chat_model_from_env(**overrides: Any) -> object:
    config = load_provider_runtime_config()
    _require("STUDENT_LLM_API_KEY", config.student_api_key)
    _require("STUDENT_LLM_MODEL", config.student_model)
    _require("STUDENT_LLM_BASE_URL", config.student_base_url)
    provider = str(overrides.get("provider") or config.student_provider or "langchain_openai")
    if provider == "direct_http":
        return DirectHttpChatModel(
            api_key=_override_str(overrides, "api_key", config.student_api_key),
            model=_override_str(overrides, "model", config.student_model),
            base_url=_override_str(overrides, "base_url", config.student_base_url),
            temperature=_override_float(overrides, "temperature", 0.0),
            timeout=_override_float(overrides, "timeout", 120.0),
            max_tokens=_override_optional_positive_int(
                overrides,
                "max_tokens",
                config.student_max_tokens,
            ),
            disable_thinking=bool(
                overrides.get("disable_thinking", config.student_disable_thinking)
            ),
        )
    if provider not in {"langchain_openai", "openai_compatible"}:
        raise MissingProviderConfigError(f"Unsupported STUDENT_LLM_PROVIDER: {provider}")
    chat_model = _build_chat_openai(
        api_key=_override_str(overrides, "api_key", config.student_api_key),
        model=_override_str(overrides, "model", config.student_model),
        base_url=_override_optional_str(overrides, "base_url", config.student_base_url),
        temperature=_override_float(overrides, "temperature", 0.0),
        timeout=_override_float(overrides, "timeout", 120.0),
        max_completion_tokens=_override_optional_positive_int(
            overrides,
            "max_tokens",
            config.student_max_tokens,
        ),
        default_headers=_self_host_default_headers(
            base_url=_override_optional_str(overrides, "base_url", config.student_base_url),
            user_agent=config.openai_compatible_user_agent,
        ),
    )
    if bool(overrides.get("disable_thinking", config.student_disable_thinking)):
        return _with_no_think_prefix(chat_model)
    return chat_model


def build_openai_compatible_embeddings_from_env(**overrides: Any) -> object:
    config = load_provider_runtime_config()
    _require("EMBEDDING_API_KEY or STUDENT_LLM_API_KEY", config.embedding_api_key)
    _require("EMBEDDING_MODEL", config.embedding_model)
    _require("EMBEDDING_BASE_URL or STUDENT_LLM_BASE_URL", config.embedding_base_url)
    provider = str(overrides.get("provider") or config.embedding_provider or "langchain_openai")
    if provider == "direct_http":
        return DirectHttpEmbeddings(
            api_key=_override_str(overrides, "api_key", config.embedding_api_key),
            model=_override_str(overrides, "model", config.embedding_model),
            base_url=_override_str(overrides, "base_url", config.embedding_base_url),
            timeout=_override_float(overrides, "timeout", 120.0),
            batch_size=int(overrides.get("batch_size") or config.embedding_batch_size),
        )
    if provider not in {"langchain_openai", "openai_compatible"}:
        raise MissingProviderConfigError(f"Unsupported EMBEDDING_PROVIDER: {provider}")
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
        chunk_size=int(overrides.get("batch_size") or config.embedding_batch_size),
        default_headers=_self_host_default_headers(
            base_url=_override_optional_str(overrides, "base_url", config.embedding_base_url),
            user_agent=config.openai_compatible_user_agent,
        ),
        tiktoken_enabled=False,
        check_embedding_ctx_length=False,
    )


class DirectHttpChatResponse:
    """Small response object compatible with LangChain-style `.content` access."""

    def __init__(self, content: str, raw_response: dict[str, Any]):
        self.content = content
        self.raw_response = raw_response


class DirectHttpChatModel:
    """OpenAI-compatible chat client using direct HTTP.

    LangChain is the main provider path. This client remains useful as a
    low-level fallback for endpoint diagnostics or SDK compatibility regressions.
    It exposes `invoke(prompt)` so existing workflow code can use the same model
    interface when the fallback is selected explicitly.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        temperature: float = 0.0,
        timeout: float = 120.0,
        max_tokens: int | None = None,
        disable_thinking: bool = True,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.disable_thinking = disable_thinking

    def invoke(self, prompt: str) -> DirectHttpChatResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": self._prepare_prompt(prompt),
                }
            ],
            "temperature": self.temperature,
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        response_json = _post_openai_compatible_json(
            url=f"{self.base_url}/chat/completions",
            api_key=self.api_key,
            payload=payload,
            timeout=self.timeout,
        )
        content = _extract_chat_content(response_json)
        if not content:
            raise RuntimeError(
                "Direct HTTP chat response returned empty content. "
                "If the endpoint cut the output, set STUDENT_LLM_MAX_TOKENS explicitly "
                "or set STUDENT_LLM_DISABLE_THINKING=true."
            )
        return DirectHttpChatResponse(content=content, raw_response=response_json)

    def _prepare_prompt(self, prompt: str) -> str:
        if self.disable_thinking and not prompt.lstrip().startswith("/no_think"):
            return "/no_think\n" + prompt
        return prompt


class DirectHttpEmbeddings:
    """OpenAI-compatible embedding client using direct HTTP."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        timeout: float = 120.0,
        batch_size: int = 16,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.batch_size = batch_size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            response_json = _post_openai_compatible_json(
                url=f"{self.base_url}/embeddings",
                api_key=self.api_key,
                payload={"model": self.model, "input": batch},
                timeout=self.timeout,
            )
            vectors.extend(_extract_embedding_vectors(response_json))
        if len(vectors) != len(texts):
            raise RuntimeError(
                f"Embedding response count mismatch: expected {len(texts)}, got {len(vectors)}."
            )
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)


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
    max_completion_tokens: int | None = None,
    default_headers: dict[str, str] | None = None,
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
    if max_completion_tokens is not None:
        kwargs["max_completion_tokens"] = max_completion_tokens
    if default_headers:
        kwargs["default_headers"] = default_headers
    return ChatOpenAI(**kwargs)


def _self_host_default_headers(*, base_url: str | None, user_agent: str) -> dict[str, str] | None:
    """Return headers needed by OpenAI-compatible self-host endpoints.

    The lumentary self-host endpoint blocks the default OpenAI SDK user-agent
    (`OpenAI/Python ...`). Overriding only self-host requests keeps official
    OpenAI teacher calls on SDK defaults while allowing LangChain to be used for
    student and embedding models.
    """
    if not base_url:
        return None
    return {"User-Agent": user_agent}


def _with_no_think_prefix(chat_model: object) -> object:
    """Compose a LangChain runnable that prefixes Qwen prompts with `/no_think`."""
    try:
        from langchain_core.runnables import RunnableLambda
    except ImportError:
        return chat_model
    return RunnableLambda(_prepare_no_think_prompt) | cast(Any, chat_model)


def _prepare_no_think_prompt(prompt: object) -> object:
    if not isinstance(prompt, str):
        return prompt
    if prompt.lstrip().startswith("/no_think"):
        return prompt
    return "/no_think\n" + prompt


def _post_openai_compatible_json(
    *,
    url: str,
    api_key: str,
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Install requests to use direct HTTP LLM providers.") from exc

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if response.status_code == 400 and "max_tokens" in payload:
        retry_payload = dict(payload)
        retry_payload["max_completion_tokens"] = retry_payload.pop("max_tokens")
        response = requests.post(url, headers=headers, json=retry_payload, timeout=timeout)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = response.text[:600]
        raise RuntimeError(
            f"Provider request failed with HTTP {response.status_code}: {body}"
        ) from exc
    try:
        parsed = response.json()
    except json.JSONDecodeError as exc:
        raise RuntimeError("Provider response is not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Provider response JSON must be an object.")
    return parsed


def _extract_chat_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("text"):
                parts.append(str(part["text"]))
            elif isinstance(part, str):
                parts.append(part)
        joined = "\n".join(parts).strip()
        if joined:
            return joined
    reasoning = message.get("reasoning_content")
    return str(reasoning).strip() if reasoning else ""


def _extract_embedding_vectors(payload: dict[str, Any]) -> list[list[float]]:
    data = payload.get("data")
    if not isinstance(data, list):
        raise RuntimeError("Embedding response is missing a data array.")
    vectors: list[list[float]] = []
    for item in data:
        if not isinstance(item, dict) or "embedding" not in item:
            raise RuntimeError("Embedding response item is missing embedding.")
        vector = item["embedding"]
        if not isinstance(vector, list):
            raise RuntimeError("Embedding vector must be a list.")
        vectors.append([float(value) for value in vector])
    return vectors


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(repo_root() / ".env")


def _env_bool(name: str, *, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, *, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return int(value)


def _env_optional_positive_int(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


def _override_optional_positive_int(
    overrides: dict[str, Any],
    key: str,
    default: int | None,
) -> int | None:
    value = overrides.get(key)
    if value is None:
        value = default
    if value is None or str(value).strip() == "":
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


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
