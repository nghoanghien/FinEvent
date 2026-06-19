"""CLI for syncing ticker dictionary CSV into PostgreSQL."""

from __future__ import annotations

import argparse
import json

from finevent.db import get_sqlalchemy_engine
from finevent.ingestion.ticker_sql import sync_ticker_dictionary_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync ticker dictionary CSV into PostgreSQL.")
    parser.add_argument("--csv-path", default="data/dictionaries/ticker_company_map.csv")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    result = sync_ticker_dictionary_csv(get_sqlalchemy_engine(), csv_path=args.csv_path)
    print(
        json.dumps(
            {
                "sync_run_id": result.sync_run_id,
                "upserted_companies": result.upserted_companies,
                "upserted_aliases": result.upserted_aliases,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
