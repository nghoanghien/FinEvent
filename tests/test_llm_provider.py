from __future__ import annotations

import json
from pathlib import Path

import pytest

from finevent.jsonl import read_jsonl, write_jsonl
from finevent.labeling.teacher_llm import run_teacher_llm_on_prompts
from finevent.llm import (
    build_openai_compatible_embeddings_from_env,
    build_student_chat_model_from_env,
    build_teacher_chat_model_from_env,
    load_provider_runtime_config,
    redact_secret,
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


def test_provider_config_redacts_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "teacher-test-1234567890")
    monkeypatch.setenv("TEACHER_LLM_MODEL", "teacher-test")

    config = load_provider_runtime_config()

    assert config.teacher_model == "teacher-test"
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
