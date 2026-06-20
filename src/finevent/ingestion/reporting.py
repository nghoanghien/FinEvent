"""Data quality reporting for ingestion runs."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from finevent.ingestion.models import CleanArticleRecord, RawArticleRecord
from finevent.ingestion.text import vietnamese_character_ratio


def build_data_quality_summary(
    *,
    raw_records: list[RawArticleRecord],
    clean_records: list[CleanArticleRecord],
    duplicate_count: int,
) -> str:
    total_raw = len(raw_records)
    total_clean = len(clean_records)
    parse_success = sum(1 for record in raw_records if record.parse_status == "success")
    parse_success_rate = _rate(parse_success, total_raw)
    duplicate_rate = _rate(duplicate_count, total_raw)
    title_coverage = _rate(sum(1 for record in clean_records if record.title), total_clean)
    date_coverage = _rate(sum(1 for record in clean_records if record.published_at), total_clean)
    ticker_coverage = _rate(sum(1 for record in clean_records if record.tickers_hint), total_clean)
    source_counts = Counter(record.source for record in clean_records)
    sector_counts = Counter(sector for record in clean_records for sector in record.sector_hints)
    keyword_counts = Counter(
        keyword for record in clean_records for keyword in record.event_keywords
    )
    event_type_counts = Counter(
        event_type for record in clean_records for event_type in record.event_type_hints
    )
    avg_vi_ratio = (
        sum(vietnamese_character_ratio(record.text) for record in clean_records) / total_clean
        if total_clean
        else 0.0
    )

    lines = [
        "# Data Quality Summary",
        "",
        "## Overview",
        "",
        f"- Raw article records: {total_raw}",
        f"- Clean article records: {total_clean}",
        f"- Parse success rate: {parse_success_rate:.2%}",
        f"- Duplicate rate after hashing: {duplicate_rate:.2%}",
        f"- Title coverage: {title_coverage:.2%}",
        f"- Published date coverage: {date_coverage:.2%}",
        f"- Ticker hint coverage: {ticker_coverage:.2%}",
        f"- Average Vietnamese character ratio: {avg_vi_ratio:.2%}",
        "",
        "## Source Distribution",
        "",
        "| Source | Count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {source} | {count} |" for source, count in sorted(source_counts.items()))
    lines.extend(
        [
            "",
            "## Sector Hints",
            "",
            "| Sector | Count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(f"| {sector} | {count} |" for sector, count in sector_counts.most_common())
    lines.extend(
        [
            "",
            "## Event Keyword Hints",
            "",
            "| Keyword | Count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(f"| {keyword} | {count} |" for keyword, count in keyword_counts.most_common())
    lines.extend(
        [
            "",
            "## Event Type Hints",
            "",
            "| Event type | Count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(
        f"| {event_type} | {count} |" for event_type, count in event_type_counts.most_common()
    )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This report measures ingestion quality only.",
            "- Ticker, company and event keyword fields are hints, not gold labels.",
            "- Vector indexes are built in the RAG preparation milestone, not here.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_data_quality_summary(path: str | Path, content: str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0
