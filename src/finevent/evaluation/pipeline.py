"""End-to-end evaluation and ablation pipeline."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from finevent.evaluation.loading import load_gold_records, load_prediction_records
from finevent.evaluation.metrics import evaluate_prediction_group, group_predictions_by_config
from finevent.evaluation.models import EvaluationRunResult
from finevent.evaluation.reporting import (
    build_evaluation_summary,
    write_csv,
    write_error_outputs,
)
from finevent.jsonl import write_jsonl
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class EvaluationPipelineResult:
    output_dir: Path
    metrics_by_run_path: Path
    per_event_type_path: Path
    hallucination_metrics_path: Path
    errors_by_type_path: Path
    error_examples_path: Path
    detailed_predictions_path: Path
    eval_summary_path: Path
    config_count: int
    article_count: int
    error_count: int


def run_evaluation_pipeline(
    *,
    gold_path: PathLike = "data/labels/events_gold.jsonl",
    predictions_path: PathLike | None = None,
    runs_dir: PathLike | None = "runs/extraction",
    retrieval_metrics_path: PathLike | None = "reports/evaluation/retrieval_metrics.csv",
    output_dir: PathLike = "reports/evaluation",
    default_config_name: str = "default",
) -> EvaluationPipelineResult:
    gold_records = load_gold_records(gold_path)
    predictions = load_prediction_records(
        predictions_path=predictions_path,
        runs_dir=runs_dir,
        default_config_name=default_config_name,
    )
    evaluated_article_ids = set(gold_records)
    evaluated_article_ids.update(
        prediction.article_id for prediction in predictions if prediction.article_id
    )
    grouped_predictions = group_predictions_by_config(predictions)
    if not grouped_predictions:
        grouped_predictions = {default_config_name: []}

    run_results: list[EvaluationRunResult] = []
    for config_name, config_predictions in sorted(grouped_predictions.items()):
        raw_result = evaluate_prediction_group(
            config_name=config_name,
            gold_records=gold_records,
            predictions=config_predictions,
        )
        run_results.append(
            EvaluationRunResult(
                config_name=config_name,
                article_count=int(raw_result["article_count"]),
                gold_event_count=int(raw_result["gold_event_count"]),
                predicted_event_count=int(raw_result["predicted_event_count"]),
                matched_event_count=int(raw_result["matched_event_count"]),
                metrics=dict(raw_result["metrics"]),
                per_event_type_rows=[
                    {"config_name": config_name, **row}
                    for row in raw_result["per_event_type_rows"]
                ],
                error_rows=list(raw_result["error_rows"]),
                hallucination_row=dict(raw_result["hallucination_row"]),
                detailed_rows=list(raw_result["detailed_rows"]),
            )
        )

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    metrics_rows = [result.metrics_row() for result in run_results]
    per_event_type_rows = [
        row for result in run_results for row in result.per_event_type_rows
    ]
    hallucination_rows = [result.hallucination_row for result in run_results]
    error_rows = [row for result in run_results for row in result.error_rows]
    detailed_rows = [row for result in run_results for row in result.detailed_rows]
    retrieval_rows = _read_csv_if_exists(retrieval_metrics_path)

    metrics_by_run_path = write_csv(output_path / "metrics_by_run.csv", metrics_rows)
    per_event_type_path = write_csv(output_path / "per_event_type_metrics.csv", per_event_type_rows)
    hallucination_metrics_path = write_csv(
        output_path / "hallucination_metrics.csv",
        hallucination_rows,
    )
    errors_by_type_path, error_examples_path = write_error_outputs(
        errors_by_type_path=output_path / "errors_by_type.csv",
        error_examples_path=output_path / "error_examples.jsonl",
        error_rows=error_rows,
    )
    detailed_predictions_path = output_path / "prediction_details.jsonl"
    write_jsonl(detailed_predictions_path, detailed_rows)

    eval_summary_path = output_path / "eval_summary.md"
    eval_summary_path.write_text(
        build_evaluation_summary(
            metrics_rows=metrics_rows,
            hallucination_rows=hallucination_rows,
            error_rows=error_rows,
            retrieval_metrics_rows=retrieval_rows,
        ),
        encoding="utf-8",
    )

    return EvaluationPipelineResult(
        output_dir=output_path,
        metrics_by_run_path=metrics_by_run_path,
        per_event_type_path=per_event_type_path,
        hallucination_metrics_path=hallucination_metrics_path,
        errors_by_type_path=errors_by_type_path,
        error_examples_path=error_examples_path,
        detailed_predictions_path=detailed_predictions_path,
        eval_summary_path=eval_summary_path,
        config_count=len(run_results),
        article_count=len(evaluated_article_ids),
        error_count=len(error_rows),
    )


def _read_csv_if_exists(path: PathLike | None) -> list[JsonDict]:
    if path is None:
        return []
    input_path = Path(path)
    if not input_path.exists():
        return []
    with input_path.open("r", encoding="utf-8", newline="") as file:
        return [dict(row) for row in csv.DictReader(file)]
