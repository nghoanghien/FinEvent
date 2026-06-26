"""Data models for retrieval and reranking."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from finevent.types import JsonDict


@dataclass(frozen=True)
class RetrievalQuery:
    query_id: str
    article_id: str
    text: str
    query_type: str
    weight: float = 1.0
    tickers: list[str] = field(default_factory=list)
    company_names: list[str] = field(default_factory=list)
    event_keywords: list[str] = field(default_factory=list)
    event_type_hints: list[str] = field(default_factory=list)
    event_subtype_hints: list[str] = field(default_factory=list)
    intent_key: str | None = None
    intent_event_type: str | None = None
    intent_subtype_hints: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalConfig:
    name: str
    dense_weight: float = 0.0
    bm25_weight: float = 0.0
    metadata_weight: float = 0.0
    recency_weight: float = 0.0
    rule_weight: float = 0.0
    llm_weight: float = 0.0
    top_k_stage1: int = 50
    top_k_final: int = 5
    per_article_limit: int = 3
    use_rule_rerank: bool = False
    use_llm_rerank: bool = False
    query_mode: str = "legacy"
    selection_strategy: str = "score"
    mmr_lambda: float = 0.72
    max_per_event_type: int = 3
    adaptive_top_k_final: bool = False
    top_k_single_event: int = 5
    top_k_two_events: int = 8
    top_k_multi_event: int = 10

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalCandidate:
    rank: int
    chunk_id: str
    article_id: str
    chunk_level: str
    title: str | None
    text: str
    source: str
    url: str
    published_at: str | None
    score: float
    score_breakdown: JsonDict
    metadata: JsonDict

    def to_dict(self) -> JsonDict:
        return asdict(self)


DEFAULT_RETRIEVAL_CONFIGS = {
    "bm25_only": RetrievalConfig(
        name="bm25_only",
        bm25_weight=1.0,
        top_k_stage1=50,
        top_k_final=5,
    ),
    "dense_only": RetrievalConfig(
        name="dense_only",
        dense_weight=1.0,
        top_k_stage1=50,
        top_k_final=5,
    ),
    "hybrid": RetrievalConfig(
        name="hybrid",
        dense_weight=0.55,
        bm25_weight=0.45,
        top_k_stage1=50,
        top_k_final=5,
    ),
    "metadata_aware_hybrid": RetrievalConfig(
        name="metadata_aware_hybrid",
        dense_weight=0.45,
        bm25_weight=0.30,
        metadata_weight=0.20,
        recency_weight=0.05,
        top_k_stage1=50,
        top_k_final=5,
    ),
    "rule_aware_rerank": RetrievalConfig(
        name="rule_aware_rerank",
        dense_weight=0.40,
        bm25_weight=0.25,
        metadata_weight=0.20,
        recency_weight=0.05,
        rule_weight=0.10,
        top_k_stage1=50,
        top_k_final=5,
        use_rule_rerank=True,
    ),
    "llm_reasoning_rerank": RetrievalConfig(
        name="llm_reasoning_rerank",
        dense_weight=0.25,
        bm25_weight=0.15,
        metadata_weight=0.10,
        recency_weight=0.00,
        rule_weight=0.10,
        llm_weight=0.40,
        top_k_stage1=20,
        top_k_final=5,
        use_rule_rerank=True,
        use_llm_rerank=True,
    ),
    "multi_event_aware_hybrid": RetrievalConfig(
        name="multi_event_aware_hybrid",
        dense_weight=0.42,
        bm25_weight=0.30,
        metadata_weight=0.18,
        recency_weight=0.04,
        rule_weight=0.06,
        top_k_stage1=75,
        top_k_final=10,
        per_article_limit=5,
        use_rule_rerank=True,
        query_mode="event_intent",
        selection_strategy="coverage_mmr",
        mmr_lambda=0.72,
        max_per_event_type=3,
        adaptive_top_k_final=True,
        top_k_single_event=5,
        top_k_two_events=8,
        top_k_multi_event=10,
    ),
}
