"""CLI entrypoint for milestone 02 labeling."""

from __future__ import annotations

import argparse
import json

from finevent.db import get_sqlalchemy_engine
from finevent.labeling.event_sql import sync_event_labels_jsonl
from finevent.labeling.pipeline import generate_teacher_prompts, validate_teacher_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate and validate AI labels for FinEvent-VN.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prompts = subparsers.add_parser("generate-prompts", help="Generate teacher LLM prompts.")
    prompts.add_argument("--articles-path", default="data/processed/articles_clean.jsonl")
    prompts.add_argument("--prompt-output-path", default="data/labels/teacher_prompts.jsonl")
    prompts.add_argument("--taxonomy-path", default="data/schema/event_taxonomy_v1.json")
    prompts.add_argument("--limit", type=int, default=None)

    validate = subparsers.add_parser(
        "validate",
        help="Validate teacher outputs and split gold/rejected labels.",
    )
    validate.add_argument("--articles-path", default="data/processed/articles_clean.jsonl")
    validate.add_argument("--teacher-output-path", default="data/labels/teacher_outputs.jsonl")
    validate.add_argument(
        "--ai-generated-output-path",
        default="data/labels/events_ai_generated.jsonl",
    )
    validate.add_argument("--gold-output-path", default="data/labels/events_gold.jsonl")
    validate.add_argument("--rejected-output-path", default="data/labels/events_rejected.jsonl")
    validate.add_argument("--report-path", default="reports/data/labeling_summary.md")
    validate.add_argument("--taxonomy-path", default="data/schema/event_taxonomy_v1.json")
    validate.add_argument("--run-id", default=None)

    sync = subparsers.add_parser(
        "sync-postgres",
        help="Sync validated label JSONL files to PostgreSQL.",
    )
    sync.add_argument("--gold-path", default="data/labels/events_gold.jsonl")
    sync.add_argument("--rejected-path", default="data/labels/events_rejected.jsonl")
    sync.add_argument("--source-path", default=None)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "generate-prompts":
        result = generate_teacher_prompts(
            articles_path=args.articles_path,
            prompt_output_path=args.prompt_output_path,
            taxonomy_path=args.taxonomy_path,
            limit=args.limit,
        )
        print(
            json.dumps(
                {
                    "prompt_path": str(result.prompt_path),
                    "prompt_count": result.prompt_count,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "validate":
        result = validate_teacher_outputs(
            articles_path=args.articles_path,
            teacher_output_path=args.teacher_output_path,
            ai_generated_output_path=args.ai_generated_output_path,
            gold_output_path=args.gold_output_path,
            rejected_output_path=args.rejected_output_path,
            report_path=args.report_path,
            taxonomy_path=args.taxonomy_path,
            run_id=args.run_id,
        )
        print(
            json.dumps(
                {
                    "ai_generated_path": str(result.ai_generated_path),
                    "gold_path": str(result.gold_path),
                    "rejected_path": str(result.rejected_path),
                    "report_path": str(result.report_path),
                    "total_count": result.total_count,
                    "pass_count": result.pass_count,
                    "rejected_count": result.rejected_count,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "sync-postgres":
        result = sync_event_labels_jsonl(
            get_sqlalchemy_engine(),
            gold_path=args.gold_path,
            rejected_path=args.rejected_path,
            source_path=args.source_path,
        )
        print(
            json.dumps(
                {
                    "labeling_run_id": result.labeling_run_id,
                    "gold_documents": result.gold_documents,
                    "gold_events": result.gold_events,
                    "rejected_documents": result.rejected_documents,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
