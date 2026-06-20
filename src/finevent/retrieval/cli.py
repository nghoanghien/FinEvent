"""CLI entrypoint for milestone 04 retrieval and reranking."""

from __future__ import annotations

import argparse
import json

from finevent.jsonl import read_jsonl
from finevent.retrieval.engine import RetrievalEngine
from finevent.retrieval.experiments import run_retrieval_comparison
from finevent.retrieval.llm_rerank import build_llm_reasoning_rerank_prompt
from finevent.retrieval.models import DEFAULT_RETRIEVAL_CONFIGS, RetrievalQuery
from finevent.retrieval.querying import build_queries_from_article


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run retrieval and reranking experiments.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query = subparsers.add_parser("query", help="Run retrieval for a raw query string.")
    _add_artifact_args(query)
    query.add_argument("--query", required=True)
    query.add_argument("--article-id", default="manual_query")
    query.add_argument("--ticker", action="append", default=[])
    query.add_argument("--company", action="append", default=[])
    query.add_argument("--event-keyword", action="append", default=[])
    query.add_argument("--event-type", action="append", default=[])
    query.add_argument("--config", default="metadata_aware_hybrid")
    query.add_argument("--top-k", type=int, default=None)

    article_query = subparsers.add_parser(
        "query-article",
        help="Build sub-queries from one article JSONL record and retrieve contexts.",
    )
    _add_artifact_args(article_query)
    article_query.add_argument("--articles-path", default="data/processed/articles_clean.jsonl")
    article_query.add_argument("--article-id", required=True)
    article_query.add_argument("--config", default="metadata_aware_hybrid")
    article_query.add_argument("--top-k", type=int, default=None)

    compare = subparsers.add_parser("compare", help="Compare retrieval strategies on gold labels.")
    _add_artifact_args(compare)
    compare.add_argument("--gold-path", default="data/labels/events_gold.jsonl")
    compare.add_argument("--logs-path", default="data/retrieval/retrieval_logs.jsonl")
    compare.add_argument("--metrics-path", default="reports/evaluation/retrieval_metrics.csv")
    compare.add_argument(
        "--error-analysis-path",
        default="reports/evaluation/retrieval_error_analysis.md",
    )
    compare.add_argument(
        "--config",
        action="append",
        dest="configs",
        default=None,
        help="Repeat to limit configs. Defaults to all core configs.",
    )

    prompt = subparsers.add_parser("llm-rerank-prompt", help="Render an LLM rerank prompt.")
    _add_artifact_args(prompt)
    prompt.add_argument("--query", required=True)
    prompt.add_argument("--article-id", default="manual_query")
    prompt.add_argument("--config", default="metadata_aware_hybrid")
    prompt.add_argument("--top-k", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "query":
        config = _config_with_optional_top_k(args.config, args.top_k)
        engine = _engine_from_args(args)
        queries = [
            RetrievalQuery(
                query_id=f"{args.article_id}_manual",
                article_id=args.article_id,
                text=args.query,
                query_type="manual",
                tickers=[ticker.upper() for ticker in args.ticker],
                company_names=args.company,
                event_keywords=args.event_keyword,
                event_type_hints=[event_type.upper() for event_type in args.event_type],
            )
        ]
        candidates = engine.retrieve(queries, config=config)
        print(
            json.dumps(
                {"results": [item.to_dict() for item in candidates]},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "query-article":
        config = _config_with_optional_top_k(args.config, args.top_k)
        engine = _engine_from_args(args)
        article = _load_article(args.articles_path, args.article_id)
        queries = build_queries_from_article(article)
        candidates = engine.retrieve(queries, config=config)
        print(
            json.dumps(
                {
                    "queries": [query.to_dict() for query in queries],
                    "results": [item.to_dict() for item in candidates],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "compare":
        result = run_retrieval_comparison(
            chunks_path=args.chunks_path,
            bm25_index_path=args.bm25_index_path,
            embeddings_path=args.embeddings_path,
            gold_path=args.gold_path,
            logs_path=args.logs_path,
            metrics_path=args.metrics_path,
            error_analysis_path=args.error_analysis_path,
            config_names=args.configs,
        )
        print(
            json.dumps(
                {
                    "logs_path": str(result.logs_path),
                    "metrics_path": str(result.metrics_path),
                    "error_analysis_path": str(result.error_analysis_path),
                    "config_count": result.config_count,
                    "eval_case_count": result.eval_case_count,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "llm-rerank-prompt":
        config = _config_with_optional_top_k(args.config, args.top_k)
        engine = _engine_from_args(args)
        query = RetrievalQuery(
            query_id=f"{args.article_id}_manual",
            article_id=args.article_id,
            text=args.query,
            query_type="manual",
        )
        candidates = engine.retrieve([query], config=config)
        print(build_llm_reasoning_rerank_prompt(query=query, candidates=candidates))
        return

    raise SystemExit(f"Unknown command: {args.command}")


def _add_artifact_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--chunks-path", default="data/processed/chunks.jsonl")
    parser.add_argument("--bm25-index-path", default="data/retrieval/bm25_index.pkl")
    parser.add_argument("--embeddings-path", default="data/retrieval/chunk_embeddings.jsonl")


def _engine_from_args(args: argparse.Namespace) -> RetrievalEngine:
    return RetrievalEngine.from_artifacts(
        chunks_path=args.chunks_path,
        bm25_index_path=args.bm25_index_path,
        embeddings_path=args.embeddings_path,
    )


def _config_with_optional_top_k(config_name: str, top_k: int | None) -> object:
    config = DEFAULT_RETRIEVAL_CONFIGS[config_name]
    if top_k is None:
        return config
    return type(config)(**{**config.to_dict(), "top_k_final": top_k})


def _load_article(articles_path: str, article_id: str) -> dict:
    for article in read_jsonl(articles_path):
        if article.get("article_id") == article_id:
            return article
    raise SystemExit(f"Article not found: {article_id}")


if __name__ == "__main__":
    main()
