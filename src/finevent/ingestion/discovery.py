"""Live URL discovery for Vietnamese financial news ingestion."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

from finevent.ingestion.download import UrlCandidate, build_research_session
from finevent.ingestion.text import canonical_url, normalize_text
from finevent.logging_utils import utc_now_iso
from finevent.types import JsonDict

DEFAULT_DISCOVERY_KEYWORD_HINTS = [
    "cổ phiếu",
    "chứng khoán",
    "doanh nghiệp",
    "công ty",
    "tập đoàn",
    "niêm yết",
    "sàn hose",
    "hnx",
    "upcom",
    "kết quả kinh doanh",
    "lợi nhuận",
    "doanh thu",
    "hợp đồng",
    "trúng thầu",
    "dự án",
    "đầu tư",
    "mở rộng",
    "phát hành",
    "trái phiếu",
    "cổ tức",
    "mua lại",
    "sáp nhập",
    "thoái vốn",
    "lãnh đạo",
    "bổ nhiệm",
    "miễn nhiệm",
    "kiện",
    "điều tra",
    "xử phạt",
]

DEFAULT_SEED_PAGES = [
    {"source": "cafef", "url": "https://cafef.vn/thi-truong-chung-khoan.chn"},
    {"source": "vietstock", "url": "https://vietstock.vn/chung-khoan.htm"},
    {"source": "tinnhanhchungkhoan", "url": "https://www.tinnhanhchungkhoan.vn/chung-khoan/"},
    {"source": "nhadautu", "url": "https://nhadautu.vn/doanh-nghiep-d3.html"},
]


@dataclass(frozen=True)
class SeedPage:
    source: str
    url: str

    @classmethod
    def from_dict(cls, data: JsonDict) -> SeedPage:
        return cls(source=str(data["source"]), url=str(data["url"]))

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class DiscoveryDiagnostics:
    source: str
    seed_url: str
    status_code: int | None
    candidate_count: int
    error: str | None = None

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass(frozen=True)
class DiscoveryResult:
    candidates: list[UrlCandidate]
    diagnostics: list[DiscoveryDiagnostics]


def default_seed_pages() -> list[SeedPage]:
    return [SeedPage.from_dict(record) for record in DEFAULT_SEED_PAGES]


def normalize_candidate_url(url: str) -> str:
    parsed = urlparse(url)
    return canonical_url(parsed._replace(fragment="").geturl())


def source_domain(seed_url: str) -> str:
    host = urlparse(seed_url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def same_site(url: str, seed_url: str) -> bool:
    host = source_domain(url)
    seed_host = source_domain(seed_url)
    return host == seed_host or host.endswith("." + seed_host)


def looks_like_article_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    clean_path = path.strip("/")
    if not path or path in {"/", ""}:
        return False
    if any(part in path for part in ["/tag/", "/topic/", "/video/", "/photo/", "/rss", "/search"]):
        return False
    if path.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".css", ".js")):
        return False
    if (
        path.endswith((".htm", ".html"))
        and "/" not in clean_path
        and not re.search(r"\d{4,}", path)
    ):
        return False
    return bool(re.search(r"(\d{4,}|\.htm|\.html|/news/|/tin-|/bai-|/doanh-nghiep/)", path))


def score_candidate(
    *,
    text: str,
    url: str,
    keyword_hints: list[str] | None = None,
) -> int:
    haystack = normalize_text(f"{text} {url}").lower()
    hints = keyword_hints or DEFAULT_DISCOVERY_KEYWORD_HINTS
    score = sum(2 for keyword in hints if keyword in haystack)
    if re.search(r"\b[A-Z]{3}\b", text):
        score += 2
    if looks_like_article_url(url):
        score += 3
    return score


def discover_url_candidates(
    *,
    seed_pages: list[SeedPage] | None = None,
    manual_candidates: list[UrlCandidate] | None = None,
    max_candidates: int = 80,
    timeout_seconds: float = 25.0,
    keyword_hints: list[str] | None = None,
    session: Any | None = None,
) -> DiscoveryResult:
    client = session or build_research_session()
    selected_seed_pages = default_seed_pages() if seed_pages is None else seed_pages
    all_candidates: list[UrlCandidate] = []
    diagnostics: list[DiscoveryDiagnostics] = []
    for seed in selected_seed_pages:
        candidates, seed_diagnostics = discover_from_seed(
            seed,
            session=client,
            timeout_seconds=timeout_seconds,
            keyword_hints=keyword_hints,
        )
        all_candidates.extend(candidates)
        diagnostics.append(seed_diagnostics)
    all_candidates.extend(manual_candidates or [])
    ranked_candidates = dedupe_and_rank_candidates(all_candidates)
    return DiscoveryResult(
        candidates=ranked_candidates[:max_candidates],
        diagnostics=diagnostics,
    )


def discover_from_seed(
    seed: SeedPage,
    *,
    session: Any,
    timeout_seconds: float,
    keyword_hints: list[str] | None = None,
) -> tuple[list[UrlCandidate], DiscoveryDiagnostics]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 is required for URL discovery.") from exc
    try:
        response = session.get(seed.url, timeout=timeout_seconds)
        status_code = response.status_code
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - diagnostics must record live-source failures.
        return [], DiscoveryDiagnostics(
            source=seed.source,
            seed_url=seed.url,
            status_code=getattr(getattr(exc, "response", None), "status_code", None),
            candidate_count=0,
            error=str(exc),
        )

    soup = BeautifulSoup(response.text, "html.parser")
    candidates: list[UrlCandidate] = []
    for anchor in soup.select("a[href]"):
        raw_href = anchor.get("href") or ""
        absolute_url = normalize_candidate_url(urljoin(seed.url, raw_href))
        if not absolute_url.startswith("http") or not same_site(absolute_url, seed.url):
            continue
        link_text = normalize_text(anchor.get_text(" ", strip=True))
        if not link_text and not looks_like_article_url(absolute_url):
            continue
        score = score_candidate(text=link_text, url=absolute_url, keyword_hints=keyword_hints)
        if score <= 0:
            continue
        candidates.append(
            UrlCandidate(
                source=seed.source,
                url=absolute_url,
                discovered_at=utc_now_iso(),
                link_text=link_text,
                score=score,
                seed_url=seed.url,
            )
        )
    return candidates, DiscoveryDiagnostics(
        source=seed.source,
        seed_url=seed.url,
        status_code=status_code,
        candidate_count=len(candidates),
    )


def dedupe_and_rank_candidates(candidates: list[UrlCandidate]) -> list[UrlCandidate]:
    deduped: dict[str, UrlCandidate] = {}
    for candidate in candidates:
        existing = deduped.get(candidate.url)
        if existing is None or (candidate.score or 0) > (existing.score or 0):
            deduped[candidate.url] = candidate
    return sorted(
        deduped.values(),
        key=lambda candidate: (candidate.score or 0, candidate.discovered_at or ""),
        reverse=True,
    )
