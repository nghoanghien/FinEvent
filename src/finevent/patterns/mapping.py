"""Map approved event patterns onto retrieval chunks."""

from __future__ import annotations

from dataclasses import dataclass, replace

from finevent.patterns.models import PatternRecord
from finevent.rag.models import ChunkRecord
from finevent.rag.tokenization import ascii_fold
from finevent.types import JsonDict


@dataclass(frozen=True)
class ChunkPatternMappingResult:
    chunks: list[ChunkRecord]
    mappings: list[JsonDict]
    warnings: list[str]


def attach_patterns_to_chunks(
    *,
    chunks: list[ChunkRecord],
    patterns: list[PatternRecord],
) -> ChunkPatternMappingResult:
    chunks_by_article: dict[str, list[ChunkRecord]] = {}
    for chunk in chunks:
        chunks_by_article.setdefault(chunk.article_id, []).append(chunk)

    refs_by_chunk: dict[str, list[JsonDict]] = {chunk.chunk_id: [] for chunk in chunks}
    mappings: list[JsonDict] = []
    warnings: list[str] = []

    for pattern in patterns:
        candidates = chunks_by_article.get(pattern.article_id, [])
        if not candidates:
            warnings.append(f"pattern_article_missing:{pattern.pattern_id}:{pattern.article_id}")
            continue
        matches = _chunks_for_pattern(pattern, candidates)
        if not matches:
            warnings.append(f"pattern_chunk_missing:{pattern.pattern_id}:{pattern.article_id}")
            continue
        for chunk, match_strategy, match_score in matches:
            ref = _pattern_ref(pattern, match_strategy=match_strategy, match_score=match_score)
            refs_by_chunk[chunk.chunk_id].append(ref)
            mappings.append(
                {
                    **ref,
                    "chunk_id": chunk.chunk_id,
                    "article_id": chunk.article_id,
                    "chunk_level": chunk.chunk_level,
                }
            )
            if match_strategy == "document_fallback":
                warnings.append(f"pattern_document_fallback:{pattern.pattern_id}:{chunk.chunk_id}")

    enriched_chunks = [
        replace(chunk, pattern_refs=refs_by_chunk.get(chunk.chunk_id, [])) for chunk in chunks
    ]
    return ChunkPatternMappingResult(
        chunks=enriched_chunks,
        mappings=mappings,
        warnings=warnings,
    )


def _chunks_for_pattern(
    pattern: PatternRecord,
    chunks: list[ChunkRecord],
) -> list[tuple[ChunkRecord, str, float]]:
    if pattern.pattern_kind == "no_event":
        document = _document_chunk(chunks)
        return [(document, "document_no_event", 1.0)] if document is not None else []

    evidence = _fold(pattern.evidence_span or "")
    matches: list[tuple[ChunkRecord, str, float]] = []
    seen_chunk_ids: set[str] = set()
    if evidence:
        for level, strategy in (
            ("paragraph", "evidence_paragraph"),
            ("section", "evidence_section"),
            ("document", "evidence_document"),
        ):
            for chunk in chunks:
                if (
                    chunk.chunk_level == level
                    and chunk.chunk_id not in seen_chunk_ids
                    and evidence in _fold(chunk.text)
                ):
                    seen_chunk_ids.add(chunk.chunk_id)
                    matches.append((chunk, strategy, 1.0))
        if matches:
            return matches

    document = _document_chunk(chunks)
    if document is not None:
        return [(document, "document_fallback", 0.0)]
    if chunks:
        return [(chunks[0], "first_chunk_fallback", 0.0)]
    return []


def _document_chunk(chunks: list[ChunkRecord]) -> ChunkRecord | None:
    for chunk in chunks:
        if chunk.chunk_level == "document":
            return chunk
    return None


def _pattern_ref(
    pattern: PatternRecord,
    *,
    match_strategy: str,
    match_score: float,
) -> JsonDict:
    return {
        "pattern_id": pattern.pattern_id,
        "pattern_kind": pattern.pattern_kind,
        "document_label": pattern.document_label,
        "event_id": pattern.event_id,
        "event_type": pattern.event_type,
        "event_subtype": pattern.event_subtype,
        "ticker": pattern.ticker,
        "company_name": pattern.company_name,
        "impact_sentiment": pattern.impact_sentiment,
        "evidence_span": pattern.evidence_span,
        "explanation_brief": pattern.explanation_brief,
        "gold_output": pattern.gold_output,
        "event_arguments": pattern.event_arguments,
        "match_strategy": match_strategy,
        "match_score": round(match_score, 6),
    }


def _fold(text: str) -> str:
    return ascii_fold(text).lower()
