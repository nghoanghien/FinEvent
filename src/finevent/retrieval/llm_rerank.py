"""LLM reasoning rerank prompt and judgment utilities."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

from finevent.retrieval.models import RetrievalCandidate, RetrievalQuery
from finevent.types import JsonDict

RELEVANCE_LABEL_TO_SCORE = {
    "HIGH": 0.92,
    "MEDIUM": 0.72,
    "LOW": 0.45,
    "IRRELEVANT": 0.05,
}
DEFAULT_LISTWISE_HYBRID_WEIGHT = 0.35
DEFAULT_LISTWISE_LLM_WEIGHT = 0.65


class InvokableRerankModel(Protocol):
    def invoke(self, prompt: str) -> Any: ...


@dataclass(frozen=True)
class ListwiseRerankResult:
    candidates: list[RetrievalCandidate]
    prompt: str
    raw_output: str | None
    parsed_output: JsonDict
    ranked_candidate_ids: list[str]
    retry_count: int
    mode: str
    model_name: str

    def to_log_dict(self) -> JsonDict:
        return {
            "mode": self.mode,
            "model_name": self.model_name,
            "prompt_chars": len(self.prompt),
            "raw_output": self.raw_output,
            "parsed_output": self.parsed_output,
            "ranked_candidate_ids": self.ranked_candidate_ids,
            "retry_count": self.retry_count,
        }

    def to_summary_dict(self) -> JsonDict:
        return {
            "mode": self.mode,
            "model_name": self.model_name,
            "prompt_chars": len(self.prompt),
            "ranked_candidate_ids": self.ranked_candidate_ids,
            "retry_count": self.retry_count,
        }


def build_listwise_llm_rerank_prompt(
    *,
    query_article: JsonDict,
    queries: list[RetrievalQuery],
    candidates: list[RetrievalCandidate],
    max_query_article_chars: int = 0,
    max_candidate_chars: int = 0,
) -> str:
    """Build a RankGPT-style listwise prompt with compact source metadata."""
    payload = {
        "task": "listwise_financial_news_rerank",
        "query_article": {
            "article_id": query_article.get("article_id"),
            "title": query_article.get("title"),
            "source": query_article.get("source"),
            "url": query_article.get("url"),
            "published_at": query_article.get("published_at"),
            "tickers_hint": query_article.get("tickers_hint", []),
            "company_names_hint": query_article.get("company_names_hint", []),
            "event_keywords": query_article.get("event_keywords", []),
            "event_type_hints": query_article.get("event_type_hints", []),
            "text_excerpt": _truncate_chars(
                str(query_article.get("text") or ""),
                max_chars=max_query_article_chars,
            ),
        },
        "query_views": [query.to_dict() for query in queries],
        "instructions": [
            "Rank all candidates by true financial-event relevance to query_article.",
            (
                "Prefer same or directly related company/ticker, event type, "
                "evidence, and time context."
            ),
            (
                "Penalize generic market commentary, stock-price-only notes, "
                "and same-keyword but different-event content."
            ),
            (
                "Use candidate title, source, publication date, "
                "article_summary_preview, chunk text, and score_breakdown."
            ),
            "Return only valid JSON. Do not extract final events.",
        ],
        "response_schema": {
            "ranked_candidate_ids": "array of candidate_id values, most relevant first",
            "judgments": [
                {
                    "candidate_id": "number or string",
                    "chunk_id": "string",
                    "relevance_score": "number in [0, 1]",
                    "relevance_label": "HIGH | MEDIUM | LOW | IRRELEVANT",
                    "reasoning_summary": "short Vietnamese explanation grounded in metadata/text",
                    "evidence_span": "short copied span from candidate chunk, or null",
                }
            ],
        },
        "candidates": [
            _candidate_prompt_payload(
                candidate,
                candidate_id=index,
                max_candidate_chars=max_candidate_chars,
            )
            for index, candidate in enumerate(candidates, start=1)
        ],
    }
    return "\n".join(
        [
            "You are a strict Vietnamese financial-news listwise reranker.",
            "Return only valid JSON that follows response_schema.",
            json.dumps(payload, ensure_ascii=False, indent=2),
        ]
    )


def rerank_candidates_listwise(
    *,
    query_article: JsonDict,
    queries: list[RetrievalQuery],
    candidates: list[RetrievalCandidate],
    mode: str,
    model_name: str,
    top_n: int = 15,
    model: InvokableRerankModel | None = None,
    max_query_article_chars: int = 0,
    max_candidate_chars: int = 0,
    max_retries: int = 1,
    retry_sleep_seconds: float = 1.0,
) -> ListwiseRerankResult:
    selected_candidates = candidates[: max(top_n, 0)]
    prompt = build_listwise_llm_rerank_prompt(
        query_article=query_article,
        queries=queries,
        candidates=selected_candidates,
        max_query_article_chars=max_query_article_chars,
        max_candidate_chars=max_candidate_chars,
    )
    if not selected_candidates:
        return ListwiseRerankResult(
            candidates=[],
            prompt=prompt,
            raw_output=None,
            parsed_output={"ranked_candidate_ids": [], "judgments": []},
            ranked_candidate_ids=[],
            retry_count=0,
            mode=mode,
            model_name=model_name,
        )
    if mode == "deterministic":
        parsed_output = _deterministic_listwise_output(
            queries=queries,
            candidates=selected_candidates,
        )
        ranked_candidates = apply_listwise_rerank_output(
            candidates=candidates,
            parsed_output=parsed_output,
            mode=mode,
            model_name=model_name,
            top_n=top_n,
        )
        return ListwiseRerankResult(
            candidates=ranked_candidates,
            prompt=prompt,
            raw_output=None,
            parsed_output=parsed_output,
            ranked_candidate_ids=[
                str(item) for item in parsed_output.get("ranked_candidate_ids", [])
            ],
            retry_count=0,
            mode=mode,
            model_name=model_name,
        )
    if model is None:
        raise ValueError("A live rerank model is required when llm rerank mode is not off.")

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            raw_output = _content_from_response(model.invoke(prompt))
            parsed_output = parse_listwise_rerank_output(raw_output)
            ranked_candidates = apply_listwise_rerank_output(
                candidates=candidates,
                parsed_output=parsed_output,
                mode=mode,
                model_name=model_name,
                top_n=top_n,
            )
            return ListwiseRerankResult(
                candidates=ranked_candidates,
                prompt=prompt,
                raw_output=raw_output,
                parsed_output=parsed_output,
                ranked_candidate_ids=[
                    str(item) for item in parsed_output.get("ranked_candidate_ids", [])
                ],
                retry_count=attempt,
                mode=mode,
                model_name=model_name,
            )
        except Exception as exc:  # noqa: BLE001 - caller needs provider/parser retry.
            last_error = exc
            if attempt >= max_retries:
                break
            time.sleep(retry_sleep_seconds * (attempt + 1))
    if last_error is not None:
        raise RuntimeError(f"LLM listwise rerank failed: {last_error}") from last_error
    raise RuntimeError("LLM listwise rerank did not return a response.")


def parse_listwise_rerank_output(raw_output: object) -> JsonDict:
    parsed = _extract_json_value(raw_output)
    if isinstance(parsed, list):
        ranked_ids = parsed
        judgments: list[JsonDict] = []
    elif isinstance(parsed, dict):
        ranked_ids = (
            parsed.get("ranked_candidate_ids")
            or parsed.get("ranked_ids")
            or parsed.get("ranking")
            or parsed.get("ranked_chunk_ids")
        )
        judgments_raw = parsed.get("judgments", [])
        judgments = [item for item in judgments_raw if isinstance(item, dict)] if isinstance(
            judgments_raw, list
        ) else []
    else:
        raise ValueError("LLM rerank output must be a JSON object or array.")
    if not isinstance(ranked_ids, list) or not ranked_ids:
        raise ValueError("LLM rerank output must include ranked_candidate_ids.")
    return {
        "ranked_candidate_ids": [str(item) for item in ranked_ids],
        "judgments": judgments,
    }


def apply_listwise_rerank_output(
    *,
    candidates: list[RetrievalCandidate],
    parsed_output: JsonDict,
    mode: str,
    model_name: str,
    top_n: int,
    hybrid_weight: float = DEFAULT_LISTWISE_HYBRID_WEIGHT,
    llm_weight: float = DEFAULT_LISTWISE_LLM_WEIGHT,
) -> list[RetrievalCandidate]:
    selected_candidates = candidates[: max(top_n, 0)]
    tail_candidates = candidates[max(top_n, 0) :]
    candidate_by_id = _candidate_lookup(selected_candidates)
    ordered: list[RetrievalCandidate] = []
    seen_chunk_ids: set[str] = set()
    for raw_id in parsed_output.get("ranked_candidate_ids", []):
        candidate = candidate_by_id.get(str(raw_id))
        if candidate is None or candidate.chunk_id in seen_chunk_ids:
            continue
        ordered.append(candidate)
        seen_chunk_ids.add(candidate.chunk_id)
    for candidate in selected_candidates:
        if candidate.chunk_id not in seen_chunk_ids:
            ordered.append(candidate)
            seen_chunk_ids.add(candidate.chunk_id)

    judgments_by_id = _judgments_by_candidate_id(parsed_output, selected_candidates)
    max_original_score = max((candidate.score for candidate in selected_candidates), default=1.0)
    max_original_score = max_original_score or 1.0
    reranked: list[RetrievalCandidate] = []
    denominator = max(len(ordered), 1)
    for index, candidate in enumerate(ordered, start=1):
        rank_score = (denominator - index + 1) / denominator
        judgment = judgments_by_id.get(candidate.chunk_id, {})
        llm_score = _judgment_score(judgment) if judgment else rank_score
        original_normalized = candidate.score / max_original_score
        final_score = hybrid_weight * original_normalized + llm_weight * llm_score
        breakdown = {
            **candidate.score_breakdown,
            "llm_rank": index,
            "llm_relevance_score": round(float(llm_score), 6),
            "llm_relevance_label": judgment.get("relevance_label") if judgment else None,
            "llm_reasoning_summary": judgment.get("reasoning_summary") if judgment else None,
            "llm_rerank_mode": mode,
            "llm_rerank_model": model_name,
        }
        reranked.append(
            RetrievalCandidate(
                **{
                    **candidate.to_dict(),
                    "rank": index,
                    "score": round(final_score, 6),
                    "score_breakdown": breakdown,
                }
            )
        )
    return reranked + tail_candidates


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
                "text": candidate.text,
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


def _candidate_prompt_payload(
    candidate: RetrievalCandidate,
    *,
    candidate_id: int,
    max_candidate_chars: int,
) -> JsonDict:
    metadata = candidate.metadata if isinstance(candidate.metadata, dict) else {}
    source_metadata = metadata.get("source_metadata")
    if not isinstance(source_metadata, dict):
        source_metadata = {}
    return {
        "candidate_id": candidate_id,
        "chunk_id": candidate.chunk_id,
        "article_id": candidate.article_id,
        "source_article": {
            "title": candidate.title,
            "source": candidate.source,
            "url": candidate.url,
            "published_at": candidate.published_at,
            "article_summary_preview": _truncate_chars(
                str(metadata.get("article_summary_preview") or ""),
                max_chars=max_candidate_chars,
            ),
        },
        "chunk": {
            "level": candidate.chunk_level,
            "text": _truncate_chars(candidate.text, max_chars=max_candidate_chars),
            "paragraph_start": metadata.get("paragraph_start"),
            "paragraph_end": metadata.get("paragraph_end"),
        },
        "metadata": {
            "tickers_hint": metadata.get("tickers_hint", []),
            "company_names_hint": metadata.get("company_names_hint", []),
            "sector_hints": metadata.get("sector_hints", []),
            "event_keywords": metadata.get("event_keywords", []),
            "event_type_hints": metadata.get("event_type_hints", []),
            "event_subtype_hints": metadata.get("event_subtype_hints", []),
            "pattern_refs": _compact_pattern_refs(
                metadata.get("pattern_refs", []),
                max_chars=max_candidate_chars,
            ),
            "chunk_representation": source_metadata.get("representation"),
        },
        "score_breakdown": candidate.score_breakdown,
    }


def _compact_pattern_refs(value: object, *, max_chars: int) -> list[JsonDict]:
    if not isinstance(value, list):
        return []
    refs: list[JsonDict] = []
    for item in value[:3]:
        if not isinstance(item, dict):
            continue
        refs.append(
            {
                "pattern_id": item.get("pattern_id"),
                "event_type": item.get("event_type"),
                "event_subtype": item.get("event_subtype"),
                "evidence_span": _truncate_chars(
                    str(item.get("evidence_span") or ""),
                    max_chars=max_chars,
                ),
            }
        )
    return refs


def _deterministic_listwise_output(
    *,
    queries: list[RetrievalQuery],
    candidates: list[RetrievalCandidate],
) -> JsonDict:
    query = queries[0] if queries else RetrievalQuery(
        query_id="deterministic",
        article_id="deterministic",
        text="",
        query_type="deterministic",
    )
    judgments = deterministic_reasoning_judgments(query=query, candidates=candidates)
    judgments.sort(key=_judgment_score, reverse=True)
    return {
        "ranked_candidate_ids": [
            _candidate_id_for_chunk(candidates, str(judgment["candidate_chunk_id"]))
            for judgment in judgments
        ],
        "judgments": judgments,
    }


def _candidate_id_for_chunk(candidates: list[RetrievalCandidate], chunk_id: str) -> str:
    for index, candidate in enumerate(candidates, start=1):
        if candidate.chunk_id == chunk_id:
            return str(index)
    return chunk_id


def _candidate_lookup(candidates: list[RetrievalCandidate]) -> dict[str, RetrievalCandidate]:
    lookup: dict[str, RetrievalCandidate] = {}
    for index, candidate in enumerate(candidates, start=1):
        lookup[str(index)] = candidate
        lookup[f"C{index}"] = candidate
        lookup[f"C{index:03d}"] = candidate
        lookup[candidate.chunk_id] = candidate
    return lookup


def _judgments_by_candidate_id(
    parsed_output: JsonDict,
    candidates: list[RetrievalCandidate],
) -> dict[str, JsonDict]:
    lookup = _candidate_lookup(candidates)
    judgments_by_chunk_id: dict[str, JsonDict] = {}
    raw_judgments = parsed_output.get("judgments", [])
    if not isinstance(raw_judgments, list):
        return judgments_by_chunk_id
    for judgment in raw_judgments:
        if not isinstance(judgment, dict):
            continue
        raw_id = (
            judgment.get("candidate_id")
            or judgment.get("candidate_chunk_id")
            or judgment.get("chunk_id")
        )
        candidate = lookup.get(str(raw_id))
        if candidate is None:
            continue
        judgments_by_chunk_id[candidate.chunk_id] = judgment
    return judgments_by_chunk_id


def _extract_json_value(raw_output: object) -> object:
    if isinstance(raw_output, dict | list):
        return raw_output
    text = str(raw_output).strip()
    if not text:
        raise ValueError("LLM rerank output is empty.")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.search(
        r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced:
        return json.loads(fenced.group(1))
    object_start = text.find("{")
    array_start = text.find("[")
    starts = [index for index in [object_start, array_start] if index >= 0]
    if not starts:
        raise ValueError("LLM rerank output does not contain JSON.")
    start = min(starts)
    end_char = "}" if text[start] == "{" else "]"
    end = text.rfind(end_char)
    if end <= start:
        raise ValueError("LLM rerank output JSON is incomplete.")
    return json.loads(text[start : end + 1])


def _content_from_response(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, list):
        return "\n".join(str(part) for part in content)
    if isinstance(content, dict):
        return json.dumps(content, ensure_ascii=False)
    return str(content)


def _truncate_chars(text: str, *, max_chars: int) -> str:
    if max_chars <= 0:
        return text
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def _judgment_score(judgment: JsonDict) -> float:
    value = judgment.get("relevance_score")
    if isinstance(value, int | float) and not isinstance(value, bool):
        return max(0.0, min(1.0, float(value)))
    label = str(judgment.get("relevance_label") or "IRRELEVANT").upper()
    return RELEVANCE_LABEL_TO_SCORE.get(label, 0.0)
