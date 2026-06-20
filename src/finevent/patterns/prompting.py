"""Prompt rendering helpers for selected few-shot event patterns."""

from __future__ import annotations

import json

from finevent.ingestion.text import normalize_text
from finevent.patterns.models import PatternCandidate


def render_few_shot_patterns(
    candidates: list[PatternCandidate],
    *,
    max_excerpt_chars: int = 900,
) -> str:
    if not candidates:
        return "No approved few-shot patterns are available."

    sections = [
        "Use these approved patterns as schema and evidence-following examples.",
        "Do not copy factual values from a pattern unless they also appear in the input article.",
    ]
    for candidate in candidates:
        label = candidate.event_type or candidate.document_label
        subtype = f"/{candidate.event_subtype}" if candidate.event_subtype else ""
        sections.extend(
            [
                "",
                f"### Pattern {candidate.rank}: {label}{subtype}",
                f"Score: {candidate.score:.6f}",
                "Input excerpt:",
                _trim(candidate.input_excerpt, max_excerpt_chars),
                "Expected output JSON:",
                json.dumps(candidate.gold_output, ensure_ascii=False, indent=2, sort_keys=True),
                "Why this pattern matters:",
                normalize_text(candidate.explanation_brief),
            ]
        )
    return "\n".join(sections).strip() + "\n"


def render_pattern_context_json(candidates: list[PatternCandidate]) -> dict:
    return {
        "patterns": [
            {
                "rank": candidate.rank,
                "pattern_id": candidate.pattern_id,
                "event_type": candidate.event_type,
                "event_subtype": candidate.event_subtype,
                "ticker": candidate.ticker,
                "company_name": candidate.company_name,
                "score": candidate.score,
                "score_breakdown": candidate.score_breakdown,
                "input_excerpt": candidate.input_excerpt,
                "gold_output": candidate.gold_output,
                "explanation_brief": candidate.explanation_brief,
            }
            for candidate in candidates
        ]
    }


def _trim(text: str, max_chars: int) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."
