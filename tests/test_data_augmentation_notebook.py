from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_data_augmentation_notebook_is_data_only_and_secret_free() -> None:
    nbformat = pytest.importorskip("nbformat")
    notebook_path = Path("data-augmentation.ipynb")
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    text = notebook_path.read_text(encoding="utf-8")
    parsed_notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(parsed_notebook)

    assert notebook["nbformat"] == 4
    assert notebook["cells"]
    assert "REAL_DOWNLOAD = True" in text
    assert "discover_url_candidates" in text
    assert "fetch_url_candidates" in text
    assert "downloaded_pages" in text
    assert "parse_article_html" in text
    assert "write_jsonl" in text
    assert "run_teacher_llm_on_prompts" not in text
    assert "run_online_extraction_workflow" not in text
    assert "get_sqlalchemy_engine" not in text
    assert "sk-" not in text
