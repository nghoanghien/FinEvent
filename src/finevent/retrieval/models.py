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
}
