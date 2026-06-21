from __future__ import annotations

from pathlib import Path

from finevent.ingestion.dictionary_audit import audit_dictionaries
from finevent.ingestion.download import html_filename_for_candidate, read_url_candidates
from finevent.ingestion.metadata import (
    extract_event_keyword_matches,
    extract_event_keywords,
    extract_event_type_hints,
    extract_tickers_and_companies,
    load_company_dictionary,
    load_event_keyword_taxonomy,
)
from finevent.ingestion.pipeline import run_local_html_ingestion
from finevent.ingestion.text import canonical_url, normalize_text, text_hash
from finevent.ingestion.ticker_sql import company_entry_to_payload, normalize_alias
from finevent.jsonl import read_jsonl


def test_normalize_and_hash_are_stable() -> None:
    assert normalize_text("  HPG\n\n\tmo rong  ") == "HPG\n\nmo rong"
    assert text_hash("HPG mo rong") == text_hash(" hpg  mo rong ")


def test_canonical_url_removes_tracking_params() -> None:
    url = "https://example.com/news/?utm_source=x&id=1&fbclid=abc"
    assert canonical_url(url) == "https://example.com/news?id=1"


def test_metadata_keyword_and_dictionary() -> None:
    entries = load_company_dictionary("data/dictionaries/ticker_company_map.csv")
    assert any(entry.ticker == "HPG" for entry in entries)
    assert extract_event_keywords("HPG vua khoi cong nha may va tang von") == [
        "khoi cong",
        "tang von",
    ]
    text = "T\u1eadp \u0111o\u00e0n H\u00f2a Ph\u00e1t v\u1eeba m\u1edf r\u1ed9ng d\u1ef1 \u00e1n"
    tickers, companies = extract_tickers_and_companies(text, entries)
    assert tickers == ["HPG"]
    assert companies == ["Hoa Phat Group"]


def test_event_keyword_taxonomy_maps_to_event_type() -> None:
    taxonomy = load_event_keyword_taxonomy("data/dictionaries/event_keyword_taxonomy.csv")
    text = "Doanh nghi\u1ec7p v\u1eeba tr\u00fang th\u1ea7u g\u00f3i th\u1ea7u l\u1edbn"
    matches = extract_event_keyword_matches(text, taxonomy)

    assert "CONTRACT" in extract_event_type_hints(matches)
    assert any(match.event_subtype == "BIDDING_WIN" for match in matches)


def test_dictionary_audit_has_no_duplicates() -> None:
    audit = audit_dictionaries()

    assert audit.company_count >= 100
    assert audit.keyword_count >= 100
    assert audit.duplicate_tickers == []
    assert audit.duplicate_keyword_keys == []
    assert "CONTRACT" in audit.event_type_counts


def test_ticker_sql_payload_from_csv_entry() -> None:
    entries = load_company_dictionary("data/dictionaries/ticker_company_map.csv")
    hpg = next(entry for entry in entries if entry.ticker == "HPG")
    payload = company_entry_to_payload(hpg)

    assert payload.ticker == "HPG"
    assert payload.company_name == "Hoa Phat Group"
    assert payload.sector == "materials_steel"
    assert payload.exchange == "UNKNOWN"
    assert payload.status == "ACTIVE"
    assert normalize_alias("T\u1eadp \u0111o\u00e0n H\u00f2a Ph\u00e1t") == "tap doan hoa phat"


def test_read_url_candidates(tmp_path: Path) -> None:
    candidates_path = tmp_path / "url_candidates.jsonl"
    candidates_path.write_text(
        '{"url":"https://example.com/a","source":"cafef","ticker_hint":"HPG"}\n',
        encoding="utf-8",
    )

    candidates = read_url_candidates(candidates_path)

    assert len(candidates) == 1
    assert candidates[0].source == "cafef"
    assert html_filename_for_candidate(candidates[0]).startswith("cafef_")


def test_run_local_html_ingestion(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.jsonl"
    clean_path = tmp_path / "clean.jsonl"
    report_path = tmp_path / "report.md"

    result = run_local_html_ingestion(
        input_html_dir="tests/fixtures/html",
        raw_output_path=raw_path,
        clean_output_path=clean_path,
        report_path=report_path,
        min_text_chars=20,
    )

    clean_records = read_jsonl(clean_path)
    assert result.raw_count == 1
    assert result.clean_count == 1
    assert clean_records[0]["tickers_hint"] == ["HPG"]
    assert clean_records[0]["sector_hints"] == ["materials_steel"]
    assert "khoi cong" in clean_records[0]["event_keywords"]
    assert "EXPANSION" in clean_records[0]["event_type_hints"]
    assert report_path.exists()
