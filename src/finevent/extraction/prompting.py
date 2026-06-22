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
    max_article_chars: int = 2200,
    max_context_chars: int = 450,
    max_pattern_excerpt_chars: int = 350,
    max_pattern_output_chars: int = 700,
    max_prompt_chars: int = 11000,
) -> str:
    attempts = [
        (
            contexts,
            patterns,
            max_article_chars,
            max_context_chars,
            max_pattern_excerpt_chars,
            max_pattern_output_chars,
        ),
        (
            contexts[:3],
            patterns[:2],
            min(max_article_chars, 1600),
            min(max_context_chars, 320),
            min(max_pattern_excerpt_chars, 260),
            min(max_pattern_output_chars, 520),
        ),
        (
            contexts[:1],
            patterns[:1],
            min(max_article_chars, 1200),
            min(max_context_chars, 240),
            min(max_pattern_excerpt_chars, 220),
            min(max_pattern_output_chars, 420),
        ),
        ([], [], min(max_article_chars, 1000), 0, 0, 0),
    ]
    last_prompt = ""
    for (
        attempt_contexts,
        attempt_patterns,
        attempt_article_chars,
        attempt_context_chars,
        attempt_pattern_excerpt_chars,
        attempt_pattern_output_chars,
    ) in attempts:
        last_prompt = _render_prompt(
            article=article,
            contexts=attempt_contexts,
            patterns=attempt_patterns,
            prompt_version=prompt_version,
            max_article_chars=attempt_article_chars,
            max_context_chars=attempt_context_chars,
            max_pattern_excerpt_chars=attempt_pattern_excerpt_chars,
            max_pattern_output_chars=attempt_pattern_output_chars,
        )
        if len(last_prompt) <= max_prompt_chars:
            return last_prompt
    return last_prompt


def _render_prompt(
    *,
    article: JsonDict,
    contexts: list[RetrievalCandidate],
    patterns: list[PatternCandidate],
    prompt_version: str,
    max_article_chars: int,
    max_context_chars: int,
    max_pattern_excerpt_chars: int,
    max_pattern_output_chars: int,
) -> str:
    payload = {
        "prompt_version": prompt_version,
        "task": "Vietnamese financial corporate event extraction",
        "output_schema": _output_schema_view(),
        "taxonomy": _relevant_taxonomy_view(article, contexts, patterns),
        "grounding_rules": [
            "Return only valid JSON. Do not wrap output in markdown.",
            "Extract only concrete corporate events about listed or potentially listed companies.",
            "Every event must include evidence_span copied from the input article.",
            "Do not infer values that are not supported by the article or retrieved contexts.",
            "impact_sentiment is direction only: POSITIVE, NEGATIVE, NEUTRAL, or MIXED.",
            "If the article is generic market commentary, return document_label=NO_EVENT.",
        ],
        "retrieved_contexts": [
            _context_view(context, max_text_chars=max_context_chars) for context in contexts
        ],
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
            "text": _trim(str(article.get("text") or ""), max_chars=max_article_chars),
        },
    }
    few_shot_block = (
        render_few_shot_patterns(
            patterns,
            max_excerpt_chars=max_pattern_excerpt_chars,
            max_output_chars=max_pattern_output_chars,
        )
        if patterns
        else "No few-shot patterns."
    )
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


def _relevant_taxonomy_view(
    article: JsonDict,
    contexts: list[RetrievalCandidate],
    patterns: list[PatternCandidate],
) -> JsonDict:
    taxonomy = load_event_taxonomy()
    relevant_types = {str(item).upper() for item in article.get("event_type_hints", [])}
    for context in contexts:
        metadata = context.metadata
        relevant_types.update(str(item).upper() for item in metadata.get("event_type_hints", []))
    relevant_types.update(
        str(pattern.event_type).upper() for pattern in patterns if pattern.event_type
    )
    relevant_types = {
        event_type for event_type in relevant_types if event_type in taxonomy.event_types
    }

    relevant_event_types: JsonDict = {}
    for event_type in sorted(relevant_types):
        relevant_event_types[event_type] = {
            "subtypes": sorted(taxonomy.allowed_subtypes(event_type)),
            "argument_fields": sorted(taxonomy.allowed_argument_fields(event_type)),
        }
    return {
        "schema_version": taxonomy.schema_version,
        "document_labels": sorted(taxonomy.document_labels),
        "impact_sentiments": sorted(taxonomy.impact_sentiments),
        "event_type_enum": sorted(taxonomy.event_types),
        "relevant_event_types": relevant_event_types,
    }


def _context_view(context: RetrievalCandidate, *, max_text_chars: int) -> JsonDict:
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
        "text": _trim(context.text, max_chars=max_text_chars),
    }


def _trim(text: str, *, max_chars: int) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."
