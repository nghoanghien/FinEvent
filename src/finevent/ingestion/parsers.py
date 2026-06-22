"""HTML parsers for financial news articles.

BeautifulSoup is used when available. A small stdlib fallback keeps M1 runnable
before optional ingestion dependencies are installed.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from typing import Any, cast

from finevent.ingestion.models import ParsedArticle
from finevent.ingestion.text import normalize_text


def parse_article_html(html: str, *, source: str, url: str) -> ParsedArticle:
    try:
        return _parse_with_bs4(html, source=source, url=url)
    except ImportError:
        return _parse_with_stdlib(html, source=source, url=url)


def infer_source_from_path(path: Path) -> str:
    stem = path.stem.lower()
    if "_" in stem:
        return stem.split("_", 1)[0]
    return "local"


def _parse_with_bs4(html: str, *, source: str, url: str) -> ParsedArticle:
    from bs4 import BeautifulSoup

    soup = cast(Any, BeautifulSoup(html, "html.parser"))
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = _first_text(
        [
            _meta_content(soup, "property", "og:title"),
            _meta_content(soup, "name", "title"),
            soup.title.get_text(" ", strip=True) if soup.title else None,
            _select_text(soup, "h1"),
        ]
    )
    published_at = _first_text(
        [
            _meta_content(soup, "property", "article:published_time"),
            _meta_content(soup, "name", "pubdate"),
            _meta_content(soup, "name", "publishdate"),
            _select_attr(soup, "time", "datetime"),
            _select_text(soup, "time"),
        ]
    )
    author = _first_text(
        [
            _meta_content(soup, "name", "author"),
            _select_text(soup, ".author"),
        ]
    )

    article_node = _select_best_article_node(soup)
    container = article_node or soup.body or soup
    paragraphs = [node.get_text(" ", strip=True) for node in container.find_all(["p", "li"])]
    body_text = normalize_text("\n".join(text for text in paragraphs if text))
    if not body_text:
        body_text = normalize_text(container.get_text("\n", strip=True))

    warnings = []
    if not title:
        warnings.append("missing_title")
    if not published_at:
        warnings.append("missing_published_at")
    if not body_text:
        warnings.append("empty_body")

    return ParsedArticle(
        source=source,
        url=url,
        title=title,
        published_at=published_at,
        author=author,
        body_text=body_text,
        warnings=warnings,
    )


def _select_best_article_node(soup: Any) -> Any | None:
    selectors = (
        "[itemprop='articleBody']",
        ".article__body",
        ".cms-body",
        ".article-content",
        ".detail-content",
        ".news-content",
        ".contentdetail",
        ".article-detail",
        ".post-content",
        ".content-news",
        "article",
    )
    candidates = []
    for selector in selectors:
        candidates.extend(soup.select(selector))
    if not candidates:
        return None
    return max(candidates, key=_article_text_score)


def _article_text_score(node: Any) -> int:
    paragraphs = [
        child.get_text(" ", strip=True)
        for child in node.find_all(["p", "li"])
        if child.get_text(" ", strip=True)
    ]
    if paragraphs:
        return sum(len(text) for text in paragraphs)
    return len(node.get_text(" ", strip=True))


def _meta_content(soup: Any, attr_name: str, attr_value: str) -> str | None:
    node = soup.find("meta", attrs={attr_name: attr_value})
    if node is None:
        return None
    content = node.get("content")
    return str(content).strip() if content else None


def _select_text(soup: Any, selector: str) -> str | None:
    node = soup.select_one(selector)
    if node is None:
        return None
    text = node.get_text(" ", strip=True)
    return text or None


def _select_attr(soup: Any, selector: str, attr: str) -> str | None:
    node = soup.select_one(selector)
    if node is None:
        return None
    value = node.get(attr)
    return str(value).strip() if value else None


def _first_text(values: list[str | None]) -> str | None:
    for value in values:
        if value and value.strip():
            return normalize_text(value)
    return None


class _FallbackArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._tag_stack: list[str] = []
        self._buffer: list[str] = []
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.paragraphs: list[str] = []
        self.time_values: list[str] = []
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        if tag == "meta":
            key = attrs_dict.get("property") or attrs_dict.get("name")
            content = attrs_dict.get("content")
            if key and content:
                self.meta[key.lower()] = content
        if tag == "time" and attrs_dict.get("datetime"):
            self.time_values.append(attrs_dict["datetime"])
        self._tag_stack.append(tag)
        if tag in {"title", "h1", "p", "li", "time"}:
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        text = normalize_text(" ".join(self._buffer))
        if text:
            if tag == "title":
                self.title_parts.append(text)
            elif tag == "h1":
                self.h1_parts.append(text)
            elif tag in {"p", "li"}:
                self.paragraphs.append(text)
            elif tag == "time":
                self.time_values.append(text)
        if self._tag_stack:
            self._tag_stack.pop()
        self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._tag_stack and self._tag_stack[-1] in {"title", "h1", "p", "li", "time"}:
            self._buffer.append(data)


def _parse_with_stdlib(html: str, *, source: str, url: str) -> ParsedArticle:
    parser = _FallbackArticleParser()
    parser.feed(html)

    title = _first_text(
        [
            parser.meta.get("og:title"),
            parser.meta.get("title"),
            parser.title_parts[0] if parser.title_parts else None,
            parser.h1_parts[0] if parser.h1_parts else None,
        ]
    )
    published_at = _first_text(
        [
            parser.meta.get("article:published_time"),
            parser.meta.get("pubdate"),
            parser.meta.get("publishdate"),
            parser.time_values[0] if parser.time_values else None,
        ]
    )
    body_text = normalize_text("\n".join(parser.paragraphs))

    warnings = []
    if not title:
        warnings.append("missing_title")
    if not published_at:
        warnings.append("missing_published_at")
    if not body_text:
        warnings.append("empty_body")

    return ParsedArticle(
        source=source,
        url=url,
        title=title,
        published_at=published_at,
        author=parser.meta.get("author"),
        body_text=body_text,
        warnings=warnings,
    )
