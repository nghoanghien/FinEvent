"""Few-shot pattern store and metadata-aware pattern selection."""

from __future__ import annotations

import math
from collections import defaultdict

from finevent.jsonl import read_jsonl
from finevent.patterns.models import (
    PatternCandidate,
    PatternEmbeddingRecord,
    PatternQuery,
    PatternRecord,
)
from finevent.rag.embeddings import EmbeddingClient, HashEmbeddingClient
from finevent.rag.tokenization import ascii_fold
from finevent.types import JsonDict, PathLike


class PatternStore:
    def __init__(
        self,
        *,
        patterns: list[PatternRecord],
        embeddings_by_pattern: dict[str, PatternEmbeddingRecord],
        query_embedding_client: EmbeddingClient | None = None,
    ) -> None:
        self.patterns = patterns
        self.patterns_by_id = {pattern.pattern_id: pattern for pattern in patterns}
        self.embeddings_by_pattern = embeddings_by_pattern
        model_name, dimension = _infer_embedding_shape(embeddings_by_pattern)
        self.query_embedding_client = query_embedding_client or HashEmbeddingClient(
            model_name=model_name,
            dimension=dimension,
        )

    @classmethod
    def from_artifacts(
        cls,
        *,
        patterns_path: PathLike = "data/patterns/patterns.jsonl",
        embeddings_path: PathLike = "data/patterns/pattern_embeddings.jsonl",
        query_embedding_client: EmbeddingClient | None = None,
    ) -> PatternStore:
        patterns = [_pattern_from_dict(record) for record in read_jsonl(patterns_path)]
        embeddings = [
            _embedding_from_dict(record)
            for record in read_jsonl(embeddings_path)
            if record.get("status") == "success"
        ]
        return cls(
            patterns=patterns,
            embeddings_by_pattern={record.pattern_id: record for record in embeddings},
            query_embedding_client=query_embedding_client,
        )

    def select_patterns(
        self,
        query: PatternQuery,
        *,
        top_k: int = 3,
        candidate_pool_size: int = 25,
        max_per_event_type: int = 2,
    ) -> list[PatternCandidate]:
        if top_k <= 0:
            return []
        query_vector = self.query_embedding_client.embed_texts([query.text])[0]
        scored = [
            self._candidate_from_pattern(pattern, query, query_vector)
            for pattern in self.patterns
            if pattern.pattern_id in self.embeddings_by_pattern
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        selected = _diversify(
            scored[:candidate_pool_size],
            top_k=min(top_k, 5),
            max_per_event_type=max_per_event_type,
        )
        return [
            PatternCandidate(**{**candidate.to_dict(), "rank": rank})
            for rank, candidate in enumerate(selected, start=1)
        ]

    def _candidate_from_pattern(
        self,
        pattern: PatternRecord,
        query: PatternQuery,
        query_vector: list[float],
    ) -> PatternCandidate:
        embedding = self.embeddings_by_pattern[pattern.pattern_id]
        dense_score = (_cosine_similarity(query_vector, embedding.vector) + 1.0) / 2.0
        metadata_score = _metadata_score(query, pattern)
        rule_score = _rule_score(query, pattern)
        score = 0.60 * dense_score + 0.30 * metadata_score + 0.10 * rule_score
        breakdown = {
            "dense_score": round(dense_score, 6),
            "metadata_score": round(metadata_score, 6),
            "rule_score": round(rule_score, 6),
            "weights": {
                "dense": 0.60,
                "metadata": 0.30,
                "rule": 0.10,
            },
        }
        return PatternCandidate(
            rank=0,
            pattern_id=pattern.pattern_id,
            article_id=pattern.article_id,
            document_label=pattern.document_label,
            event_type=pattern.event_type,
            event_subtype=pattern.event_subtype,
            ticker=pattern.ticker,
            company_name=pattern.company_name,
            score=round(score, 6),
            score_breakdown=breakdown,
            input_excerpt=pattern.input_excerpt,
            gold_output=pattern.gold_output,
            explanation_brief=pattern.explanation_brief,
            metadata=pattern.metadata,
        )


def _metadata_score(query: PatternQuery, pattern: PatternRecord) -> float:
    score = 0.0
    query_tickers = {ticker.upper() for ticker in query.tickers}
    pattern_tickers = _upper_set([pattern.ticker, *_metadata_list(pattern, "tickers_hint")])
    if query_tickers and query_tickers & pattern_tickers:
        score += 0.30

    query_companies = _folded_set(query.company_names)
    pattern_companies = _folded_set(
        [pattern.company_name, *_metadata_list(pattern, "company_names_hint")]
    )
    if query_companies and query_companies & pattern_companies:
        score += 0.20

    query_types = {event_type.upper() for event_type in query.event_type_hints}
    if query_types and pattern.event_type and pattern.event_type.upper() in query_types:
        score += 0.25

    query_subtypes = {subtype.upper() for subtype in query.event_subtype_hints}
    if query_subtypes and pattern.event_subtype and pattern.event_subtype.upper() in query_subtypes:
        score += 0.10

    query_keywords = _folded_set(query.event_keywords)
    pattern_keywords = _folded_set(_metadata_list(pattern, "event_keywords"))
    if query_keywords and pattern_keywords:
        score += 0.15 * len(query_keywords & pattern_keywords) / len(query_keywords)

    if query.document_label_hint and query.document_label_hint == pattern.document_label:
        score += 0.10
    return min(score, 1.0)


def _rule_score(query: PatternQuery, pattern: PatternRecord) -> float:
    is_event_specific = bool(
        query.tickers
        or query.company_names
        or query.event_keywords
        or query.event_type_hints
        or query.event_subtype_hints
    )
    score = 0.0
    if pattern.document_label == "NO_EVENT":
        score += 0.35 if not is_event_specific else -0.20
    if pattern.document_label == "HAS_EVENT" and is_event_specific:
        score += 0.20
    if pattern.evidence_span:
        score += 0.10
    if pattern.event_type == "OTHER":
        score -= 0.10
    return max(0.0, min(1.0, score))


def _diversify(
    candidates: list[PatternCandidate],
    *,
    top_k: int,
    max_per_event_type: int,
) -> list[PatternCandidate]:
    selected: list[PatternCandidate] = []
    type_counts: dict[str, int] = defaultdict(int)
    for candidate in candidates:
        type_key = candidate.event_type or candidate.document_label
        if type_counts[type_key] >= max_per_event_type:
            continue
        selected.append(candidate)
        type_counts[type_key] += 1
        if len(selected) >= top_k:
            return selected

    selected_ids = {candidate.pattern_id for candidate in selected}
    for candidate in candidates:
        if candidate.pattern_id in selected_ids:
            continue
        selected.append(candidate)
        if len(selected) >= top_k:
            break
    return selected


def _pattern_from_dict(record: JsonDict) -> PatternRecord:
    return PatternRecord(
        pattern_id=str(record["pattern_id"]),
        article_id=str(record["article_id"]),
        document_label=str(record["document_label"]),
        pattern_kind=str(record["pattern_kind"]),
        input_excerpt=str(record["input_excerpt"]),
        gold_output=dict(record["gold_output"]),
        pattern_text=str(record["pattern_text"]),
        source=str(record.get("source") or ""),
        url=str(record.get("url") or ""),
        published_at=record.get("published_at"),
        teacher_model=str(record.get("teacher_model") or "unknown_teacher"),
        teacher_prompt_version=str(record.get("teacher_prompt_version") or ""),
        auto_validation_status=str(record.get("auto_validation_status") or "PASS"),
        validation_errors=list(record.get("validation_errors", [])),
        event_id=record.get("event_id"),
        event_type=record.get("event_type"),
        event_subtype=record.get("event_subtype"),
        ticker=record.get("ticker"),
        company_name=record.get("company_name"),
        impact_sentiment=record.get("impact_sentiment"),
        evidence_span=record.get("evidence_span"),
        event_arguments=dict(record.get("event_arguments", {})),
        explanation_brief=str(record.get("explanation_brief") or ""),
        metadata=dict(record.get("metadata", {})),
        version=str(record.get("version") or "m05_v1"),
    )


def _embedding_from_dict(record: JsonDict) -> PatternEmbeddingRecord:
    return PatternEmbeddingRecord(
        embedding_id=str(record["embedding_id"]),
        pattern_id=str(record["pattern_id"]),
        embedding_model=str(record["embedding_model"]),
        embedding_dimension=int(record.get("embedding_dimension") or len(record.get("vector", []))),
        pattern_hash=str(record["pattern_hash"]),
        vector=[float(value) for value in record.get("vector", [])],
        status=str(record.get("status") or "success"),
        created_at=str(record.get("created_at") or ""),
        cache_hit=bool(record.get("cache_hit", False)),
        error=record.get("error"),
    )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _infer_embedding_shape(records: dict[str, PatternEmbeddingRecord]) -> tuple[str, int]:
    for record in records.values():
        return record.embedding_model, record.embedding_dimension
    return "local_hash_embedding_v1", 128


def _metadata_list(pattern: PatternRecord, key: str) -> list[object]:
    value = pattern.metadata.get(key, [])
    return value if isinstance(value, list) else []


def _upper_set(values: object) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(value).upper() for value in values if value}


def _folded_set(values: object) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {ascii_fold(str(value)).lower() for value in values if value}
