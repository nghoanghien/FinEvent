from __future__ import annotations

import json
from pathlib import Path

from finevent.jsonl import read_jsonl
from finevent.patterns.builder import build_patterns_from_gold
from finevent.patterns.mapping import attach_patterns_to_chunks
from finevent.patterns.pipeline import run_pattern_library_build
from finevent.rag.models import ChunkRecord


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
    assert event_pattern.explanation_brief == "Bang chung noi ro Hoa Phat khoi cong nha may moi."
    assert event_pattern.validation_errors == []
    assert no_event_pattern.gold_output == {"document_label": "NO_EVENT", "events": []}
    assert no_event_pattern.explanation_brief == "Bai viet chi noi ve dien bien thi truong chung."


def test_attach_patterns_to_chunks_uses_matching_evidence_chunk() -> None:
    pattern = build_patterns_from_gold(
        gold_records=[_event_gold_record()],
        articles_by_id={"cafef_833adef5f3d9": _event_article()},
    )[0]
    chunks = [
        _chunk("document", 0, _event_article()["text"]),
        _chunk("paragraph", 1, "Thong tin chung khong chua bang chung."),
        _chunk(
            "paragraph",
            2,
            "Tap doan Hoa Phat cong bo khoi cong du an nha may moi tai khu cong nghiep.",
        ),
    ]

    result = attach_patterns_to_chunks(chunks=chunks, patterns=[pattern])

    matched = next(chunk for chunk in result.chunks if chunk.chunk_index == 2)
    assert matched.pattern_refs
    assert matched.pattern_refs[0]["pattern_id"] == pattern.pattern_id
    assert matched.pattern_refs[0]["match_strategy"] == "evidence_paragraph"
    assert result.mappings[0]["chunk_id"] == matched.chunk_id
    assert result.warnings == []


def test_attach_no_event_pattern_to_document_chunk() -> None:
    pattern = build_patterns_from_gold(
        gold_records=[_no_event_gold_record()],
        articles_by_id={"cafef_generic_market": _no_event_article()},
    )[0]
    document_chunk = _chunk(
        "document",
        0,
        _no_event_article()["text"],
        article_id="cafef_generic_market",
    )

    result = attach_patterns_to_chunks(chunks=[document_chunk], patterns=[pattern])

    assert result.chunks[0].pattern_refs[0]["document_label"] == "NO_EVENT"
    assert result.chunks[0].pattern_refs[0]["match_strategy"] == "document_no_event"
    assert result.mappings[0]["article_id"] == "cafef_generic_market"


def test_run_pattern_library_build_writes_record_artifacts(tmp_path: Path) -> None:
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
        metrics_path=tmp_path / "pattern_metrics.csv",
        report_path=tmp_path / "pattern_summary.md",
    )

    assert result.pattern_count == 2
    assert result.rejected_pattern_count == 0
    assert len(read_jsonl(result.patterns_path)) == 2
    assert "pattern_count" in result.metrics_path.read_text(encoding="utf-8")
    assert "Pattern Record Summary" in result.report_path.read_text(encoding="utf-8")


def _chunk(
    chunk_level: str,
    chunk_index: int,
    text: str,
    *,
    article_id: str = "cafef_833adef5f3d9",
) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=f"{article_id}_{chunk_level}_{chunk_index}",
        article_id=article_id,
        chunk_level=chunk_level,
        chunk_index=chunk_index,
        text=text,
        title="HPG khoi cong du an nha may moi",
        source="cafef",
        url="file://tests/fixtures/html/cafef_sample.html",
        published_at="2026-01-15T08:00:00+07:00",
        content_hash="sha256:fixture",
        chunk_hash=f"hash-{chunk_index}",
        text_word_count=len(text.split()),
        tickers_hint=["HPG"],
        company_names_hint=["Hoa Phat Group"],
        sector_hints=["materials_steel"],
        event_keywords=["khoi cong", "mo rong", "nha may moi"],
        event_type_hints=["EXPANSION"],
        event_subtype_hints=["NEW_FACTORY"],
    )


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
            "label_reason": "Bai viet co su kien khoi cong du an moi cua Hoa Phat.",
            "events": [
                {
                    "event_id": "cafef_833adef5f3d9_e01",
                    "ticker": "HPG",
                    "company_name": "Hoa Phat Group",
                    "event_type": "EXPANSION",
                    "event_subtype": "NEW_FACTORY",
                    "event_summary": "Hoa Phat cong bo khoi cong du an nha may moi.",
                    "event_reason": "Bang chung noi ro Hoa Phat khoi cong nha may moi.",
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
            "label_reason": "Bai viet chi noi ve dien bien thi truong chung.",
            "events": [],
            "warnings": [],
        },
    }
