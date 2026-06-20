"""Report generation for RAG preparation runs."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from finevent.rag.models import ChunkRecord, EmbeddingRecord
from finevent.types import PathLike


def build_rag_preparation_summary(
    *,
    article_count: int,
    chunks: list[ChunkRecord],
    embeddings: list[EmbeddingRecord],
    bm25_index_path: str,
    vector_manifest_path: str,
    duration_seconds: float,
) -> str:
    chunk_level_counts = Counter(chunk.chunk_level for chunk in chunks)
    source_counts = Counter(chunk.source for chunk in chunks if chunk.chunk_level == "document")
    ticker_coverage = _coverage(
        sum(1 for chunk in chunks if chunk.tickers_hint),
        len(chunks),
    )
    keyword_coverage = _coverage(
        sum(1 for chunk in chunks if chunk.event_keywords),
        len(chunks),
    )
    success_embeddings = [record for record in embeddings if record.status == "success"]
    cache_hits = sum(1 for record in embeddings if record.cache_hit)
    avg_chunks_per_article = len(chunks) / article_count if article_count else 0.0

    lines = [
        "# RAG Preparation Summary",
        "",
        "## Overview",
        "",
        f"- Clean articles indexed: {article_count}",
        f"- Chunks generated: {len(chunks)}",
        f"- Average chunks/article: {avg_chunks_per_article:.2f}",
        f"- Embeddings generated or loaded: {len(success_embeddings)}",
        f"- Embedding success rate: {_coverage(len(success_embeddings), len(chunks)):.2%}",
        f"- Embedding cache hit rate: {_coverage(cache_hits, len(embeddings)):.2%}",
        f"- Chunk ticker metadata coverage: {ticker_coverage:.2%}",
        f"- Chunk event keyword coverage: {keyword_coverage:.2%}",
        f"- Build duration: {duration_seconds:.2f}s",
        "",
        "## Artifact Paths",
        "",
        f"- BM25 index: `{bm25_index_path}`",
        f"- Vector manifest: `{vector_manifest_path}`",
        "",
        "## Chunk Levels",
        "",
        "| Chunk level | Count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {level} | {count} |" for level, count in sorted(chunk_level_counts.items()))
    lines.extend(
        [
            "",
            "## Source Distribution",
            "",
            "| Source | Document chunks |",
            "| --- | ---: |",
        ]
    )
    lines.extend(f"| {source} | {count} |" for source, count in source_counts.most_common())
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Structure-aware chunking creates document, section and paragraph representations.",
            (
                "- Hash embeddings are deterministic offline baselines; "
                "use Cloudflare embeddings for real runs."
            ),
            (
                "- FAISS binary index is built only when `faiss-cpu` and `numpy` "
                "are installed."
            ),
            (
                "- PostgreSQL/pgvector schema is defined separately in "
                "`infra/postgres/004_retrieval.sql`."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_rag_preparation_summary(path: PathLike, content: str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def _coverage(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0
