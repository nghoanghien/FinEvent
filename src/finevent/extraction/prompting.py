"""Prompt construction for schema-guided event extraction."""

from __future__ import annotations

import json

from finevent.ingestion.text import normalize_text
from finevent.patterns.models import PatternCandidate
from finevent.patterns.prompting import render_few_shot_patterns
from finevent.retrieval.models import RetrievalCandidate
from finevent.schema.taxonomy import load_event_taxonomy
from finevent.types import JsonDict


def build_extraction_prompt(
    *,
    article: JsonDict,
    contexts: list[RetrievalCandidate],
    patterns: list[PatternCandidate],
    prompt_version: str,
) -> str:
    payload = {
        "prompt_version": prompt_version,
        "task": "Vietnamese financial corporate event extraction",
        "output_schema": _output_schema_view(),
        "taxonomy": load_event_taxonomy().compact_prompt_view(),
        "grounding_rules": [
            "Return only valid JSON. Do not wrap output in markdown.",
            "Extract only concrete corporate events about listed or potentially listed companies.",
            "Every event must include evidence_span copied from the input article.",
            "Do not infer values that are not supported by the article or retrieved contexts.",
            "impact_sentiment is direction only: POSITIVE, NEGATIVE, NEUTRAL, or MIXED.",
            "If the article is generic market commentary, return document_label=NO_EVENT.",
        ],
        "retrieved_contexts": [_context_view(context) for context in contexts],
        "input_article": {
            "article_id": article.get("article_id"),
            "title": article.get("title"),
            "source": article.get("source"),
            "url": article.get("url"),
            "published_at": article.get("published_at"),
            "tickers_hint": article.get("tickers_hint", []),
            "company_names_hint": article.get("company_names_hint", []),
            "event_keywords": article.get("event_keywords", []),
            "event_type_hints": article.get("event_type_hints", []),
            "event_subtype_hints": article.get("event_subtype_hints", []),
            "text": _trim(str(article.get("text") or ""), max_chars=6500),
        },
    }
    few_shot_block = render_few_shot_patterns(patterns) if patterns else "No few-shot patterns."
    return "\n".join(
        [
            "You are a strict Vietnamese financial event extraction model.",
            "Use the schema, taxonomy, retrieved contexts, and patterns below.",
            "Few-shot patterns:",
            few_shot_block,
            "Extraction payload:",
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        ]
    )


def _output_schema_view() -> JsonDict:
    return {
        "article_id": "string",
        "document_label": "HAS_EVENT | NO_EVENT | UNCERTAIN",
        "events": [
            {
                "event_id": "string",
                "ticker": "string or null",
                "company_name": "string or null",
                "event_type": "taxonomy enum",
                "event_subtype": "taxonomy subtype enum or null",
                "event_summary": "short Vietnamese summary",
                "event_arguments": "object with taxonomy-compatible slot keys",
                "impact_sentiment": "POSITIVE | NEGATIVE | NEUTRAL | MIXED",
                "evidence_span": "exact span from article",
                "source_url": "string",
                "published_at": "string or null",
                "confidence": "number in [0, 1]",
            }
        ],
        "warnings": "array of strings",
        "model_info": {
            "model_name": "string",
            "prompt_version": "string",
            "run_id": "string",
        },
    }


def _context_view(context: RetrievalCandidate) -> JsonDict:
    return {
        "rank": context.rank,
        "chunk_id": context.chunk_id,
        "article_id": context.article_id,
        "title": context.title,
        "source": context.source,
        "url": context.url,
        "published_at": context.published_at,
        "score": context.score,
        "metadata": context.metadata,
        "text": _trim(context.text, max_chars=1400),
    }


def _trim(text: str, *, max_chars: int) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."
