"""Build gold-derived pattern records from AI-generated labels."""

from __future__ import annotations

import hashlib
import json

from finevent.ingestion.text import normalize_text
from finevent.patterns.models import PatternRecord
from finevent.schema.taxonomy import load_event_taxonomy
from finevent.types import JsonDict


def build_patterns_from_gold(
    *,
    gold_records: list[JsonDict],
    articles_by_id: dict[str, JsonDict],
) -> list[PatternRecord]:
    patterns: list[PatternRecord] = []
    for gold_record in gold_records:
        label = (
            gold_record.get("label")
            if isinstance(gold_record.get("label"), dict)
            else gold_record
        )
        if not isinstance(label, dict):
            continue
        article_id = str(label.get("article_id") or gold_record.get("article_id") or "")
        article = articles_by_id.get(article_id, {})
        document_label = str(label.get("document_label") or "")
        if document_label == "NO_EVENT":
            pattern = _build_no_event_pattern(gold_record, label, article)
            if pattern:
                patterns.append(pattern)
            continue

        for event_index, event in enumerate(label.get("events", [])):
            if not isinstance(event, dict):
                continue
            pattern = _build_event_pattern(gold_record, label, article, event, event_index)
            if pattern:
                patterns.append(pattern)
    return patterns


def validate_pattern(pattern: PatternRecord) -> list[JsonDict]:
    taxonomy = load_event_taxonomy()
    errors: list[JsonDict] = []
    if not pattern.pattern_id:
        errors.append(_issue("pattern_id", "missing_pattern_id", "pattern_id is required."))
    if not pattern.article_id:
        errors.append(_issue("article_id", "missing_article_id", "article_id is required."))
    if not pattern.input_excerpt:
        errors.append(
            _issue("input_excerpt", "missing_input_excerpt", "input_excerpt is required.")
        )
    if not isinstance(pattern.gold_output, dict):
        errors.append(
            _issue("gold_output", "invalid_gold_output", "gold_output must be an object.")
        )
    if pattern.document_label == "NO_EVENT":
        events = pattern.gold_output.get("events", [])
        if events:
            errors.append(_issue("gold_output.events", "no_event_has_events", "NO_EVENT needs []."))
        return errors

    if pattern.document_label != "HAS_EVENT":
        errors.append(
            _issue(
                "document_label",
                "invalid_document_label",
                "Pattern must be HAS_EVENT or NO_EVENT.",
            )
        )
    if pattern.event_type not in taxonomy.event_types:
        errors.append(_issue("event_type", "invalid_event_type", "event_type is not in taxonomy."))
    if pattern.event_subtype and pattern.event_subtype not in taxonomy.allowed_subtypes(
        pattern.event_type or ""
    ):
        errors.append(
            _issue(
                "event_subtype",
                "invalid_event_subtype",
                "event_subtype is invalid for event_type.",
            )
        )
    if not pattern.evidence_span:
        errors.append(
            _issue("evidence_span", "missing_evidence", "HAS_EVENT pattern needs evidence.")
        )
    return errors


def build_pattern_text(pattern: PatternRecord) -> str:
    parts = [
        f"Document label: {pattern.document_label}",
        f"Title/source: {pattern.metadata.get('title') or ''} | {pattern.source}",
        f"Ticker/company: {pattern.ticker or ''} | {pattern.company_name or ''}",
        f"Event type/subtype: {pattern.event_type or ''} | {pattern.event_subtype or ''}",
        f"Impact sentiment: {pattern.impact_sentiment or ''}",
        f"Evidence: {pattern.evidence_span or pattern.input_excerpt}",
        f"Summary: {_event_summary(pattern)}",
        f"Arguments: {json.dumps(pattern.event_arguments, ensure_ascii=False, sort_keys=True)}",
    ]
    return normalize_text("\n".join(part for part in parts if part.strip()))


def _build_event_pattern(
    gold_record: JsonDict,
    label: JsonDict,
    article: JsonDict,
    event: JsonDict,
    event_index: int,
) -> PatternRecord | None:
    article_id = str(label.get("article_id") or gold_record.get("article_id") or "")
    event_id = str(event.get("event_id") or f"{article_id}_event_{event_index:02d}")
    evidence_span = normalize_text(str(event.get("evidence_span") or ""))
    input_excerpt = _evidence_excerpt(article, evidence_span)
    gold_output = {
        "document_label": "HAS_EVENT",
        "events": [event],
    }
    pattern = PatternRecord(
        pattern_id=_pattern_id(article_id, event_id, "event"),
        article_id=article_id,
        document_label="HAS_EVENT",
        pattern_kind="event",
        event_id=event_id,
        event_type=event.get("event_type"),
        event_subtype=event.get("event_subtype"),
        ticker=event.get("ticker"),
        company_name=event.get("company_name"),
        impact_sentiment=event.get("impact_sentiment"),
        evidence_span=evidence_span,
        event_arguments=dict(event.get("event_arguments", {})),
        input_excerpt=input_excerpt,
        gold_output=gold_output,
        pattern_text="",
        source=str(article.get("source") or ""),
        url=str(article.get("url") or event.get("source_url") or ""),
        published_at=article.get("published_at") or event.get("published_at"),
        teacher_model=str(gold_record.get("teacher_model") or "unknown_teacher"),
        teacher_prompt_version=str(gold_record.get("prompt_version") or ""),
        auto_validation_status=str(gold_record.get("validation_status") or "PASS"),
        validation_errors=list(gold_record.get("validation_errors", [])),
        explanation_brief=_event_explanation(event),
        metadata=_metadata(article, label, event),
    )
    errors = validate_pattern(pattern)
    if errors:
        return PatternRecord(**{**pattern.to_dict(), "validation_errors": errors})
    return PatternRecord(**{**pattern.to_dict(), "pattern_text": build_pattern_text(pattern)})


def _build_no_event_pattern(
    gold_record: JsonDict,
    label: JsonDict,
    article: JsonDict,
) -> PatternRecord | None:
    article_id = str(label.get("article_id") or gold_record.get("article_id") or "")
    input_excerpt = _article_excerpt(article)
    gold_output = {
        "document_label": "NO_EVENT",
        "events": [],
    }
    pattern = PatternRecord(
        pattern_id=_pattern_id(article_id, "no_event", "no_event"),
        article_id=article_id,
        document_label="NO_EVENT",
        pattern_kind="no_event",
        input_excerpt=input_excerpt,
        gold_output=gold_output,
        pattern_text="",
        source=str(article.get("source") or ""),
        url=str(article.get("url") or ""),
        published_at=article.get("published_at"),
        teacher_model=str(gold_record.get("teacher_model") or "unknown_teacher"),
        teacher_prompt_version=str(gold_record.get("prompt_version") or ""),
        auto_validation_status=str(gold_record.get("validation_status") or "PASS"),
        validation_errors=list(gold_record.get("validation_errors", [])),
        explanation_brief=_no_event_explanation(gold_record, label, article),
        metadata=_metadata(article, label, None),
    )
    errors = validate_pattern(pattern)
    if errors:
        return PatternRecord(**{**pattern.to_dict(), "validation_errors": errors})
    return PatternRecord(**{**pattern.to_dict(), "pattern_text": build_pattern_text(pattern)})


def _metadata(article: JsonDict, label: JsonDict, event: JsonDict | None) -> JsonDict:
    return {
        "title": article.get("title"),
        "tickers_hint": article.get("tickers_hint", []),
        "company_names_hint": article.get("company_names_hint", []),
        "sector_hints": article.get("sector_hints", []),
        "event_keywords": article.get("event_keywords", []),
        "event_type_hints": article.get("event_type_hints", []),
        "event_subtype_hints": article.get("event_subtype_hints", []),
        "document_label": label.get("document_label"),
        "event_summary": event.get("event_summary") if event else None,
    }


def _evidence_excerpt(article: JsonDict, evidence_span: str) -> str:
    text = normalize_text(str(article.get("text") or ""))
    if not text:
        return evidence_span
    folded_evidence = evidence_span.lower()
    for paragraph in text.split("\n"):
        if folded_evidence and folded_evidence in paragraph.lower():
            return normalize_text(paragraph)
    return evidence_span or _article_excerpt(article)


def _article_excerpt(article: JsonDict, *, max_words: int = 120) -> str:
    title = normalize_text(str(article.get("title") or ""))
    text = normalize_text(str(article.get("text") or ""))
    words = text.split()
    body = " ".join(words[:max_words])
    return normalize_text("\n".join(part for part in [title, body] if part))


def _event_explanation(event: JsonDict) -> str:
    for key in ("event_reason", "reasoning_summary", "rationale", "explanation"):
        reason = normalize_text(str(event.get(key) or ""))
        if reason:
            return reason
    summary = normalize_text(str(event.get("event_summary") or ""))
    evidence = normalize_text(str(event.get("evidence_span") or ""))
    if summary and evidence:
        return f"{summary} Evidence: {evidence}"
    return summary or evidence


def _no_event_explanation(gold_record: JsonDict, label: JsonDict, article: JsonDict) -> str:
    for source in (label, gold_record):
        for key in ("label_reason", "reasoning_summary", "rationale", "explanation"):
            reason = normalize_text(str(source.get(key) or ""))
            if reason:
                return reason
    title = normalize_text(str(article.get("title") or ""))
    if title:
        return f"No reportable taxonomy event was identified in article: {title}."
    return "No reportable taxonomy event was identified in the article."


def _event_summary(pattern: PatternRecord) -> str:
    events = pattern.gold_output.get("events", [])
    if events and isinstance(events[0], dict):
        return str(events[0].get("event_summary") or "")
    return ""


def _pattern_id(article_id: str, event_id: str, kind: str) -> str:
    digest = hashlib.sha1(f"{article_id}:{event_id}:{kind}".encode()).hexdigest()
    return f"pattern_{digest[:16]}"


def _issue(path: str, code: str, message: str) -> JsonDict:
    return {
        "path": path,
        "code": code,
        "message": message,
        "severity": "error",
    }
