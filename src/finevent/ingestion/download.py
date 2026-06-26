"""Optional URL download support for ingestion.

The project can run M1 from local HTML without dependencies. This module is
used when the ingestion extra is installed and real URLs should be downloaded.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from finevent.jsonl import read_jsonl, write_jsonl
from finevent.logging_utils import utc_now_iso
from finevent.types import JsonDict

DEFAULT_USER_AGENT = "Mozilla/5.0 FinEvent-VN research data collector/0.1"
DEFAULT_HTML_MANIFEST_PATH = "data/raw/html_manifest.jsonl"


@dataclass(frozen=True)
class UrlCandidate:
    url: str
    source: str
    ticker_hint: str | None = None
    keyword_hint: str | None = None
    discovered_at: str | None = None
    link_text: str | None = None
    score: int | None = None
    seed_url: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> UrlCandidate:
        return cls(
            url=str(data["url"]),
            source=str(data.get("source") or "unknown"),
            ticker_hint=data.get("ticker_hint"),
            keyword_hint=data.get("keyword_hint"),
            discovered_at=data.get("discovered_at"),
            link_text=data.get("link_text"),
            score=int(data["score"]) if data.get("score") is not None else None,
            seed_url=data.get("seed_url"),
        )

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class DownloadRecord:
    url: str
    source: str
    status_code: int | None
    html_path: str | None
    downloaded_at: str
    error: str | None = None

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class HtmlManifestRecord:
    html_path: str
    source_url: str
    source: str
    downloaded_at: str
    status_code: int | None

    @classmethod
    def from_dict(cls, data: JsonDict) -> HtmlManifestRecord:
        return cls(
            html_path=str(data["html_path"]),
            source_url=str(data["source_url"]),
            source=str(data.get("source") or "unknown"),
            downloaded_at=str(data.get("downloaded_at") or ""),
            status_code=int(data["status_code"]) if data.get("status_code") is not None else None,
        )

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class FetchedPage:
    candidate: UrlCandidate
    status_code: int | None
    html: str | None
    downloaded_at: str
    error: str | None = None

    def to_download_record(self, *, html_path: str | None = None) -> DownloadRecord:
        return DownloadRecord(
            url=self.candidate.url,
            source=self.candidate.source,
            status_code=self.status_code,
            html_path=html_path,
            downloaded_at=self.downloaded_at,
            error=self.error,
        )

    def to_log_dict(self, *, html_path: str | None = None) -> JsonDict:
        data = self.to_download_record(html_path=html_path).to_dict()
        data["html_char_count"] = len(self.html or "")
        data["candidate_score"] = self.candidate.score
        data["link_text"] = self.candidate.link_text
        data["seed_url"] = self.candidate.seed_url
        return data


def read_url_candidates(path: str | Path) -> list[UrlCandidate]:
    return [UrlCandidate.from_dict(record) for record in read_jsonl(path)]


def html_manifest_key(path: str | Path) -> str:
    return str(Path(path).resolve())


def read_html_manifest(path: str | Path) -> dict[str, HtmlManifestRecord]:
    records: dict[str, HtmlManifestRecord] = {}
    for record in read_jsonl(path):
        manifest_record = HtmlManifestRecord.from_dict(record)
        records[html_manifest_key(manifest_record.html_path)] = manifest_record
    return records


def upsert_html_manifest(
    path: str | Path,
    records: list[HtmlManifestRecord],
) -> None:
    if not records:
        return
    manifest_path = Path(path)
    existing = read_html_manifest(manifest_path)
    for record in records:
        existing[html_manifest_key(record.html_path)] = record
    sorted_records = sorted(existing.values(), key=lambda item: item.html_path)
    write_jsonl(manifest_path, (record.to_dict() for record in sorted_records))


def html_filename_for_candidate(candidate: UrlCandidate) -> str:
    safe_source = "".join(char if char.isalnum() else "_" for char in candidate.source.lower())
    digest = hashlib.sha1(candidate.url.encode("utf-8")).hexdigest()[:12]
    return f"{safe_source}_{digest}.html"


def build_research_session() -> Any:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "requests is required for live downloads. Install the ingestion extra first."
        ) from exc
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.7",
        }
    )
    return session


def fetch_url_candidates(
    candidates: list[UrlCandidate],
    *,
    timeout_seconds: float = 20.0,
    max_records: int | None = None,
    session: Any | None = None,
) -> list[FetchedPage]:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "requests is required for URL downloads. Install the ingestion extra first."
        ) from exc

    client = session or build_research_session()
    selected_candidates = candidates[:max_records] if max_records is not None else candidates
    pages: list[FetchedPage] = []
    for candidate in selected_candidates:
        downloaded_at = utc_now_iso()
        try:
            response = client.get(candidate.url, timeout=timeout_seconds)
            response.raise_for_status()
            html = _decode_response_text(response)
            pages.append(
                FetchedPage(
                    candidate=candidate,
                    status_code=response.status_code,
                    html=html,
                    downloaded_at=downloaded_at,
                )
            )
        except requests.RequestException as exc:
            pages.append(
                FetchedPage(
                    candidate=candidate,
                    status_code=getattr(getattr(exc, "response", None), "status_code", None),
                    html=None,
                    downloaded_at=downloaded_at,
                    error=str(exc),
                )
            )
    return pages


def download_url_candidates(
    candidates: list[UrlCandidate],
    *,
    output_html_dir: str | Path,
    html_manifest_path: str | Path | None = None,
    timeout_seconds: float = 20.0,
    max_records: int | None = None,
    session: Any | None = None,
) -> list[DownloadRecord]:
    html_dir = Path(output_html_dir)
    html_dir.mkdir(parents=True, exist_ok=True)
    records: list[DownloadRecord] = []
    manifest_records: list[HtmlManifestRecord] = []
    for page in fetch_url_candidates(
        candidates,
        timeout_seconds=timeout_seconds,
        max_records=max_records,
        session=session,
    ):
        candidate = page.candidate
        html_path = html_dir / html_filename_for_candidate(candidate)
        if page.error or page.html is None:
            records.append(page.to_download_record())
            continue
        html_path.write_text(page.html, encoding="utf-8")
        records.append(
            page.to_download_record(
                html_path=str(html_path),
            )
        )
        manifest_records.append(
            HtmlManifestRecord(
                html_path=str(html_path),
                source_url=candidate.url,
                source=candidate.source,
                downloaded_at=page.downloaded_at,
                status_code=page.status_code,
            )
        )

    if html_manifest_path is not None:
        upsert_html_manifest(html_manifest_path, manifest_records)

    return records


def _decode_response_text(response: Any) -> str:
    content = getattr(response, "content", None)
    if isinstance(content, bytes) and content:
        encoding = getattr(response, "encoding", None)
        apparent_encoding = getattr(response, "apparent_encoding", None)
        if not encoding or str(encoding).lower() in {"iso-8859-1", "latin-1"}:
            encoding = apparent_encoding or "utf-8"
        try:
            return content.decode(str(encoding), errors="replace")
        except LookupError:
            return content.decode("utf-8", errors="replace")
    return str(getattr(response, "text", ""))
