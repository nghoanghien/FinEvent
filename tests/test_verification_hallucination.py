from __future__ import annotations

from pathlib import Path

from finevent.extraction.models import ExtractionRunConfig
from finevent.extraction.verification import (
    build_self_verification_prompt,
    verify_extraction_output,
)
from finevent.extraction.workflow import (
    ExtractionWorkflowArtifacts,
    build_public_result,
    run_online_extraction_workflow,
)


def test_verification_drops_event_without_grounded_evidence() -> None:
    draft = _draft_contract_output()
    draft["events"][0]["evidence_span"] = "HPG ky hop dong 999 ty voi doi tac bi mat."

    result = verify_extraction_output(draft, article=_article())

    assert result.verified_output["document_label"] == "NO_EVENT"
    assert result.verified_output["events"] == []
    assert result.report["dropped_events"][0]["reason"] == "evidence_span_unsupported"
    assert result.metrics["unsupported_event_rate"] == 1.0
    assert result.metrics["evidence_coverage"] == 0.0


def test_verification_nulls_unsupported_argument_but_keeps_supported_event() -> None:
    draft = _draft_contract_output()
    draft["events"][0]["event_arguments"]["contract_value"] = "500 ty dong"
    draft["events"][0]["event_arguments"]["project"] = "goi thau xay dung nha may"

    result = verify_extraction_output(draft, article=_article())
    event = result.verified_output["events"][0]

    assert result.verified_output["document_label"] == "HAS_EVENT"
    assert event["event_arguments"]["project"] == "goi thau xay dung nha may"
    assert event["event_arguments"]["contract_value"] is None
    assert result.report["unsupported_fields"][0]["field"] == "event_arguments.contract_value"
    assert result.metrics["unsupported_field_rate"] > 0


def test_verification_strips_fields_outside_schema() -> None:
    draft = _draft_contract_output()
    draft["impact_severity"] = "HIGH"
    draft["events"][0]["impact_severity"] = "HIGH"

    result = verify_extraction_output(draft, article=_article())

    assert "impact_severity" not in result.verified_output
    assert "impact_severity" not in result.verified_output["events"][0]
    assert {
        repair["action"] for repair in result.report["repairs"]
    } >= {"drop_unexpected_top_level_field", "drop_unexpected_event_field"}


def test_online_workflow_runs_verification_and_writes_artifacts(tmp_path: Path) -> None:
    state = run_online_extraction_workflow(
        {"input_type": "article", "article": _article()},
        config=ExtractionRunConfig(use_retrieval=False, use_patterns=False),
        artifacts=ExtractionWorkflowArtifacts(logs_dir=tmp_path / "runs"),
        raw_model_output=_draft_contract_output(),
    )
    result = build_public_result(state)

    assert result["verification_report"]["verified_event_count"] == 1
    assert "verification" in {trace["node"] for trace in result["node_traces"]}
    assert result["hallucination_metrics"]["groundedness_score"] > 0
    assert Path(result["run_dir"], "draft_output.json").exists()
    assert Path(result["run_dir"], "verified_output.json").exists()
    assert Path(result["run_dir"], "verification_report.json").exists()


def test_self_verification_prompt_is_grounded_and_json_only_oriented() -> None:
    prompt = build_self_verification_prompt(
        article=_article(),
        draft_output=_draft_contract_output(),
        retrieved_contexts=[
            {
                "chunk_id": "ctx_001",
                "title": "Tin lien quan",
                "text": "Bo canh tranh dau thau cong bo ket qua goi thau.",
            }
        ],
    )

    assert "Use only the article and retrieved contexts" in prompt
    assert "Return JSON only" in prompt
    assert "draft_output_json" in prompt


def _article() -> dict:
    return {
        "article_id": "manual_contract_001",
        "source": "manual",
        "url": "https://example.test/hpg-hop-dong",
        "title": "HPG trung thau goi thau xay dung nha may",
        "published_at": "2026-01-15T08:00:00+07:00",
        "text": (
            "Tap doan Hoa Phat cho biet HPG da trung thau goi thau xay dung nha may "
            "tai Binh Duong. Du an du kien giup cong ty mo rong nang luc san xuat."
        ),
        "tickers_hint": ["HPG"],
        "company_names_hint": ["Hoa Phat"],
        "event_keywords": ["trung thau", "goi thau", "nha may"],
        "event_type_hints": ["CONTRACT"],
        "event_subtype_hints": ["BIDDING_WIN"],
        "language": "vi",
    }


def _draft_contract_output() -> dict:
    return {
        "article_id": "manual_contract_001",
        "document_label": "HAS_EVENT",
        "events": [
            {
                "event_id": "manual_contract_001_e01",
                "ticker": "HPG",
                "company_name": "Hoa Phat",
                "event_type": "CONTRACT",
                "event_subtype": "BIDDING_WIN",
                "event_summary": "HPG trung thau goi thau xay dung nha may.",
                "event_arguments": {
                    "project": "goi thau xay dung nha may",
                },
                "impact_sentiment": "POSITIVE",
                "evidence_span": "HPG da trung thau goi thau xay dung nha may tai Binh Duong.",
                "source_url": "https://example.test/hpg-hop-dong",
                "published_at": "2026-01-15T08:00:00+07:00",
                "confidence": 0.86,
            }
        ],
        "warnings": [],
        "model_info": {
            "model_name": "fixture_student",
            "prompt_version": "m07_test",
            "run_id": "fixture_run",
        },
    }
