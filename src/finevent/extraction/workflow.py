"""Online article extraction workflow orchestration."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from finevent.extraction.models import ExtractionRunConfig, ExtractionWorkflowState, NodeTrace
from finevent.extraction.preprocess import preprocess_extraction_input
from finevent.extraction.prompting import build_extraction_prompt
from finevent.extraction.student import (
    InvokableStudentModel,
    run_deterministic_student_extractor,
    run_langchain_student_model_with_trace,
)
from finevent.extraction.validation import validate_or_repair_extraction_output
from finevent.extraction.verification import VerificationConfig, verify_extraction_output
from finevent.jsonl import read_jsonl, write_jsonl
from finevent.logging_utils import create_run_id
from finevent.retrieval.models import RetrievalCandidate
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class ExtractionWorkflowArtifacts:
    retrieval_results_path: PathLike = "data/retrieval/online_contexts.jsonl"
    logs_dir: PathLike = "runs/extraction"
    dictionary_path: PathLike = "data/dictionaries/ticker_company_map.csv"
    keyword_taxonomy_path: PathLike = "data/dictionaries/event_keyword_taxonomy.csv"


def run_online_extraction_workflow(
    input_payload: JsonDict,
    *,
    config: ExtractionRunConfig | None = None,
    artifacts: ExtractionWorkflowArtifacts | None = None,
    langchain_model: InvokableStudentModel | None = None,
    raw_model_output: str | JsonDict | None = None,
    persist_logs: bool = True,
) -> ExtractionWorkflowState:
    run_config = config or ExtractionRunConfig.from_dict(input_payload.get("run_config"))
    artifact_config = artifacts or ExtractionWorkflowArtifacts()
    state = ExtractionWorkflowState(
        run_id=create_run_id("extract"),
        config=run_config,
        input_payload=input_payload,
    )

    _run_node(state, "preprocess", lambda: _node_preprocess(state, artifact_config))
    _run_node(
        state,
        "load_retrieval_contexts",
        lambda: _node_load_retrieval_contexts(state, artifact_config),
    )
    _run_node(
        state,
        "extraction",
        lambda: _node_extract(
            state,
            langchain_model=langchain_model,
            raw_model_output=raw_model_output,
        ),
    )
    _run_node(state, "validation_repair", lambda: _node_validate(state))
    if run_config.enable_verification:
        _run_node(state, "verification", lambda: _node_verify(state))
    else:
        state.warnings.append("verification_disabled")
    if persist_logs:
        _run_node(state, "logging", lambda: _node_log(state, artifact_config))
    return state


def build_public_result(state: ExtractionWorkflowState) -> JsonDict:
    final_output = state.final_output or {
        "article_id": state.article.get("article_id") if state.article else None,
        "document_label": "UNCERTAIN",
        "events": [],
        "warnings": ["workflow_finished_without_final_output"],
    }
    return {
        **final_output,
        "run_id": state.run_id,
        "retrieval_trace": state.retrieved_contexts,
        "selected_patterns": state.selected_patterns,
        "reasoning_trace": state.reasoning_trace,
        "validation_issues": state.validation_issues,
        "verification_report": state.verification_report,
        "hallucination_metrics": state.hallucination_metrics,
        "workflow_warnings": state.warnings,
        "workflow_errors": state.errors,
        "node_traces": [trace.to_dict() for trace in state.traces],
        "run_dir": state.run_dir,
    }


def _run_node(
    state: ExtractionWorkflowState,
    node_name: str,
    action: Callable[[], JsonDict],
) -> None:
    start = time.perf_counter()
    warnings_before = len(state.warnings)
    errors_before = len(state.errors)
    try:
        output_summary = action()
        status = "success"
    except Exception as exc:  # noqa: BLE001 - workflow must log node failure and continue/return.
        state.errors.append(f"{node_name}: {exc}")
        output_summary = {"error": str(exc)}
        status = "error"
    latency_ms = round((time.perf_counter() - start) * 1000, 3)
    state.traces.append(
        NodeTrace(
            node=node_name,
            status=status,
            latency_ms=latency_ms,
            output_summary=output_summary,
            warnings=state.warnings[warnings_before:],
            errors=state.errors[errors_before:],
        )
    )


def _node_preprocess(
    state: ExtractionWorkflowState,
    artifacts: ExtractionWorkflowArtifacts,
) -> JsonDict:
    article, warnings = preprocess_extraction_input(
        state.input_payload,
        dictionary_path=artifacts.dictionary_path,
        keyword_taxonomy_path=artifacts.keyword_taxonomy_path,
    )
    state.article = article
    state.warnings.extend(warnings)
    return {
        "article_id": article["article_id"],
        "text_char_count": article["text_char_count"],
        "ticker_count": len(article.get("tickers_hint", [])),
        "event_keyword_count": len(article.get("event_keywords", [])),
    }


def _node_load_retrieval_contexts(
    state: ExtractionWorkflowState,
    artifacts: ExtractionWorkflowArtifacts,
) -> JsonDict:
    if not state.article:
        raise ValueError("preprocess must run before loading retrieval contexts.")
    if not state.config.use_retrieval:
        state.warnings.append("retrieval_disabled")
        return {"retrieval_run_id": None, "retrieved_count": 0, "pattern_ref_count": 0}
    records = read_jsonl(artifacts.retrieval_results_path)
    if not records:
        state.warnings.append("retrieval_results_missing")
        if not state.config.allow_zero_context:
            state.errors.append("retrieval_results_missing")
        return {"retrieval_run_id": None, "retrieved_count": 0, "pattern_ref_count": 0}

    article_id = str(state.article.get("article_id") or "")
    record = _select_retrieval_record(
        records,
        article_id=article_id,
        retrieval_config=state.config.retrieval_config,
    )
    if record is None:
        state.warnings.append("retrieval_context_missing_for_article")
        if not state.config.allow_zero_context:
            state.errors.append("retrieval_context_missing_for_article")
        return {"retrieval_run_id": None, "retrieved_count": 0, "pattern_ref_count": 0}

    contexts = [
        context
        for context in record.get("contexts", [])
        if isinstance(context, dict)
    ][: state.config.max_contexts]
    state.retrieval_run_id = str(record.get("retrieval_run_id") or "")
    state.query_plan = [
        query for query in record.get("queries", []) if isinstance(query, dict)
    ]
    state.retrieved_contexts = contexts
    state.selected_patterns = _pattern_refs_from_contexts(contexts)
    if not contexts:
        state.warnings.append("retrieval_empty")
        if not state.config.allow_zero_context:
            state.errors.append("retrieval_empty")
    return {
        "retrieval_run_id": state.retrieval_run_id,
        "retrieved_count": len(contexts),
        "query_count": len(state.query_plan),
        "pattern_ref_count": len(state.selected_patterns),
    }


def _node_extract(
    state: ExtractionWorkflowState,
    *,
    langchain_model: InvokableStudentModel | None,
    raw_model_output: str | JsonDict | None,
) -> JsonDict:
    if not state.article:
        raise ValueError("preprocess must run before extraction.")
    contexts = [_retrieval_candidate_from_dict(record) for record in state.retrieved_contexts]
    state.extraction_prompt = build_extraction_prompt(
        article=state.article,
        contexts=contexts,
        prompt_version=state.config.prompt_version,
        max_article_chars=state.config.max_article_chars,
        max_context_chars=state.config.max_context_chars,
        max_pattern_output_chars=state.config.max_pattern_output_chars,
        max_prompt_chars=state.config.max_prompt_chars,
    )
    if raw_model_output is not None:
        state.raw_model_output = raw_model_output
        state.reasoning_trace = _reasoning_trace_from_raw_model_output(raw_model_output)
    elif langchain_model is not None:
        model_result = run_langchain_student_model_with_trace(
            langchain_model,
            state.extraction_prompt,
        )
        state.raw_model_output = model_result.content
        state.reasoning_trace = model_result.reasoning_trace
    else:
        state.raw_model_output = run_deterministic_student_extractor(
            article=state.article,
            run_id=state.run_id,
            model_name=state.config.student_model,
            prompt_version=state.config.prompt_version,
        )
        state.reasoning_trace = {
            "source": "deterministic_student",
            "has_provider_reasoning": False,
            "provider_reasoning_content": None,
        }
    return {
        "prompt_chars": len(state.extraction_prompt),
        "raw_output_type": type(state.raw_model_output).__name__,
        "has_provider_reasoning": bool(
            state.reasoning_trace.get("provider_reasoning_content")
        ),
    }


def _node_validate(state: ExtractionWorkflowState) -> JsonDict:
    if not state.article:
        raise ValueError("preprocess must run before validation.")
    if state.raw_model_output is None:
        raise ValueError("extraction must produce raw_model_output before validation.")
    result = validate_or_repair_extraction_output(
        state.raw_model_output,
        article=state.article,
        run_id=state.run_id,
        config=state.config,
    )
    state.draft_output = result.output
    state.final_output = result.output
    state.validation_issues = result.issues
    state.reasoning_trace = _with_output_reasons(state.reasoning_trace, result.output)
    if result.repaired:
        state.warnings.append("model_output_repaired")
    if result.parse_error:
        state.warnings.append("model_output_parse_error")
    if any(issue.get("severity") == "error" for issue in result.issues):
        state.warnings.append("validation_has_errors")
    return {
        "document_label": result.output.get("document_label"),
        "event_count": len(result.output.get("events", [])),
        "issue_count": len(result.issues),
        "repaired": result.repaired,
    }


def _node_verify(state: ExtractionWorkflowState) -> JsonDict:
    if not state.article:
        raise ValueError("preprocess must run before verification.")
    if state.draft_output is None:
        raise ValueError("validation_repair must produce draft_output before verification.")
    result = verify_extraction_output(
        state.draft_output,
        article=state.article,
        retrieved_contexts=state.retrieved_contexts,
        config=VerificationConfig(
            evidence_match_threshold=state.config.evidence_match_threshold,
            argument_match_threshold=state.config.argument_match_threshold,
            drop_unsupported_events=state.config.drop_unsupported_events,
            null_unsupported_arguments=state.config.null_unsupported_arguments,
            verification_version=state.config.verification_version,
        ),
    )
    state.final_output = result.verified_output
    state.verification_report = result.report
    state.hallucination_metrics = result.metrics

    if result.report.get("dropped_events"):
        state.warnings.append("verification_dropped_events")
    if result.report.get("unsupported_fields"):
        state.warnings.append("verification_unsupported_fields")
    if not result.report.get("schema_valid_after_verification", False):
        state.warnings.append("verification_schema_has_errors")
    return {
        "document_label": result.verified_output.get("document_label"),
        "event_count": len(result.verified_output.get("events", [])),
        "dropped_event_count": len(result.report.get("dropped_events", [])),
        "unsupported_field_count": len(result.report.get("unsupported_fields", [])),
        "groundedness_score": result.metrics.get("groundedness_score"),
    }


def _node_log(
    state: ExtractionWorkflowState,
    artifacts: ExtractionWorkflowArtifacts,
) -> JsonDict:
    run_dir = Path(artifacts.logs_dir) / state.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    state.run_dir = str(run_dir)
    (run_dir / "prompt.txt").write_text(state.extraction_prompt, encoding="utf-8")
    if state.draft_output is not None:
        (run_dir / "draft_output.json").write_text(
            json.dumps(state.draft_output, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if state.final_output is not None:
        (run_dir / "verified_output.json").write_text(
            json.dumps(state.final_output, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    if state.verification_report is not None:
        (run_dir / "verification_report.json").write_text(
            json.dumps(state.verification_report, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    (run_dir / "reasoning_trace.json").write_text(
        json.dumps(state.reasoning_trace, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (run_dir / "result.json").write_text(
        json.dumps(build_public_result(state), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_jsonl(run_dir / "trace.jsonl", (trace.to_dict() for trace in state.traces))
    return {
        "run_dir": str(run_dir),
        "trace_count": len(state.traces),
    }


def _reasoning_trace_from_raw_model_output(raw_output: str | JsonDict) -> JsonDict:
    if isinstance(raw_output, dict):
        explicit_reasoning = (
            raw_output.get("reasoning_trace")
            or raw_output.get("reasoning_content")
            or raw_output.get("cot")
        )
        return {
            "source": "raw_model_output",
            "has_provider_reasoning": bool(explicit_reasoning),
            "provider_reasoning_content": explicit_reasoning or None,
        }
    return {
        "source": "raw_model_output",
        "has_provider_reasoning": False,
        "provider_reasoning_content": None,
    }


def _with_output_reasons(reasoning_trace: JsonDict, output: JsonDict) -> JsonDict:
    events = output.get("events", [])
    event_reasons = []
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            event_reasons.append(
                {
                    "event_id": event.get("event_id"),
                    "event_type": event.get("event_type"),
                    "event_reason": event.get("event_reason"),
                    "evidence_span": event.get("evidence_span"),
                }
            )
    return {
        **reasoning_trace,
        "reasoning_policy": {
            "prompt_uses_private_step_by_step_reasoning": True,
            "output_exposes_raw_chain_of_thought": False,
            "output_exposes_concise_reasons": True,
        },
        "output_reasons": {
            "label_reason": output.get("label_reason"),
            "event_reasons": event_reasons,
        },
    }


def _select_retrieval_record(
    records: list[JsonDict],
    *,
    article_id: str,
    retrieval_config: str,
) -> JsonDict | None:
    matching_article = [
        record
        for record in records
        if isinstance(record, dict) and str(record.get("article_id") or "") == article_id
    ]
    for record in matching_article:
        if str(record.get("retrieval_config") or "") == retrieval_config:
            return record
    return matching_article[0] if matching_article else None


def _pattern_refs_from_contexts(contexts: list[JsonDict]) -> list[JsonDict]:
    seen: set[str] = set()
    refs: list[JsonDict] = []
    for context in contexts:
        raw_metadata = context.get("metadata")
        metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
        for raw_ref in metadata.get("pattern_refs", []):
            if not isinstance(raw_ref, dict):
                continue
            pattern_id = str(raw_ref.get("pattern_id") or "")
            key = pattern_id or repr(sorted(raw_ref.items()))
            if key in seen:
                continue
            seen.add(key)
            refs.append(raw_ref)
    return refs


def _retrieval_candidate_from_dict(record: JsonDict) -> RetrievalCandidate:
    return RetrievalCandidate(
        rank=int(record["rank"]),
        chunk_id=str(record["chunk_id"]),
        article_id=str(record["article_id"]),
        chunk_level=str(record["chunk_level"]),
        title=record.get("title"),
        text=str(record["text"]),
        source=str(record.get("source") or ""),
        url=str(record.get("url") or ""),
        published_at=record.get("published_at"),
        score=float(record.get("score", 0.0)),
        score_breakdown=dict(record.get("score_breakdown", {})),
        metadata=dict(record.get("metadata", {})),
    )
