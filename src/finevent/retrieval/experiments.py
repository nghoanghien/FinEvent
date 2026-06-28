"""Retrieval strategy comparison runner."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from finevent.jsonl import read_jsonl, write_jsonl
from finevent.rag.embeddings import EmbeddingClient
from finevent.retrieval.engine import RetrievalEngine
from finevent.retrieval.evaluation import (
    aggregate_metric_rows,
    build_error_analysis,
    build_eval_cases_from_gold,
    evaluate_results,
    write_metrics_csv,
)
from finevent.retrieval.llm_rerank import InvokableRerankModel, rerank_candidates_listwise
from finevent.retrieval.models import DEFAULT_RETRIEVAL_CONFIGS, RetrievalConfig
from finevent.retrieval.querying import build_queries_from_article
from finevent.retrieval.selection import select_final_candidates
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class RetrievalExperimentResult:
    logs_path: Path
    metrics_path: Path
    error_analysis_path: Path
    config_count: int
    eval_case_count: int


@dataclass(frozen=True)
class OnlineRetrievalRunResult:
    output_path: Path
    logs_path: Path
    metrics_path: Path
    error_analysis_path: Path
    article_count: int
    context_count: int
    eval_case_count: int


def run_retrieval_comparison(
    *,
    chunks_path: PathLike = "data/processed/chunks.jsonl",
    bm25_index_path: PathLike = "data/retrieval/bm25_index.pkl",
    embeddings_path: PathLike = "data/retrieval/chunk_embeddings.jsonl",
    gold_path: PathLike = "data/labels/events_gold.jsonl",
    logs_path: PathLike = "data/retrieval/retrieval_logs.jsonl",
    metrics_path: PathLike = "reports/evaluation/retrieval_metrics.csv",
    error_analysis_path: PathLike = "reports/evaluation/retrieval_error_analysis.md",
    config_names: list[str] | None = None,
    query_embedding_client: EmbeddingClient | None = None,
) -> RetrievalExperimentResult:
    engine = RetrievalEngine.from_artifacts(
        chunks_path=chunks_path,
        bm25_index_path=bm25_index_path,
        embeddings_path=embeddings_path,
        query_embedding_client=query_embedding_client,
    )
    eval_cases = build_eval_cases_from_gold(gold_path=gold_path, chunks_path=chunks_path)
    selected_config_names = config_names or [
        "bm25_only",
        "dense_only",
        "hybrid",
        "metadata_aware_hybrid",
        "rule_aware_rerank",
        "llm_reasoning_rerank",
        "multi_event_aware_hybrid",
    ]

    logs: list[JsonDict] = []
    metric_rows: list[JsonDict] = []
    for eval_case in eval_cases:
        for config_name in selected_config_names:
            config = DEFAULT_RETRIEVAL_CONFIGS[config_name]
            candidates = engine.retrieve(eval_case.queries, config=config)
            metrics = evaluate_results(
                candidates=candidates,
                relevant_chunk_ids=eval_case.relevant_chunk_ids,
                event_types=eval_case.article_event_types,
                event_relevant_chunk_ids=eval_case.article_event_relevant_chunk_ids,
            )
            metric_row = {
                "retrieval_config": config_name,
                "case_id": eval_case.case_id,
                "article_id": eval_case.article_id,
                "event_id": eval_case.event_id,
                "event_type": eval_case.event_type or "",
                "relevant_chunk_count": len(eval_case.relevant_chunk_ids),
                **metrics,
            }
            metric_rows.append(metric_row)
            logs.append(
                {
                    "case_id": eval_case.case_id,
                    "query_article_id": eval_case.article_id,
                    "retrieval_config": config_name,
                    "queries": [query.to_dict() for query in eval_case.queries],
                    "relevant_chunk_ids": sorted(eval_case.relevant_chunk_ids),
                    "metrics": metrics,
                    "results": [candidate.to_dict() for candidate in candidates],
                }
            )

    aggregate_rows = aggregate_metric_rows(metric_rows)
    write_jsonl(logs_path, logs)
    write_metrics_csv(metrics_path, aggregate_rows)
    Path(error_analysis_path).parent.mkdir(parents=True, exist_ok=True)
    Path(error_analysis_path).write_text(
        build_error_analysis(detailed_rows=metric_rows),
        encoding="utf-8",
    )
    return RetrievalExperimentResult(
        logs_path=Path(logs_path),
        metrics_path=Path(metrics_path),
        error_analysis_path=Path(error_analysis_path),
        config_count=len(selected_config_names),
        eval_case_count=len(eval_cases),
    )


def run_online_retrieval(
    *,
    chunks_path: PathLike = "data/processed/chunks.jsonl",
    bm25_index_path: PathLike = "data/retrieval/bm25_index.pkl",
    embeddings_path: PathLike = "data/retrieval/chunk_embeddings.jsonl",
    articles_path: PathLike = "data/processed/articles_clean.jsonl",
    gold_path: PathLike = "data/labels/events_gold.jsonl",
    output_path: PathLike = "data/retrieval/online_contexts.jsonl",
    logs_path: PathLike = "data/retrieval/online_retrieval_logs.jsonl",
    metrics_path: PathLike = "reports/evaluation/online_retrieval_metrics.csv",
    error_analysis_path: PathLike = "reports/evaluation/online_retrieval_error_analysis.md",
    config_name: str = "metadata_aware_hybrid",
    limit: int | None = None,
    offset: int = 0,
    max_contexts: int | None = None,
    query_embedding_client: EmbeddingClient | None = None,
    llm_rerank_mode: str = "off",
    llm_rerank_model: InvokableRerankModel | None = None,
    llm_rerank_model_name: str = "deterministic_listwise_rerank",
    llm_rerank_top_n: int = 15,
    llm_rerank_max_query_article_chars: int = 0,
    llm_rerank_max_candidate_chars: int = 0,
    llm_rerank_max_retries: int = 1,
    llm_rerank_retry_sleep_seconds: float = 1.0,
) -> OnlineRetrievalRunResult:
    if config_name not in DEFAULT_RETRIEVAL_CONFIGS:
        raise ValueError(f"Unknown retrieval config: {config_name}")
    config = DEFAULT_RETRIEVAL_CONFIGS[config_name]
    engine = RetrievalEngine.from_artifacts(
        chunks_path=chunks_path,
        bm25_index_path=bm25_index_path,
        embeddings_path=embeddings_path,
        query_embedding_client=query_embedding_client,
    )
    articles = _slice_articles(read_jsonl(articles_path), limit=limit, offset=offset)
    eval_cases_by_article = _eval_cases_by_article(
        gold_path=gold_path,
        chunks_path=chunks_path,
    )

    records: list[JsonDict] = []
    logs: list[JsonDict] = []
    metric_rows: list[JsonDict] = []
    context_count = 0
    eval_case_count = 0
    for article in articles:
        article_id = str(article.get("article_id") or "")
        queries = build_queries_from_article(article, query_mode=config.query_mode)
        candidate_pool = engine.retrieve(
            queries,
            config=config,
            select_final=False,
            apply_config_llm=llm_rerank_mode == "off",
        )
        llm_rerank_trace: JsonDict | None = None
        if llm_rerank_mode != "off":
            preselect_config = _config_with_preselect_count(
                config,
                count=max(
                    llm_rerank_top_n,
                    max_contexts or 0,
                    config.top_k_final,
                ),
            )
            preselected_candidates = select_final_candidates(
                candidate_pool,
                queries,
                preselect_config,
            )
            rerank_result = rerank_candidates_listwise(
                query_article=article,
                queries=queries,
                candidates=preselected_candidates,
                mode=llm_rerank_mode,
                model_name=llm_rerank_model_name,
                top_n=llm_rerank_top_n,
                model=llm_rerank_model,
                max_query_article_chars=llm_rerank_max_query_article_chars,
                max_candidate_chars=llm_rerank_max_candidate_chars,
                max_retries=llm_rerank_max_retries,
                retry_sleep_seconds=llm_rerank_retry_sleep_seconds,
            )
            candidates = rerank_result.candidates
            llm_rerank_trace = rerank_result.to_log_dict()
            llm_rerank_trace["preselect_context_count"] = len(preselected_candidates)
            llm_rerank_trace["final_context_cap"] = max_contexts
        else:
            candidates = select_final_candidates(candidate_pool, queries, config)
        if max_contexts is not None:
            candidates = candidates[:max_contexts]
        context_dicts = [candidate.to_dict() for candidate in candidates]
        context_count += len(context_dicts)
        pattern_refs = _pattern_refs_from_contexts(context_dicts)
        run_id = f"retrieval_{article_id}_{config_name}"
        metrics_for_article: list[JsonDict] = []
        for eval_case in eval_cases_by_article.get(article_id, []):
            metrics = evaluate_results(
                candidates=candidates,
                relevant_chunk_ids=eval_case.relevant_chunk_ids,
                event_types=eval_case.article_event_types,
                event_relevant_chunk_ids=eval_case.article_event_relevant_chunk_ids,
            )
            row = {
                "retrieval_config": config_name,
                "case_id": eval_case.case_id,
                "article_id": article_id,
                "event_id": eval_case.event_id,
                "event_type": eval_case.event_type or "",
                "relevant_chunk_count": len(eval_case.relevant_chunk_ids),
                **metrics,
            }
            metric_rows.append(row)
            metrics_for_article.append(row)
            eval_case_count += 1
        record = {
            "retrieval_run_id": run_id,
            "article_id": article_id,
            "retrieval_config": config_name,
            "retrieval_config_payload": config.to_dict(),
            "queries": [query.to_dict() for query in queries],
            "contexts": context_dicts,
            "pattern_refs": pattern_refs,
            "metrics": metrics_for_article,
        }
        if llm_rerank_trace is not None:
            record["llm_rerank"] = {
                key: value
                for key, value in llm_rerank_trace.items()
                if key not in {"raw_output", "parsed_output"}
            }
        records.append(record)
        logs.append(
            {
                "retrieval_run_id": run_id,
                "article_id": article_id,
                "retrieval_config": config_name,
                "query_count": len(queries),
                "context_count": len(context_dicts),
                "pattern_ref_count": len(pattern_refs),
                "llm_rerank": llm_rerank_trace,
                "metrics": metrics_for_article,
            }
        )

    aggregate_rows = aggregate_metric_rows(metric_rows)
    write_jsonl(output_path, records)
    write_jsonl(logs_path, logs)
    write_metrics_csv(metrics_path, aggregate_rows)
    Path(error_analysis_path).parent.mkdir(parents=True, exist_ok=True)
    Path(error_analysis_path).write_text(
        build_error_analysis(detailed_rows=metric_rows),
        encoding="utf-8",
    )
    return OnlineRetrievalRunResult(
        output_path=Path(output_path),
        logs_path=Path(logs_path),
        metrics_path=Path(metrics_path),
        error_analysis_path=Path(error_analysis_path),
        article_count=len(articles),
        context_count=context_count,
        eval_case_count=eval_case_count,
    )


def _slice_articles(
    articles: list[JsonDict],
    *,
    limit: int | None,
    offset: int,
) -> list[JsonDict]:
    start = max(offset, 0)
    selected = articles[start:]
    if limit is not None:
        selected = selected[: max(limit, 0)]
    return selected


def _config_with_preselect_count(config: RetrievalConfig, *, count: int) -> RetrievalConfig:
    if count <= 0:
        return config
    if not config.adaptive_top_k_final:
        return replace(config, top_k_final=max(config.top_k_final, count))
    return replace(
        config,
        top_k_final=max(config.top_k_final, count),
        top_k_single_event=max(config.top_k_single_event, count),
        top_k_two_events=max(config.top_k_two_events, count),
        top_k_multi_event=max(config.top_k_multi_event, count),
    )


def _eval_cases_by_article(
    *,
    gold_path: PathLike,
    chunks_path: PathLike,
) -> dict[str, list]:
    if not Path(gold_path).exists():
        return {}
    grouped: dict[str, list] = {}
    for eval_case in build_eval_cases_from_gold(gold_path=gold_path, chunks_path=chunks_path):
        grouped.setdefault(eval_case.article_id, []).append(eval_case)
    return grouped


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
