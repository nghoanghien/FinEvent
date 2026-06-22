"""CLI entrypoint for milestone 06 online extraction workflow."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import cast

from finevent.db import get_sqlalchemy_engine
from finevent.extraction.models import ExtractionRunConfig
from finevent.extraction.run_sql import sync_extraction_state
from finevent.extraction.student import InvokableStudentModel
from finevent.extraction.workflow import (
    ExtractionWorkflowArtifacts,
    build_public_result,
    run_online_extraction_workflow,
)
from finevent.jsonl import read_jsonl, write_jsonl
from finevent.llm import build_student_chat_model_from_env, load_provider_runtime_config


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

    run_batch = subparsers.add_parser("run-batch", help="Extract events for a JSONL article batch.")
    _add_common_args(run_batch)
    run_batch.add_argument("--articles-path", default="data/processed/articles_clean.jsonl")
    run_batch.add_argument("--limit", type=int, default=None)
    run_batch.add_argument("--offset", type=int, default=0)

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
        _run_and_print(
            payload,
            config=config,
            artifacts=artifacts,
            output_path=args.output_path,
            student_provider=args.student_provider,
            sync_postgres=args.sync_postgres,
        )
        return

    if args.command == "run-article":
        article = _load_article(args.articles_path, args.article_id)
        payload = {"input_type": "article", "article": article}
        _run_and_print(
            payload,
            config=config,
            artifacts=artifacts,
            output_path=args.output_path,
            student_provider=args.student_provider,
            sync_postgres=args.sync_postgres,
        )
        return

    if args.command == "run-batch":
        _run_batch_and_print_summary(
            articles_path=args.articles_path,
            limit=args.limit,
            offset=args.offset,
            config=config,
            artifacts=artifacts,
            output_path=args.output_path or "data/extraction/student_predictions.jsonl",
            student_provider=args.student_provider,
            sync_postgres=args.sync_postgres,
        )
        return

    if args.command == "run-url":
        payload = {"input_type": "url", "value": args.url}
        _run_and_print(
            payload,
            config=config,
            artifacts=artifacts,
            output_path=args.output_path,
            student_provider=args.student_provider,
            sync_postgres=args.sync_postgres,
        )
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
    parser.add_argument(
        "--student-provider",
        default="deterministic",
        choices=["deterministic", "env"],
        help=(
            "Use deterministic for local baseline/tests, or env to call the configured "
            "student LLM from .env."
        ),
    )
    parser.add_argument("--retrieval-config", default="metadata_aware_hybrid")
    parser.add_argument("--pattern-count", type=int, default=3)
    parser.add_argument("--max-contexts", type=int, default=5)
    parser.add_argument("--student-model", default="deterministic_student_v1")
    parser.add_argument("--prompt-version", default="m06_extraction_v1")
    parser.add_argument("--disable-retrieval", action="store_true")
    parser.add_argument("--disable-patterns", action="store_true")
    parser.add_argument("--disable-verification", action="store_true")
    parser.add_argument("--evidence-match-threshold", type=float, default=0.82)
    parser.add_argument("--argument-match-threshold", type=float, default=0.78)
    parser.add_argument("--chunks-path", default="data/processed/chunks.jsonl")
    parser.add_argument("--bm25-index-path", default="data/retrieval/bm25_index.pkl")
    parser.add_argument(
        "--retrieval-embeddings-path",
        default="data/retrieval/chunk_embeddings.jsonl",
    )
    parser.add_argument(
        "--retrieval-query-embedding-provider",
        default=None,
        choices=["hash", "cloudflare", "openai_compatible", "direct_http"],
    )
    parser.add_argument("--retrieval-query-embedding-model", default=None)
    parser.add_argument("--retrieval-query-embedding-dimension", type=int, default=128)
    parser.add_argument("--patterns-path", default="data/patterns/patterns.jsonl")
    parser.add_argument(
        "--pattern-embeddings-path",
        default="data/patterns/pattern_embeddings.jsonl",
    )
    parser.add_argument(
        "--pattern-query-embedding-provider",
        default=None,
        choices=["hash", "cloudflare", "openai_compatible", "direct_http"],
    )
    parser.add_argument("--pattern-query-embedding-model", default=None)
    parser.add_argument("--pattern-query-embedding-dimension", type=int, default=128)
    parser.add_argument("--logs-dir", default="runs/extraction")
    parser.add_argument("--output-path", default=None)
    parser.add_argument("--sync-postgres", action="store_true")
    parser.add_argument("--max-article-chars", type=int, default=2200)
    parser.add_argument("--max-context-chars", type=int, default=450)
    parser.add_argument("--max-pattern-excerpt-chars", type=int, default=350)
    parser.add_argument("--max-pattern-output-chars", type=int, default=700)
    parser.add_argument("--max-prompt-chars", type=int, default=11000)


def _config_from_args(args: argparse.Namespace) -> ExtractionRunConfig:
    return ExtractionRunConfig(
        retrieval_config=args.retrieval_config,
        pattern_count=args.pattern_count,
        max_contexts=args.max_contexts,
        student_model=args.student_model,
        prompt_version=args.prompt_version,
        use_retrieval=not args.disable_retrieval,
        use_patterns=not args.disable_patterns,
        enable_verification=not args.disable_verification,
        evidence_match_threshold=args.evidence_match_threshold,
        argument_match_threshold=args.argument_match_threshold,
        max_article_chars=args.max_article_chars,
        max_context_chars=args.max_context_chars,
        max_pattern_excerpt_chars=args.max_pattern_excerpt_chars,
        max_pattern_output_chars=args.max_pattern_output_chars,
        max_prompt_chars=args.max_prompt_chars,
    )


def _artifacts_from_args(args: argparse.Namespace) -> ExtractionWorkflowArtifacts:
    return ExtractionWorkflowArtifacts(
        chunks_path=args.chunks_path,
        bm25_index_path=args.bm25_index_path,
        retrieval_embeddings_path=args.retrieval_embeddings_path,
        patterns_path=args.patterns_path,
        pattern_embeddings_path=args.pattern_embeddings_path,
        logs_dir=args.logs_dir,
        retrieval_query_embedding_provider=args.retrieval_query_embedding_provider,
        retrieval_query_embedding_model=args.retrieval_query_embedding_model,
        retrieval_query_embedding_dimension=args.retrieval_query_embedding_dimension,
        pattern_query_embedding_provider=args.pattern_query_embedding_provider,
        pattern_query_embedding_model=args.pattern_query_embedding_model,
        pattern_query_embedding_dimension=args.pattern_query_embedding_dimension,
    )


def _run_and_print(
    payload: dict,
    *,
    config: ExtractionRunConfig,
    artifacts: ExtractionWorkflowArtifacts,
    output_path: str | None,
    student_provider: str = "deterministic",
    sync_postgres: bool = False,
) -> None:
    student_model, config = _student_model_and_config(config, student_provider)
    state = run_online_extraction_workflow(
        payload,
        config=config,
        artifacts=artifacts,
        langchain_model=student_model,
    )
    result = build_public_result(state)
    if sync_postgres:
        sync_result = sync_extraction_state(get_sqlalchemy_engine(), state)
        result["postgres_sync"] = {
            "run_id": sync_result.run_id,
            "trace_count": sync_result.trace_count,
        }
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(text)


def _run_batch_and_print_summary(
    *,
    articles_path: str,
    limit: int | None,
    offset: int,
    config: ExtractionRunConfig,
    artifacts: ExtractionWorkflowArtifacts,
    output_path: str,
    student_provider: str,
    sync_postgres: bool,
) -> None:
    student_model, config = _student_model_and_config(config, student_provider)
    articles = [
        article for article in read_jsonl(articles_path) if isinstance(article, dict)
    ]
    selected_articles = articles[offset : offset + limit if limit is not None else None]
    results: list[dict] = []
    synced_count = 0
    for article in selected_articles:
        state = run_online_extraction_workflow(
            {"input_type": "article", "article": article},
            config=config,
            artifacts=artifacts,
            langchain_model=student_model,
        )
        result = build_public_result(state)
        result["config_name"] = config.run_label
        if sync_postgres:
            sync_result = sync_extraction_state(get_sqlalchemy_engine(), state)
            result["postgres_sync"] = {
                "run_id": sync_result.run_id,
                "trace_count": sync_result.trace_count,
            }
            synced_count += 1
        results.append(result)
    write_jsonl(output_path, results)
    print(
        json.dumps(
            {
                "articles_path": articles_path,
                "output_path": output_path,
                "selected_count": len(selected_articles),
                "success_count": sum(1 for result in results if not result.get("workflow_errors")),
                "error_count": sum(1 for result in results if result.get("workflow_errors")),
                "synced_count": synced_count,
                "config_name": config.run_label,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _student_model_and_config(
    config: ExtractionRunConfig,
    student_provider: str,
) -> tuple[InvokableStudentModel | None, ExtractionRunConfig]:
    if student_provider != "env":
        return None, config
    provider_config = load_provider_runtime_config()
    student_model = cast(InvokableStudentModel, build_student_chat_model_from_env())
    return (
        student_model,
        replace(
            config,
            student_model=provider_config.student_model or config.student_model,
        ),
    )


def _load_article(articles_path: str, article_id: str) -> dict:
    for article in read_jsonl(articles_path):
        if article.get("article_id") == article_id:
            return article
    raise SystemExit(f"Article not found: {article_id}")


if __name__ == "__main__":
    main()
