from __future__ import annotations

from pathlib import Path

from finevent.jsonl import read_jsonl, write_jsonl
from finevent.rag.bm25 import build_bm25_index
from finevent.rag.chunking import build_corpus_chunks
from finevent.rag.embeddings import HashEmbeddingClient, embed_chunks_with_cache
from finevent.retrieval.engine import RetrievalEngine
from finevent.retrieval.experiments import run_retrieval_comparison
from finevent.retrieval.llm_rerank import build_llm_reasoning_rerank_prompt
from finevent.retrieval.querying import build_queries_from_article


class CountingEmbeddingClient(HashEmbeddingClient):
    def __init__(self, *, dimension: int = 32):
        super().__init__(dimension=dimension)
        self.call_count = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.call_count += len(texts)
        return super().embed_texts(texts)


def test_query_decomposition_uses_article_metadata() -> None:
    queries = build_queries_from_article(_article())
    query_types = {query.query_type for query in queries}

    assert {"title", "ticker_event", "company_event", "event_type"}.issubset(query_types)
    assert any("HPG" in query.text for query in queries)
    assert any(query.event_type_hints == ["EXPANSION"] for query in queries)


def test_retrieval_strategies_return_score_breakdown(tmp_path: Path) -> None:
    artifacts = _build_retrieval_artifacts(tmp_path)
    engine = RetrievalEngine.from_artifacts(**artifacts)
    queries = build_queries_from_article(_article())

    for config_name in ["bm25_only", "dense_only", "hybrid", "metadata_aware_hybrid"]:
        candidates = engine.retrieve(queries, config=config_name)

        assert candidates
        assert candidates[0].rank == 1
        assert candidates[0].article_id == "cafef_833adef5f3d9"
        assert "dense_score" in candidates[0].score_breakdown
        assert "bm25_score" in candidates[0].score_breakdown
        assert "metadata_score" in candidates[0].score_breakdown


def test_query_embeddings_are_cached_across_retrieval_configs(tmp_path: Path) -> None:
    artifacts = _build_retrieval_artifacts(tmp_path)
    client = CountingEmbeddingClient(dimension=32)
    engine = RetrievalEngine.from_artifacts(**artifacts, query_embedding_client=client)
    queries = build_queries_from_article(_article())

    engine.retrieve(queries, config="dense_only")
    engine.retrieve(queries, config="hybrid")

    assert client.call_count == len(queries)


def test_rule_and_llm_rerank_keep_relevant_event_chunk_on_top(tmp_path: Path) -> None:
    artifacts = _build_retrieval_artifacts(tmp_path)
    engine = RetrievalEngine.from_artifacts(**artifacts)
    queries = build_queries_from_article(_article())

    rule_candidates = engine.retrieve(queries, config="rule_aware_rerank")
    llm_candidates = engine.retrieve(queries, config="llm_reasoning_rerank")

    assert rule_candidates[0].article_id == "cafef_833adef5f3d9"
    assert llm_candidates[0].score_breakdown["llm_relevance_score"] > 0
    assert llm_candidates[0].score_breakdown["llm_relevance_label"] in {"HIGH", "MEDIUM"}


def test_llm_reasoning_prompt_contains_candidate_schema(tmp_path: Path) -> None:
    artifacts = _build_retrieval_artifacts(tmp_path)
    engine = RetrievalEngine.from_artifacts(**artifacts)
    query = build_queries_from_article(_article())[0]
    candidates = engine.retrieve([query], config="metadata_aware_hybrid")

    prompt = build_llm_reasoning_rerank_prompt(query=query, candidates=candidates)

    assert "candidate_schema" in prompt
    assert "has_corporate_event" in prompt
    assert "relevance_score" in prompt


def test_retrieval_comparison_writes_metrics_and_logs(tmp_path: Path) -> None:
    artifacts = _build_retrieval_artifacts(tmp_path)
    gold_path = tmp_path / "events_gold.jsonl"
    logs_path = tmp_path / "retrieval_logs.jsonl"
    metrics_path = tmp_path / "retrieval_metrics.csv"
    error_path = tmp_path / "retrieval_error_analysis.md"
    write_jsonl(gold_path, [_gold_record()])

    result = run_retrieval_comparison(
        chunks_path=artifacts["chunks_path"],
        bm25_index_path=artifacts["bm25_index_path"],
        embeddings_path=artifacts["embeddings_path"],
        gold_path=gold_path,
        logs_path=logs_path,
        metrics_path=metrics_path,
        error_analysis_path=error_path,
        config_names=["bm25_only", "dense_only", "hybrid", "metadata_aware_hybrid"],
    )

    logs = read_jsonl(logs_path)
    metrics_text = metrics_path.read_text(encoding="utf-8")
    assert result.config_count == 4
    assert result.eval_case_count == 1
    assert len(logs) == 4
    assert "retrieval_config,case_count" in metrics_text
    assert "metadata_aware_hybrid" in metrics_text
    assert "Retrieval Error Analysis" in error_path.read_text(encoding="utf-8")


def _build_retrieval_artifacts(tmp_path: Path) -> dict:
    chunks = build_corpus_chunks([_article()], target_words=16, max_words=28, overlap_words=4)
    chunks_path = tmp_path / "chunks.jsonl"
    bm25_path = tmp_path / "bm25_index.pkl"
    embeddings_path = tmp_path / "chunk_embeddings.jsonl"
    cache_path = tmp_path / "embedding_cache.jsonl"
    write_jsonl(chunks_path, (chunk.to_dict() for chunk in chunks))
    build_bm25_index(chunks, bm25_path)
    embed_chunks_with_cache(
        chunks,
        client=HashEmbeddingClient(dimension=32),
        output_path=embeddings_path,
        cache_path=cache_path,
    )
    return {
        "chunks_path": chunks_path,
        "bm25_index_path": bm25_path,
        "embeddings_path": embeddings_path,
    }


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


def _gold_record() -> dict:
    return {
        "article_id": "cafef_833adef5f3d9",
        "label_schema_version": "event_schema_v1",
        "label_source": "ai_generated",
        "teacher_model": "fixture_teacher",
        "prompt_version": "m02_teacher_v1",
        "validation_status": "PASS",
        "validation_errors": [],
        "label": {
            "article_id": "cafef_833adef5f3d9",
            "document_label": "HAS_EVENT",
            "events": [
                {
                    "event_id": "cafef_833adef5f3d9_e01",
                    "ticker": "HPG",
                    "company_name": "Hoa Phat Group",
                    "event_type": "EXPANSION",
                    "event_subtype": "NEW_FACTORY",
                    "event_summary": "Hoa Phat cong bo khoi cong du an nha may moi.",
                    "event_arguments": {
                        "project": "du an nha may moi",
                        "location": "khu cong nghiep",
                    },
                    "impact_sentiment": "POSITIVE",
                    "evidence_span": (
                        "Tap doan Hoa Phat cong bo khoi cong du an nha may moi "
                        "tai khu cong nghiep."
                    ),
                    "source_url": "file://tests/fixtures/html/cafef_sample.html",
                    "published_at": "2026-01-15T08:00:00+07:00",
                    "confidence": 0.86,
                }
            ],
            "warnings": [],
            "model_info": {
                "model_name": "fixture_teacher",
                "prompt_version": "m02_teacher_v1",
                "run_id": "fixture_run",
            },
        },
        "raw_output": {},
    }
