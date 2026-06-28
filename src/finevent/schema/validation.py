"""Validation for AI-generated event labels."""

from __future__ import annotations

import copy
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import Any

from finevent.ingestion.text import normalize_text
from finevent.schema.taxonomy import EventTaxonomy, load_event_taxonomy
from finevent.types import JsonDict

TOP_LEVEL_KEYS = {
    "article_id",
    "document_label",
    "label_reason",
    "events",
    "warnings",
    "model_info",
}
EVENT_KEYS = {
    "event_id",
    "ticker",
    "company_name",
    "event_type",
    "event_subtype",
    "event_summary",
    "event_reason",
    "event_arguments",
    "impact_sentiment",
    "evidence_span",
    "source_url",
    "published_at",
    "confidence",
}
MODEL_INFO_KEYS = {"model_name", "prompt_version", "run_id"}
ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str
    severity: str = ERROR

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class ValidationResult:
    normalized: JsonDict | None
    issues: list[ValidationIssue]

    @property
    def errors(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == WARNING]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def issues_as_dicts(self) -> list[JsonDict]:
        return [issue.to_dict() for issue in self.issues]


def parse_teacher_output(raw_output: Any) -> JsonDict:
    """Parse a teacher output object or JSON string, including fenced JSON."""
    if isinstance(raw_output, dict):
        return copy.deepcopy(raw_output)
    if not isinstance(raw_output, str):
        raise ValueError("raw_output must be a JSON object or JSON string")

    text = raw_output.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1).strip()

    loaded = json.loads(text)
    if not isinstance(loaded, dict):
        raise ValueError("teacher output JSON must be an object")
    return loaded


def validate_label_document(
    label_document: JsonDict,
    article_record: JsonDict,
    *,
    taxonomy: EventTaxonomy | None = None,
) -> ValidationResult:
    """Validate and normalize one document-level event label."""
    taxonomy = taxonomy or load_event_taxonomy()
    issues: list[ValidationIssue] = []
    if not isinstance(label_document, dict):
        return ValidationResult(
            normalized=None,
            issues=[
                ValidationIssue("$", "not_object", "Label document must be a JSON object."),
            ],
        )

    normalized = copy.deepcopy(label_document)
    _normalize_document_fields(normalized)
    article_id = str(article_record.get("article_id") or "")
    article_text = _article_text_for_grounding(article_record)

    _check_required_object_fields(
        normalized,
        TOP_LEVEL_KEYS,
        "$",
        issues,
        allowed_extra_keys=TOP_LEVEL_KEYS,
    )
    if normalized.get("article_id") != article_id:
        issues.append(
            ValidationIssue(
                "article_id",
                "article_id_mismatch",
                f"Label article_id must match source article_id {article_id!r}.",
            )
        )

    document_label = normalized.get("document_label")
    if document_label not in taxonomy.document_labels:
        issues.append(
            ValidationIssue(
                "document_label",
                "invalid_document_label",
                f"document_label must be one of {sorted(taxonomy.document_labels)}.",
            )
        )
    _check_required_string(normalized, "label_reason", "$", issues)

    events = normalized.get("events")
    if not isinstance(events, list):
        issues.append(ValidationIssue("events", "events_not_array", "events must be an array."))
        events = []
    if document_label == "NO_EVENT" and events:
        issues.append(
            ValidationIssue(
                "events",
                "no_event_has_events",
                "document_label=NO_EVENT requires events=[].",
            )
        )
    if document_label == "HAS_EVENT" and not events:
        issues.append(
            ValidationIssue(
                "events",
                "has_event_without_events",
                "document_label=HAS_EVENT requires at least one event.",
            )
        )

    warnings = normalized.get("warnings")
    if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
        issues.append(
            ValidationIssue(
                "warnings",
                "warnings_not_string_array",
                "warnings must be an array of strings.",
            )
        )

    model_info = normalized.get("model_info")
    if not isinstance(model_info, dict):
        issues.append(
            ValidationIssue(
                "model_info",
                "model_info_not_object",
                "model_info must be an object.",
            )
        )
    else:
        missing_model_fields = sorted(MODEL_INFO_KEYS - set(model_info))
        if missing_model_fields:
            issues.append(
                ValidationIssue(
                    "model_info",
                    "missing_model_info_fields",
                    f"model_info is missing fields: {missing_model_fields}.",
                )
            )

    event_ids: set[str] = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            issues.append(
                ValidationIssue(
                    f"events[{index}]",
                    "event_not_object",
                    "Each event must be a JSON object.",
                )
            )
            continue
        _normalize_event_fields(event)
        _validate_event(
            event,
            index=index,
            article_record=article_record,
            article_text=article_text,
            taxonomy=taxonomy,
            event_ids=event_ids,
            issues=issues,
        )

    return ValidationResult(normalized=normalized, issues=issues)


def evidence_is_grounded(evidence_span: str, article_text: str, *, threshold: float = 0.82) -> bool:
    if not evidence_span or not article_text:
        return False
    evidence = normalize_text(evidence_span)
    text = normalize_text(article_text)
    if evidence in text:
        return True
    folded_evidence = _ascii_fold(evidence).lower()
    folded_text = _ascii_fold(text).lower()
    if folded_evidence in folded_text:
        return True

    candidates = [candidate for candidate in _split_sentences(text) if candidate]
    if not candidates:
        candidates = [text]
    max_similarity = max(
        (
            _similarity(folded_evidence, _ascii_fold(candidate).lower())
            for candidate in candidates
        ),
        default=0.0,
    )
    return max_similarity >= threshold


def _validate_event(
    event: JsonDict,
    *,
    index: int,
    article_record: JsonDict,
    article_text: str,
    taxonomy: EventTaxonomy,
    event_ids: set[str],
    issues: list[ValidationIssue],
) -> None:
    path = f"events[{index}]"
    _check_required_object_fields(event, EVENT_KEYS, path, issues, allowed_extra_keys=EVENT_KEYS)

    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        issues.append(
            ValidationIssue(
                f"{path}.event_id",
                "missing_event_id",
                "event_id must be a non-empty string.",
            )
        )
    elif event_id in event_ids:
        issues.append(
            ValidationIssue(
                f"{path}.event_id",
                "duplicate_event_id",
                "event_id must be unique in the article.",
            )
        )
    else:
        event_ids.add(event_id)

    event_type = event.get("event_type")
    if event_type not in taxonomy.event_types:
        issues.append(
            ValidationIssue(
                f"{path}.event_type",
                "invalid_event_type",
                f"event_type must be one of {sorted(taxonomy.event_types)}.",
            )
        )

    subtype = event.get("event_subtype")
    if subtype is not None:
        if not isinstance(subtype, str) or not subtype:
            issues.append(
                ValidationIssue(
                    f"{path}.event_subtype",
                    "invalid_event_subtype",
                    "event_subtype must be string or null.",
                )
            )
        elif isinstance(event_type, str) and subtype not in taxonomy.allowed_subtypes(event_type):
            issues.append(
                ValidationIssue(
                    f"{path}.event_subtype",
                    "invalid_event_subtype_for_type",
                    f"Subtype {subtype!r} is not valid for event_type {event_type!r}.",
                )
            )

    sentiment = event.get("impact_sentiment")
    if sentiment not in taxonomy.impact_sentiments:
        issues.append(
            ValidationIssue(
                f"{path}.impact_sentiment",
                "invalid_impact_sentiment",
                f"impact_sentiment must be one of {sorted(taxonomy.impact_sentiments)}.",
            )
        )

    _check_nullable_string(event, "ticker", path, issues)
    _check_nullable_string(event, "company_name", path, issues)
    _check_required_string(event, "event_summary", path, issues)
    _check_required_string(event, "event_reason", path, issues)
    _check_required_string(event, "evidence_span", path, issues)
    _check_required_string(event, "source_url", path, issues)
    _check_nullable_string(event, "published_at", path, issues)

    confidence = event.get("confidence")
    if (
        not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or not 0 <= confidence <= 1
    ):
        issues.append(
            ValidationIssue(
                f"{path}.confidence",
                "invalid_confidence",
                "confidence must be a number in [0, 1].",
            )
        )

    arguments = event.get("event_arguments")
    if not isinstance(arguments, dict):
        issues.append(
            ValidationIssue(
                f"{path}.event_arguments",
                "event_arguments_not_object",
                "event_arguments must be an object.",
            )
        )
    elif isinstance(event_type, str) and event_type in taxonomy.event_types:
        allowed_argument_fields = taxonomy.allowed_argument_fields(event_type)
        extra_argument_fields = sorted(set(arguments) - allowed_argument_fields)
        for argument_key in extra_argument_fields:
            issues.append(
                ValidationIssue(
                    f"{path}.event_arguments.{argument_key}",
                    "non_taxonomy_argument_field",
                    (
                        "Argument key is outside the preferred taxonomy fields; "
                        "keep only if it is evidence-grounded."
                    ),
                    severity=WARNING,
                )
            )
        for argument_key in arguments:
            if not re.fullmatch(r"[a-z][a-z0-9_]*", str(argument_key)):
                issues.append(
                    ValidationIssue(
                        f"{path}.event_arguments.{argument_key}",
                        "argument_key_not_snake_case",
                        "Argument keys should use snake_case.",
                        severity=WARNING,
                    )
                )

    evidence_span = event.get("evidence_span")
    if isinstance(evidence_span, str) and not evidence_is_grounded(evidence_span, article_text):
        issues.append(
            ValidationIssue(
                f"{path}.evidence_span",
                "evidence_not_grounded",
                "evidence_span must appear in or closely match the article title/body.",
            )
        )

    ticker = event.get("ticker")
    if isinstance(ticker, str) and ticker:
        _validate_ticker_grounding(ticker, path, article_record, article_text, issues)


def _check_required_object_fields(
    payload: JsonDict,
    required_keys: set[str],
    path: str,
    issues: list[ValidationIssue],
    *,
    allowed_extra_keys: set[str],
) -> None:
    missing_keys = sorted(required_keys - set(payload))
    if missing_keys:
        issues.append(
            ValidationIssue(
                path,
                "missing_required_fields",
                f"Missing required fields: {missing_keys}.",
            )
        )
    extra_keys = sorted(set(payload) - allowed_extra_keys)
    if extra_keys:
        issues.append(
            ValidationIssue(
                path,
                "unexpected_fields",
                f"Unexpected fields are not allowed: {extra_keys}.",
            )
        )


def _check_required_string(
    payload: JsonDict,
    field_name: str,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        issues.append(
            ValidationIssue(
                f"{path}.{field_name}",
                "missing_required_string",
                f"{field_name} must be a non-empty string.",
            )
        )


def _check_nullable_string(
    payload: JsonDict,
    field_name: str,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    value = payload.get(field_name)
    if value is not None and not isinstance(value, str):
        issues.append(
            ValidationIssue(
                f"{path}.{field_name}",
                "invalid_nullable_string",
                f"{field_name} must be string or null.",
            )
        )


def _validate_ticker_grounding(
    ticker: str,
    path: str,
    article_record: JsonDict,
    article_text: str,
    issues: list[ValidationIssue],
) -> None:
    ticker_upper = ticker.upper()
    hint_tickers = {str(item).upper() for item in article_record.get("tickers_hint", [])}
    if ticker_upper in hint_tickers:
        return
    if re.search(rf"(?<![A-Z0-9]){re.escape(ticker_upper)}(?![A-Z0-9])", article_text.upper()):
        return
    issues.append(
        ValidationIssue(
            f"{path}.ticker",
            "ticker_not_grounded",
            "ticker must be present in ticker hints or article text.",
        )
    )


def _normalize_document_fields(label_document: JsonDict) -> None:
    label = label_document.get("document_label")
    if isinstance(label, str):
        label_document["document_label"] = label.strip().upper()


def _normalize_event_fields(event: JsonDict) -> None:
    for key in ("event_type", "event_subtype", "impact_sentiment", "ticker"):
        value = event.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            event[key] = stripped.upper() if stripped else None


def _article_text_for_grounding(article_record: JsonDict) -> str:
    return "\n".join(
        part
        for part in [
            str(article_record.get("title") or ""),
            str(article_record.get("text") or ""),
        ]
        if part
    )


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"[\n\r]+|(?<=[.!?;:])\s+", text) if part.strip()]


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _ascii_fold(text: str) -> str:
    replacements = {"\u0111": "d", "\u0110": "D"}
    for source, target in replacements.items():
        text = text.replace(source, target)
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
