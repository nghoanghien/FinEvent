"""Milestone 02 AI-generated labeling pipeline."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from finevent.jsonl import read_jsonl, write_jsonl
from finevent.labeling.prompting import PROMPT_VERSION, build_teacher_prompt
from finevent.labeling.reporting import build_labeling_summary, write_labeling_summary
from finevent.logging_utils import utc_now_iso
from finevent.schema.taxonomy import EventTaxonomy, load_event_taxonomy
from finevent.schema.validation import (
    ValidationIssue,
    parse_teacher_output,
    validate_label_document,
)
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class PromptGenerationResult:
    prompt_path: Path
    prompt_count: int


@dataclass(frozen=True)
class LabelingValidationResult:
    ai_generated_path: Path
    gold_path: Path
    rejected_path: Path
    report_path: Path
    total_count: int
    pass_count: int
    rejected_count: int


def generate_teacher_prompts(
    *,
    articles_path: PathLike = "data/processed/articles_clean.jsonl",
    prompt_output_path: PathLike = "data/labels/teacher_prompts.jsonl",
    taxonomy_path: PathLike = "data/schema/event_taxonomy_v1.json",
    limit: int | None = None,
    prompt_version: str = PROMPT_VERSION,
) -> PromptGenerationResult:
    taxonomy = load_event_taxonomy(taxonomy_path)
    articles = read_jsonl(articles_path)
    if limit is not None:
        articles = articles[:limit]
    prompt_records = [
        {
            "article_id": article["article_id"],
            "prompt_version": prompt_version,
            "taxonomy_version": taxonomy.schema_version,
            "prompt": build_teacher_prompt(
                article,
                taxonomy=taxonomy,
                prompt_version=prompt_version,
            ),
            "article_metadata": {
                "source": article.get("source"),
                "url": article.get("url"),
                "published_at": article.get("published_at"),
                "tickers_hint": article.get("tickers_hint", []),
                "event_type_hints": article.get("event_type_hints", []),
                "event_subtype_hints": article.get("event_subtype_hints", []),
            },
        }
        for article in articles
    ]
    prompt_path = Path(prompt_output_path)
    prompt_count = write_jsonl(prompt_path, prompt_records)
    return PromptGenerationResult(prompt_path=prompt_path, prompt_count=prompt_count)


def validate_teacher_outputs(
    *,
    articles_path: PathLike = "data/processed/articles_clean.jsonl",
    teacher_output_path: PathLike = "data/labels/teacher_outputs.jsonl",
    ai_generated_output_path: PathLike = "data/labels/events_ai_generated.jsonl",
    gold_output_path: PathLike = "data/labels/events_gold.jsonl",
    rejected_output_path: PathLike = "data/labels/events_rejected.jsonl",
    report_path: PathLike = "reports/data/labeling_summary.md",
    taxonomy_path: PathLike = "data/schema/event_taxonomy_v1.json",
    run_id: str | None = None,
    accept_ai_as_gold: bool = True,
) -> LabelingValidationResult:
    taxonomy = load_event_taxonomy(taxonomy_path)
    articles_by_id = {record["article_id"]: record for record in read_jsonl(articles_path)}
    teacher_records = read_jsonl(teacher_output_path)
    run_id = run_id or _stable_run_id(teacher_records)

    ai_generated_records: list[JsonDict] = []
    gold_records: list[JsonDict] = []
    rejected_records: list[JsonDict] = []

    for index, teacher_record in enumerate(teacher_records):
        standardized = _standardize_teacher_record(
            teacher_record,
            index=index,
            articles_by_id=articles_by_id,
            taxonomy=taxonomy,
            run_id=run_id,
        )
        ai_generated_records.append(standardized)
        if standardized.get("label") is not None and accept_ai_as_gold:
            if standardized["validation_status"] != "PASS":
                standardized["validation_status"] = "AUTO_ACCEPTED_WITH_ISSUES"
            gold_records.append(standardized)
        elif standardized["validation_status"] == "PASS":
            gold_records.append(standardized)
        else:
            rejected_records.append(standardized)

    write_jsonl(ai_generated_output_path, ai_generated_records)
    write_jsonl(gold_output_path, gold_records)
    write_jsonl(rejected_output_path, rejected_records)
    summary = build_labeling_summary(
        ai_generated_records=ai_generated_records,
        gold_records=gold_records,
        rejected_records=rejected_records,
    )
    write_labeling_summary(report_path, summary)

    return LabelingValidationResult(
        ai_generated_path=Path(ai_generated_output_path),
        gold_path=Path(gold_output_path),
        rejected_path=Path(rejected_output_path),
        report_path=Path(report_path),
        total_count=len(ai_generated_records),
        pass_count=len(gold_records),
        rejected_count=len(rejected_records),
    )


def _standardize_teacher_record(
    teacher_record: JsonDict,
    *,
    index: int,
    articles_by_id: dict[str, JsonDict],
    taxonomy: EventTaxonomy,
    run_id: str,
) -> JsonDict:
    article_id = _extract_article_id(teacher_record)
    teacher_model = str(
        teacher_record.get("teacher_model")
        or teacher_record.get("model_name")
        or "unknown_teacher"
    )
    prompt_version = str(teacher_record.get("prompt_version") or PROMPT_VERSION)
    generated_at = str(teacher_record.get("generated_at") or utc_now_iso())
    raw_output = _extract_raw_output(teacher_record)
    base_record = {
        "article_id": article_id,
        "label_schema_version": taxonomy.schema_version,
        "label_source": "ai_generated",
        "teacher_model": teacher_model,
        "prompt_version": prompt_version,
        "labeling_run_id": run_id,
        "generated_at": generated_at,
        "validation_status": "FAIL",
        "validation_errors": [],
        "label": None,
        "raw_output": raw_output,
    }

    if not article_id:
        return _reject(
            base_record,
            ValidationIssue(
                "$",
                "missing_article_id",
                f"Teacher output record at index {index} has no article_id.",
            ),
        )
    article_record = articles_by_id.get(article_id)
    if article_record is None:
        return _reject(
            base_record,
            ValidationIssue(
                "article_id",
                "unknown_article_id",
                f"article_id {article_id!r} is not present in the clean article file.",
            ),
        )

    try:
        parsed_output = parse_teacher_output(raw_output)
    except (json.JSONDecodeError, ValueError) as exc:
        return _reject(
            base_record,
            ValidationIssue(
                "raw_output",
                "invalid_json",
                f"Teacher output cannot be parsed as JSON: {exc}",
            ),
        )

    label_document = _inject_runtime_metadata(
        parsed_output,
        article_record=article_record,
        teacher_model=teacher_model,
        prompt_version=prompt_version,
        run_id=run_id,
    )
    validation = validate_label_document(label_document, article_record, taxonomy=taxonomy)
    base_record["label"] = validation.normalized
    base_record["validation_errors"] = validation.issues_as_dicts()
    if validation.is_valid:
        base_record["validation_status"] = "PASS"
    return base_record


def _extract_article_id(teacher_record: JsonDict) -> str:
    if teacher_record.get("article_id"):
        return str(teacher_record["article_id"])
    raw_output = _extract_raw_output(teacher_record)
    if isinstance(raw_output, dict) and raw_output.get("article_id"):
        return str(raw_output["article_id"])
    if isinstance(raw_output, str):
        try:
            parsed = parse_teacher_output(raw_output)
        except (json.JSONDecodeError, ValueError):
            return ""
        if parsed.get("article_id"):
            return str(parsed["article_id"])
    return ""


def _extract_raw_output(teacher_record: JsonDict) -> Any:
    if "raw_output" in teacher_record:
        return teacher_record["raw_output"]
    if "output" in teacher_record:
        return teacher_record["output"]
    if "label" in teacher_record:
        return teacher_record["label"]
    return teacher_record


def _inject_runtime_metadata(
    label_document: JsonDict,
    *,
    article_record: JsonDict,
    teacher_model: str,
    prompt_version: str,
    run_id: str,
) -> JsonDict:
    normalized = dict(label_document)
    normalized.setdefault("article_id", article_record["article_id"])
    normalized.setdefault("warnings", [])
    normalized.setdefault("events", [])
    raw_model_info = normalized.get("model_info")
    model_info = raw_model_info if isinstance(raw_model_info, dict) else {}
    normalized["model_info"] = {
        **model_info,
        "model_name": model_info.get("model_name") or teacher_model,
        "prompt_version": model_info.get("prompt_version") or prompt_version,
        "run_id": run_id,
    }

    for event_index, event in enumerate(normalized.get("events", []), start=1):
        if not isinstance(event, dict):
            continue
        event.setdefault("event_id", f"{article_record['article_id']}_e{event_index:02d}")
        event.setdefault("source_url", article_record.get("url") or "")
        event.setdefault("published_at", article_record.get("published_at"))
        event.setdefault("event_arguments", {})
    return normalized


def _reject(base_record: JsonDict, issue: ValidationIssue) -> JsonDict:
    base_record["validation_errors"] = [issue.to_dict()]
    return base_record


def _stable_run_id(records: list[JsonDict]) -> str:
    serialized = json.dumps(records, ensure_ascii=False, sort_keys=True).encode("utf-8")
    digest = hashlib.sha1(serialized).hexdigest()
    return f"m02_{digest[:12]}"
