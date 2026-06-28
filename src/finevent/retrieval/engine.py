"""Retrieval engine with BM25, dense, hybrid and reranking strategies."""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path

from finevent.jsonl import read_jsonl
from finevent.rag.bm25 import Bm25Index, load_bm25_index
from finevent.rag.embeddings import EmbeddingClient, HashEmbeddingClient
from finevent.rag.models import ChunkRecord
from finevent.rag.pipeline import chunks_from_jsonl
from finevent.retrieval.llm_rerank import (
    apply_llm_reasoning_judgments,
    deterministic_reasoning_judgments,
)
from finevent.retrieval.models import (
    DEFAULT_RETRIEVAL_CONFIGS,
    RetrievalCandidate,
    RetrievalConfig,
    RetrievalQuery,
)
from finevent.retrieval.selection import select_final_candidates
from finevent.types import JsonDict, PathLike

GENERIC_MARKET_TERMS = {
    "gia co phieu",
    "thi truong",
    "vn-index",
    "nhan dinh",
    "khuyen nghi",
}
TRUSTED_SOURCE_BONUS = {
    "cafef": 0.05,
    "vietstock": 0.05,
    "hsx": 0.08,
    "hnx": 0.08,
}


class RetrievalEngine:
    def __init__(
        self,
        *,
        chunks: list[ChunkRecord],
        bm25_index: Bm25Index,
        embeddings_by_chunk: dict[str, JsonDict],
        query_embedding_client: EmbeddingClient | None = None,
    ):
        self.chunks = chunks
        self.chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        self.document_previews_by_article = {
            chunk.article_id: chunk.text[:900]
            for chunk in chunks
            if chunk.chunk_level == "document"
        }
        self.bm25_index = bm25_index
        self.embeddings_by_chunk = embeddings_by_chunk
        self.embedding_model, self.embedding_dimension = _infer_embedding_shape(embeddings_by_chunk)
        self.query_embedding_client = query_embedding_client or HashEmbeddingClient(
            model_name=self.embedding_model,
            dimension=self.embedding_dimension,
        )
        self._query_embedding_cache: dict[str, list[float]] = {}

    @classmethod
    def from_artifacts(
        cls,
        *,
        chunks_path: PathLike = "data/processed/chunks.jsonl",
        bm25_index_path: PathLike = "data/retrieval/bm25_index.pkl",
        embeddings_path: PathLike = "data/retrieval/chunk_embeddings.jsonl",
        query_embedding_client: EmbeddingClient | None = None,
    ) -> RetrievalEngine:
        chunks = chunks_from_jsonl(chunks_path)
        bm25_index = load_bm25_index(bm25_index_path)
        embeddings_by_chunk = {
            str(record["chunk_id"]): record
            for record in read_jsonl(embeddings_path)
            if record.get("status") == "success"
        }
        return cls(
            chunks=chunks,
            bm25_index=bm25_index,
            embeddings_by_chunk=embeddings_by_chunk,
            query_embedding_client=query_embedding_client,
        )

    def retrieve(
        self,
        queries: list[RetrievalQuery],
        *,
        config: RetrievalConfig | str = "metadata_aware_hybrid",
        llm_judgments: list[JsonDict] | None = None,
        select_final: bool = True,
        apply_config_llm: bool = True,
    ) -> list[RetrievalCandidate]:
        retrieval_config = _resolve_config(config)
        score_state = self._collect_stage1_scores(queries, retrieval_config)
        candidates = [
            self._candidate_from_scores(chunk_id, score_breakdown, queries, retrieval_config)
            for chunk_id, score_breakdown in score_state.items()
            if chunk_id in self.chunks_by_id
        ]
        candidates = self._dedupe_candidates(candidates, retrieval_config)
        candidates.sort(key=lambda item: item.score, reverse=True)
        candidates = [
            RetrievalCandidate(**{**candidate.to_dict(), "rank": rank})
            for rank, candidate in enumerate(candidates, start=1)
        ]

        if apply_config_llm and retrieval_config.use_llm_rerank and candidates:
            judgments = llm_judgments
            if judgments is None:
                judgments = deterministic_reasoning_judgments(
                    query=queries[0],
                    candidates=candidates[: retrieval_config.top_k_stage1],
                )
            candidates = apply_llm_reasoning_judgments(
                candidates[: retrieval_config.top_k_stage1],
                judgments,
                hybrid_weight=1.0 - retrieval_config.llm_weight,
                llm_weight=retrieval_config.llm_weight,
            )

        if not select_final:
            return candidates
        return select_final_candidates(candidates, queries, retrieval_config)

    def _collect_stage1_scores(
        self,
        queries: list[RetrievalQuery],
        config: RetrievalConfig,
    ) -> dict[str, JsonDict]:
        score_state: dict[str, JsonDict] = defaultdict(_empty_score_breakdown)
        for query in queries:
            if config.bm25_weight > 0:
                self._merge_bm25_scores(query, config, score_state)
            if config.dense_weight > 0:
                self._merge_dense_scores(query, config, score_state)
            if config.metadata_weight > 0 or config.rule_weight > 0:
                self._merge_metadata_scores(query, score_state)
        return score_state

    def _merge_bm25_scores(
        self,
        query: RetrievalQuery,
        config: RetrievalConfig,
        score_state: dict[str, JsonDict],
    ) -> None:
        results = self.bm25_index.search(query.text, top_k=config.top_k_stage1)
        max_score = max((result.score for result in results), default=0.0)
        for result in results:
            normalized_score = result.score / max_score if max_score else 0.0
            state = score_state[result.chunk_id]
            state["bm25_score"] = max(state["bm25_score"], normalized_score * query.weight)
            _record_query_match(state, query)

    def _merge_dense_scores(
        self,
        query: RetrievalQuery,
        config: RetrievalConfig,
        score_state: dict[str, JsonDict],
    ) -> None:
        query_vector = self._embed_query(query)
        scored: list[tuple[str, float]] = []
        for chunk_id, embedding in self.embeddings_by_chunk.items():
            vector = [float(value) for value in embedding.get("vector", [])]
            if not vector:
                continue
            dense_score = _cosine_similarity(query_vector, vector)
            normalized_score = (dense_score + 1.0) / 2.0
            scored.append((chunk_id, normalized_score))
        scored.sort(key=lambda item: item[1], reverse=True)
        for chunk_id, score in scored[: config.top_k_stage1]:
            state = score_state[chunk_id]
            state["dense_score"] = max(state["dense_score"], score * query.weight)
            _record_query_match(state, query)

    def _embed_query(self, query: RetrievalQuery) -> list[float]:
        cache_key = f"{self.query_embedding_client.model_name}::{query.text}"
        cached = self._query_embedding_cache.get(cache_key)
        if cached is not None:
            return cached
        vector = self.query_embedding_client.embed_texts([query.text])[0]
        self._query_embedding_cache[cache_key] = vector
        return vector

    def _merge_metadata_scores(
        self,
        query: RetrievalQuery,
        score_state: dict[str, JsonDict],
    ) -> None:
        for chunk in self.chunks:
            metadata_score = _metadata_score(query, chunk)
            rule_score = _rule_score(query, chunk)
            if metadata_score <= 0 and rule_score <= 0:
                continue
            state = score_state[chunk.chunk_id]
            state["metadata_score"] = max(state["metadata_score"], metadata_score)
            state["rule_score"] = max(state["rule_score"], rule_score)
            _record_query_match(state, query)

    def _candidate_from_scores(
        self,
        chunk_id: str,
        score_breakdown: JsonDict,
        queries: list[RetrievalQuery],
        config: RetrievalConfig,
    ) -> RetrievalCandidate:
        chunk = self.chunks_by_id[chunk_id]
        recency_score = _source_recency_score(chunk)
        rule_score = float(score_breakdown["rule_score"]) if config.use_rule_rerank else 0.0
        score = (
            config.dense_weight * float(score_breakdown["dense_score"])
            + config.bm25_weight * float(score_breakdown["bm25_score"])
            + config.metadata_weight * float(score_breakdown["metadata_score"])
            + config.recency_weight * recency_score
            + config.rule_weight * rule_score
        )
        matched_query_types = sorted(score_breakdown["matched_query_types"])
        matched_intent_keys = sorted(score_breakdown["matched_intent_keys"])
        matched_intent_event_types = sorted(score_breakdown["matched_intent_event_types"])
        breakdown = {
            "dense_score": round(float(score_breakdown["dense_score"]), 6),
            "bm25_score": round(float(score_breakdown["bm25_score"]), 6),
            "metadata_score": round(float(score_breakdown["metadata_score"]), 6),
            "recency_score": round(recency_score, 6),
            "rule_score": round(rule_score, 6),
            "matched_query_types": matched_query_types,
            "matched_intent_keys": matched_intent_keys,
            "matched_intent_event_types": matched_intent_event_types,
            "retrieval_config": config.name,
            "query_mode": config.query_mode,
            "query_count": len(queries),
        }
        return RetrievalCandidate(
            rank=0,
            chunk_id=chunk.chunk_id,
            article_id=chunk.article_id,
            chunk_level=chunk.chunk_level,
            title=chunk.title,
            text=chunk.text,
            source=chunk.source,
            url=chunk.url,
            published_at=chunk.published_at,
            score=round(score, 6),
            score_breakdown=breakdown,
            metadata=_chunk_metadata(
                chunk,
                article_summary_preview=self.document_previews_by_article.get(chunk.article_id),
            ),
        )

    def _dedupe_candidates(
        self,
        candidates: list[RetrievalCandidate],
        config: RetrievalConfig,
    ) -> list[RetrievalCandidate]:
        candidates.sort(key=lambda item: item.score, reverse=True)
        seen_chunk_hashes: set[str] = set()
        per_article_counts: dict[str, int] = defaultdict(int)
        deduped: list[RetrievalCandidate] = []
        for candidate in candidates:
            chunk = self.chunks_by_id[candidate.chunk_id]
            if chunk.chunk_hash in seen_chunk_hashes:
                continue
            if per_article_counts[candidate.article_id] >= config.per_article_limit:
                continue
            seen_chunk_hashes.add(chunk.chunk_hash)
            per_article_counts[candidate.article_id] += 1
            deduped.append(candidate)
        return deduped


def _resolve_config(config: RetrievalConfig | str) -> RetrievalConfig:
    if isinstance(config, RetrievalConfig):
        return config
    if config not in DEFAULT_RETRIEVAL_CONFIGS:
        raise ValueError(f"Unknown retrieval config: {config}")
    return DEFAULT_RETRIEVAL_CONFIGS[config]


def _empty_score_breakdown() -> JsonDict:
    return {
        "dense_score": 0.0,
        "bm25_score": 0.0,
        "metadata_score": 0.0,
        "rule_score": 0.0,
        "matched_query_types": set(),
        "matched_intent_keys": set(),
        "matched_intent_event_types": set(),
    }


def _record_query_match(state: JsonDict, query: RetrievalQuery) -> None:
    state["matched_query_types"].add(query.query_type)
    if query.intent_key:
        state["matched_intent_keys"].add(query.intent_key)
    if query.intent_event_type:
        state["matched_intent_event_types"].add(query.intent_event_type.upper())


def _metadata_score(query: RetrievalQuery, chunk: ChunkRecord) -> float:
    score = 0.0
    query_tickers = {ticker.upper() for ticker in query.tickers}
    chunk_tickers = {ticker.upper() for ticker in chunk.tickers_hint}
    if query_tickers and query_tickers & chunk_tickers:
        score += 0.45

    query_companies = {company.lower() for company in query.company_names}
    chunk_companies = {company.lower() for company in chunk.company_names_hint}
    if query_companies and query_companies & chunk_companies:
        score += 0.25

    query_keywords = {keyword.lower() for keyword in query.event_keywords}
    chunk_keywords = {keyword.lower() for keyword in chunk.event_keywords}
    if query_keywords and chunk_keywords:
        score += 0.20 * len(query_keywords & chunk_keywords) / len(query_keywords)

    query_types = {event_type.upper() for event_type in query.event_type_hints}
    chunk_types = {event_type.upper() for event_type in chunk.event_type_hints}
    if query_types and query_types & chunk_types:
        score += 0.10
    return min(score, 1.0)


def _rule_score(query: RetrievalQuery, chunk: ChunkRecord) -> float:
    score = _metadata_score(query, chunk)
    text_lower = chunk.text.lower()
    if any(term in text_lower for term in GENERIC_MARKET_TERMS):
        score -= 0.25
    if chunk.chunk_level == "paragraph" and chunk.event_keywords:
        score += 0.10
    if len(chunk.text.split()) < 8:
        score -= 0.10
    return max(0.0, min(1.0, score))


def _source_recency_score(chunk: ChunkRecord) -> float:
    return TRUSTED_SOURCE_BONUS.get(chunk.source.lower(), 0.0)


def _chunk_metadata(chunk: ChunkRecord, *, article_summary_preview: str | None = None) -> JsonDict:
    return {
        "tickers_hint": chunk.tickers_hint,
        "company_names_hint": chunk.company_names_hint,
        "sector_hints": chunk.sector_hints,
        "event_keywords": chunk.event_keywords,
        "event_type_hints": chunk.event_type_hints,
        "event_subtype_hints": chunk.event_subtype_hints,
        "pattern_refs": chunk.pattern_refs,
        "paragraph_start": chunk.paragraph_start,
        "paragraph_end": chunk.paragraph_end,
        "article_summary_preview": article_summary_preview,
        "source_metadata": chunk.metadata,
    }


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _infer_embedding_shape(embeddings_by_chunk: dict[str, JsonDict]) -> tuple[str, int]:
    for record in embeddings_by_chunk.values():
        model = str(record.get("embedding_model") or "local_hash_embedding_v1")
        dimension = int(record.get("embedding_dimension") or len(record.get("vector", [])) or 128)
        return model, dimension
    return "local_hash_embedding_v1", 128


def artifacts_exist(
    *,
    chunks_path: PathLike,
    bm25_index_path: PathLike,
    embeddings_path: PathLike,
) -> bool:
    return (
        Path(chunks_path).exists()
        and Path(bm25_index_path).exists()
        and Path(embeddings_path).exists()
    )
