"""Final context selection strategies for retrieval candidates."""

from __future__ import annotations

import re
from collections import Counter

from finevent.retrieval.models import RetrievalCandidate, RetrievalConfig, RetrievalQuery
from finevent.types import JsonDict

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+")
COVERAGE_BONUS = 0.14
EVENT_OVERFLOW_PENALTY = 0.08


def select_final_candidates(
    candidates: list[RetrievalCandidate],
    queries: list[RetrievalQuery],
    config: RetrievalConfig,
) -> list[RetrievalCandidate]:
    target_k = target_context_count(queries, config)
    if target_k <= 0:
        return []
    if config.selection_strategy == "coverage_mmr":
        return _select_coverage_mmr(candidates, queries, config, target_k=target_k)
    return candidates[:target_k]


def target_context_count(queries: list[RetrievalQuery], config: RetrievalConfig) -> int:
    if not config.adaptive_top_k_final:
        return config.top_k_final
    event_type_count = len(_query_event_types(queries))
    if event_type_count <= 1:
        return min(config.top_k_final, config.top_k_single_event)
    if event_type_count == 2:
        return min(config.top_k_final, config.top_k_two_events)
    return min(config.top_k_final, config.top_k_multi_event)


def _select_coverage_mmr(
    candidates: list[RetrievalCandidate],
    queries: list[RetrievalQuery],
    config: RetrievalConfig,
    *,
    target_k: int,
) -> list[RetrievalCandidate]:
    if not candidates:
        return []

    query_event_types = _query_event_types(queries)
    max_score = max((candidate.score for candidate in candidates), default=1.0) or 1.0
    selected: list[tuple[RetrievalCandidate, JsonDict]] = []
    remaining = list(candidates)
    event_type_counts: Counter[str] = Counter()

    while remaining and len(selected) < target_k:
        eligible = [
            candidate
            for candidate in remaining
            if not _exceeds_event_limit(candidate, query_event_types, event_type_counts, config)
        ]
        pool = eligible or remaining
        best_candidate: RetrievalCandidate | None = None
        best_info: JsonDict | None = None
        best_score = float("-inf")
        covered_types = {event_type for event_type, count in event_type_counts.items() if count > 0}

        for candidate in pool:
            candidate_types = _candidate_event_types(candidate, query_event_types)
            relevance = candidate.score / max_score
            similarity_penalty = _max_text_similarity(
                candidate,
                [selected_candidate for selected_candidate, _ in selected],
            )
            new_types = sorted(candidate_types - covered_types)
            coverage_bonus = COVERAGE_BONUS if new_types else 0.0
            overflow_penalty = _event_overflow_penalty(candidate_types, event_type_counts, config)
            selection_score = (
                config.mmr_lambda * relevance
                + (1.0 - config.mmr_lambda) * (1.0 - similarity_penalty)
                + coverage_bonus
                - overflow_penalty
            )
            if selection_score > best_score:
                best_candidate = candidate
                best_score = selection_score
                best_info = {
                    "selection_score": round(selection_score, 6),
                    "selection_strategy": config.selection_strategy,
                    "normalized_relevance": round(relevance, 6),
                    "coverage_bonus": round(coverage_bonus, 6),
                    "diversity_penalty": round(similarity_penalty, 6),
                    "event_overflow_penalty": round(overflow_penalty, 6),
                    "covered_new_event_types": new_types,
                }

        if best_candidate is None or best_info is None:
            break
        selected.append((best_candidate, best_info))
        for event_type in _candidate_event_types(best_candidate, query_event_types):
            event_type_counts[event_type] += 1
        remaining = [
            candidate
            for candidate in remaining
            if candidate.chunk_id != best_candidate.chunk_id
        ]

    return [
        _with_selection_metadata(candidate, rank=rank, selection_info=selection_info)
        for rank, (candidate, selection_info) in enumerate(selected, start=1)
    ]


def _with_selection_metadata(
    candidate: RetrievalCandidate,
    *,
    rank: int,
    selection_info: JsonDict,
) -> RetrievalCandidate:
    data = candidate.to_dict()
    breakdown = dict(data.get("score_breakdown") or {})
    breakdown.update(selection_info)
    data["rank"] = rank
    data["score_breakdown"] = breakdown
    return RetrievalCandidate(**data)


def _query_event_types(queries: list[RetrievalQuery]) -> set[str]:
    event_types = {
        str(query.intent_event_type).upper()
        for query in queries
        if query.intent_event_type
    }
    if event_types:
        return event_types
    return {
        str(event_type).upper()
        for query in queries
        for event_type in query.event_type_hints
        if event_type
    }


def _candidate_event_types(
    candidate: RetrievalCandidate,
    query_event_types: set[str],
) -> set[str]:
    breakdown_types = {
        str(event_type).upper()
        for event_type in candidate.score_breakdown.get("matched_intent_event_types", [])
        if event_type
    }
    metadata_types = {
        str(event_type).upper()
        for event_type in candidate.metadata.get("event_type_hints", [])
        if event_type
    }
    event_types = breakdown_types or metadata_types
    if query_event_types:
        matched = event_types & query_event_types
        if matched:
            return matched
    return event_types


def _exceeds_event_limit(
    candidate: RetrievalCandidate,
    query_event_types: set[str],
    event_type_counts: Counter[str],
    config: RetrievalConfig,
) -> bool:
    if len(query_event_types) <= 1 or config.max_per_event_type <= 0:
        return False
    candidate_types = _candidate_event_types(candidate, query_event_types)
    if not candidate_types:
        return False
    return all(
        event_type_counts[event_type] >= config.max_per_event_type
        for event_type in candidate_types
    )


def _event_overflow_penalty(
    candidate_types: set[str],
    event_type_counts: Counter[str],
    config: RetrievalConfig,
) -> float:
    if not candidate_types or config.max_per_event_type <= 0:
        return 0.0
    overflow = max(
        max(0, event_type_counts[event_type] - config.max_per_event_type + 1)
        for event_type in candidate_types
    )
    return EVENT_OVERFLOW_PENALTY * overflow


def _max_text_similarity(
    candidate: RetrievalCandidate,
    selected: list[RetrievalCandidate],
) -> float:
    if not selected:
        return 0.0
    candidate_tokens = _tokens(candidate.text)
    if not candidate_tokens:
        return 0.0
    return max(_jaccard(candidate_tokens, _tokens(item.text)) for item in selected)


def _tokens(text: str) -> set[str]:
    return {match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text)}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
