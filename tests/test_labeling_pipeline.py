from __future__ import annotations

import json
from pathlib import Path

from finevent.jsonl import read_jsonl
from finevent.labeling.pipeline import generate_teacher_prompts, validate_teacher_outputs


def test_generate_teacher_prompts(tmp_path: Path) -> None:
    articles_path = tmp_path / "articles_clean.jsonl"
    prompts_path = tmp_path / "teacher_prompts.jsonl"
    articles_path.write_text(json.dumps(_article(), ensure_ascii=False) + "\n", encoding="utf-8")

    result = generate_teacher_prompts(
        articles_path=articles_path,
        prompt_output_path=prompts_path,
    )

    records = read_jsonl(prompts_path)
    assert result.prompt_count == 1
    assert records[0]["article_id"] == "cafef_833adef5f3d9"
    assert "Return only valid JSON" in records[0]["prompt"]
    assert "EXPANSION" in records[0]["prompt"]


def test_validate_teacher_outputs_splits_gold_and_rejected(tmp_path: Path) -> None:
    articles_path = tmp_path / "articles_clean.jsonl"
    teacher_outputs_path = tmp_path / "teacher_outputs.jsonl"
    ai_path = tmp_path / "events_ai_generated.jsonl"
    gold_path = tmp_path / "events_gold.jsonl"
    rejected_path = tmp_path / "events_rejected.jsonl"
    report_path = tmp_path / "labeling_summary.md"
    articles_path.write_text(json.dumps(_article(), ensure_ascii=False) + "\n", encoding="utf-8")
    teacher_outputs_path.write_text(
        json.dumps(_teacher_output_record(), ensure_ascii=False) + "\n"
        + json.dumps(_bad_teacher_output_record(), ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    result = validate_teacher_outputs(
        articles_path=articles_path,
        teacher_output_path=teacher_outputs_path,
        ai_generated_output_path=ai_path,
        gold_output_path=gold_path,
        rejected_output_path=rejected_path,
        report_path=report_path,
        run_id="test_run",
    )

    assert result.total_count == 2
    assert result.pass_count == 1
    assert result.rejected_count == 1
    assert read_jsonl(gold_path)[0]["validation_status"] == "PASS"
    assert read_jsonl(rejected_path)[0]["validation_status"] == "FAIL"
    assert "Auto validation pass rate" in report_path.read_text(encoding="utf-8")


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
            "den ket qua kinh doanh."
        ),
        "tickers_hint": ["HPG"],
        "company_names_hint": ["Hoa Phat Group"],
        "event_type_hints": ["EXPANSION"],
        "event_subtype_hints": ["NEW_FACTORY"],
    }


def _teacher_output_record() -> dict:
    return {
        "article_id": "cafef_833adef5f3d9",
        "teacher_model": "fixture_teacher",
        "prompt_version": "m02_teacher_v1",
        "raw_output": {
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
    }


def _bad_teacher_output_record() -> dict:
    record = _teacher_output_record()
    record["raw_output"] = dict(record["raw_output"])
    record["raw_output"]["events"] = [dict(record["raw_output"]["events"][0])]
    record["raw_output"]["events"][0]["event_type"] = "BAD_TYPE"
    return record
