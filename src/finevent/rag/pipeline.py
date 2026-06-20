"""Milestone 03 RAG preparation pipeline."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from finevent.jsonl import read_jsonl, write_jsonl
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
    report_path: Path
    article_count: int
    chunk_count: int
    embedding_count: int


def run_rag_preparation(
    *,
    articles_path: PathLike = "data/processed/articles_clean.jsonl",
    chunks_output_path: PathLike = "data/processed/chunks.jsonl",
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
        report_path=Path(report_path),
        article_count=len(articles),
        chunk_count=len(chunks),
        embedding_count=len(embeddings),
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
        parent_chunk_id=record.get("parent_chunk_id"),
        paragraph_start=record.get("paragraph_start"),
        paragraph_end=record.get("paragraph_end"),
        metadata=dict(record.get("metadata", {})),
        version=str(record.get("version") or "m03_v1"),
    )
