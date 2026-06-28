"""CLI helpers for pattern records.

The active workflow builds and attaches patterns during M03. This CLI remains
available for rebuilding/syncing the standalone pattern artifact.
"""

from __future__ import annotations

import argparse
import json

from finevent.db import get_sqlalchemy_engine
from finevent.patterns.pattern_sql import sync_pattern_artifacts
from finevent.patterns.pipeline import run_pattern_library_build


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and sync event pattern records.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build pattern records from gold labels.")
    build.add_argument("--articles-path", default="data/processed/articles_clean.jsonl")
    build.add_argument("--gold-path", default="data/labels/events_gold.jsonl")
    build.add_argument("--patterns-output-path", default="data/patterns/patterns.jsonl")
    build.add_argument(
        "--rejected-patterns-output-path",
        default="data/patterns/patterns_rejected.jsonl",
    )
    build.add_argument("--metrics-path", default="reports/evaluation/pattern_metrics.csv")
    build.add_argument("--report-path", default="reports/evaluation/pattern_library_summary.md")

    sync = subparsers.add_parser("sync-postgres", help="Sync patterns to PostgreSQL.")
    sync.add_argument("--patterns-path", default="data/patterns/patterns.jsonl")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "build":
        result = run_pattern_library_build(
            articles_path=args.articles_path,
            gold_path=args.gold_path,
            patterns_output_path=args.patterns_output_path,
            rejected_patterns_output_path=args.rejected_patterns_output_path,
            metrics_path=args.metrics_path,
            report_path=args.report_path,
        )
        print(
            json.dumps(
                {
                    "patterns_path": str(result.patterns_path),
                    "rejected_patterns_path": str(result.rejected_patterns_path),
                    "metrics_path": str(result.metrics_path),
                    "report_path": str(result.report_path),
                    "pattern_count": result.pattern_count,
                    "rejected_pattern_count": result.rejected_pattern_count,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "sync-postgres":
        result = sync_pattern_artifacts(
            get_sqlalchemy_engine(),
            patterns_path=args.patterns_path,
        )
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
