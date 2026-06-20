"""CLI entrypoint for milestone 06 online extraction workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from finevent.extraction.models import ExtractionRunConfig
from finevent.extraction.workflow import (
    ExtractionWorkflowArtifacts,
    build_public_result,
    run_online_extraction_workflow,
)
from finevent.jsonl import read_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run online financial event extraction workflow.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_text = subparsers.add_parser("run-text", help="Extract events from raw title/text input.")
    _add_common_args(run_text)
    run_text.add_argument("--title", default=None)
    run_text.add_argument("--text", required=True)
    run_text.add_argument("--source", default="manual")
    run_text.add_argument("--url", default="")
    run_text.add_argument("--published-at", default=None)

    run_article = subparsers.add_parser("run-article", help="Extract events for one JSONL article.")
    _add_common_args(run_article)
    run_article.add_argument("--articles-path", default="data/processed/articles_clean.jsonl")
    run_article.add_argument("--article-id", required=True)

    run_url = subparsers.add_parser(
        "run-url",
        help="Extract events from a URL or file:// HTML path.",
    )
    _add_common_args(run_url)
    run_url.add_argument("--url", required=True)

    prompt = subparsers.add_parser(
        "render-prompt",
        help="Run workflow and print extraction prompt.",
    )
    _add_common_args(prompt)
    prompt.add_argument("--title", default=None)
    prompt.add_argument("--text", required=True)
    prompt.add_argument("--source", default="manual")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    config = _config_from_args(args)
    artifacts = _artifacts_from_args(args)

    if args.command == "run-text":
        payload = {
            "input_type": "text",
            "title": args.title,
            "value": args.text,
            "source": args.source,
            "url": args.url,
            "published_at": args.published_at,
        }
        _run_and_print(payload, config=config, artifacts=artifacts, output_path=args.output_path)
        return

    if args.command == "run-article":
        article = _load_article(args.articles_path, args.article_id)
        payload = {"input_type": "article", "article": article}
        _run_and_print(payload, config=config, artifacts=artifacts, output_path=args.output_path)
        return

    if args.command == "run-url":
        payload = {"input_type": "url", "value": args.url}
        _run_and_print(payload, config=config, artifacts=artifacts, output_path=args.output_path)
        return

    if args.command == "render-prompt":
        payload = {
            "input_type": "text",
            "title": args.title,
            "value": args.text,
            "source": args.source,
        }
        state = run_online_extraction_workflow(payload, config=config, artifacts=artifacts)
        print(state.extraction_prompt)
        return

    raise SystemExit(f"Unknown command: {args.command}")


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--retrieval-config", default="metadata_aware_hybrid")
    parser.add_argument("--pattern-count", type=int, default=3)
    parser.add_argument("--max-contexts", type=int, default=5)
    parser.add_argument("--student-model", default="deterministic_student_v1")
    parser.add_argument("--prompt-version", default="m06_extraction_v1")
    parser.add_argument("--disable-retrieval", action="store_true")
    parser.add_argument("--disable-patterns", action="store_true")
    parser.add_argument("--chunks-path", default="data/processed/chunks.jsonl")
    parser.add_argument("--bm25-index-path", default="data/retrieval/bm25_index.pkl")
    parser.add_argument(
        "--retrieval-embeddings-path",
        default="data/retrieval/chunk_embeddings.jsonl",
    )
    parser.add_argument("--patterns-path", default="data/patterns/patterns.jsonl")
    parser.add_argument(
        "--pattern-embeddings-path",
        default="data/patterns/pattern_embeddings.jsonl",
    )
    parser.add_argument("--logs-dir", default="runs/extraction")
    parser.add_argument("--output-path", default=None)


def _config_from_args(args: argparse.Namespace) -> ExtractionRunConfig:
    return ExtractionRunConfig(
        retrieval_config=args.retrieval_config,
        pattern_count=args.pattern_count,
        max_contexts=args.max_contexts,
        student_model=args.student_model,
        prompt_version=args.prompt_version,
        use_retrieval=not args.disable_retrieval,
        use_patterns=not args.disable_patterns,
    )


def _artifacts_from_args(args: argparse.Namespace) -> ExtractionWorkflowArtifacts:
    return ExtractionWorkflowArtifacts(
        chunks_path=args.chunks_path,
        bm25_index_path=args.bm25_index_path,
        retrieval_embeddings_path=args.retrieval_embeddings_path,
        patterns_path=args.patterns_path,
        pattern_embeddings_path=args.pattern_embeddings_path,
        logs_dir=args.logs_dir,
    )


def _run_and_print(
    payload: dict,
    *,
    config: ExtractionRunConfig,
    artifacts: ExtractionWorkflowArtifacts,
    output_path: str | None,
) -> None:
    state = run_online_extraction_workflow(payload, config=config, artifacts=artifacts)
    result = build_public_result(state)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)


def _load_article(articles_path: str, article_id: str) -> dict:
    for article in read_jsonl(articles_path):
        if article.get("article_id") == article_id:
            return article
    raise SystemExit(f"Article not found: {article_id}")


if __name__ == "__main__":
    main()
