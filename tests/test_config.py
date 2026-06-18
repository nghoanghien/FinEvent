from __future__ import annotations

from pathlib import Path

from finevent.config import load_config
from finevent.logging_utils import create_run_logger


def test_load_default_config() -> None:
    config = load_config()

    assert config.project.name == "finevent-vn"
    assert config.project.timezone == "Asia/Bangkok"
    assert config.storage.vector_backend == "pgvector"
    assert config.retrieval.top_k_stage1 > config.retrieval.top_k_final


def test_env_example_does_not_contain_real_secrets() -> None:
    env_example = Path(".env.example").read_text(encoding="utf-8")

    forbidden_fragments = ["sk-", "AIza", "eyJ", "Bearer "]
    assert all(fragment not in env_example for fragment in forbidden_fragments)


def test_run_logger_writes_jsonl(tmp_path: Path) -> None:
    logger = create_run_logger(
        run_dir=tmp_path,
        config_path="configs/default.yaml",
        prefix="test",
    )

    logger.log("unit_test_event", status="ok")

    lines = logger.context.log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert "unit_test_event" in lines[0]
