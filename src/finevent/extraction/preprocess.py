"""Input preprocessing for online article extraction."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from finevent.ingestion.metadata import (
    DEFAULT_EVENT_KEYWORD_TAXONOMY_PATH,
    extract_event_keyword_matches,
    extract_event_keywords,
    extract_event_subtype_hints,
    extract_event_type_hints,
    extract_sector_hints,
    extract_tickers_and_companies,
    load_company_dictionary,
    load_event_keyword_taxonomy,
)
from finevent.ingestion.parsers import parse_article_html
from finevent.ingestion.text import canonical_url, stable_article_id, text_hash
from finevent.ingestion.vietnamese_preprocessing import preprocess_vietnamese_text
from finevent.logging_utils import utc_now_iso
from finevent.types import JsonDict, PathLike


def preprocess_extraction_input(
    payload: JsonDict,
    *,
    dictionary_path: PathLike = "data/dictionaries/ticker_company_map.csv",
    keyword_taxonomy_path: PathLike = DEFAULT_EVENT_KEYWORD_TAXONOMY_PATH,
) -> tuple[JsonDict, list[str]]:
    input_type = str(payload.get("input_type") or "text").lower()
    warnings: list[str] = []
    if input_type == "article":
        article = _article_from_record(payload.get("article") or payload)
    elif input_type == "url":
        article, url_warnings = _article_from_url(payload)
        warnings.extend(url_warnings)
    elif input_type == "text":
        article = _article_from_text(payload)
    else:
        raise ValueError(f"Unsupported extraction input_type: {input_type}")

    clean_article = _attach_metadata_hints(
        article,
        dictionary_path=dictionary_path,
        keyword_taxonomy_path=keyword_taxonomy_path,
    )
    if clean_article["text_char_count"] < 80:
        warnings.append("input_text_short")
    if not clean_article["event_keywords"]:
        warnings.append("no_event_keyword_hint")
    if not clean_article["tickers_hint"] and not clean_article["company_names_hint"]:
        warnings.append("no_company_or_ticker_hint")
    return clean_article, warnings


def _article_from_record(record: object) -> JsonDict:
    if not isinstance(record, dict):
        raise ValueError("input_type=article requires an article object.")
    text_result = preprocess_vietnamese_text(
        str(record.get("text") or record.get("body_text") or "")
    )
    text = text_result.normalized_text
    title_result = preprocess_vietnamese_text(str(record.get("title") or ""))
    source = str(record.get("source") or "manual")
    url = canonical_url(str(record.get("url") or record.get("source_url") or ""))
    if not url:
        url = _manual_url(source, text)
    article_id = str(record.get("article_id") or stable_article_id(source, url, text))
    return {
        "article_id": article_id,
        "source": source,
        "url": url,
        "title": title_result.normalized_text or None,
        "published_at": record.get("published_at"),
        "text": text,
        "preprocessing": record.get("preprocessing")
        or {
            "body": text_result.to_metadata(),
            "title": title_result.to_metadata(),
        },
        "language": str(record.get("language") or "vi"),
        "content_hash": str(record.get("content_hash") or text_hash(text)),
    }


def _article_from_text(payload: JsonDict) -> JsonDict:
    text_result = preprocess_vietnamese_text(str(payload.get("value") or payload.get("text") or ""))
    title_result = preprocess_vietnamese_text(str(payload.get("title") or ""))
    text = text_result.normalized_text
    if not text:
        raise ValueError("input_type=text requires a non-empty value.")
    source = str(payload.get("source") or "manual")
    url = canonical_url(str(payload.get("url") or ""))
    if not url:
        url = _manual_url(source, text)
    article_id = str(payload.get("article_id") or stable_article_id(source, url, text))
    return {
        "article_id": article_id,
        "source": source,
        "url": url,
        "title": title_result.normalized_text or None,
        "published_at": payload.get("published_at") or utc_now_iso(),
        "text": text,
        "preprocessing": {
            "body": text_result.to_metadata(),
            "title": title_result.to_metadata(),
        },
        "language": "vi",
        "content_hash": text_hash(text),
    }


def _article_from_url(payload: JsonDict) -> tuple[JsonDict, list[str]]:
    url = str(payload.get("value") or payload.get("url") or "")
    if not url:
        raise ValueError("input_type=url requires a non-empty value.")
    html, source, warnings = _load_html_from_url(url)
    parsed = parse_article_html(html, source=source, url=url)
    text_result = preprocess_vietnamese_text(parsed.body_text)
    title_result = preprocess_vietnamese_text(parsed.title or "")
    text = text_result.normalized_text
    article_id = stable_article_id(source, canonical_url(url), text or url)
    warnings.extend(parsed.warnings)
    return (
        {
            "article_id": article_id,
            "source": source,
            "url": canonical_url(url),
            "title": title_result.normalized_text or None,
            "published_at": parsed.published_at,
            "text": text,
            "preprocessing": {
                "body": text_result.to_metadata(),
                "title": title_result.to_metadata(),
            },
            "language": "vi",
            "content_hash": text_hash(text),
        },
        warnings,
    )


def _load_html_from_url(url: str) -> tuple[str, str, list[str]]:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        path = Path(parsed.path)
        html = path.read_text(encoding="utf-8", errors="replace")
        source = path.stem.split("_", 1)[0].lower() if "_" in path.stem else "local"
        return html, source, []
    if parsed.scheme in {"http", "https"}:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("requests is required for URL extraction input.") from exc
        response = requests.get(
            url,
            timeout=20,
            headers={"User-Agent": "FinEvent-VN online extraction/0.1"},
        )
        response.raise_for_status()
        source = parsed.netloc.lower().replace("www.", "") or "web"
        return response.text, source, []
    raise ValueError(f"Unsupported URL scheme for extraction input: {parsed.scheme}")


def _attach_metadata_hints(
    article: JsonDict,
    *,
    dictionary_path: PathLike,
    keyword_taxonomy_path: PathLike,
) -> JsonDict:
    metadata_text = "\n".join(
        part for part in [str(article.get("title") or ""), str(article.get("text") or "")] if part
    )
    company_entries = load_company_dictionary(dictionary_path)
    taxonomy_entries = load_event_keyword_taxonomy(keyword_taxonomy_path)
    tickers, company_names = extract_tickers_and_companies(metadata_text, company_entries)
    keyword_matches = extract_event_keyword_matches(metadata_text, taxonomy_entries)
    clean_article = {
        **article,
        "tickers_hint": tickers,
        "company_names_hint": company_names,
        "sector_hints": extract_sector_hints(tickers, company_entries),
        "event_keyword_matches": [
            {
                "event_type": match.event_type,
                "event_subtype": match.event_subtype,
                "keyword": match.keyword,
                "polarity_hint": match.polarity_hint,
                "priority": match.priority,
            }
            for match in keyword_matches
        ],
        "event_keywords": extract_event_keywords(metadata_text, taxonomy_entries=taxonomy_entries),
        "event_type_hints": extract_event_type_hints(keyword_matches),
        "event_subtype_hints": extract_event_subtype_hints(keyword_matches),
        "text_char_count": len(str(article.get("text") or "")),
        "version": "m06_v1",
    }
    return clean_article


def _manual_url(source: str, text: str) -> str:
    digest = text_hash(text).replace("sha256:", "")[:16]
    return f"manual://{source}/{digest}"
