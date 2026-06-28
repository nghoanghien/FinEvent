"""CLI entrypoint for milestone 04 retrieval and reranking."""

from __future__ import annotations

import argparse
import json

from finevent.db import get_sqlalchemy_engine
from finevent.jsonl import read_jsonl
from finevent.llm import build_student_chat_model_from_env, load_provider_runtime_config
from finevent.rag.embeddings import EmbeddingClient, build_embedding_client
from finevent.retrieval.engine import RetrievalEngine
from finevent.retrieval.experiments import run_online_retrieval, run_retrieval_comparison
from finevent.retrieval.llm_rerank import build_listwise_llm_rerank_prompt
from finevent.retrieval.models import DEFAULT_RETRIEVAL_CONFIGS, RetrievalConfig, RetrievalQuery
from finevent.retrieval.querying import build_queries_from_article
from finevent.retrieval.retrieval_sql import sync_retrieval_runs_jsonl


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

    run_batch = subparsers.add_parser(
        "run-batch",
        help="Retrieve contexts for article records and write M06-ready retrieval runs.",
    )
    _add_artifact_args(run_batch)
    run_batch.add_argument("--articles-path", default="data/processed/articles_clean.jsonl")
    run_batch.add_argument("--gold-path", default="data/labels/events_gold.jsonl")
    run_batch.add_argument("--output-path", default="data/retrieval/online_contexts.jsonl")
    run_batch.add_argument("--logs-path", default="data/retrieval/online_retrieval_logs.jsonl")
    run_batch.add_argument(
        "--metrics-path",
        default="reports/evaluation/online_retrieval_metrics.csv",
    )
    run_batch.add_argument(
        "--error-analysis-path",
        default="reports/evaluation/online_retrieval_error_analysis.md",
    )
    run_batch.add_argument("--config", default="metadata_aware_hybrid")
    run_batch.add_argument("--limit", type=int, default=None)
    run_batch.add_argument("--offset", type=int, default=0)
    run_batch.add_argument("--max-contexts", type=int, default=None)
    run_batch.add_argument(
        "--llm-rerank-mode",
        choices=["off", "deterministic", "student_env"],
        default="student_env",
        help=(
            "student_env calls the configured student LLM as a listwise reranker; "
            "deterministic is for tests/local smoke runs."
        ),
    )
    run_batch.add_argument("--llm-rerank-top-n", type=int, default=15)
    run_batch.add_argument("--llm-rerank-max-query-article-chars", type=int, default=0)
    run_batch.add_argument("--llm-rerank-max-candidate-chars", type=int, default=0)
    run_batch.add_argument("--llm-rerank-max-retries", type=int, default=1)

    prompt = subparsers.add_parser("llm-rerank-prompt", help="Render an LLM rerank prompt.")
    _add_artifact_args(prompt)
    prompt.add_argument("--query", required=True)
    prompt.add_argument("--article-id", default="manual_query")
    prompt.add_argument("--config", default="metadata_aware_hybrid")
    prompt.add_argument("--top-k", type=int, default=10)

    sync = subparsers.add_parser("sync-postgres", help="Sync online retrieval runs to PostgreSQL.")
    sync.add_argument("--retrieval-results-path", default="data/retrieval/online_contexts.jsonl")
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
        queries = build_queries_from_article(article, query_mode=config.query_mode)
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
        query_client = _query_client_from_args(args)
        result = run_retrieval_comparison(
            chunks_path=args.chunks_path,
            bm25_index_path=args.bm25_index_path,
            embeddings_path=args.embeddings_path,
            gold_path=args.gold_path,
            logs_path=args.logs_path,
            metrics_path=args.metrics_path,
            error_analysis_path=args.error_analysis_path,
            config_names=args.configs,
            query_embedding_client=query_client,
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

    if args.command == "run-batch":
        query_client = _query_client_from_args(args)
        llm_rerank_model, llm_rerank_model_name = _llm_reranker_from_args(args)
        result = run_online_retrieval(
            chunks_path=args.chunks_path,
            bm25_index_path=args.bm25_index_path,
            embeddings_path=args.embeddings_path,
            articles_path=args.articles_path,
            gold_path=args.gold_path,
            output_path=args.output_path,
            logs_path=args.logs_path,
            metrics_path=args.metrics_path,
            error_analysis_path=args.error_analysis_path,
            config_name=args.config,
            limit=args.limit,
            offset=args.offset,
            max_contexts=args.max_contexts,
            query_embedding_client=query_client,
            llm_rerank_mode=args.llm_rerank_mode,
            llm_rerank_model=llm_rerank_model,
            llm_rerank_model_name=llm_rerank_model_name,
            llm_rerank_top_n=args.llm_rerank_top_n,
            llm_rerank_max_query_article_chars=args.llm_rerank_max_query_article_chars,
            llm_rerank_max_candidate_chars=args.llm_rerank_max_candidate_chars,
            llm_rerank_max_retries=args.llm_rerank_max_retries,
        )
        print(
            json.dumps(
                {
                    "output_path": str(result.output_path),
                    "logs_path": str(result.logs_path),
                    "metrics_path": str(result.metrics_path),
                    "error_analysis_path": str(result.error_analysis_path),
                    "article_count": result.article_count,
                    "context_count": result.context_count,
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
        candidates = engine.retrieve([query], config=config, select_final=False)
        print(
            build_listwise_llm_rerank_prompt(
                query_article={
                    "article_id": args.article_id,
                    "title": args.query,
                    "source": "manual",
                    "text": args.query,
                },
                queries=[query],
                candidates=candidates[: args.top_k],
            )
        )
        return

    if args.command == "sync-postgres":
        result = sync_retrieval_runs_jsonl(
            get_sqlalchemy_engine(),
            retrieval_results_path=args.retrieval_results_path,
        )
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return

    raise SystemExit(f"Unknown command: {args.command}")


def _add_artifact_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--chunks-path", default="data/processed/chunks.jsonl")
    parser.add_argument("--bm25-index-path", default="data/retrieval/bm25_index.pkl")
    parser.add_argument("--embeddings-path", default="data/retrieval/chunk_embeddings.jsonl")
    parser.add_argument(
        "--query-embedding-provider",
        default=None,
        choices=["hash", "cloudflare", "openai_compatible", "direct_http"],
        help="Use the same provider/model as the stored dense embeddings for live dense search.",
    )
    parser.add_argument("--query-embedding-model", default=None)
    parser.add_argument("--query-embedding-dimension", type=int, default=128)


def _engine_from_args(args: argparse.Namespace) -> RetrievalEngine:
    return RetrievalEngine.from_artifacts(
        chunks_path=args.chunks_path,
        bm25_index_path=args.bm25_index_path,
        embeddings_path=args.embeddings_path,
        query_embedding_client=_query_client_from_args(args),
    )


def _query_client_from_args(args: argparse.Namespace) -> EmbeddingClient | None:
    if not args.query_embedding_provider:
        return None
    return build_embedding_client(
        provider=args.query_embedding_provider,
        model_name=args.query_embedding_model,
        dimension=args.query_embedding_dimension,
    )


def _llm_reranker_from_args(args: argparse.Namespace) -> tuple[object | None, str]:
    mode = str(getattr(args, "llm_rerank_mode", "off"))
    if mode == "off":
        return None, "none"
    if mode == "deterministic":
        return None, "deterministic_listwise_rerank"
    provider_config = load_provider_runtime_config()
    return (
        build_student_chat_model_from_env(),
        provider_config.student_model or "student_model",
    )


def _config_with_optional_top_k(config_name: str, top_k: int | None) -> RetrievalConfig:
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
