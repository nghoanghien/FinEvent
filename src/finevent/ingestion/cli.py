"""CLI entrypoint for milestone 01 data ingestion."""

from __future__ import annotations

import argparse
import json

from finevent.db import get_sqlalchemy_engine
from finevent.ingestion.article_sql import sync_clean_articles_jsonl
from finevent.ingestion.discovery import SeedPage, default_seed_pages, discover_url_candidates
from finevent.ingestion.download import download_url_candidates, read_url_candidates
from finevent.ingestion.pipeline import run_local_html_ingestion
from finevent.jsonl import read_jsonl, write_jsonl


def read_seed_pages(path: str) -> list[SeedPage]:
    return [SeedPage.from_dict(record) for record in read_jsonl(path)]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local HTML ingestion for FinEvent-VN.")
    parser.add_argument("--input-html-dir", default="data/raw/html")
    parser.add_argument("--raw-output-path", default="data/raw/articles_raw.jsonl")
    parser.add_argument("--clean-output-path", default="data/processed/articles_clean.jsonl")
    parser.add_argument("--report-path", default="reports/data/data_quality_summary.md")
    parser.add_argument("--dictionary-path", default="data/dictionaries/ticker_company_map.csv")
    parser.add_argument(
        "--keyword-taxonomy-path",
        default="data/dictionaries/event_keyword_taxonomy.csv",
    )
    parser.add_argument("--min-text-chars", type=int, default=300)
    parser.add_argument("--url-candidates-path", default=None)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--seed-pages-path", default=None)
    parser.add_argument("--discovered-output-path", default="data/raw/discovered_urls.jsonl")
    parser.add_argument("--download-log-path", default="data/raw/download_log.jsonl")
    parser.add_argument("--max-discovered-urls", type=int, default=80)
    parser.add_argument("--max-download-articles", type=int, default=25)
    parser.add_argument("--request-timeout-seconds", type=float, default=20.0)
    parser.add_argument("--sync-postgres", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    discovery_count = 0
    discovery_error_count = 0
    download_count = 0
    download_error_count = 0
    download_records = []
    if args.discover:
        seed_pages = (
            read_seed_pages(args.seed_pages_path)
            if args.seed_pages_path
            else default_seed_pages()
        )
        discovery_result = discover_url_candidates(
            seed_pages=seed_pages,
            max_candidates=args.max_discovered_urls,
            timeout_seconds=args.request_timeout_seconds,
        )
        discovered_records = [candidate.to_dict() for candidate in discovery_result.candidates]
        write_jsonl(args.discovered_output_path, discovered_records)
        discovery_count = len(discovered_records)
        discovery_error_count = sum(1 for item in discovery_result.diagnostics if item.error)

        download_records = download_url_candidates(
            discovery_result.candidates,
            output_html_dir=args.input_html_dir,
            timeout_seconds=args.request_timeout_seconds,
            max_records=args.max_download_articles,
        )
        download_count = len(download_records)
        download_error_count = sum(1 for record in download_records if record.error)
        write_jsonl(args.download_log_path, (record.to_dict() for record in download_records))

    if args.download:
        if not args.url_candidates_path:
            raise SystemExit("--download requires --url-candidates-path")
        download_records = download_url_candidates(
            read_url_candidates(args.url_candidates_path),
            output_html_dir=args.input_html_dir,
            timeout_seconds=args.request_timeout_seconds,
            max_records=args.max_download_articles,
        )
        download_count = len(download_records)
        download_error_count = sum(1 for record in download_records if record.error)
        write_jsonl(args.download_log_path, (record.to_dict() for record in download_records))

    result = run_local_html_ingestion(
        input_html_dir=args.input_html_dir,
        raw_output_path=args.raw_output_path,
        clean_output_path=args.clean_output_path,
        report_path=args.report_path,
        dictionary_path=args.dictionary_path,
        keyword_taxonomy_path=args.keyword_taxonomy_path,
        min_text_chars=args.min_text_chars,
    )
    article_sync = None
    if args.sync_postgres:
        article_sync = sync_clean_articles_jsonl(
            get_sqlalchemy_engine(),
            articles_path=args.clean_output_path,
        )
    print(
        json.dumps(
            {
                "raw_path": str(result.raw_path),
                "clean_path": str(result.clean_path),
                "report_path": str(result.report_path),
                "raw_count": result.raw_count,
                "clean_count": result.clean_count,
                "duplicate_count": result.duplicate_count,
                "discovery_count": discovery_count,
                "discovery_error_count": discovery_error_count,
                "discovered_output_path": args.discovered_output_path if args.discover else None,
                "download_count": download_count,
                "download_error_count": download_error_count,
                "download_log_path": args.download_log_path if download_records else None,
                "postgres_sync": article_sync.__dict__ if article_sync else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
