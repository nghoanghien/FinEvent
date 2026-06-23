from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from finevent.jsonl import read_jsonl, write_jsonl
from finevent.labeling.teacher_llm import run_teacher_llm_on_prompts
from finevent.llm import (
    DirectHttpChatModel,
    DirectHttpEmbeddings,
    build_openai_compatible_embeddings_from_env,
    build_student_chat_model_from_env,
    build_teacher_chat_model_from_env,
    load_provider_runtime_config,
    redact_secret,
)
from finevent.llm.providers import (
    DEFAULT_OPENAI_COMPATIBLE_USER_AGENT,
    _with_no_think_prefix,
)
from finevent.rag.embeddings import LangChainEmbeddingClient


class FakeResponse:
    def __init__(self, content: object):
        self.content = content


class FakeChatModel:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> FakeResponse:
        self.prompts.append(prompt)
        return FakeResponse({"document_label": "NO_EVENT", "events": []})


class FakeEmbeddingModel:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(index), 1.0] for index, _ in enumerate(texts)]


class FakeHttpResponse:
    def __init__(self, payload: dict, status_code: int = 200, text: str = "ok") -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError("fixture http error")

    def json(self) -> dict:
        return self._payload


def test_provider_config_redacts_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "teacher-test-1234567890")
    monkeypatch.setenv("TEACHER_LLM_MODEL", "teacher-test")
    monkeypatch.setenv("STUDENT_LLM_PROVIDER", "")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "")

    config = load_provider_runtime_config()

    assert config.teacher_model == "teacher-test"
    assert config.student_provider == "langchain_openai"
    assert config.embedding_provider == "langchain_openai"
    assert redact_secret("teacher-test-1234567890") == "teac...7890"
    assert config.redacted_dict()["teacher_api_key"] == "teac...7890"


def test_teacher_llm_runner_writes_raw_outputs(tmp_path: Path) -> None:
    prompts_path = tmp_path / "teacher_prompts.jsonl"
    output_path = tmp_path / "teacher_outputs.jsonl"
    write_jsonl(
        prompts_path,
        [
            {
                "article_id": "article_001",
                "prompt_version": "fixture_prompt",
                "prompt": "Return JSON.",
            }
        ],
    )
    model = FakeChatModel()

    result = run_teacher_llm_on_prompts(
        prompt_path=prompts_path,
        output_path=output_path,
        teacher_model=model,
        teacher_model_name="fake_teacher",
        run_id="teacher_fixture",
    )
    records = read_jsonl(output_path)

    assert result.success_count == 1
    assert result.error_count == 0
    assert model.prompts == ["Return JSON."]
    assert records[0]["teacher_model"] == "fake_teacher"
    assert json.loads(records[0]["raw_output"])["document_label"] == "NO_EVENT"


def test_langchain_embedding_client_adapts_embed_documents() -> None:
    client = LangChainEmbeddingClient(
        embedding_model=FakeEmbeddingModel(),
        model_name="fake_embedding",
    )

    assert client.embed_texts(["a", "b"]) == [[0.0, 1.0], [1.0, 1.0]]


def test_direct_http_chat_model_invokes_openai_compatible_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict] = []

    def fake_post(url: str, headers: dict, json: dict, timeout: float) -> FakeHttpResponse:
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeHttpResponse({"choices": [{"message": {"content": '{"ok": true}'}}]})

    import requests

    monkeypatch.setattr(requests, "post", fake_post)
    model = DirectHttpChatModel(
        api_key="student-key",
        model="qwen/qwen3-8b",
        base_url="https://example.local/v1",
        max_tokens=64,
        disable_thinking=True,
    )

    response = model.invoke("Return JSON.")

    assert response.content == '{"ok": true}'
    assert calls[0]["url"] == "https://example.local/v1/chat/completions"
    assert calls[0]["json"]["messages"][0]["content"].startswith("/no_think")
    assert calls[0]["json"]["max_tokens"] == 64


def test_direct_http_embeddings_parse_vectors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, headers: dict, json: dict, timeout: float) -> FakeHttpResponse:
        assert url == "https://example.local/v1/embeddings"
        assert json["input"] == ["a", "b"]
        return FakeHttpResponse(
            {
                "data": [
                    {"embedding": [0.1, 0.2]},
                    {"embedding": [0.3, 0.4]},
                ]
            }
        )

    import requests

    monkeypatch.setattr(requests, "post", fake_post)
    embeddings = DirectHttpEmbeddings(
        api_key="embedding-key",
        model="embedding-model",
        base_url="https://example.local/v1",
    )

    assert embeddings.embed_documents(["a", "b"]) == [[0.1, 0.2], [0.3, 0.4]]


def test_langchain_provider_builders_accept_openai_compatible_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "teacher-key")
    monkeypatch.setenv("TEACHER_LLM_MODEL", "teacher-model")
    monkeypatch.setenv("STUDENT_LLM_API_KEY", "student-key")
    monkeypatch.setenv("STUDENT_LLM_MODEL", "qwen/qwen3-8b")
    monkeypatch.setenv("STUDENT_LLM_ENDPOINT", "https://example.local/v1")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-qwen3-embedding-0.6b")

    teacher = build_teacher_chat_model_from_env()
    student = build_student_chat_model_from_env()
    embeddings = build_openai_compatible_embeddings_from_env()

    assert teacher is not None
    assert student is not None
    assert embeddings is not None


def test_langchain_student_builder_sets_self_host_headers_and_token_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STUDENT_LLM_API_KEY", "student-key")
    monkeypatch.setenv("STUDENT_LLM_MODEL", "qwen/qwen3-8b")
    monkeypatch.setenv("STUDENT_LLM_BASE_URL", "https://example.local/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_USER_AGENT", "finevent-test/0.1")

    student = build_student_chat_model_from_env(
        provider="langchain_openai",
        disable_thinking=False,
        max_tokens=64,
    )
    student_client = cast(Any, student)

    assert student_client.default_headers == {"User-Agent": "finevent-test/0.1"}
    assert student_client.max_tokens == 64


def test_langchain_embedding_builder_sets_self_host_headers_and_batching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STUDENT_LLM_API_KEY", "student-key")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-qwen3-embedding-0.6b")
    monkeypatch.setenv("EMBEDDING_BASE_URL", "https://example.local/v1")

    embeddings = build_openai_compatible_embeddings_from_env(
        provider="langchain_openai",
        batch_size=7,
    )
    embeddings_client = cast(Any, embeddings)

    assert embeddings_client.default_headers == {
        "User-Agent": DEFAULT_OPENAI_COMPATIBLE_USER_AGENT
    }
    assert embeddings_client.chunk_size == 7
    assert embeddings_client.tiktoken_enabled is False
    assert embeddings_client.check_embedding_ctx_length is False


def test_no_think_prefix_uses_langchain_runnable_composition() -> None:
    from langchain_core.runnables import RunnableLambda

    chain = cast(Any, _with_no_think_prefix(RunnableLambda(lambda value: value)))

    assert chain.invoke("Return JSON.") == "/no_think\nReturn JSON."
    assert chain.invoke("/no_think\nReturn JSON.") == "/no_think\nReturn JSON."
