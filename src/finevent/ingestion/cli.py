"""CLI entrypoint for milestone 01 data ingestion."""

from __future__ import annotations

import argparse
import json

from finevent.ingestion.download import download_url_candidates, read_url_candidates
from finevent.ingestion.pipeline import run_local_html_ingestion


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local HTML ingestion for FinEvent-VN.")
    parser.add_argument("--input-html-dir", default="data/raw/html")
    parser.add_argument("--raw-output-path", default="data/raw/articles_raw.jsonl")
    parser.add_argument("--clean-output-path", default="data/processed/articles_clean.jsonl")
    parser.add_argument("--report-path", default="reports/data/data_quality_summary.md")
    parser.add_argument("--dictionary-path", default="data/dictionaries/ticker_company_map.csv")
    parser.add_argument("--keyword-taxonomy-path", default="data/dictionaries/event_keyword_taxonomy.csv")
    parser.add_argument("--min-text-chars", type=int, default=300)
    parser.add_argument("--url-candidates-path", default=None)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--request-timeout-seconds", type=float, default=20.0)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    download_count = 0
    download_error_count = 0
    if args.download:
        if not args.url_candidates_path:
            raise SystemExit("--download requires --url-candidates-path")
        download_records = download_url_candidates(
            read_url_candidates(args.url_candidates_path),
            output_html_dir=args.input_html_dir,
            timeout_seconds=args.request_timeout_seconds,
        )
        download_count = len(download_records)
        download_error_count = sum(1 for record in download_records if record.error)

    result = run_local_html_ingestion(
        input_html_dir=args.input_html_dir,
        raw_output_path=args.raw_output_path,
        clean_output_path=args.clean_output_path,
        report_path=args.report_path,
        dictionary_path=args.dictionary_path,
        keyword_taxonomy_path=args.keyword_taxonomy_path,
        min_text_chars=args.min_text_chars,
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
                "download_count": download_count,
                "download_error_count": download_error_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
