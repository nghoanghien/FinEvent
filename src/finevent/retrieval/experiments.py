"""Retrieval strategy comparison runner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from finevent.jsonl import write_jsonl
from finevent.retrieval.engine import RetrievalEngine
from finevent.retrieval.evaluation import (
    aggregate_metric_rows,
    build_error_analysis,
    build_eval_cases_from_gold,
    evaluate_results,
    write_metrics_csv,
)
from finevent.retrieval.models import DEFAULT_RETRIEVAL_CONFIGS
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class RetrievalExperimentResult:
    logs_path: Path
    metrics_path: Path
    error_analysis_path: Path
    config_count: int
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
) -> RetrievalExperimentResult:
    engine = RetrievalEngine.from_artifacts(
        chunks_path=chunks_path,
        bm25_index_path=bm25_index_path,
        embeddings_path=embeddings_path,
    )
    eval_cases = build_eval_cases_from_gold(gold_path=gold_path, chunks_path=chunks_path)
    selected_config_names = config_names or [
        "bm25_only",
        "dense_only",
        "hybrid",
        "metadata_aware_hybrid",
        "rule_aware_rerank",
        "llm_reasoning_rerank",
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
