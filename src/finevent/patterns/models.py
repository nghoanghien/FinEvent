"""Data models for pattern library artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from finevent.types import JsonDict


@dataclass(frozen=True)
class PatternQuery:
    query_id: str
    article_id: str
    text: str
    query_type: str = "pattern"
    tickers: list[str] = field(default_factory=list)
    company_names: list[str] = field(default_factory=list)
    event_keywords: list[str] = field(default_factory=list)
    event_type_hints: list[str] = field(default_factory=list)
    event_subtype_hints: list[str] = field(default_factory=list)
    document_label_hint: str | None = None
    intent_key: str | None = None
    intent_event_type: str | None = None
    intent_subtype_hints: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return asdict(self)


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


@dataclass(frozen=True)
class PatternEmbeddingRecord:
    embedding_id: str
    pattern_id: str
    embedding_model: str
    embedding_dimension: int
    pattern_hash: str
    vector: list[float]
    status: str
    created_at: str
    cache_hit: bool = False
    error: str | None = None

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class PatternCandidate:
    rank: int
    pattern_id: str
    article_id: str
    document_label: str
    event_type: str | None
    event_subtype: str | None
    ticker: str | None
    company_name: str | None
    score: float
    score_breakdown: JsonDict
    input_excerpt: str
    gold_output: JsonDict
    explanation_brief: str
    metadata: JsonDict

    def to_dict(self) -> JsonDict:
        return asdict(self)
