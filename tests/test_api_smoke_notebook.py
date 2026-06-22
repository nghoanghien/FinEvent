from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_api_smoke_notebook_is_valid_and_secret_free() -> None:
    nbformat = pytest.importorskip("nbformat")
    notebook_path = Path("api-smoke-test.ipynb")
    notebook_text = notebook_path.read_text(encoding="utf-8")
    notebook = json.loads(notebook_text)
    parsed_notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(parsed_notebook)

    assert notebook["nbformat"] == 4
    assert "chat_completion(" in notebook_text
    assert "embedding_request(" in notebook_text
    assert "teacher-llm-test" in notebook_text
    assert "student-llm-test" in notebook_text
    assert "embedding-test" in notebook_text
    assert "OPENAI_API_KEY" in notebook_text
    assert "STUDENT_LLM_MODEL" in notebook_text
    assert "EMBEDDING_MODEL" in notebook_text
    assert "mini_rag" not in notebook_text
    assert "check_models_endpoint" not in notebook_text
    assert "sk-" not in notebook_text
