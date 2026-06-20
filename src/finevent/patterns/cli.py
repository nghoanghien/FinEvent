"""CLI entrypoint for milestone 05 pattern library."""

from __future__ import annotations

import argparse
import json

from finevent.db import get_sqlalchemy_engine
from finevent.jsonl import read_jsonl
from finevent.patterns.models import PatternCandidate
from finevent.patterns.pattern_sql import sync_pattern_artifacts
from finevent.patterns.pipeline import run_pattern_library_build
from finevent.patterns.prompting import render_few_shot_patterns, render_pattern_context_json
from finevent.patterns.querying import (
    build_pattern_query_from_article,
    build_pattern_query_from_raw,
)
from finevent.patterns.store import PatternStore
from finevent.rag.embeddings import build_embedding_client


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and query the event pattern library.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser(
        "build",
        help="Build pattern records and embeddings from gold labels.",
    )
    build.add_argument("--articles-path", default="data/processed/articles_clean.jsonl")
    build.add_argument("--gold-path", default="data/labels/events_gold.jsonl")
    build.add_argument("--patterns-output-path", default="data/patterns/patterns.jsonl")
    build.add_argument(
        "--rejected-patterns-output-path",
        default="data/patterns/patterns_rejected.jsonl",
    )
    build.add_argument("--embeddings-output-path", default="data/patterns/pattern_embeddings.jsonl")
    build.add_argument(
        "--embedding-cache-path",
        default="data/patterns/pattern_embedding_cache.jsonl",
    )
    build.add_argument("--metrics-path", default="reports/evaluation/pattern_metrics.csv")
    build.add_argument("--report-path", default="reports/evaluation/pattern_library_summary.md")
    build.add_argument("--embedding-provider", default="hash")
    build.add_argument("--embedding-model", default=None)
    build.add_argument("--embedding-dimension", type=int, default=128)

    search = subparsers.add_parser("search", help="Select few-shot patterns for a raw query.")
    _add_store_args(search)
    search.add_argument("--query", required=True)
    search.add_argument("--article-id", default="manual_query")
    search.add_argument("--ticker", action="append", default=[])
    search.add_argument("--company", action="append", default=[])
    search.add_argument("--event-keyword", action="append", default=[])
    search.add_argument("--event-type", action="append", default=[])
    search.add_argument("--event-subtype", action="append", default=[])
    search.add_argument("--document-label", default=None)
    search.add_argument("--top-k", type=int, default=3)

    article = subparsers.add_parser("query-article", help="Select patterns for one article record.")
    _add_store_args(article)
    article.add_argument("--articles-path", default="data/processed/articles_clean.jsonl")
    article.add_argument("--article-id", required=True)
    article.add_argument("--top-k", type=int, default=3)

    render = subparsers.add_parser(
        "render-few-shot",
        help="Render selected patterns as prompt text.",
    )
    _add_store_args(render)
    render.add_argument("--query", required=True)
    render.add_argument("--article-id", default="manual_query")
    render.add_argument("--ticker", action="append", default=[])
    render.add_argument("--company", action="append", default=[])
    render.add_argument("--event-keyword", action="append", default=[])
    render.add_argument("--event-type", action="append", default=[])
    render.add_argument("--event-subtype", action="append", default=[])
    render.add_argument("--document-label", default=None)
    render.add_argument("--top-k", type=int, default=3)

    sync = subparsers.add_parser(
        "sync-postgres",
        help="Sync patterns and embeddings to PostgreSQL.",
    )
    _add_store_args(sync)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "build":
        result = run_pattern_library_build(
            articles_path=args.articles_path,
            gold_path=args.gold_path,
            patterns_output_path=args.patterns_output_path,
            rejected_patterns_output_path=args.rejected_patterns_output_path,
            embeddings_output_path=args.embeddings_output_path,
            embedding_cache_path=args.embedding_cache_path,
            metrics_path=args.metrics_path,
            report_path=args.report_path,
            embedding_provider=args.embedding_provider,
            embedding_model=args.embedding_model,
            embedding_dimension=args.embedding_dimension,
        )
        print(
            json.dumps(
                {
                    "patterns_path": str(result.patterns_path),
                    "rejected_patterns_path": str(result.rejected_patterns_path),
                    "embeddings_path": str(result.embeddings_path),
                    "metrics_path": str(result.metrics_path),
                    "report_path": str(result.report_path),
                    "pattern_count": result.pattern_count,
                    "rejected_pattern_count": result.rejected_pattern_count,
                    "embedding_count": result.embedding_count,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "search":
        candidates = _select_from_raw_args(args)
        print(json.dumps(render_pattern_context_json(candidates), ensure_ascii=False, indent=2))
        return

    if args.command == "query-article":
        article = _load_article(args.articles_path, args.article_id)
        store = _store_from_args(args)
        query = build_pattern_query_from_article(article)
        candidates = store.select_patterns(query, top_k=args.top_k)
        print(
            json.dumps(
                {
                    "query": query.to_dict(),
                    "results": [candidate.to_dict() for candidate in candidates],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "render-few-shot":
        print(render_few_shot_patterns(_select_from_raw_args(args)))
        return

    if args.command == "sync-postgres":
        result = sync_pattern_artifacts(
            get_sqlalchemy_engine(),
            patterns_path=args.patterns_path,
            embeddings_path=args.embeddings_path,
        )
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    raise SystemExit(f"Unknown command: {args.command}")


def _add_store_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--patterns-path", default="data/patterns/patterns.jsonl")
    parser.add_argument("--embeddings-path", default="data/patterns/pattern_embeddings.jsonl")
    parser.add_argument(
        "--query-embedding-provider",
        default=None,
        help="Set this to cloudflare when pattern embeddings were built with Cloudflare.",
    )
    parser.add_argument("--query-embedding-model", default=None)
    parser.add_argument("--query-embedding-dimension", type=int, default=128)


def _select_from_raw_args(args: argparse.Namespace) -> list[PatternCandidate]:
    store = _store_from_args(args)
    query = build_pattern_query_from_raw(
        article_id=args.article_id,
        text=args.query,
        tickers=[ticker.upper() for ticker in args.ticker],
        company_names=args.company,
        event_keywords=args.event_keyword,
        event_type_hints=[event_type.upper() for event_type in args.event_type],
        event_subtype_hints=[subtype.upper() for subtype in args.event_subtype],
        document_label_hint=args.document_label,
    )
    return store.select_patterns(query, top_k=args.top_k)


def _store_from_args(args: argparse.Namespace) -> PatternStore:
    query_client = None
    if args.query_embedding_provider:
        query_client = build_embedding_client(
            provider=args.query_embedding_provider,
            model_name=args.query_embedding_model,
            dimension=args.query_embedding_dimension,
        )
    return PatternStore.from_artifacts(
        patterns_path=args.patterns_path,
        embeddings_path=args.embeddings_path,
        query_embedding_client=query_client,
    )


def _load_article(articles_path: str, article_id: str) -> dict:
    for article in read_jsonl(articles_path):
        if article.get("article_id") == article_id:
            return article
    raise SystemExit(f"Article not found: {article_id}")


if __name__ == "__main__":
    main()
