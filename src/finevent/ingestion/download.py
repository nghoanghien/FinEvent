"""Optional URL download support for ingestion.

The project can run M1 from local HTML without dependencies. This module is
used when the ingestion extra is installed and real URLs should be downloaded.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path

from finevent.jsonl import read_jsonl
from finevent.logging_utils import utc_now_iso
from finevent.types import JsonDict


@dataclass(frozen=True)
class UrlCandidate:
    url: str
    source: str
    ticker_hint: str | None = None
    keyword_hint: str | None = None
    discovered_at: str | None = None

    @classmethod
    def from_dict(cls, data: JsonDict) -> "UrlCandidate":
        return cls(
            url=str(data["url"]),
            source=str(data.get("source") or "unknown"),
            ticker_hint=data.get("ticker_hint"),
            keyword_hint=data.get("keyword_hint"),
            discovered_at=data.get("discovered_at"),
        )


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


def read_url_candidates(path: str | Path) -> list[UrlCandidate]:
    return [UrlCandidate.from_dict(record) for record in read_jsonl(path)]


def html_filename_for_candidate(candidate: UrlCandidate) -> str:
    safe_source = "".join(char if char.isalnum() else "_" for char in candidate.source.lower())
    digest = hashlib.sha1(candidate.url.encode("utf-8")).hexdigest()[:12]
    return f"{safe_source}_{digest}.html"


def download_url_candidates(
    candidates: list[UrlCandidate],
    *,
    output_html_dir: str | Path,
    timeout_seconds: float = 20.0,
) -> list[DownloadRecord]:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "requests is required for URL downloads. Install the ingestion extra first."
        ) from exc

    html_dir = Path(output_html_dir)
    html_dir.mkdir(parents=True, exist_ok=True)
    records: list[DownloadRecord] = []

    for candidate in candidates:
        html_path = html_dir / html_filename_for_candidate(candidate)
        try:
            response = requests.get(
                candidate.url,
                timeout=timeout_seconds,
                headers={"User-Agent": "FinEvent-VN research crawler/0.1"},
            )
            response.raise_for_status()
            html_path.write_text(response.text, encoding=response.encoding or "utf-8")
            records.append(
                DownloadRecord(
                    url=candidate.url,
                    source=candidate.source,
                    status_code=response.status_code,
                    html_path=str(html_path),
                    downloaded_at=utc_now_iso(),
                )
            )
        except requests.RequestException as exc:
            records.append(
                DownloadRecord(
                    url=candidate.url,
                    source=candidate.source,
                    status_code=getattr(getattr(exc, "response", None), "status_code", None),
                    html_path=None,
                    downloaded_at=utc_now_iso(),
                    error=str(exc),
                )
            )

    return records
