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
    run_langchain_student_model,
)
from finevent.extraction.validation import validate_or_repair_extraction_output
from finevent.extraction.verification import VerificationConfig, verify_extraction_output
from finevent.jsonl import write_jsonl
from finevent.logging_utils import create_run_id
from finevent.patterns.models import PatternCandidate
from finevent.patterns.querying import build_pattern_queries_from_article
from finevent.patterns.store import PatternStore
from finevent.rag.embeddings import build_embedding_client
from finevent.retrieval.engine import RetrievalEngine, artifacts_exist
from finevent.retrieval.models import DEFAULT_RETRIEVAL_CONFIGS, RetrievalCandidate, RetrievalQuery
from finevent.retrieval.querying import build_queries_from_article
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class ExtractionWorkflowArtifacts:
    chunks_path: PathLike = "data/processed/chunks.jsonl"
    bm25_index_path: PathLike = "data/retrieval/bm25_index.pkl"
    retrieval_embeddings_path: PathLike = "data/retrieval/chunk_embeddings.jsonl"
    patterns_path: PathLike = "data/patterns/patterns.jsonl"
    pattern_embeddings_path: PathLike = "data/patterns/pattern_embeddings.jsonl"
    logs_dir: PathLike = "runs/extraction"
    dictionary_path: PathLike = "data/dictionaries/ticker_company_map.csv"
    keyword_taxonomy_path: PathLike = "data/dictionaries/event_keyword_taxonomy.csv"
    retrieval_query_embedding_provider: str | None = None
    retrieval_query_embedding_model: str | None = None
    retrieval_query_embedding_dimension: int = 128
    pattern_query_embedding_provider: str | None = None
    pattern_query_embedding_model: str | None = None
    pattern_query_embedding_dimension: int = 128


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
    _run_node(state, "query_plan", lambda: _node_query_plan(state))
    _run_node(state, "retrieve_rerank", lambda: _node_retrieve(state, artifact_config))
    _run_node(state, "pattern_selection", lambda: _node_select_patterns(state, artifact_config))
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


def _node_query_plan(state: ExtractionWorkflowState) -> JsonDict:
    if not state.article:
        raise ValueError("preprocess must run before query_plan.")
    retrieval_config = DEFAULT_RETRIEVAL_CONFIGS.get(state.config.retrieval_config)
    query_mode = retrieval_config.query_mode if retrieval_config else "legacy"
    queries = build_queries_from_article(state.article, query_mode=query_mode)
    state.query_plan = [query.to_dict() for query in queries]
    if not queries:
        state.warnings.append("query_plan_empty")
    return {"query_count": len(queries), "query_mode": query_mode}


def _node_retrieve(
    state: ExtractionWorkflowState,
    artifacts: ExtractionWorkflowArtifacts,
) -> JsonDict:
    if not state.config.use_retrieval:
        state.warnings.append("retrieval_disabled")
        return {"retrieved_count": 0}
    if not state.query_plan:
        state.warnings.append("retrieval_skipped_empty_query_plan")
        return {"retrieved_count": 0}
    if not artifacts_exist(
        chunks_path=artifacts.chunks_path,
        bm25_index_path=artifacts.bm25_index_path,
        embeddings_path=artifacts.retrieval_embeddings_path,
    ):
        state.warnings.append("retrieval_artifacts_missing")
        return {"retrieved_count": 0}

    query_client = None
    if artifacts.retrieval_query_embedding_provider:
        query_client = build_embedding_client(
            provider=artifacts.retrieval_query_embedding_provider,
            model_name=artifacts.retrieval_query_embedding_model,
            dimension=artifacts.retrieval_query_embedding_dimension,
        )
    engine = RetrievalEngine.from_artifacts(
        chunks_path=artifacts.chunks_path,
        bm25_index_path=artifacts.bm25_index_path,
        embeddings_path=artifacts.retrieval_embeddings_path,
        query_embedding_client=query_client,
    )
    candidates = engine.retrieve(
        [_retrieval_query_from_dict(query) for query in state.query_plan],
        config=state.config.retrieval_config,
    )
    selected = candidates[: state.config.max_contexts]
    state.retrieved_contexts = [candidate.to_dict() for candidate in selected]
    if not selected and not state.config.allow_zero_context:
        state.errors.append("retrieval_empty")
    if not selected:
        state.warnings.append("retrieval_empty")
    return {"retrieved_count": len(selected)}


def _node_select_patterns(
    state: ExtractionWorkflowState,
    artifacts: ExtractionWorkflowArtifacts,
) -> JsonDict:
    if not state.config.use_patterns:
        state.warnings.append("pattern_selection_disabled")
        return {"pattern_count": 0}
    if not state.article:
        raise ValueError("preprocess must run before pattern selection.")
    patterns_path = Path(artifacts.patterns_path)
    pattern_embeddings_path = Path(artifacts.pattern_embeddings_path)
    if not patterns_path.exists() or not pattern_embeddings_path.exists():
        state.warnings.append("pattern_artifacts_missing")
        return {"pattern_count": 0}

    query_client = None
    if artifacts.pattern_query_embedding_provider:
        query_client = build_embedding_client(
            provider=artifacts.pattern_query_embedding_provider,
            model_name=artifacts.pattern_query_embedding_model,
            dimension=artifacts.pattern_query_embedding_dimension,
        )
    store = PatternStore.from_artifacts(
        patterns_path=artifacts.patterns_path,
        embeddings_path=artifacts.pattern_embeddings_path,
        query_embedding_client=query_client,
    )
    retrieval_config = DEFAULT_RETRIEVAL_CONFIGS.get(state.config.retrieval_config)
    query_mode = retrieval_config.query_mode if retrieval_config else "legacy"
    selection_strategy = "coverage" if query_mode == "event_intent" else "score"
    queries = build_pattern_queries_from_article(state.article, query_mode=query_mode)
    candidates = store.select_patterns_for_queries(
        queries,
        top_k=state.config.pattern_count,
        selection_strategy=selection_strategy,
    )
    state.selected_patterns = [candidate.to_dict() for candidate in candidates]
    if not candidates:
        state.warnings.append("pattern_selection_empty")
    return {
        "pattern_count": len(candidates),
        "pattern_query_count": len(queries),
        "pattern_query_mode": query_mode,
        "pattern_selection_strategy": selection_strategy,
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
    patterns = [_pattern_candidate_from_dict(record) for record in state.selected_patterns]
    state.extraction_prompt = build_extraction_prompt(
        article=state.article,
        contexts=contexts,
        patterns=patterns,
        prompt_version=state.config.prompt_version,
        max_article_chars=state.config.max_article_chars,
        max_context_chars=state.config.max_context_chars,
        max_pattern_excerpt_chars=state.config.max_pattern_excerpt_chars,
        max_pattern_output_chars=state.config.max_pattern_output_chars,
        max_prompt_chars=state.config.max_prompt_chars,
    )
    if raw_model_output is not None:
        state.raw_model_output = raw_model_output
    elif langchain_model is not None:
        state.raw_model_output = run_langchain_student_model(
            langchain_model,
            state.extraction_prompt,
        )
    else:
        state.raw_model_output = run_deterministic_student_extractor(
            article=state.article,
            run_id=state.run_id,
            model_name=state.config.student_model,
            prompt_version=state.config.prompt_version,
        )
    return {
        "prompt_chars": len(state.extraction_prompt),
        "raw_output_type": type(state.raw_model_output).__name__,
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
    (run_dir / "result.json").write_text(
        json.dumps(build_public_result(state), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_jsonl(run_dir / "trace.jsonl", (trace.to_dict() for trace in state.traces))
    return {
        "run_dir": str(run_dir),
        "trace_count": len(state.traces),
    }


def _retrieval_query_from_dict(record: JsonDict) -> RetrievalQuery:
    return RetrievalQuery(
        query_id=str(record["query_id"]),
        article_id=str(record["article_id"]),
        text=str(record["text"]),
        query_type=str(record["query_type"]),
        weight=float(record.get("weight", 1.0)),
        tickers=[str(item) for item in record.get("tickers", [])],
        company_names=[str(item) for item in record.get("company_names", [])],
        event_keywords=[str(item) for item in record.get("event_keywords", [])],
        event_type_hints=[str(item) for item in record.get("event_type_hints", [])],
        event_subtype_hints=[str(item) for item in record.get("event_subtype_hints", [])],
        intent_key=str(record["intent_key"]) if record.get("intent_key") else None,
        intent_event_type=(
            str(record["intent_event_type"]) if record.get("intent_event_type") else None
        ),
        intent_subtype_hints=[
            str(item) for item in record.get("intent_subtype_hints", [])
        ],
    )


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


def _pattern_candidate_from_dict(record: JsonDict) -> PatternCandidate:
    return PatternCandidate(
        rank=int(record["rank"]),
        pattern_id=str(record["pattern_id"]),
        article_id=str(record["article_id"]),
        document_label=str(record["document_label"]),
        event_type=record.get("event_type"),
        event_subtype=record.get("event_subtype"),
        ticker=record.get("ticker"),
        company_name=record.get("company_name"),
        score=float(record.get("score", 0.0)),
        score_breakdown=dict(record.get("score_breakdown", {})),
        input_excerpt=str(record["input_excerpt"]),
        gold_output=dict(record["gold_output"]),
        explanation_brief=str(record.get("explanation_brief") or ""),
        metadata=dict(record.get("metadata", {})),
    )
