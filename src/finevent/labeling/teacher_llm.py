"""Teacher LLM execution for AI-generated gold labels."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from finevent.jsonl import read_jsonl, write_jsonl
from finevent.logging_utils import create_run_id, utc_now_iso
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class TeacherExecutionResult:
    teacher_output_path: Path
    prompt_count: int
    success_count: int
    error_count: int
    run_id: str


class InvokableModel(Protocol):
    def invoke(self, prompt: str) -> Any: ...


def run_teacher_llm_on_prompts(
    *,
    prompt_path: PathLike,
    output_path: PathLike,
    teacher_model: InvokableModel,
    teacher_model_name: str,
    max_records: int | None = None,
    max_retries: int = 2,
    retry_sleep_seconds: float = 2.0,
    run_id: str | None = None,
) -> TeacherExecutionResult:
    """Call a teacher LLM for prompt records and persist raw outputs.

    The raw teacher output is intentionally preserved. Validation and conversion
    to `events_gold.jsonl` remains the responsibility of M02 validation.
    """
    prompt_records = read_jsonl(prompt_path)
    if max_records is not None:
        prompt_records = prompt_records[:max_records]
    run_id = run_id or create_run_id("teacher")
    output_records: list[JsonDict] = []
    success_count = 0
    error_count = 0

    for index, prompt_record in enumerate(prompt_records, start=1):
        article_id = str(prompt_record.get("article_id") or "")
        prompt_text = str(prompt_record.get("prompt") or "")
        prompt_version = str(prompt_record.get("prompt_version") or "")
        record: JsonDict = {
            "article_id": article_id,
            "teacher_model": teacher_model_name,
            "prompt_version": prompt_version,
            "teacher_run_id": run_id,
            "generated_at": utc_now_iso(),
            "prompt_index": index,
            "raw_output": None,
            "error": None,
        }
        try:
            record["raw_output"] = _invoke_with_retry(
                teacher_model,
                prompt_text,
                max_retries=max_retries,
                retry_sleep_seconds=retry_sleep_seconds,
            )
            success_count += 1
        except Exception as exc:  # noqa: BLE001 - live runs must capture provider failures.
            record["error"] = str(exc)
            error_count += 1
        output_records.append(record)

    teacher_output_path = Path(output_path)
    write_jsonl(teacher_output_path, output_records)
    return TeacherExecutionResult(
        teacher_output_path=teacher_output_path,
        prompt_count=len(prompt_records),
        success_count=success_count,
        error_count=error_count,
        run_id=run_id,
    )


def _invoke_with_retry(
    model: InvokableModel,
    prompt: str,
    *,
    max_retries: int,
    retry_sleep_seconds: float,
) -> str:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return _content_from_response(model.invoke(prompt))
        except Exception as exc:  # noqa: BLE001 - caller decides retry policy.
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_sleep_seconds * (attempt + 1))
    if last_error is not None:
        raise last_error
    raise RuntimeError("Teacher model did not return a response.")


def _content_from_response(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):
        return "\n".join(str(part) for part in content)
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return str(content)
