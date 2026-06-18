"""Configuration loading for FinEvent-VN.

The loader prefers PyYAML when installed, but keeps a small fallback parser so
M0 smoke tests can run before optional dependencies are installed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from finevent.paths import repo_root, resolve_project_path
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    timezone: str
    config_version: str


@dataclass(frozen=True)
class StorageConfig:
    postgres_dsn: str
    vector_backend: str
    raw_dir: str
    processed_dir: str
    labels_dir: str
    vector_store_dir: str


@dataclass(frozen=True)
class ModelsConfig:
    embedding_default: str
    teacher_model: str
    student_model: str


@dataclass(frozen=True)
class RetrievalConfig:
    top_k_stage1: int
    top_k_stage2: int
    top_k_final: int


@dataclass(frozen=True)
class LoggingConfig:
    run_dir: str


@dataclass(frozen=True)
class AppConfig:
    project: ProjectConfig
    storage: StorageConfig
    models: ModelsConfig
    retrieval: RetrievalConfig
    logging: LoggingConfig
    config_path: Path

    @classmethod
    def from_mapping(cls, data: JsonDict, config_path: Path) -> "AppConfig":
        storage = dict(data["storage"])
        if os.getenv("POSTGRES_DSN"):
            storage["postgres_dsn"] = os.environ["POSTGRES_DSN"]

        return cls(
            project=ProjectConfig(**data["project"]),
            storage=StorageConfig(**storage),
            models=ModelsConfig(**data["models"]),
            retrieval=RetrievalConfig(**data["retrieval"]),
            logging=LoggingConfig(**data["logging"]),
            config_path=config_path,
        )


def load_config(config_path: PathLike | None = None) -> AppConfig:
    """Load the project config from YAML and environment overrides."""
    _load_dotenv_if_available()
    path = resolve_project_path(config_path or "configs/default.yaml")
    data = _load_yaml(path)
    return AppConfig.from_mapping(data, config_path=path)


def _load_dotenv_if_available() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(repo_root() / ".env")


def _load_yaml(path: Path) -> JsonDict:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml
    except ImportError:
        return _parse_simple_yaml(text)
    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    return loaded


def _parse_simple_yaml(text: str) -> JsonDict:
    """Parse the simple two-level YAML shape used by configs/default.yaml."""
    result: JsonDict = {}
    current_section: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        if not line.startswith(" "):
            key = line.rstrip(":")
            result[key] = {}
            current_section = key
            continue

        if current_section is None or ":" not in line:
            raise ValueError("Invalid simple YAML structure")

        key, value = line.strip().split(":", 1)
        result[current_section][key] = _parse_scalar(value.strip())

    return result


def _parse_scalar(value: str) -> Any:
    if value == "":
        return ""
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        return value.strip('"').strip("'")
