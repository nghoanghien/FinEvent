"""CLI for validating dictionary assets."""

from __future__ import annotations

import argparse
import json

from finevent.ingestion.dictionary_audit import write_dictionary_audit_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit FinEvent-VN dictionary assets.")
    parser.add_argument("--company-dictionary-path", default="data/dictionaries/ticker_company_map.csv")
    parser.add_argument("--keyword-taxonomy-path", default="data/dictionaries/event_keyword_taxonomy.csv")
    parser.add_argument("--output-path", default="reports/data/dictionary_audit.md")
    parser.add_argument("--fail-on-error", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    audit = write_dictionary_audit_report(
        args.output_path,
        company_dictionary_path=args.company_dictionary_path,
        keyword_taxonomy_path=args.keyword_taxonomy_path,
    )
    print(
        json.dumps(
            {
                "company_count": audit.company_count,
                "keyword_count": audit.keyword_count,
                "duplicate_tickers": audit.duplicate_tickers,
                "duplicate_keyword_keys": audit.duplicate_keyword_keys,
                "output_path": args.output_path,
                "has_errors": audit.has_errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if args.fail_on_error and audit.has_errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
