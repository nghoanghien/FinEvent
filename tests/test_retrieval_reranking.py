from __future__ import annotations

from pathlib import Path

from finevent.jsonl import read_jsonl, write_jsonl
from finevent.rag.bm25 import build_bm25_index
from finevent.rag.chunking import build_corpus_chunks
from finevent.rag.embeddings import HashEmbeddingClient, embed_chunks_with_cache
from finevent.rag.models import ChunkRecord
from finevent.retrieval.engine import RetrievalEngine
from finevent.retrieval.evaluation import evaluate_results
from finevent.retrieval.experiments import run_online_retrieval, run_retrieval_comparison
from finevent.retrieval.llm_rerank import (
    build_listwise_llm_rerank_prompt,
    build_llm_reasoning_rerank_prompt,
    parse_listwise_rerank_output,
    rerank_candidates_listwise,
)
from finevent.retrieval.models import RetrievalCandidate, RetrievalQuery
from finevent.retrieval.querying import build_queries_from_article


class CountingEmbeddingClient(HashEmbeddingClient):
    def __init__(self, *, dimension: int = 32):
        super().__init__(dimension=dimension)
        self.call_count = 0

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.call_count += len(texts)
        return super().embed_texts(texts)


class FakeListwiseModel:
    def __init__(self, output: str):
        self.output = output
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.output


def test_query_decomposition_uses_article_metadata() -> None:
    queries = build_queries_from_article(_article())
    query_types = {query.query_type for query in queries}

    assert {"title", "ticker_event", "company_event", "event_type"}.issubset(query_types)
    assert any("HPG" in query.text for query in queries)
    assert any(query.event_type_hints == ["EXPANSION"] for query in queries)


def test_event_intent_query_mode_creates_one_query_per_event_type() -> None:
    queries = build_queries_from_article(_multi_event_article(), query_mode="event_intent")
    intent_queries = [query for query in queries if query.query_type.startswith("event_intent_")]

    assert {query.intent_event_type for query in intent_queries} == {"DIVIDEND", "MA"}
    assert any(
        query.intent_event_type == "DIVIDEND" and query.event_keywords == ["co tuc"]
        for query in intent_queries
    )
    assert any(
        query.intent_event_type == "MA" and query.event_keywords == ["mua lai"]
        for query in intent_queries
    )


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


def test_multi_event_aware_hybrid_keeps_minor_event_context(tmp_path: Path) -> None:
    artifacts = _build_multi_event_retrieval_artifacts(tmp_path)
    engine = RetrievalEngine.from_artifacts(**artifacts)
    queries = build_queries_from_article(_multi_event_article(), query_mode="event_intent")

    candidates = engine.retrieve(queries, config="multi_event_aware_hybrid")

    assert candidates
    assert candidates[0].score_breakdown["selection_strategy"] == "coverage_mmr"
    assert len(candidates) <= 8
    assert any(
        "DIVIDEND" in candidate.metadata.get("event_type_hints", [])
        for candidate in candidates
    )
    assert any(
        "DIVIDEND" in candidate.score_breakdown.get("matched_intent_event_types", [])
        for candidate in candidates
    )


def test_retrieval_metrics_include_multi_event_context_coverage() -> None:
    candidates = [
        _candidate("ma_context", ["MA"], rank=1),
        _candidate("dividend_context", ["DIVIDEND"], rank=2),
    ]

    metrics = evaluate_results(
        candidates=candidates,
        relevant_chunk_ids={"ma_context", "dividend_context"},
        event_types={"MA", "DIVIDEND"},
        event_relevant_chunk_ids={
            "event_ma": {"ma_context"},
            "event_dividend": {"dividend_context"},
        },
    )

    assert metrics["event_type_coverage_at_5"] == 1.0
    assert metrics["event_evidence_coverage_at_5"] == 1.0
    assert metrics["unique_event_types_at_5"] == 2
    assert metrics["dominance_ratio_at_5"] == 0.5


def test_llm_reasoning_prompt_contains_candidate_schema(tmp_path: Path) -> None:
    artifacts = _build_retrieval_artifacts(tmp_path)
    engine = RetrievalEngine.from_artifacts(**artifacts)
    query = build_queries_from_article(_article())[0]
    candidates = engine.retrieve([query], config="metadata_aware_hybrid")

    prompt = build_llm_reasoning_rerank_prompt(query=query, candidates=candidates)

    assert "candidate_schema" in prompt
    assert "has_corporate_event" in prompt
    assert "relevance_score" in prompt


def test_listwise_llm_prompt_includes_article_and_candidate_metadata(tmp_path: Path) -> None:
    artifacts = _build_retrieval_artifacts(tmp_path)
    engine = RetrievalEngine.from_artifacts(**artifacts)
    queries = build_queries_from_article(_article())
    candidates = engine.retrieve(queries, config="metadata_aware_hybrid", select_final=False)

    prompt = build_listwise_llm_rerank_prompt(
        query_article=_article(),
        queries=queries,
        candidates=candidates[:3],
        max_query_article_chars=120,
        max_candidate_chars=90,
    )

    assert "listwise_financial_news_rerank" in prompt
    assert "query_article" in prompt
    assert "source_article" in prompt
    assert "article_summary_preview" in prompt
    assert "published_at" in prompt
    assert "score_breakdown" in prompt
    assert "candidate_schema" not in prompt


def test_listwise_llm_prompt_default_has_no_text_cap() -> None:
    query_article = {
        "article_id": "manual_article",
        "title": "HPG cap nhat thong tin doanh nghiep",
        "source": "manual",
        "text": "noi dung bai viet " * 300 + "QUERY_UNCAPPED_TAIL",
    }
    candidate = RetrievalCandidate(
        rank=1,
        chunk_id="long_context",
        article_id="long_context_article",
        chunk_level="paragraph",
        title="Fixture",
        text="noi dung chunk " * 300 + "CANDIDATE_UNCAPPED_TAIL",
        source="fixture",
        url="fixture://long_context",
        published_at=None,
        score=1.0,
        score_breakdown={},
        metadata={
            "event_type_hints": ["EXPANSION"],
            "article_summary_preview": "tom tat dai " * 100 + "SUMMARY_UNCAPPED_TAIL",
        },
    )

    prompt = build_listwise_llm_rerank_prompt(
        query_article=query_article,
        queries=[],
        candidates=[candidate],
    )

    assert "QUERY_UNCAPPED_TAIL" in prompt
    assert "CANDIDATE_UNCAPPED_TAIL" in prompt
    assert "SUMMARY_UNCAPPED_TAIL" in prompt


def test_listwise_rerank_parser_accepts_object_and_array() -> None:
    parsed_object = parse_listwise_rerank_output(
        '```json\n{"ranked_candidate_ids": [2, "chunk_a"], "judgments": []}\n```'
    )
    parsed_array = parse_listwise_rerank_output("[3, 1, 2]")

    assert parsed_object["ranked_candidate_ids"] == ["2", "chunk_a"]
    assert parsed_array["ranked_candidate_ids"] == ["3", "1", "2"]


def test_listwise_llm_rerank_reorders_candidates_with_fake_model() -> None:
    candidates = [
        _candidate("first_context", ["MA"], rank=1),
        _candidate("second_context", ["DIVIDEND"], rank=2),
    ]
    query = RetrievalQuery(
        query_id="manual_query",
        article_id="manual_article",
        text="Cong ty A chia co tuc",
        query_type="manual",
        event_type_hints=["DIVIDEND"],
    )
    model = FakeListwiseModel(
        """
        {
          "ranked_candidate_ids": [2, 1],
          "judgments": [
            {
              "candidate_id": 2,
              "relevance_score": 0.98,
              "relevance_label": "HIGH",
              "reasoning_summary": "Ung vien noi ve co tuc."
            }
          ]
        }
        """
    )

    result = rerank_candidates_listwise(
        query_article=_multi_event_article(),
        queries=[query],
        candidates=candidates,
        mode="student_env",
        model_name="fake_student",
        model=model,
        top_n=2,
    )

    assert result.candidates[0].chunk_id == "second_context"
    assert result.candidates[0].score_breakdown["llm_rank"] == 1
    assert result.candidates[0].score_breakdown["llm_rerank_model"] == "fake_student"
    assert model.prompts and "article_summary_preview" in model.prompts[0]


def test_online_retrieval_runs_listwise_rerank_before_context_output(tmp_path: Path) -> None:
    artifacts = _build_multi_event_retrieval_artifacts(tmp_path)
    articles_path = tmp_path / "articles.jsonl"
    output_path = tmp_path / "online_contexts.jsonl"
    logs_path = tmp_path / "online_logs.jsonl"
    metrics_path = tmp_path / "metrics.csv"
    error_path = tmp_path / "errors.md"
    write_jsonl(articles_path, [_multi_event_article()])
    model = FakeListwiseModel(
        """
        {
          "ranked_candidate_ids": ["dividend_context"],
          "judgments": [
            {
              "chunk_id": "dividend_context",
              "relevance_score": 0.99,
              "relevance_label": "HIGH",
              "reasoning_summary": "Chunk nay noi ve co tuc."
            }
          ]
        }
        """
    )

    run_online_retrieval(
        chunks_path=artifacts["chunks_path"],
        bm25_index_path=artifacts["bm25_index_path"],
        embeddings_path=artifacts["embeddings_path"],
        articles_path=articles_path,
        gold_path=tmp_path / "missing_gold.jsonl",
        output_path=output_path,
        logs_path=logs_path,
        metrics_path=metrics_path,
        error_analysis_path=error_path,
        config_name="multi_event_aware_hybrid",
        llm_rerank_mode="student_env",
        llm_rerank_model=model,
        llm_rerank_model_name="fake_student",
        llm_rerank_top_n=15,
        max_contexts=2,
    )

    records = read_jsonl(output_path)
    logs = read_jsonl(logs_path)
    dividend_context = next(
        context
        for context in records[0]["contexts"]
        if context["chunk_id"] == "dividend_context"
    )
    assert records[0]["llm_rerank"]["mode"] == "student_env"
    assert dividend_context["score_breakdown"]["llm_rank"] == 1
    assert dividend_context["score_breakdown"]["llm_rerank_model"] == "fake_student"
    assert dividend_context["score_breakdown"]["selection_strategy"] == "coverage_mmr"
    assert logs[0]["llm_rerank"]["preselect_context_count"] > len(records[0]["contexts"])
    assert len(records[0]["contexts"]) == 2
    assert logs[0]["llm_rerank"]["raw_output"]
    assert logs[0]["llm_rerank"]["parsed_output"]["ranked_candidate_ids"] == [
        "dividend_context"
    ]


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
    assert "event_type_coverage_at_5" in metrics_text
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


def _build_multi_event_retrieval_artifacts(tmp_path: Path) -> dict:
    chunks = [
        _chunk(
            chunk_id=f"ma_context_{index}",
            article_id=f"ma_article_{index}",
            text=(
                "Cong ty A mua lai doanh nghiep muc tieu va thuc hien sap nhap. "
                "Thuong vu mua lai co gia tri lon."
            ),
            event_type_hints=["MA"],
            chunk_index=index,
        )
        for index in range(8)
    ]
    chunks.append(
        _chunk(
            chunk_id="dividend_context",
            article_id="dividend_article",
            text=(
                "Cong ty A cong bo chia co tuc bang tien mat, ngay dang ky cuoi cung "
                "va ngay thanh toan cho co dong."
            ),
            event_type_hints=["DIVIDEND"],
            chunk_index=8,
        )
    )
    chunks_path = tmp_path / "multi_chunks.jsonl"
    bm25_path = tmp_path / "multi_bm25_index.pkl"
    embeddings_path = tmp_path / "multi_chunk_embeddings.jsonl"
    cache_path = tmp_path / "multi_embedding_cache.jsonl"
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


def _chunk(
    *,
    chunk_id: str,
    article_id: str,
    text: str,
    event_type_hints: list[str],
    chunk_index: int,
) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        article_id=article_id,
        chunk_level="paragraph",
        chunk_index=chunk_index,
        text=text,
        title="Cong ty A cong bo nhieu su kien",
        source="fixture",
        url=f"fixture://{article_id}",
        published_at="2026-01-15T08:00:00+07:00",
        content_hash=f"content_{chunk_id}",
        chunk_hash=f"hash_{chunk_id}",
        text_word_count=len(text.split()),
        tickers_hint=["AAA"],
        company_names_hint=["Cong ty A"],
        sector_hints=[],
        event_keywords=["mua lai"] if event_type_hints == ["MA"] else ["co tuc"],
        event_type_hints=event_type_hints,
        event_subtype_hints=[],
    )


def _candidate(chunk_id: str, event_type_hints: list[str], *, rank: int):
    return RetrievalCandidate(
        rank=rank,
        chunk_id=chunk_id,
        article_id=f"{chunk_id}_article",
        chunk_level="paragraph",
        title="Fixture",
        text=f"{chunk_id} text",
        source="fixture",
        url=f"fixture://{chunk_id}",
        published_at=None,
        score=1.0 / rank,
        score_breakdown={},
        metadata={"event_type_hints": event_type_hints},
    )


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


def _multi_event_article() -> dict:
    return {
        "article_id": "manual_multi_event",
        "source": "manual",
        "url": "manual://multi-event",
        "title": "Cong ty A mua lai doanh nghiep va chia co tuc",
        "published_at": "2026-01-15T08:00:00+07:00",
        "text": (
            "Cong ty A cong bo mua lai mot doanh nghiep trong cung nganh. "
            "Cong ty cung thong qua phuong an chia co tuc bang tien mat cho co dong."
        ),
        "content_hash": "sha256:multi",
        "tickers_hint": ["AAA"],
        "company_names_hint": ["Cong ty A"],
        "sector_hints": [],
        "event_keywords": ["co tuc", "mua lai"],
        "event_type_hints": ["DIVIDEND", "MA"],
        "event_subtype_hints": ["ACQUISITION", "CASH_DIVIDEND"],
        "event_keyword_matches": [
            {
                "event_type": "MA",
                "event_subtype": "ACQUISITION",
                "keyword": "mua lai",
                "polarity_hint": "neutral",
                "priority": 3,
            },
            {
                "event_type": "DIVIDEND",
                "event_subtype": "CASH_DIVIDEND",
                "keyword": "co tuc",
                "polarity_hint": "positive",
                "priority": 3,
            },
        ],
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
            "label_reason": "Bai viet co thong tin Hoa Phat khoi cong du an nha may moi.",
            "events": [
                {
                    "event_id": "cafef_833adef5f3d9_e01",
                    "ticker": "HPG",
                    "company_name": "Hoa Phat Group",
                    "event_type": "EXPANSION",
                    "event_subtype": "NEW_FACTORY",
                    "event_summary": "Hoa Phat cong bo khoi cong du an nha may moi.",
                    "event_reason": "Bang chung neu ro Hoa Phat khoi cong nha may moi.",
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
