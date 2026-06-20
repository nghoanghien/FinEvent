"""LLM reasoning rerank prompt and deterministic judgment utilities."""

from __future__ import annotations

import json

from finevent.retrieval.models import RetrievalCandidate, RetrievalQuery
from finevent.types import JsonDict

RELEVANCE_LABEL_TO_SCORE = {
    "HIGH": 0.92,
    "MEDIUM": 0.72,
    "LOW": 0.45,
    "IRRELEVANT": 0.05,
}


def build_llm_reasoning_rerank_prompt(
    *,
    query: RetrievalQuery,
    candidates: list[RetrievalCandidate],
) -> str:
    payload = {
        "query": query.to_dict(),
        "candidate_schema": {
            "candidate_chunk_id": "string",
            "has_corporate_event": "boolean",
            "candidate_event_type": "string or null",
            "same_or_related_company": "boolean",
            "same_or_related_event_type": "boolean",
            "reasoning_summary": "short Vietnamese explanation",
            "evidence_span": "text span copied from candidate, or null",
            "relevance_label": "HIGH | MEDIUM | LOW | IRRELEVANT",
            "relevance_score": "number in [0, 1]",
        },
        "instructions": [
            "Read each candidate carefully.",
            "Check whether it contains a concrete corporate event.",
            "Prefer candidates with same ticker/company, same event type, and grounded evidence.",
            "Penalize generic market commentary or stock-price-only news.",
            "Return only JSON with a judgments array.",
        ],
        "candidates": [
            {
                "chunk_id": candidate.chunk_id,
                "article_id": candidate.article_id,
                "title": candidate.title,
                "chunk_level": candidate.chunk_level,
                "metadata": candidate.metadata,
                "text": candidate.text[:1800],
                "score_breakdown": candidate.score_breakdown,
            }
            for candidate in candidates
        ],
    }
    return "\n".join(
        [
            "You are a strict financial-news relevance reranker.",
            "Return only valid JSON. Do not extract final events.",
            json.dumps(payload, ensure_ascii=False, indent=2),
        ]
    )


def apply_llm_reasoning_judgments(
    candidates: list[RetrievalCandidate],
    judgments: list[JsonDict],
    *,
    hybrid_weight: float = 0.40,
    llm_weight: float = 0.60,
) -> list[RetrievalCandidate]:
    judgments_by_chunk = {
        str(judgment.get("candidate_chunk_id") or judgment.get("chunk_id")): judgment
        for judgment in judgments
    }
    reranked: list[RetrievalCandidate] = []
    for candidate in candidates:
        judgment = judgments_by_chunk.get(candidate.chunk_id, {})
        llm_score = _judgment_score(judgment)
        score = hybrid_weight * candidate.score + llm_weight * llm_score
        breakdown = {
            **candidate.score_breakdown,
            "llm_relevance_score": round(llm_score, 6),
            "llm_relevance_label": judgment.get("relevance_label"),
            "llm_reasoning_summary": judgment.get("reasoning_summary"),
        }
        reranked.append(
            RetrievalCandidate(
                **{
                    **candidate.to_dict(),
                    "rank": 0,
                    "score": round(score, 6),
                    "score_breakdown": breakdown,
                }
            )
        )
    reranked.sort(key=lambda item: item.score, reverse=True)
    return [
        RetrievalCandidate(**{**candidate.to_dict(), "rank": rank})
        for rank, candidate in enumerate(reranked, start=1)
    ]


def deterministic_reasoning_judgments(
    *,
    query: RetrievalQuery,
    candidates: list[RetrievalCandidate],
) -> list[JsonDict]:
    """Cheap local stand-in for tests and demos before a real LLM is connected."""
    judgments: list[JsonDict] = []
    query_tickers = {ticker.upper() for ticker in query.tickers}
    query_event_types = {event_type.upper() for event_type in query.event_type_hints}
    for candidate in candidates:
        candidate_tickers = {
            str(item).upper() for item in candidate.metadata.get("tickers_hint", [])
        }
        candidate_event_types = {
            str(item).upper() for item in candidate.metadata.get("event_type_hints", [])
        }
        same_company = bool(query_tickers & candidate_tickers)
        same_event_type = bool(query_event_types & candidate_event_types)
        has_event = bool(candidate.metadata.get("event_keywords") or candidate_event_types)
        if same_company and same_event_type and has_event:
            label = "HIGH"
        elif same_event_type or same_company:
            label = "MEDIUM"
        elif has_event:
            label = "LOW"
        else:
            label = "IRRELEVANT"
        judgments.append(
            {
                "candidate_chunk_id": candidate.chunk_id,
                "has_corporate_event": has_event,
                "candidate_event_type": next(iter(candidate_event_types), None),
                "same_or_related_company": same_company,
                "same_or_related_event_type": same_event_type,
                "reasoning_summary": "Deterministic metadata-based relevance judgment.",
                "evidence_span": candidate.text[:180] if has_event else None,
                "relevance_label": label,
                "relevance_score": RELEVANCE_LABEL_TO_SCORE[label],
            }
        )
    return judgments


def _judgment_score(judgment: JsonDict) -> float:
    value = judgment.get("relevance_score")
    if isinstance(value, int | float) and not isinstance(value, bool):
        return max(0.0, min(1.0, float(value)))
    label = str(judgment.get("relevance_label") or "IRRELEVANT").upper()
    return RELEVANCE_LABEL_TO_SCORE.get(label, 0.0)
