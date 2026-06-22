"""Optional URL download support for ingestion.

The project can run M1 from local HTML without dependencies. This module is
used when the ingestion extra is installed and real URLs should be downloaded.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from finevent.jsonl import read_jsonl
from finevent.logging_utils import utc_now_iso
from finevent.types import JsonDict

DEFAULT_USER_AGENT = "Mozilla/5.0 FinEvent-VN research data collector/0.1"


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
            html = response.text
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
    timeout_seconds: float = 20.0,
    max_records: int | None = None,
    session: Any | None = None,
) -> list[DownloadRecord]:
    html_dir = Path(output_html_dir)
    html_dir.mkdir(parents=True, exist_ok=True)
    records: list[DownloadRecord] = []
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

    return records
