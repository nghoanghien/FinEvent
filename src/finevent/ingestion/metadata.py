"""Metadata hint extraction for Vietnamese financial articles."""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from finevent.ingestion.text import normalize_text

DEFAULT_EVENT_KEYWORDS = [
    "M&A",
    "bo nhiem",
    "hop dong",
    "khoi cong",
    "kien tung",
    "mien nhiem",
    "mo rong",
    "phat hanh",
    "sap nhap",
    "tang von",
    "trung thau",
]

DEFAULT_EVENT_KEYWORD_TAXONOMY_PATH = "data/dictionaries/event_keyword_taxonomy.csv"


@dataclass(frozen=True)
class CompanyEntry:
    ticker: str
    company_name: str
    aliases: tuple[str, ...]
    sector: str | None = None
    exchange: str | None = None
    status: str | None = None
    source_note: str | None = None
    source_url: str | None = None
    last_verified_at: str | None = None


@dataclass(frozen=True)
class EventKeywordEntry:
    event_type: str
    event_subtype: str
    keyword: str
    polarity_hint: str
    priority: int
    notes: str = ""


def load_company_dictionary(path: str | Path) -> list[CompanyEntry]:
    dictionary_path = Path(path)
    if not dictionary_path.exists():
        return []

    entries: list[CompanyEntry] = []
    with dictionary_path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            ticker = normalize_text(row.get("ticker", "")).upper()
            company_name = normalize_text(row.get("company_name", ""))
            aliases = tuple(
                normalize_text(alias)
                for alias in (row.get("aliases", "") or "").split("|")
                if alias.strip()
            )
            if ticker and company_name:
                entries.append(
                    CompanyEntry(
                        ticker=ticker,
                        company_name=company_name,
                        aliases=aliases,
                        sector=normalize_text(row.get("sector", "")) or None,
                        exchange=normalize_text(row.get("exchange", "")) or None,
                        status=normalize_text(row.get("status", "")) or None,
                        source_note=normalize_text(row.get("source_note", "")) or None,
                        source_url=normalize_text(row.get("source_url", "")) or None,
                        last_verified_at=normalize_text(row.get("last_verified_at", "")) or None,
                    )
                )
    return entries


def load_event_keyword_taxonomy(path: str | Path) -> list[EventKeywordEntry]:
    taxonomy_path = Path(path)
    if not taxonomy_path.exists():
        return [
            EventKeywordEntry(
                event_type="UNKNOWN",
                event_subtype="UNKNOWN",
                keyword=keyword,
                polarity_hint="neutral",
                priority=1,
                notes="fallback keyword",
            )
            for keyword in DEFAULT_EVENT_KEYWORDS
        ]

    entries: list[EventKeywordEntry] = []
    with taxonomy_path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            keyword = normalize_text(row.get("keyword", ""))
            event_type = normalize_text(row.get("event_type", "")).upper()
            event_subtype = normalize_text(row.get("event_subtype", "")).upper()
            if not keyword or not event_type:
                continue
            entries.append(
                EventKeywordEntry(
                    event_type=event_type,
                    event_subtype=event_subtype,
                    keyword=keyword,
                    polarity_hint=normalize_text(row.get("polarity_hint", "neutral")) or "neutral",
                    priority=_parse_int(row.get("priority", ""), default=1),
                    notes=normalize_text(row.get("notes", "")),
                )
            )
    return entries


def extract_tickers_and_companies(
    text: str,
    entries: list[CompanyEntry],
) -> tuple[list[str], list[str]]:
    haystack = normalize_text(text)
    haystack_lower = haystack.lower()
    folded_haystack_lower = _ascii_fold(haystack).lower()
    tickers: set[str] = set()
    company_names: set[str] = set()

    for entry in entries:
        if re.search(rf"(?<![A-Z0-9]){re.escape(entry.ticker)}(?![A-Z0-9])", haystack):
            tickers.add(entry.ticker)
            company_names.add(entry.company_name)
            continue

        names = (entry.company_name, *entry.aliases)
        if any(
            name
            and (
                name.lower() in haystack_lower
                or _ascii_fold(name).lower() in folded_haystack_lower
            )
            for name in names
        ):
            tickers.add(entry.ticker)
            company_names.add(entry.company_name)

    return sorted(tickers), sorted(company_names)


def extract_event_keyword_matches(
    text: str,
    taxonomy_entries: list[EventKeywordEntry],
) -> list[EventKeywordEntry]:
    haystack = _ascii_fold(normalize_text(text)).lower()
    matched: dict[tuple[str, str, str], EventKeywordEntry] = {}
    for entry in taxonomy_entries:
        folded_keyword = _ascii_fold(entry.keyword).lower()
        if folded_keyword and folded_keyword in haystack:
            matched[(entry.event_type, entry.event_subtype, entry.keyword)] = entry
    return sorted(
        matched.values(),
        key=lambda item: (-item.priority, item.event_type, item.keyword),
    )


def extract_event_keywords(
    text: str,
    keywords: list[str] | None = None,
    taxonomy_entries: list[EventKeywordEntry] | None = None,
) -> list[str]:
    if taxonomy_entries is not None:
        return sorted(
            {entry.keyword for entry in extract_event_keyword_matches(text, taxonomy_entries)}
        )

    haystack = _ascii_fold(normalize_text(text)).lower()
    matched: set[str] = set()
    for keyword in keywords or DEFAULT_EVENT_KEYWORDS:
        folded_keyword = _ascii_fold(keyword).lower()
        if folded_keyword and folded_keyword in haystack:
            matched.add(keyword)
    return sorted(matched)


def extract_event_type_hints(matches: list[EventKeywordEntry]) -> list[str]:
    return sorted({entry.event_type for entry in matches})


def extract_event_subtype_hints(matches: list[EventKeywordEntry]) -> list[str]:
    return sorted({entry.event_subtype for entry in matches if entry.event_subtype})


def extract_sector_hints(tickers: list[str], entries: list[CompanyEntry]) -> list[str]:
    ticker_set = set(tickers)
    return sorted(
        {entry.sector for entry in entries if entry.ticker in ticker_set and entry.sector}
    )


def _ascii_fold(text: str) -> str:
    replacements = {
        "\u0111": "d",
        "\u0110": "D",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )


def _parse_int(value: str | None, *, default: int) -> int:
    try:
        return int(value or "")
    except ValueError:
        return default
