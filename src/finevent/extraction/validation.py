"""Parse, normalize and validate extraction model outputs."""

from __future__ import annotations

import copy
import json
import re

from finevent.extraction.models import ExtractionRunConfig, ValidationRepairResult
from finevent.schema.validation import parse_teacher_output, validate_label_document
from finevent.types import JsonDict


def validate_or_repair_extraction_output(
    raw_output: str | JsonDict,
    *,
    article: JsonDict,
    run_id: str,
    config: ExtractionRunConfig,
) -> ValidationRepairResult:
    parse_error: str | None = None
    repaired = False
    try:
        parsed = parse_teacher_output(raw_output)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        parse_error = str(exc)
        parsed = _extract_json_object(raw_output)
        repaired = parsed is not None

    if parsed is None:
        fallback = _fallback_uncertain_output(article=article, run_id=run_id, config=config)
        return ValidationRepairResult(
            output=fallback,
            issues=[
                {
                    "path": "$",
                    "code": "parse_failed",
                    "message": parse_error or "Model output could not be parsed as JSON.",
                    "severity": "error",
                }
            ],
            repaired=False,
            parse_error=parse_error,
        )

    normalized = _fill_required_fields(parsed, article=article, run_id=run_id, config=config)
    validation = validate_label_document(normalized, article)
    output = validation.normalized or normalized
    return ValidationRepairResult(
        output=output,
        issues=validation.issues_as_dicts(),
        repaired=repaired,
        parse_error=parse_error,
    )


def _extract_json_object(raw_output: object) -> JsonDict | None:
    if not isinstance(raw_output, str):
        return None
    text = raw_output.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            return None
        text = text[start : end + 1]
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _fill_required_fields(
    payload: JsonDict,
    *,
    article: JsonDict,
    run_id: str,
    config: ExtractionRunConfig,
) -> JsonDict:
    normalized = copy.deepcopy(payload)
    article_id = str(article.get("article_id") or "")
    normalized["article_id"] = article_id
    events = normalized.get("events")
    if not isinstance(events, list):
        events = []
        normalized["events"] = events
    normalized.setdefault("document_label", "HAS_EVENT" if events else "NO_EVENT")
    normalized.setdefault("label_reason", _default_label_reason(normalized["document_label"]))
    normalized.setdefault("warnings", [])
    model_info = normalized.get("model_info")
    if not isinstance(model_info, dict):
        model_info = {}
    normalized["model_info"] = {
        **model_info,
        "model_name": config.student_model,
        "prompt_version": config.prompt_version,
        "run_id": run_id,
    }

    if normalized["document_label"] == "NO_EVENT":
        normalized["events"] = []
        return normalized

    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("event_id") or "")
        if not event_id.startswith(f"{article_id}_"):
            event_id = f"{article_id}_e{index + 1:02d}"
        event["event_id"] = event_id
        event.setdefault("ticker", None)
        event.setdefault("company_name", None)
        event.setdefault("event_subtype", None)
        event.setdefault("event_summary", "")
        event.setdefault("event_reason", _default_event_reason(event))
        event.setdefault("event_arguments", {})
        event.setdefault("impact_sentiment", "NEUTRAL")
        event.setdefault("evidence_span", "")
        event["source_url"] = article.get("url") or event.get("source_url") or ""
        event["published_at"] = article.get("published_at") or event.get("published_at")
        event.setdefault("confidence", 0.5)
    return normalized


def _fallback_uncertain_output(
    *,
    article: JsonDict,
    run_id: str,
    config: ExtractionRunConfig,
) -> JsonDict:
    return {
        "article_id": article.get("article_id"),
        "document_label": "UNCERTAIN",
        "label_reason": "Model output could not be parsed, so the document label is uncertain.",
        "events": [],
        "warnings": ["model_output_parse_failed"],
        "model_info": {
            "model_name": config.student_model,
            "prompt_version": config.prompt_version,
            "run_id": run_id,
        },
    }


def _default_label_reason(document_label: object) -> str:
    if document_label == "HAS_EVENT":
        return "Model output contains at least one candidate event."
    if document_label == "NO_EVENT":
        return "Model output contains no grounded reportable event."
    return "Model output is uncertain or incomplete."


def _default_event_reason(event: JsonDict) -> str:
    evidence = str(event.get("evidence_span") or "").strip()
    if evidence:
        return f"Evidence supports this event: {evidence[:180]}"
    return "Event is retained as a model candidate but needs evidence validation."
