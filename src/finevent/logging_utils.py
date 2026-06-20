"""Run logging helpers.

M0 uses JSONL logs so every later pipeline step can append structured events.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from finevent.paths import repo_root, resolve_project_path
from finevent.types import JsonDict, PathLike


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_run_id(prefix: str = "run") -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{suffix}"


def current_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root(),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_dir: Path
    log_path: Path
    config_path: Path
    git_commit: str | None


class JsonlRunLogger:
    def __init__(self, context: RunContext) -> None:
        self.context = context
        self.context.run_dir.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, **payload: Any) -> None:
        record: JsonDict = {
            "run_id": self.context.run_id,
            "timestamp": utc_now_iso(),
            "event": event,
            "git_commit": self.context.git_commit,
            **payload,
        }
        with self.context.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def as_dict(self) -> JsonDict:
        data = asdict(self.context)
        return {
            key: str(value) if isinstance(value, Path) else value
            for key, value in data.items()
        }


def create_run_logger(
    *,
    run_dir: PathLike,
    config_path: PathLike,
    prefix: str = "m00",
) -> JsonlRunLogger:
    run_id = create_run_id(prefix)
    base_run_dir = resolve_project_path(run_dir)
    concrete_run_dir = base_run_dir / run_id
    context = RunContext(
        run_id=run_id,
        run_dir=concrete_run_dir,
        log_path=concrete_run_dir / "run.jsonl",
        config_path=resolve_project_path(config_path),
        git_commit=current_git_commit(),
    )
    return JsonlRunLogger(context)
