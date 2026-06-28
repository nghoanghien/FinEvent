"""Data models for gold-derived pattern records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from finevent.types import JsonDict


@dataclass(frozen=True)
class PatternRecord:
    pattern_id: str
    article_id: str
    document_label: str
    pattern_kind: str
    input_excerpt: str
    gold_output: JsonDict
    pattern_text: str
    source: str
    url: str
    published_at: str | None
    teacher_model: str
    teacher_prompt_version: str
    auto_validation_status: str
    validation_errors: list[JsonDict]
    event_id: str | None = None
    event_type: str | None = None
    event_subtype: str | None = None
    ticker: str | None = None
    company_name: str | None = None
    impact_sentiment: str | None = None
    evidence_span: str | None = None
    event_arguments: JsonDict = field(default_factory=dict)
    explanation_brief: str = ""
    metadata: JsonDict = field(default_factory=dict)
    version: str = "m05_v1"

    def to_dict(self) -> JsonDict:
        return asdict(self)
