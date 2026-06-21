"""CLI for evaluation and ablation study."""

from __future__ import annotations

import argparse
import json

from finevent.evaluation.pipeline import run_evaluation_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run FinEvent-VN evaluation and ablation.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Evaluate extraction predictions against gold labels.")
    run.add_argument("--gold-path", default="data/labels/events_gold.jsonl")
    run.add_argument("--predictions-path", default=None)
    run.add_argument("--runs-dir", default="runs/extraction")
    run.add_argument(
        "--retrieval-metrics-path",
        default="reports/evaluation/retrieval_metrics.csv",
    )
    run.add_argument("--output-dir", default="reports/evaluation")
    run.add_argument("--default-config-name", default="default")
    run.add_argument(
        "--ignore-runs-dir",
        action="store_true",
        help="Only read --predictions-path and ignore runs/extraction artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        result = run_evaluation_pipeline(
            gold_path=args.gold_path,
            predictions_path=args.predictions_path,
            runs_dir=None if args.ignore_runs_dir else args.runs_dir,
            retrieval_metrics_path=args.retrieval_metrics_path,
            output_dir=args.output_dir,
            default_config_name=args.default_config_name,
        )
        print(
            json.dumps(
                {
                    "output_dir": str(result.output_dir),
                    "metrics_by_run_path": str(result.metrics_by_run_path),
                    "per_event_type_path": str(result.per_event_type_path),
                    "hallucination_metrics_path": str(result.hallucination_metrics_path),
                    "errors_by_type_path": str(result.errors_by_type_path),
                    "eval_summary_path": str(result.eval_summary_path),
                    "config_count": result.config_count,
                    "article_count": result.article_count,
                    "error_count": result.error_count,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
