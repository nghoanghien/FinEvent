from __future__ import annotations

import json
from pathlib import Path

from finevent.extraction.models import ExtractionRunConfig
from finevent.extraction.validation import validate_or_repair_extraction_output
from finevent.extraction.workflow import (
    ExtractionWorkflowArtifacts,
    build_public_result,
    run_online_extraction_workflow,
)
from finevent.rag.pipeline import run_rag_preparation
from finevent.retrieval.experiments import run_online_retrieval


class RecordingStudentModel:
    def __init__(self, output: dict):
        self.output = output
        self.prompt = ""

    def invoke(self, prompt: str) -> str:
        self.prompt = prompt
        return json.dumps(self.output, ensure_ascii=False)


def test_online_extraction_event_text_runs_without_retrieval(tmp_path: Path) -> None:
    state = run_online_extraction_workflow(
        {
            "input_type": "text",
            "title": "HPG khoi cong du an nha may moi",
            "value": (
                "Tap doan Hoa Phat cong bo khoi cong du an nha may moi tai khu cong nghiep. "
                "Du an du kien mo rong nang luc san xuat."
            ),
            "source": "manual",
        },
        config=ExtractionRunConfig(use_retrieval=False),
        artifacts=ExtractionWorkflowArtifacts(logs_dir=tmp_path / "runs"),
    )
    result = build_public_result(state)

    assert result["document_label"] == "HAS_EVENT"
    assert result["events"]
    assert result["events"][0]["event_type"] == "EXPANSION"
    assert result["retrieval_trace"] == []
    assert result["selected_patterns"] == []
    assert Path(result["run_dir"], "result.json").exists()
    assert {trace["node"] for trace in result["node_traces"]} >= {
        "preprocess",
        "extraction",
        "validation_repair",
    }


def test_online_extraction_respects_prompt_budget_before_student_call(tmp_path: Path) -> None:
    student = RecordingStudentModel(
        {
            "article_id": "manual_long_input",
            "document_label": "NO_EVENT",
            "label_reason": "Fixture output has no reportable event.",
            "events": [],
            "warnings": [],
            "model_info": {
                "model_name": "fixture_student",
                "prompt_version": "m06_test",
                "run_id": "fixture_run",
            },
        }
    )
    state = run_online_extraction_workflow(
        {
            "input_type": "text",
            "title": "HPG cong bo nhieu thong tin doanh nghiep",
            "value": "HPG cap nhat thong tin du an va tinh hinh kinh doanh. " * 300,
            "source": "manual",
        },
        config=ExtractionRunConfig(
            use_retrieval=False,
            max_article_chars=900,
            max_prompt_chars=5000,
        ),
        artifacts=ExtractionWorkflowArtifacts(logs_dir=tmp_path / "runs"),
        langchain_model=student,
    )

    assert len(student.prompt) <= 5000
    assert state.raw_model_output is not None


def test_online_extraction_default_prompt_has_no_text_cap(tmp_path: Path) -> None:
    student = RecordingStudentModel(
        {
            "article_id": "manual_uncapped_input",
            "document_label": "NO_EVENT",
            "label_reason": "Fixture output has no reportable event.",
            "events": [],
            "warnings": [],
            "model_info": {
                "model_name": "fixture_student",
                "prompt_version": "m06_test",
                "run_id": "fixture_run",
            },
        }
    )
    text = "HPG cap nhat thong tin du an. " + ("noi dung dai " * 400) + "UNCAPPED_TAIL"

    run_online_extraction_workflow(
        {
            "input_type": "text",
            "title": "HPG cap nhat thong tin doanh nghiep",
            "value": text,
            "source": "manual",
        },
        config=ExtractionRunConfig(use_retrieval=False),
        artifacts=ExtractionWorkflowArtifacts(logs_dir=tmp_path / "runs"),
        langchain_model=student,
    )

    assert "UNCAPPED_TAIL" in student.prompt
    assert len(student.prompt) > 2200


def test_online_extraction_no_event_text_returns_no_event(tmp_path: Path) -> None:
    state = run_online_extraction_workflow(
        {
            "input_type": "text",
            "title": "Thi truong chung khoan dao dong trong phien",
            "value": (
                "VN-Index tang giam dan xen trong phien khi nha dau tu than trong. "
                "Bai viet chi tom tat dien bien thi truong chung."
            ),
        },
        config=ExtractionRunConfig(use_retrieval=False),
        artifacts=ExtractionWorkflowArtifacts(logs_dir=tmp_path / "runs"),
    )
    result = build_public_result(state)

    assert result["document_label"] == "NO_EVENT"
    assert result["events"] == []
    assert "no_company_or_ticker_hint" in result["workflow_warnings"]


def test_validation_repairs_markdown_wrapped_json() -> None:
    article = _event_article()
    config = ExtractionRunConfig()
    raw_output = """
    Here is the JSON:
    ```json
    {
      "article_id": "cafef_833adef5f3d9",
      "document_label": "NO_EVENT",
      "label_reason": "Fixture repair case has no remaining event.",
      "events": [],
      "warnings": [],
      "model_info": {
        "model_name": "fixture_student",
        "prompt_version": "m06_test",
        "run_id": "fixture_run"
      }
    }
    ```
    """

    result = validate_or_repair_extraction_output(
        raw_output,
        article=article,
        run_id="fixture_run",
        config=config,
    )

    assert result.repaired
    assert result.output["document_label"] == "NO_EVENT"
    assert not [issue for issue in result.issues if issue["severity"] == "error"]


def test_validation_locks_system_identifiers_to_input_article() -> None:
    article = _event_article()
    raw_output = {
        "article_id": "wrong_article_id",
        "document_label": "HAS_EVENT",
        "label_reason": "Wrong article id fixture still contains an expansion event.",
        "events": [
            {
                "event_id": "wrong_article_id_e01",
                "ticker": "HPG",
                "company_name": "Hoa Phat Group",
                "event_type": "EXPANSION",
                "event_subtype": "NEW_FACTORY",
                "event_summary": "Hoa Phat cong bo khoi cong du an nha may moi.",
                "event_reason": "Evidence states Hoa Phat started a new factory project.",
                "event_arguments": {},
                "impact_sentiment": "POSITIVE",
                "evidence_span": "Tap doan Hoa Phat cong bo khoi cong du an nha may moi.",
                "source_url": "https://example.com/wrong",
                "published_at": "2025-01-01",
                "confidence": 0.8,
            }
        ],
        "warnings": [],
        "model_info": {
            "model_name": "hallucinated_model",
            "prompt_version": "bad_prompt",
            "run_id": "bad_run",
        },
    }

    result = validate_or_repair_extraction_output(
        raw_output,
        article=article,
        run_id="fixture_run",
        config=ExtractionRunConfig(student_model="fixture_student", prompt_version="m06_test"),
    )

    assert result.output["article_id"] == article["article_id"]
    assert result.output["model_info"]["run_id"] == "fixture_run"
    assert result.output["model_info"]["model_name"] == "fixture_student"
    assert result.output["events"][0]["event_id"].startswith(f"{article['article_id']}_")
    assert result.output["events"][0]["source_url"] == article["url"]
    assert result.output["events"][0]["published_at"] == article["published_at"]


def test_online_extraction_uses_m04_retrieval_context_patterns(tmp_path: Path) -> None:
    articles_path = tmp_path / "articles_clean.jsonl"
    gold_path = tmp_path / "events_gold.jsonl"
    articles_path.write_text(
        json.dumps(_event_article(), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    gold_path.write_text(
        json.dumps(_event_gold_record(), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    rag_result = run_rag_preparation(
        articles_path=articles_path,
        gold_path=gold_path,
        chunks_output_path=tmp_path / "chunks.jsonl",
        patterns_output_path=tmp_path / "patterns.jsonl",
        rejected_patterns_output_path=tmp_path / "patterns_rejected.jsonl",
        chunk_patterns_output_path=tmp_path / "chunk_patterns.jsonl",
        retrieval_dir=tmp_path / "retrieval",
        vector_store_dir=tmp_path / "vector_store",
        report_path=tmp_path / "rag_summary.md",
        embedding_dimension=32,
        target_words=16,
        max_words=32,
        overlap_words=4,
    )
    retrieval_result = run_online_retrieval(
        chunks_path=rag_result.chunks_path,
        bm25_index_path=rag_result.bm25_index_path,
        embeddings_path=rag_result.embeddings_path,
        articles_path=articles_path,
        gold_path=gold_path,
        output_path=tmp_path / "online_contexts.jsonl",
        logs_path=tmp_path / "online_retrieval_logs.jsonl",
        metrics_path=tmp_path / "online_retrieval_metrics.csv",
        error_analysis_path=tmp_path / "online_retrieval_error_analysis.md",
    )

    state = run_online_extraction_workflow(
        {"input_type": "article", "article": _event_article()},
        artifacts=ExtractionWorkflowArtifacts(
            retrieval_results_path=retrieval_result.output_path,
            logs_dir=tmp_path / "runs",
        ),
    )
    result = build_public_result(state)

    assert result["document_label"] == "HAS_EVENT"
    assert result["retrieval_trace"]
    assert result["selected_patterns"]
    assert result["selected_patterns"][0]["event_type"] == "EXPANSION"
    assert "matched_patterns" in state.extraction_prompt
    assert state.retrieval_run_id


def test_online_extraction_multi_event_mode_consumes_matching_m04_run(tmp_path: Path) -> None:
    articles_path = tmp_path / "articles_clean.jsonl"
    gold_path = tmp_path / "events_gold.jsonl"
    articles_path.write_text(
        json.dumps(_event_article(), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    gold_path.write_text(
        json.dumps(_event_gold_record(), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    rag_result = run_rag_preparation(
        articles_path=articles_path,
        gold_path=gold_path,
        chunks_output_path=tmp_path / "chunks.jsonl",
        patterns_output_path=tmp_path / "patterns.jsonl",
        rejected_patterns_output_path=tmp_path / "patterns_rejected.jsonl",
        chunk_patterns_output_path=tmp_path / "chunk_patterns.jsonl",
        retrieval_dir=tmp_path / "retrieval",
        vector_store_dir=tmp_path / "vector_store",
        report_path=tmp_path / "rag_summary.md",
        embedding_dimension=32,
        target_words=16,
        max_words=32,
        overlap_words=4,
    )
    retrieval_result = run_online_retrieval(
        chunks_path=rag_result.chunks_path,
        bm25_index_path=rag_result.bm25_index_path,
        embeddings_path=rag_result.embeddings_path,
        articles_path=articles_path,
        gold_path=gold_path,
        output_path=tmp_path / "online_contexts.jsonl",
        logs_path=tmp_path / "online_retrieval_logs.jsonl",
        metrics_path=tmp_path / "online_retrieval_metrics.csv",
        error_analysis_path=tmp_path / "online_retrieval_error_analysis.md",
        config_name="multi_event_aware_hybrid",
    )

    state = run_online_extraction_workflow(
        {"input_type": "article", "article": _event_article()},
        config=ExtractionRunConfig(retrieval_config="multi_event_aware_hybrid"),
        artifacts=ExtractionWorkflowArtifacts(
            retrieval_results_path=retrieval_result.output_path,
            logs_dir=tmp_path / "runs",
        ),
    )
    result = build_public_result(state)

    assert result["selected_patterns"]
    retrieval_trace = next(
        trace for trace in result["node_traces"] if trace["node"] == "load_retrieval_contexts"
    )
    assert retrieval_trace["output_summary"]["retrieval_run_id"] == state.retrieval_run_id
    assert state.retrieval_run_id and "multi_event_aware_hybrid" in state.retrieval_run_id


def _event_article() -> dict:
    text = (
        "Tap doan Hoa Phat cong bo khoi cong du an nha may moi tai khu cong nghiep.\n"
        "Du an du kien mo rong nang luc san xuat va co the tac dong tich cuc "
        "den ket qua kinh doanh."
    )
    return {
        "article_id": "cafef_833adef5f3d9",
        "source": "cafef",
        "url": "file://tests/fixtures/html/cafef_sample.html",
        "title": "HPG khoi cong du an nha may moi",
        "published_at": "2026-01-15T08:00:00+07:00",
        "text": text,
        "content_hash": "sha256:fixture",
        "tickers_hint": ["HPG"],
        "company_names_hint": ["Hoa Phat Group"],
        "sector_hints": ["materials_steel"],
        "event_keywords": ["khoi cong", "mo rong", "nha may moi"],
        "event_type_hints": ["EXPANSION"],
        "event_subtype_hints": ["NEW_FACTORY"],
        "language": "vi",
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
