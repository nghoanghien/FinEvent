from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finevent.ingestion.article_sql import _upsert_article
from finevent.ingestion.dictionary_audit import audit_dictionaries
from finevent.ingestion.discovery import SeedPage, discover_url_candidates, looks_like_article_url
from finevent.ingestion.download import (
    UrlCandidate,
    download_url_candidates,
    fetch_url_candidates,
    html_filename_for_candidate,
    read_html_manifest,
    read_url_candidates,
)
from finevent.ingestion.metadata import (
    extract_event_keyword_matches,
    extract_event_keywords,
    extract_event_type_hints,
    extract_tickers_and_companies,
    load_company_dictionary,
    load_event_keyword_taxonomy,
)
from finevent.ingestion.parsers import parse_article_html
from finevent.ingestion.pipeline import reset_html_snapshots, run_local_html_ingestion
from finevent.ingestion.text import canonical_url, normalize_text, text_hash
from finevent.ingestion.ticker_sql import company_entry_to_payload, normalize_alias
from finevent.jsonl import read_jsonl


class FakeResponse:
    def __init__(
        self,
        text: str,
        status_code: int = 200,
        *,
        content: bytes | None = None,
        encoding: str | None = None,
        apparent_encoding: str | None = None,
    ) -> None:
        self.text = text
        self.status_code = status_code
        self.content = content
        self.encoding = encoding
        self.apparent_encoding = apparent_encoding

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, html: str, response: FakeResponse | None = None) -> None:
        self.html = html
        self.response = response
        self.requested_urls: list[str] = []

    def get(self, url: str, timeout: float) -> FakeResponse:
        self.requested_urls.append(url)
        if self.response is not None:
            return self.response
        return FakeResponse(self.html)


class FakeSqlConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: str, params: dict[str, Any]) -> None:
        self.calls.append((statement, params))


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


def test_discover_url_candidates_filters_categories_and_ranks_articles() -> None:
    seed_html = """
    <html>
      <body>
        <a href="/chung-khoan.htm">Chung khoan</a>
        <a href="/cii-thay-doi-phuong-an-su-dung-von-post392506.html">
          CII thay doi phuong an su dung von trai phieu cho du an doanh nghiep
        </a>
        <a href="https://external.test/hpg-mo-rong-du-an-post12345.html">
          HPG mo rong du an
        </a>
      </body>
    </html>
    """

    result = discover_url_candidates(
        seed_pages=[SeedPage(source="example", url="https://example.com/chung-khoan/")],
        max_candidates=10,
        session=FakeSession(seed_html),
        keyword_hints=["doanh nghiep", "trai phieu", "du an"],
    )

    assert len(result.candidates) == 1
    assert "post392506" in result.candidates[0].url
    assert result.candidates[0].score is not None
    assert result.candidates[0].score > 0
    assert result.diagnostics[0].candidate_count == 1
    assert not looks_like_article_url("https://example.com/chung-khoan.htm")
    assert looks_like_article_url("https://example.com/a-post392506.html")


def test_fetch_url_candidates_keeps_html_in_memory() -> None:
    candidate = UrlCandidate(
        url="https://example.com/cii-thay-doi-phuong-an-su-dung-von-post392506.html",
        source="example",
        score=9,
        link_text="CII thay doi phuong an su dung von",
        seed_url="https://example.com/chung-khoan/",
    )

    pages = fetch_url_candidates(
        [candidate],
        session=FakeSession("<html><body>article body</body></html>"),
        timeout_seconds=1.0,
    )

    assert len(pages) == 1
    assert pages[0].html == "<html><body>article body</body></html>"
    log_record = pages[0].to_log_dict()
    assert log_record["html_char_count"] > 0
    assert log_record["candidate_score"] == 9


def test_fetch_url_candidates_prefers_detected_vietnamese_encoding() -> None:
    candidate = UrlCandidate(
        url="https://example.com/vietnamese.html",
        source="example",
    )
    html = "<html><body>Doanh nghiệp tăng vốn</body></html>"
    response = FakeResponse(
        text="<html><body>Doanh nghiá»‡p tÄƒng vá»‘n</body></html>",
        content=html.encode("utf-8"),
        encoding="ISO-8859-1",
        apparent_encoding="utf-8",
    )

    pages = fetch_url_candidates(
        [candidate],
        session=FakeSession("", response=response),
        timeout_seconds=1.0,
    )

    assert pages[0].html == html


def test_download_url_candidates_upserts_html_manifest(tmp_path: Path) -> None:
    candidate = UrlCandidate(
        url="https://cafef.vn/hpg-khoi-cong-post123.html",
        source="cafef",
    )
    html_dir = tmp_path / "html"
    manifest_path = tmp_path / "html_manifest.jsonl"

    records = download_url_candidates(
        [candidate],
        output_html_dir=html_dir,
        html_manifest_path=manifest_path,
        session=FakeSession("<html><body>first</body></html>"),
        timeout_seconds=1.0,
    )
    updated_records = download_url_candidates(
        [candidate],
        output_html_dir=html_dir,
        html_manifest_path=manifest_path,
        session=FakeSession(
            "<html><body>second</body></html>",
            response=FakeResponse("<html><body>second</body></html>", status_code=202),
        ),
        timeout_seconds=1.0,
    )

    manifest = read_html_manifest(manifest_path)
    manifest_record = next(iter(manifest.values()))
    assert len(records) == 1
    assert len(updated_records) == 1
    assert len(manifest) == 1
    assert manifest_record.source_url == candidate.url
    assert manifest_record.source == "cafef"
    assert manifest_record.status_code == 202
    assert manifest_record.html_path.endswith(html_filename_for_candidate(candidate))


def test_parser_prefers_real_article_body_over_short_article_tag() -> None:
    html = """
    <html>
      <head><title>Tin doanh nghiệp</title></head>
      <body>
        <article>Tin liên quan quá ngắn</article>
        <div class="article__body cms-body">
          <p>CTCP Hạ tầng Kỹ thuật TP.HCM công bố thay đổi phương án sử dụng vốn.</p>
          <p>Doanh nghiệp cho biết nguồn vốn trái phiếu chuyển đổi sẽ được phân bổ
          cho các dự án hạ tầng trọng điểm và kế hoạch đầu tư mới.</p>
        </div>
      </body>
    </html>
    """

    parsed = parse_article_html(
        html,
        source="tinnhanhchungkhoan",
        url="https://example.com/post.html",
    )

    assert "thay đổi phương án sử dụng vốn" in parsed.body_text
    assert "Tin liên quan quá ngắn" not in parsed.body_text


def test_run_local_html_ingestion(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.jsonl"
    clean_path = tmp_path / "clean.jsonl"
    report_path = tmp_path / "report.md"

    result = run_local_html_ingestion(
        input_html_dir="tests/fixtures/html",
        html_manifest_path=tmp_path / "missing_manifest.jsonl",
        raw_output_path=raw_path,
        clean_output_path=clean_path,
        report_path=report_path,
        min_text_chars=20,
    )

    clean_records = read_jsonl(clean_path)
    assert result.raw_count == 1
    assert result.clean_count == 1
    assert clean_records[0]["tickers_hint"] == ["HPG"]
    assert clean_records[0]["url"].startswith("file://")
    assert clean_records[0]["raw_html_path"] == str(Path("tests/fixtures/html/cafef_sample.html"))
    assert clean_records[0]["sector_hints"] == ["materials_steel"]
    assert "khoi cong" in clean_records[0]["event_keywords"]
    assert "EXPANSION" in clean_records[0]["event_type_hints"]
    assert report_path.exists()


def test_run_local_html_ingestion_uses_manifest_source_url(tmp_path: Path) -> None:
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    html_path = html_dir / "cafef_sample.html"
    html_path.write_text(
        Path("tests/fixtures/html/cafef_sample.html").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "html_manifest.jsonl"
    manifest_path.write_text(
        json.dumps(
            {
                "html_path": str(html_path),
                "source_url": "https://cafef.vn/hpg-khoi-cong-post123.html",
                "source": "cafef",
                "downloaded_at": "2026-06-26T00:00:00+00:00",
                "status_code": 200,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    clean_path = tmp_path / "clean.jsonl"
    raw_path = tmp_path / "raw.jsonl"

    run_local_html_ingestion(
        input_html_dir=html_dir,
        html_manifest_path=manifest_path,
        raw_output_path=raw_path,
        clean_output_path=clean_path,
        report_path=tmp_path / "report.md",
        min_text_chars=20,
    )

    raw_record = read_jsonl(raw_path)[0]
    clean_record = read_jsonl(clean_path)[0]
    assert raw_record["url"] == "https://cafef.vn/hpg-khoi-cong-post123.html"
    assert clean_record["url"] == "https://cafef.vn/hpg-khoi-cong-post123.html"
    assert clean_record["raw_html_path"] == str(html_path)


def test_reset_html_snapshots_only_removes_html_and_manifest(tmp_path: Path) -> None:
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    html_file = html_dir / "old.html"
    non_html_file = html_dir / "keep.txt"
    manifest_path = tmp_path / "html_manifest.jsonl"
    raw_path = tmp_path / "articles_raw.jsonl"
    clean_path = tmp_path / "articles_clean.jsonl"
    report_path = tmp_path / "data_quality_summary.md"
    for path in [html_file, non_html_file, manifest_path, raw_path, clean_path, report_path]:
        path.write_text("keep\n", encoding="utf-8")

    deleted_count = reset_html_snapshots(
        input_html_dir=html_dir,
        html_manifest_path=manifest_path,
    )

    assert deleted_count == 1
    assert not html_file.exists()
    assert not manifest_path.exists()
    assert non_html_file.exists()
    assert raw_path.exists()
    assert clean_path.exists()
    assert report_path.exists()


def test_article_sql_upsert_includes_source_url_and_raw_html_path() -> None:
    connection = FakeSqlConnection()

    _upsert_article(
        connection,
        lambda statement: statement,
        {
            "article_id": "article_001",
            "source": "cafef",
            "url": "https://cafef.vn/hpg-khoi-cong-post123.html",
            "raw_html_path": "data/raw/html/cafef_abc.html",
            "title": "HPG khoi cong",
            "published_at": None,
            "content_hash": "hash",
            "language": "vi",
        },
    )

    statement, params = connection.calls[0]
    assert "raw_html_path" in statement
    assert params["url"] == "https://cafef.vn/hpg-khoi-cong-post123.html"
    assert params["raw_html_path"] == "data/raw/html/cafef_abc.html"
