"""Local HTML ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from finevent.ingestion.download import (
    DEFAULT_HTML_MANIFEST_PATH,
    html_manifest_key,
    read_html_manifest,
)
from finevent.ingestion.metadata import (
    DEFAULT_EVENT_KEYWORD_TAXONOMY_PATH,
    DEFAULT_EVENT_KEYWORDS,
    extract_event_keyword_matches,
    extract_event_keywords,
    extract_event_subtype_hints,
    extract_event_type_hints,
    extract_sector_hints,
    extract_tickers_and_companies,
    load_company_dictionary,
    load_event_keyword_taxonomy,
)
from finevent.ingestion.models import CleanArticleRecord, RawArticleRecord
from finevent.ingestion.parsers import infer_source_from_path, parse_article_html
from finevent.ingestion.reporting import build_data_quality_summary, write_data_quality_summary
from finevent.ingestion.text import canonical_url, normalize_text, stable_article_id, text_hash
from finevent.jsonl import write_jsonl
from finevent.logging_utils import utc_now_iso


@dataclass(frozen=True)
class IngestionResult:
    raw_path: Path
    clean_path: Path
    report_path: Path
    raw_count: int
    clean_count: int
    duplicate_count: int


def run_local_html_ingestion(
    *,
    input_html_dir: str | Path = "data/raw/html",
    html_manifest_path: str | Path | None = DEFAULT_HTML_MANIFEST_PATH,
    raw_output_path: str | Path = "data/raw/articles_raw.jsonl",
    clean_output_path: str | Path = "data/processed/articles_clean.jsonl",
    report_path: str | Path = "reports/data/data_quality_summary.md",
    dictionary_path: str | Path = "data/dictionaries/ticker_company_map.csv",
    keyword_taxonomy_path: str | Path = DEFAULT_EVENT_KEYWORD_TAXONOMY_PATH,
    min_text_chars: int = 300,
    event_keywords: list[str] | None = None,
) -> IngestionResult:
    html_dir = Path(input_html_dir)
    raw_path = Path(raw_output_path)
    clean_path = Path(clean_output_path)
    report_output_path = Path(report_path)
    html_manifest = read_html_manifest(html_manifest_path) if html_manifest_path else {}

    entries = load_company_dictionary(dictionary_path)
    taxonomy_entries = load_event_keyword_taxonomy(keyword_taxonomy_path)
    keywords = event_keywords or DEFAULT_EVENT_KEYWORDS

    raw_records: list[RawArticleRecord] = []
    clean_records: list[CleanArticleRecord] = []
    seen_hashes: set[str] = set()
    duplicate_count = 0

    for html_path in sorted(html_dir.glob("*.html")):
        html = html_path.read_text(encoding="utf-8", errors="replace")
        manifest_record = html_manifest.get(html_manifest_key(html_path))
        source = manifest_record.source if manifest_record else infer_source_from_path(html_path)
        url = manifest_record.source_url if manifest_record else f"file://{html_path.resolve()}"
        raw_html_path = str(html_path)
        parsed = parse_article_html(html, source=source, url=url)
        normalized_text = normalize_text(parsed.body_text)
        article_id = stable_article_id(source, url, normalized_text or html_path.stem)
        parse_warnings = list(parsed.warnings)
        parse_status = "success"
        if len(normalized_text) < min_text_chars:
            parse_status = "too_short"
            parse_warnings.append("text_below_min_chars")

        raw_records.append(
            RawArticleRecord(
                article_id=article_id,
                source=source,
                url=canonical_url(url),
                title=parsed.title,
                published_at=parsed.published_at,
                author=parsed.author,
                http_status=None,
                crawl_time=utc_now_iso(),
                html_path=raw_html_path,
                raw_text=normalized_text,
                parse_status=parse_status,
                parse_warnings=parse_warnings,
            )
        )

        if parse_status != "success":
            continue

        content_hash = text_hash(normalized_text)
        if content_hash in seen_hashes:
            duplicate_count += 1
            continue
        seen_hashes.add(content_hash)

        metadata_text = "\n".join(part for part in [parsed.title, normalized_text] if part)
        tickers, company_names = extract_tickers_and_companies(metadata_text, entries)
        keyword_matches = extract_event_keyword_matches(metadata_text, taxonomy_entries)
        matched_keywords = (
            extract_event_keywords(metadata_text, keywords)
            if event_keywords is not None
            else extract_event_keywords(metadata_text, taxonomy_entries=taxonomy_entries)
        )
        clean_records.append(
            CleanArticleRecord(
                article_id=article_id,
                source=source,
                url=canonical_url(url),
                raw_html_path=raw_html_path,
                title=parsed.title,
                published_at=parsed.published_at,
                text=normalized_text,
                tickers_hint=tickers,
                company_names_hint=company_names,
                sector_hints=extract_sector_hints(tickers, entries),
                event_keywords=matched_keywords,
                event_type_hints=extract_event_type_hints(keyword_matches),
                event_subtype_hints=extract_event_subtype_hints(keyword_matches),
                language="vi",
                content_hash=content_hash,
                text_char_count=len(normalized_text),
            )
        )

    write_jsonl(raw_path, (record.to_dict() for record in raw_records))
    write_jsonl(clean_path, (record.to_dict() for record in clean_records))
    summary = build_data_quality_summary(
        raw_records=raw_records,
        clean_records=clean_records,
        duplicate_count=duplicate_count,
    )
    write_data_quality_summary(report_output_path, summary)

    return IngestionResult(
        raw_path=raw_path,
        clean_path=clean_path,
        report_path=report_output_path,
        raw_count=len(raw_records),
        clean_count=len(clean_records),
        duplicate_count=duplicate_count,
    )


def reset_html_snapshots(
    *,
    input_html_dir: str | Path = "data/raw/html",
    html_manifest_path: str | Path | None = DEFAULT_HTML_MANIFEST_PATH,
) -> int:
    html_dir = Path(input_html_dir)
    deleted_count = 0
    if html_dir.exists():
        for html_path in html_dir.glob("*.html"):
            html_path.unlink()
            deleted_count += 1
    if html_manifest_path is not None:
        manifest_path = Path(html_manifest_path)
        if manifest_path.exists():
            manifest_path.unlink()
    return deleted_count
