"""Dictionary validation and reporting utilities."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from finevent.ingestion.metadata import load_company_dictionary, load_event_keyword_taxonomy


@dataclass(frozen=True)
class DictionaryAudit:
    company_count: int
    keyword_count: int
    duplicate_tickers: list[str]
    duplicate_keyword_keys: list[str]
    sector_counts: dict[str, int]
    event_type_counts: dict[str, int]

    @property
    def has_errors(self) -> bool:
        return bool(self.duplicate_tickers or self.duplicate_keyword_keys)

    def to_markdown(self) -> str:
        lines = [
            "# Dictionary Audit",
            "",
            "## Overview",
            "",
            f"- Company entries: {self.company_count}",
            f"- Event keyword entries: {self.keyword_count}",
            f"- Duplicate tickers: {len(self.duplicate_tickers)}",
            f"- Duplicate keyword keys: {len(self.duplicate_keyword_keys)}",
            "",
            "## Sector Distribution",
            "",
            "| Sector | Count |",
            "| --- | ---: |",
        ]
        lines.extend(f"| {sector} | {count} |" for sector, count in self.sector_counts.items())
        lines.extend(
            [
                "",
                "## Event Type Keyword Distribution",
                "",
                "| Event type | Keyword count |",
                "| --- | ---: |",
            ]
        )
        lines.extend(
            f"| {event_type} | {count} |" for event_type, count in self.event_type_counts.items()
        )
        if self.duplicate_tickers:
            lines.extend(["", "## Duplicate Tickers", ""])
            lines.extend(f"- {ticker}" for ticker in self.duplicate_tickers)
        if self.duplicate_keyword_keys:
            lines.extend(["", "## Duplicate Keyword Keys", ""])
            lines.extend(f"- {key}" for key in self.duplicate_keyword_keys)
        return "\n".join(lines) + "\n"


def audit_dictionaries(
    *,
    company_dictionary_path: str | Path = "data/dictionaries/ticker_company_map.csv",
    keyword_taxonomy_path: str | Path = "data/dictionaries/event_keyword_taxonomy.csv",
) -> DictionaryAudit:
    companies = load_company_dictionary(company_dictionary_path)
    keywords = load_event_keyword_taxonomy(keyword_taxonomy_path)

    ticker_counts = Counter(company.ticker for company in companies)
    keyword_key_counts = Counter(
        f"{keyword.event_type}/{keyword.event_subtype}/{keyword.keyword}" for keyword in keywords
    )
    sector_counts = Counter(company.sector or "UNKNOWN" for company in companies)
    event_type_counts = Counter(keyword.event_type for keyword in keywords)

    return DictionaryAudit(
        company_count=len(companies),
        keyword_count=len(keywords),
        duplicate_tickers=sorted(ticker for ticker, count in ticker_counts.items() if count > 1),
        duplicate_keyword_keys=sorted(
            key for key, count in keyword_key_counts.items() if count > 1
        ),
        sector_counts=dict(sorted(sector_counts.items())),
        event_type_counts=dict(sorted(event_type_counts.items())),
    )


def write_dictionary_audit_report(
    output_path: str | Path = "reports/data/dictionary_audit.md",
    *,
    company_dictionary_path: str | Path = "data/dictionaries/ticker_company_map.csv",
    keyword_taxonomy_path: str | Path = "data/dictionaries/event_keyword_taxonomy.csv",
) -> DictionaryAudit:
    audit = audit_dictionaries(
        company_dictionary_path=company_dictionary_path,
        keyword_taxonomy_path=keyword_taxonomy_path,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(audit.to_markdown(), encoding="utf-8")
    return audit
