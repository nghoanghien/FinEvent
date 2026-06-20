"""JSONL helpers used by batch workflows."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from finevent.types import JsonDict, PathLike


def write_jsonl(path: PathLike, records: Iterable[JsonDict]) -> int:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def read_jsonl(path: PathLike) -> list[JsonDict]:
    input_path = Path(path)
    if not input_path.exists():
        return []
    records: list[JsonDict] = []
    with input_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                loaded = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {input_path}:{line_number}") from exc
            if not isinstance(loaded, dict):
                raise ValueError(f"JSONL record must be an object at {input_path}:{line_number}")
            records.append(loaded)
    return records
