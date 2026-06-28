"""CLI entrypoint for milestone 03 RAG preparation."""

from __future__ import annotations

import argparse
import json

from finevent.db import get_sqlalchemy_engine
from finevent.rag.bm25 import load_bm25_index
from finevent.rag.pipeline import run_rag_preparation
from finevent.rag.rag_sql import sync_retrieval_artifacts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare retrieval artifacts for FinEvent-VN.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Build chunks, embeddings and BM25 artifacts.")
    prepare.add_argument("--articles-path", default="data/processed/articles_clean.jsonl")
    prepare.add_argument("--gold-path", default="data/labels/events_gold.jsonl")
    prepare.add_argument("--chunks-output-path", default="data/processed/chunks.jsonl")
    prepare.add_argument("--patterns-output-path", default="data/patterns/patterns.jsonl")
    prepare.add_argument(
        "--rejected-patterns-output-path",
        default="data/patterns/patterns_rejected.jsonl",
    )
    prepare.add_argument(
        "--chunk-patterns-output-path",
        default="data/processed/chunk_patterns.jsonl",
    )
    prepare.add_argument("--retrieval-dir", default="data/retrieval")
    prepare.add_argument("--vector-store-dir", default="data/vector_store")
    prepare.add_argument("--report-path", default="reports/data/rag_preparation_summary.md")
    prepare.add_argument(
        "--embedding-provider",
        default="hash",
        choices=["hash", "cloudflare", "openai_compatible", "direct_http"],
    )
    prepare.add_argument("--embedding-model", default=None)
    prepare.add_argument("--embedding-dimension", type=int, default=128)
    prepare.add_argument("--target-words", type=int, default=420)
    prepare.add_argument("--max-words", type=int, default=620)
    prepare.add_argument("--overlap-words", type=int, default=80)

    query = subparsers.add_parser("query-bm25", help="Run a BM25 smoke query.")
    query.add_argument("--index-path", default="data/retrieval/bm25_index.pkl")
    query.add_argument("--query", required=True)
    query.add_argument("--top-k", type=int, default=5)

    sync = subparsers.add_parser(
        "sync-postgres",
        help="Sync retrieval JSONL artifacts to PostgreSQL.",
    )
    sync.add_argument("--articles-path", default="data/processed/articles_clean.jsonl")
    sync.add_argument("--chunks-path", default="data/processed/chunks.jsonl")
    sync.add_argument("--embeddings-path", default="data/retrieval/chunk_embeddings.jsonl")
    sync.add_argument("--chunk-patterns-path", default="data/processed/chunk_patterns.jsonl")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        result = run_rag_preparation(
            articles_path=args.articles_path,
            gold_path=args.gold_path,
            chunks_output_path=args.chunks_output_path,
            patterns_output_path=args.patterns_output_path,
            rejected_patterns_output_path=args.rejected_patterns_output_path,
            chunk_patterns_output_path=args.chunk_patterns_output_path,
            retrieval_dir=args.retrieval_dir,
            vector_store_dir=args.vector_store_dir,
            report_path=args.report_path,
            embedding_provider=args.embedding_provider,
            embedding_model=args.embedding_model,
            embedding_dimension=args.embedding_dimension,
            target_words=args.target_words,
            max_words=args.max_words,
            overlap_words=args.overlap_words,
        )
        print(
            json.dumps(
                {
                    "articles_path": str(result.articles_path),
                    "chunks_path": str(result.chunks_path),
                    "embeddings_path": str(result.embeddings_path),
                    "bm25_index_path": str(result.bm25_index_path),
                    "vector_manifest_path": str(result.vector_manifest_path),
                    "patterns_path": str(result.patterns_path),
                    "rejected_patterns_path": str(result.rejected_patterns_path),
                    "chunk_patterns_path": str(result.chunk_patterns_path),
                    "report_path": str(result.report_path),
                    "article_count": result.article_count,
                    "chunk_count": result.chunk_count,
                    "embedding_count": result.embedding_count,
                    "pattern_count": result.pattern_count,
                    "rejected_pattern_count": result.rejected_pattern_count,
                    "chunk_pattern_count": result.chunk_pattern_count,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "query-bm25":
        index = load_bm25_index(args.index_path)
        results = [record.to_dict() for record in index.search(args.query, top_k=args.top_k)]
        print(json.dumps({"results": results}, ensure_ascii=False, indent=2))
        return

    if args.command == "sync-postgres":
        result = sync_retrieval_artifacts(
            get_sqlalchemy_engine(),
            articles_path=args.articles_path,
            chunks_path=args.chunks_path,
            embeddings_path=args.embeddings_path,
            chunk_patterns_path=args.chunk_patterns_path,
        )
        print(
            json.dumps(
                {
                    "article_count": result.article_count,
                    "chunk_count": result.chunk_count,
                    "embedding_count": result.embedding_count,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
