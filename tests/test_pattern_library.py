from __future__ import annotations

import json
from pathlib import Path

from finevent.jsonl import read_jsonl
from finevent.patterns.builder import build_patterns_from_gold
from finevent.patterns.embeddings import embed_patterns_with_cache
from finevent.patterns.pipeline import run_pattern_library_build
from finevent.patterns.prompting import render_few_shot_patterns
from finevent.patterns.querying import build_pattern_query_from_article
from finevent.patterns.store import PatternStore
from finevent.rag.embeddings import HashEmbeddingClient


def test_build_patterns_from_ai_gold_labels_without_human_review() -> None:
    articles = [_event_article(), _no_event_article()]
    patterns = build_patterns_from_gold(
        gold_records=[_event_gold_record(), _no_event_gold_record()],
        articles_by_id={article["article_id"]: article for article in articles},
    )

    assert len(patterns) == 2
    event_pattern = next(pattern for pattern in patterns if pattern.document_label == "HAS_EVENT")
    no_event_pattern = next(pattern for pattern in patterns if pattern.document_label == "NO_EVENT")
    assert event_pattern.event_type == "EXPANSION"
    assert event_pattern.event_subtype == "NEW_FACTORY"
    assert event_pattern.pattern_text
    assert event_pattern.validation_errors == []
    assert no_event_pattern.gold_output == {"document_label": "NO_EVENT", "events": []}
    assert "NO_EVENT" in no_event_pattern.pattern_text


def test_pattern_embedding_cache_and_selection(tmp_path: Path) -> None:
    patterns = build_patterns_from_gold(
        gold_records=[_event_gold_record(), _no_event_gold_record()],
        articles_by_id={
            "cafef_833adef5f3d9": _event_article(),
            "cafef_generic_market": _no_event_article(),
        },
    )
    client = HashEmbeddingClient(dimension=32)
    embeddings = embed_patterns_with_cache(
        patterns,
        client=client,
        output_path=tmp_path / "pattern_embeddings.jsonl",
        cache_path=tmp_path / "pattern_embedding_cache.jsonl",
    )
    second = embed_patterns_with_cache(
        patterns,
        client=client,
        output_path=tmp_path / "pattern_embeddings_second.jsonl",
        cache_path=tmp_path / "pattern_embedding_cache.jsonl",
    )
    store = PatternStore(
        patterns=patterns,
        embeddings_by_pattern={record.pattern_id: record for record in embeddings},
    )
    query = build_pattern_query_from_article(_event_article())
    candidates = store.select_patterns(query, top_k=2)

    assert len(embeddings) == 2
    assert all(record.cache_hit for record in second)
    assert candidates
    assert candidates[0].event_type == "EXPANSION"
    assert candidates[0].ticker == "HPG"


def test_render_few_shot_patterns_contains_schema_output(tmp_path: Path) -> None:
    patterns = build_patterns_from_gold(
        gold_records=[_event_gold_record()],
        articles_by_id={"cafef_833adef5f3d9": _event_article()},
    )
    embeddings = embed_patterns_with_cache(
        patterns,
        client=HashEmbeddingClient(dimension=32),
        output_path=tmp_path / "pattern_embeddings.jsonl",
        cache_path=tmp_path / "pattern_embedding_cache.jsonl",
    )
    store = PatternStore(
        patterns=patterns,
        embeddings_by_pattern={record.pattern_id: record for record in embeddings},
    )
    prompt = render_few_shot_patterns(
        store.select_patterns(build_pattern_query_from_article(_event_article()))
    )

    assert "Input excerpt:" in prompt
    assert "Expected output JSON:" in prompt
    assert '"event_type": "EXPANSION"' in prompt
    assert "Do not copy factual values" in prompt


def test_run_pattern_library_build_writes_artifacts(tmp_path: Path) -> None:
    articles_path = tmp_path / "articles_clean.jsonl"
    gold_path = tmp_path / "events_gold.jsonl"
    articles_path.write_text(
        json.dumps(_event_article(), ensure_ascii=False) + "\n"
        + json.dumps(_no_event_article(), ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    gold_path.write_text(
        json.dumps(_event_gold_record(), ensure_ascii=False) + "\n"
        + json.dumps(_no_event_gold_record(), ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    result = run_pattern_library_build(
        articles_path=articles_path,
        gold_path=gold_path,
        patterns_output_path=tmp_path / "patterns.jsonl",
        rejected_patterns_output_path=tmp_path / "patterns_rejected.jsonl",
        embeddings_output_path=tmp_path / "pattern_embeddings.jsonl",
        embedding_cache_path=tmp_path / "pattern_embedding_cache.jsonl",
        metrics_path=tmp_path / "pattern_metrics.csv",
        report_path=tmp_path / "pattern_library_summary.md",
        embedding_dimension=32,
    )

    assert result.pattern_count == 2
    assert result.rejected_pattern_count == 0
    assert result.embedding_count == 2
    assert len(read_jsonl(result.patterns_path)) == 2
    assert result.metrics_path.exists()
    assert "pattern_selection_default" in result.metrics_path.read_text(encoding="utf-8")
    assert "Pattern Library Summary" in result.report_path.read_text(encoding="utf-8")


def _event_article() -> dict:
    return {
        "article_id": "cafef_833adef5f3d9",
        "source": "cafef",
        "url": "file://tests/fixtures/html/cafef_sample.html",
        "title": "HPG khoi cong du an nha may moi",
        "published_at": "2026-01-15T08:00:00+07:00",
        "text": (
            "Tap doan Hoa Phat cong bo khoi cong du an nha may moi tai khu cong nghiep.\n"
            "Du an du kien mo rong nang luc san xuat va co the tac dong tich cuc "
            "den ket qua kinh doanh."
        ),
        "tickers_hint": ["HPG"],
        "company_names_hint": ["Hoa Phat Group"],
        "sector_hints": ["materials_steel"],
        "event_keywords": ["khoi cong", "mo rong", "nha may moi"],
        "event_type_hints": ["EXPANSION"],
        "event_subtype_hints": ["NEW_FACTORY"],
    }


def _no_event_article() -> dict:
    return {
        "article_id": "cafef_generic_market",
        "source": "cafef",
        "url": "file://tests/fixtures/html/cafef_generic.html",
        "title": "Thi truong chung khoan dao dong trong phien",
        "published_at": "2026-01-16T08:00:00+07:00",
        "text": (
            "VN-Index tang giam dan xen trong phien khi nha dau tu than trong. "
            "Bai viet khong neu hanh dong cu the cua mot doanh nghiep niem yet."
        ),
        "tickers_hint": [],
        "company_names_hint": [],
        "sector_hints": [],
        "event_keywords": [],
        "event_type_hints": [],
        "event_subtype_hints": [],
    }


def _event_gold_record() -> dict:
    return {
        "article_id": "cafef_833adef5f3d9",
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
        },
    }


def _no_event_gold_record() -> dict:
    return {
        "article_id": "cafef_generic_market",
        "teacher_model": "fixture_teacher",
        "prompt_version": "m02_teacher_v1",
        "validation_status": "PASS",
        "validation_errors": [],
        "label": {
            "article_id": "cafef_generic_market",
            "document_label": "NO_EVENT",
            "events": [],
            "warnings": [],
        },
    }
