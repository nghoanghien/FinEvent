from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from finevent.rag.bm25 import Bm25Index, load_bm25_index
from finevent.rag.chunking import build_article_chunks
from finevent.rag.embeddings import HashEmbeddingClient, embed_chunks_with_cache
from finevent.rag.pipeline import run_rag_preparation


def test_structure_aware_chunking_keeps_metadata() -> None:
    chunks = build_article_chunks(_article(), target_words=16, max_words=28, overlap_words=4)
    levels = {chunk.chunk_level for chunk in chunks}

    assert {"document", "section", "paragraph"}.issubset(levels)
    assert all(chunk.article_id == "cafef_833adef5f3d9" for chunk in chunks)
    assert all(chunk.source == "cafef" for chunk in chunks)
    assert all(chunk.tickers_hint == ["HPG"] for chunk in chunks)
    assert all("khoi cong" in chunk.event_keywords for chunk in chunks)
    assert all(chunk.chunk_hash.startswith("sha256:") for chunk in chunks)


def test_bm25_query_returns_event_related_chunk() -> None:
    chunks = build_article_chunks(_article(), target_words=16, max_words=28, overlap_words=4)
    index = Bm25Index.from_chunks(chunks)

    results = index.search("HPG khoi cong nha may", top_k=3)

    assert results
    assert results[0].article_id == "cafef_833adef5f3d9"
    assert results[0].score > 0


def test_embedding_cache_reuses_same_chunk_hash(tmp_path: Path) -> None:
    chunks = build_article_chunks(_article(), target_words=16, max_words=28, overlap_words=4)
    client = HashEmbeddingClient(dimension=32)
    cache_path = tmp_path / "embedding_cache.jsonl"

    first = embed_chunks_with_cache(
        chunks,
        client=client,
        output_path=tmp_path / "embeddings_first.jsonl",
        cache_path=cache_path,
    )
    second = embed_chunks_with_cache(
        chunks,
        client=client,
        output_path=tmp_path / "embeddings_second.jsonl",
        cache_path=cache_path,
    )

    assert first
    assert all(record.embedding_dimension == 32 for record in second)
    assert all(record.cache_hit for record in second)


def test_duplicate_chunk_hash_keeps_unique_embedding_ids(tmp_path: Path) -> None:
    chunks = build_article_chunks(_article(), target_words=16, max_words=28, overlap_words=4)
    duplicate = replace(chunks[0], chunk_id=f"{chunks[0].chunk_id}_duplicate")
    client = HashEmbeddingClient(dimension=32)

    first = embed_chunks_with_cache(
        [chunks[0], duplicate],
        client=client,
        output_path=tmp_path / "embeddings_first.jsonl",
        cache_path=tmp_path / "embedding_cache.jsonl",
    )
    second = embed_chunks_with_cache(
        [chunks[0], duplicate],
        client=client,
        output_path=tmp_path / "embeddings_second.jsonl",
        cache_path=tmp_path / "embedding_cache.jsonl",
    )

    assert len({record.embedding_id for record in first}) == 2
    assert len({record.embedding_id for record in second}) == 2
    assert all(record.cache_hit for record in second)


def test_run_rag_preparation_writes_artifacts(tmp_path: Path) -> None:
    articles_path = tmp_path / "articles_clean.jsonl"
    articles_path.write_text(json.dumps(_article(), ensure_ascii=False) + "\n", encoding="utf-8")

    result = run_rag_preparation(
        articles_path=articles_path,
        chunks_output_path=tmp_path / "chunks.jsonl",
        retrieval_dir=tmp_path / "retrieval",
        vector_store_dir=tmp_path / "vector_store",
        report_path=tmp_path / "rag_summary.md",
        embedding_dimension=32,
        target_words=16,
        max_words=28,
        overlap_words=4,
    )

    assert result.article_count == 1
    assert result.chunk_count >= 3
    assert result.embedding_count == result.chunk_count
    assert result.chunks_path.exists()
    assert result.bm25_index_path.exists()
    assert result.vector_manifest_path.exists()
    assert result.report_path.exists()
    assert "RAG Preparation Summary" in result.report_path.read_text(encoding="utf-8")

    index = load_bm25_index(result.bm25_index_path)
    assert index.search("mo rong nha may", top_k=1)


def _article() -> dict:
    return {
        "article_id": "cafef_833adef5f3d9",
        "source": "cafef",
        "url": "file://tests/fixtures/html/cafef_sample.html",
        "title": "HPG khoi cong du an nha may moi",
        "published_at": "2026-01-15T08:00:00+07:00",
        "text": (
            "Tap doan Hoa Phat cong bo khoi cong du an nha may moi tai khu cong nghiep.\n"
            "Du an du kien mo rong nang luc san xuat va co the tac dong tich cuc "
            "den ket qua kinh doanh.\n"
            "Ban lanh dao cho biet tien do se duoc cap nhat trong cac bao cao tiep theo."
        ),
        "content_hash": "sha256:f15b8727f93f7392814d4797c8e5c1e72276753da3bb340675e9a9d0b5fd12c2",
        "tickers_hint": ["HPG"],
        "company_names_hint": ["Hoa Phat Group"],
        "sector_hints": ["materials_steel"],
        "event_keywords": ["khoi cong", "mo rong", "nha may moi"],
        "event_type_hints": ["EXPANSION"],
        "event_subtype_hints": ["NEW_FACTORY"],
        "language": "vi",
    }
