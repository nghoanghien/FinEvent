"""Local vector-store artifacts used as offline baseline and pgvector staging."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from finevent.jsonl import write_jsonl
from finevent.rag.models import ChunkRecord, EmbeddingRecord
from finevent.types import JsonDict, PathLike


def write_vector_store_artifacts(
    *,
    chunks: list[ChunkRecord],
    embeddings: list[EmbeddingRecord],
    vector_store_dir: PathLike = "data/vector_store",
) -> JsonDict:
    output_dir = Path(vector_store_dir)
    local_dir = output_dir / "local"
    faiss_dir = output_dir / "faiss"
    local_dir.mkdir(parents=True, exist_ok=True)
    faiss_dir.mkdir(parents=True, exist_ok=True)

    embeddings_by_chunk = {
        record.chunk_id: record for record in embeddings if record.status == "success"
    }
    metadata_records = [
        _vector_metadata_record(chunk, embeddings_by_chunk.get(chunk.chunk_id))
        for chunk in chunks
    ]
    write_jsonl(local_dir / "metadata.jsonl", metadata_records)
    write_jsonl(faiss_dir / "metadata.jsonl", metadata_records)

    faiss_status = _try_write_faiss_index(
        embeddings=[record for record in embeddings if record.status == "success"],
        faiss_dir=faiss_dir,
    )

    manifest = {
        "local_metadata_path": str(local_dir / "metadata.jsonl"),
        "faiss_metadata_path": str(faiss_dir / "metadata.jsonl"),
        "faiss_index_path": str(faiss_dir / "index.faiss"),
        "faiss_index_status": faiss_status["status"],
        "faiss_note": faiss_status["note"],
        "chunk_count": len(chunks),
        "embedding_count": len(embeddings_by_chunk),
        "embedding_models": sorted({record.embedding_model for record in embeddings}),
        "embedding_dimensions": sorted({record.embedding_dimension for record in embeddings}),
        "chunk_level_counts": dict(Counter(chunk.chunk_level for chunk in chunks)),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest


def _try_write_faiss_index(embeddings: list[EmbeddingRecord], faiss_dir: Path) -> JsonDict:
    if not embeddings:
        return {"status": "skipped_no_embeddings", "note": "No successful embeddings to index."}
    try:
        import faiss  # type: ignore[import-not-found]
        import numpy as np
    except ImportError:
        return {
            "status": "skipped_missing_faiss",
            "note": "Install faiss-cpu and numpy to create a binary FAISS index.",
        }

    dimensions = {record.embedding_dimension for record in embeddings}
    if len(dimensions) != 1:
        return {
            "status": "skipped_mixed_dimensions",
            "note": "FAISS index requires all embeddings to have the same dimension.",
        }

    matrix = np.array([record.vector for record in embeddings], dtype="float32")
    index = faiss.IndexFlatIP(int(matrix.shape[1]))
    index.add(matrix)
    faiss.write_index(index, str(faiss_dir / "index.faiss"))
    return {
        "status": "built",
        "note": f"Built IndexFlatIP with {len(embeddings)} vectors.",
    }


def _vector_metadata_record(
    chunk: ChunkRecord,
    embedding: EmbeddingRecord | None,
) -> JsonDict:
    return {
        "chunk_id": chunk.chunk_id,
        "article_id": chunk.article_id,
        "chunk_level": chunk.chunk_level,
        "source": chunk.source,
        "url": chunk.url,
        "published_at": chunk.published_at,
        "title": chunk.title,
        "tickers_hint": chunk.tickers_hint,
        "company_names_hint": chunk.company_names_hint,
        "event_keywords": chunk.event_keywords,
        "event_type_hints": chunk.event_type_hints,
        "event_subtype_hints": chunk.event_subtype_hints,
        "chunk_hash": chunk.chunk_hash,
        "embedding_id": embedding.embedding_id if embedding else None,
        "embedding_model": embedding.embedding_model if embedding else None,
        "embedding_dimension": embedding.embedding_dimension if embedding else None,
    }
