"""Milestone 03 RAG preparation pipeline."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from finevent.jsonl import read_jsonl, write_jsonl
from finevent.patterns.builder import build_patterns_from_gold
from finevent.patterns.mapping import attach_patterns_to_chunks
from finevent.rag.bm25 import build_bm25_index
from finevent.rag.chunking import build_corpus_chunks
from finevent.rag.embeddings import build_embedding_client, embed_chunks_with_cache
from finevent.rag.models import ChunkRecord
from finevent.rag.reporting import build_rag_preparation_summary, write_rag_preparation_summary
from finevent.rag.vector_store import write_vector_store_artifacts
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class RagPreparationResult:
    articles_path: Path
    chunks_path: Path
    embeddings_path: Path
    bm25_index_path: Path
    vector_manifest_path: Path
    patterns_path: Path
    rejected_patterns_path: Path
    chunk_patterns_path: Path
    report_path: Path
    article_count: int
    chunk_count: int
    embedding_count: int
    pattern_count: int
    rejected_pattern_count: int
    chunk_pattern_count: int


def run_rag_preparation(
    *,
    articles_path: PathLike = "data/processed/articles_clean.jsonl",
    gold_path: PathLike = "data/labels/events_gold.jsonl",
    chunks_output_path: PathLike = "data/processed/chunks.jsonl",
    patterns_output_path: PathLike = "data/patterns/patterns.jsonl",
    rejected_patterns_output_path: PathLike = "data/patterns/patterns_rejected.jsonl",
    chunk_patterns_output_path: PathLike = "data/processed/chunk_patterns.jsonl",
    retrieval_dir: PathLike = "data/retrieval",
    vector_store_dir: PathLike = "data/vector_store",
    report_path: PathLike = "reports/data/rag_preparation_summary.md",
    embedding_provider: str = "hash",
    embedding_model: str | None = None,
    embedding_dimension: int = 128,
    target_words: int = 420,
    max_words: int = 620,
    overlap_words: int = 80,
) -> RagPreparationResult:
    start = time.perf_counter()
    articles = read_jsonl(articles_path)
    chunks = build_corpus_chunks(
        articles,
        target_words=target_words,
        max_words=max_words,
        overlap_words=overlap_words,
    )
    articles_by_id = {str(article.get("article_id")): article for article in articles}
    gold_records = read_jsonl(gold_path) if Path(gold_path).exists() else []
    all_patterns = build_patterns_from_gold(
        gold_records=gold_records,
        articles_by_id=articles_by_id,
    )
    valid_patterns = [pattern for pattern in all_patterns if not _has_validation_error(pattern)]
    rejected_patterns = [pattern for pattern in all_patterns if _has_validation_error(pattern)]
    mapping_result = attach_patterns_to_chunks(chunks=chunks, patterns=valid_patterns)
    chunks = mapping_result.chunks

    write_jsonl(patterns_output_path, (pattern.to_dict() for pattern in valid_patterns))
    write_jsonl(
        rejected_patterns_output_path,
        (pattern.to_dict() for pattern in rejected_patterns),
    )
    write_jsonl(chunk_patterns_output_path, mapping_result.mappings)

    chunks_path = Path(chunks_output_path)
    write_jsonl(chunks_path, (chunk.to_dict() for chunk in chunks))

    retrieval_path = Path(retrieval_dir)
    retrieval_path.mkdir(parents=True, exist_ok=True)
    bm25_index_path = retrieval_path / "bm25_index.pkl"
    build_bm25_index(chunks, bm25_index_path)

    embeddings_path = retrieval_path / "chunk_embeddings.jsonl"
    embedding_cache_path = retrieval_path / "embedding_cache.jsonl"
    client = build_embedding_client(
        provider=embedding_provider,
        model_name=embedding_model,
        dimension=embedding_dimension,
    )
    embeddings = embed_chunks_with_cache(
        chunks,
        client=client,
        output_path=embeddings_path,
        cache_path=embedding_cache_path,
    )
    write_vector_store_artifacts(
        chunks=chunks,
        embeddings=embeddings,
        vector_store_dir=vector_store_dir,
    )
    vector_manifest_path = Path(vector_store_dir) / "manifest.json"
    duration_seconds = time.perf_counter() - start
    summary = build_rag_preparation_summary(
        article_count=len(articles),
        chunks=chunks,
        embeddings=embeddings,
        bm25_index_path=str(bm25_index_path),
        vector_manifest_path=str(vector_manifest_path),
        duration_seconds=duration_seconds,
    )
    write_rag_preparation_summary(report_path, summary)
    return RagPreparationResult(
        articles_path=Path(articles_path),
        chunks_path=chunks_path,
        embeddings_path=embeddings_path,
        bm25_index_path=bm25_index_path,
        vector_manifest_path=vector_manifest_path,
        patterns_path=Path(patterns_output_path),
        rejected_patterns_path=Path(rejected_patterns_output_path),
        chunk_patterns_path=Path(chunk_patterns_output_path),
        report_path=Path(report_path),
        article_count=len(articles),
        chunk_count=len(chunks),
        embedding_count=len(embeddings),
        pattern_count=len(valid_patterns),
        rejected_pattern_count=len(rejected_patterns),
        chunk_pattern_count=len(mapping_result.mappings),
    )


def chunks_from_jsonl(path: PathLike) -> list[ChunkRecord]:
    records = read_jsonl(path)
    return [_chunk_from_dict(record) for record in records]


def _chunk_from_dict(record: JsonDict) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=str(record["chunk_id"]),
        article_id=str(record["article_id"]),
        chunk_level=str(record["chunk_level"]),
        chunk_index=int(record["chunk_index"]),
        text=str(record["text"]),
        title=record.get("title"),
        source=str(record.get("source") or "unknown"),
        url=str(record.get("url") or ""),
        published_at=record.get("published_at"),
        content_hash=str(record.get("content_hash") or ""),
        chunk_hash=str(record["chunk_hash"]),
        text_word_count=int(record.get("text_word_count") or 0),
        tickers_hint=list(record.get("tickers_hint", [])),
        company_names_hint=list(record.get("company_names_hint", [])),
        sector_hints=list(record.get("sector_hints", [])),
        event_keywords=list(record.get("event_keywords", [])),
        event_type_hints=list(record.get("event_type_hints", [])),
        event_subtype_hints=list(record.get("event_subtype_hints", [])),
        pattern_refs=list(record.get("pattern_refs", [])),
        parent_chunk_id=record.get("parent_chunk_id"),
        paragraph_start=record.get("paragraph_start"),
        paragraph_end=record.get("paragraph_end"),
        metadata=dict(record.get("metadata", {})),
        version=str(record.get("version") or "m03_v1"),
    )


def _has_validation_error(pattern: object) -> bool:
    validation_errors = getattr(pattern, "validation_errors", [])
    return any(issue.get("severity") == "error" for issue in validation_errors)
