from __future__ import annotations

import csv
from pathlib import Path

from finevent.evaluation.metrics import event_match_score, match_events
from finevent.evaluation.pipeline import run_evaluation_pipeline
from finevent.jsonl import read_jsonl, write_jsonl


def test_event_matching_scores_ticker_type_and_evidence_overlap() -> None:
    gold = _contract_event()
    prediction = {
        **_contract_event(),
        "event_id": "pred_001",
        "event_summary": "HPG trung thau goi thau nha may.",
    }

    score, breakdown = event_match_score(gold, prediction)
    matches, unmatched_gold, unmatched_pred = match_events([gold], [prediction])

    assert score > 0.8
    assert breakdown["ticker_or_company"] == 1.0
    assert breakdown["event_type"] == 1.0
    assert len(matches) == 1
    assert unmatched_gold == []
    assert unmatched_pred == []


def test_evaluation_pipeline_writes_ablation_reports(tmp_path: Path) -> None:
    gold_path = tmp_path / "events_gold.jsonl"
    predictions_path = tmp_path / "predictions.jsonl"
    output_dir = tmp_path / "evaluation"
    write_jsonl(gold_path, _gold_records())
    write_jsonl(predictions_path, _prediction_records())

    result = run_evaluation_pipeline(
        gold_path=gold_path,
        predictions_path=predictions_path,
        runs_dir=None,
        retrieval_metrics_path=None,
        output_dir=output_dir,
        default_config_name="fixture_default",
    )

    metrics_rows = _read_csv(result.metrics_by_run_path)
    hallucination_rows = _read_csv(result.hallucination_metrics_path)
    error_rows = _read_csv(result.errors_by_type_path)
    per_type_rows = _read_csv(result.per_event_type_path)
    error_examples = read_jsonl(result.error_examples_path)
    summary = result.eval_summary_path.read_text(encoding="utf-8")
    report_index = result.report_index_path.read_text(encoding="utf-8")
    extraction_summary = result.extraction_batch_summary_path.read_text(encoding="utf-8")
    verification_summary = result.verification_summary_path.read_text(encoding="utf-8")
    schema_summary = result.schema_error_summary_path.read_text(encoding="utf-8")
    recommendations = result.improvement_recommendations_path.read_text(encoding="utf-8")

    assert result.config_count == 2
    assert result.article_count == 3
    assert {row["config_name"] for row in metrics_rows} == {"baseline", "workflow"}
    assert _metric(metrics_rows, "workflow", "event_detection_f1") > _metric(
        metrics_rows,
        "baseline",
        "event_detection_f1",
    )
    assert _metric(metrics_rows, "workflow", "event_type_macro_f1") > 0
    assert any(row["config_name"] == "workflow" for row in hallucination_rows)
    assert any(row["event_type"] == "CONTRACT" for row in per_type_rows)
    assert any(row["error_code"] == "E_NO_EVENT_FALSE_POSITIVE" for row in error_rows)
    assert any(row["error_code"] == "E_MISSED_EVENT" for row in error_rows)
    assert any(record["error_code"] == "E_UNSUPPORTED_ARGUMENT" for record in error_examples)
    assert "Best config: `workflow`" in summary
    assert "extraction_batch_summary.md" in report_index
    assert "Extraction Batch Summary" in extraction_summary
    assert "Verification And Grounding Summary" in verification_summary
    assert "Schema And Error Summary" in schema_summary
    assert "Improvement Recommendations" in recommendations


def test_evaluation_handles_missing_predictions_without_crashing(tmp_path: Path) -> None:
    gold_path = tmp_path / "events_gold.jsonl"
    output_dir = tmp_path / "evaluation"
    write_jsonl(gold_path, [_gold_record("article_001", [_contract_event()])])

    result = run_evaluation_pipeline(
        gold_path=gold_path,
        predictions_path=None,
        runs_dir=None,
        retrieval_metrics_path=None,
        output_dir=output_dir,
        default_config_name="no_predictions",
    )
    metrics_rows = _read_csv(result.metrics_by_run_path)
    error_examples = read_jsonl(result.error_examples_path)

    assert result.config_count == 1
    assert float(metrics_rows[0]["event_detection_recall"]) == 0.0
    assert error_examples[0]["error_code"] == "E_MISSED_EVENT"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]


def _metric(rows: list[dict[str, str]], config_name: str, metric_name: str) -> float:
    for row in rows:
        if row["config_name"] == config_name:
            return float(row[metric_name])
    raise AssertionError(f"Missing metric row for {config_name}")


def _gold_records() -> list[dict]:
    return [
        _gold_record("article_contract", [_contract_event()]),
        _gold_record("article_no_event", []),
        _gold_record("article_leadership", [_leadership_event()]),
    ]


def _prediction_records() -> list[dict]:
    return [
        {
            "config_name": "baseline",
            "run_id": "baseline_001",
            "prediction": _label("article_contract", [_contract_event()]),
            "verification_report": {
                "unsupported_fields": [
                    {
                        "event_id": "contract_e01",
                        "field": "event_arguments.contract_value",
                    }
                ],
                "metrics": {
                    "evidence_coverage": 1.0,
                    "unsupported_field_rate": 0.25,
                    "unsupported_event_rate": 0.0,
                    "groundedness_score": 0.7,
                },
            },
        },
        {
            "config_name": "baseline",
            "run_id": "baseline_002",
            "prediction": _label("article_no_event", [_extra_contract_event()]),
        },
        {
            "config_name": "workflow",
            "run_id": "workflow_001",
            "prediction": _label("article_contract", [_contract_event()]),
            "hallucination_metrics": {
                "evidence_coverage": 1.0,
                "unsupported_field_rate": 0.0,
                "unsupported_event_rate": 0.0,
                "groundedness_score": 1.0,
            },
        },
        {
            "config_name": "workflow",
            "run_id": "workflow_002",
            "prediction": _label("article_no_event", []),
        },
        {
            "config_name": "workflow",
            "run_id": "workflow_003",
            "prediction": _label("article_leadership", [_leadership_event()]),
        },
    ]


def _gold_record(article_id: str, events: list[dict]) -> dict:
    return {
        "article_id": article_id,
        "label_schema_version": "event_schema_v1",
        "label_source": "ai_generated",
        "teacher_model": "fixture_teacher",
        "prompt_version": "fixture_prompt",
        "validation_status": "PASS",
        "label": _label(article_id, events),
    }


def _label(article_id: str, events: list[dict]) -> dict:
    return {
        "article_id": article_id,
        "document_label": "HAS_EVENT" if events else "NO_EVENT",
        "events": events,
        "warnings": [],
        "model_info": {
            "model_name": "fixture_model",
            "prompt_version": "fixture_prompt",
            "run_id": "fixture_run",
        },
    }


def _contract_event() -> dict:
    return {
        "event_id": "contract_e01",
        "ticker": "HPG",
        "company_name": "Hoa Phat",
        "event_type": "CONTRACT",
        "event_subtype": "BIDDING_WIN",
        "event_summary": "HPG trung thau goi thau xay dung nha may.",
        "event_arguments": {
            "project": "goi thau xay dung nha may",
            "contract_value": "500 ty dong",
        },
        "impact_sentiment": "POSITIVE",
        "evidence_span": "HPG da trung thau goi thau xay dung nha may tri gia 500 ty dong.",
        "source_url": "https://example.test/contract",
        "published_at": "2026-01-15T08:00:00+07:00",
        "confidence": 0.9,
    }


def _extra_contract_event() -> dict:
    event = _contract_event()
    event["event_id"] = "extra_e01"
    event["ticker"] = "VNM"
    return event


def _leadership_event() -> dict:
    return {
        "event_id": "leadership_e01",
        "ticker": "VCB",
        "company_name": "Vietcombank",
        "event_type": "LEADERSHIP",
        "event_subtype": "CEO_APPOINTMENT",
        "event_summary": "VCB bo nhiem tong giam doc moi.",
        "event_arguments": {
            "person": "Nguyen Van A",
            "role": "tong giam doc",
            "action": "bo nhiem",
        },
        "impact_sentiment": "NEUTRAL",
        "evidence_span": "VCB bo nhiem ong Nguyen Van A lam tong giam doc.",
        "source_url": "https://example.test/leadership",
        "published_at": "2026-01-16T08:00:00+07:00",
        "confidence": 0.82,
    }
