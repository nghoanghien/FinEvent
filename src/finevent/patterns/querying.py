"""Pattern query construction for few-shot selection."""

from __future__ import annotations

import hashlib

from finevent.ingestion.text import normalize_text
from finevent.patterns.models import PatternQuery, PatternRecord
from finevent.types import JsonDict


def build_pattern_query_from_article(article: JsonDict) -> PatternQuery:
    article_id = str(article.get("article_id") or "input")
    title = normalize_text(str(article.get("title") or ""))
    text = normalize_text(str(article.get("text") or ""))
    tickers = [str(item).upper() for item in article.get("tickers_hint", [])]
    companies = [str(item) for item in article.get("company_names_hint", [])]
    keywords = [str(item) for item in article.get("event_keywords", [])]
    event_types = [str(item).upper() for item in article.get("event_type_hints", [])]
    event_subtypes = [str(item).upper() for item in article.get("event_subtype_hints", [])]
    body_preview = " ".join(text.split()[:120])
    query_text = normalize_text(
        " ".join(
            [title, *tickers, *companies, *keywords, *event_types, *event_subtypes, body_preview]
        )
    )
    return _make_query(
        article_id=article_id,
        text=query_text,
        tickers=tickers,
        company_names=companies,
        event_keywords=keywords,
        event_type_hints=event_types,
        event_subtype_hints=event_subtypes,
        document_label_hint=article.get("document_label_hint"),
    )


def build_pattern_query_from_pattern(pattern: PatternRecord) -> PatternQuery:
    metadata = pattern.metadata
    text = normalize_text(
        " ".join(
            part
            for part in [
                str(metadata.get("title") or ""),
                pattern.ticker or "",
                pattern.company_name or "",
                pattern.event_type or "",
                pattern.event_subtype or "",
                str(metadata.get("event_summary") or ""),
                pattern.evidence_span or pattern.input_excerpt,
                pattern.pattern_text,
            ]
            if part
        )
    )
    return _make_query(
        article_id=pattern.article_id,
        text=text,
        tickers=[pattern.ticker] if pattern.ticker else [],
        company_names=[pattern.company_name] if pattern.company_name else [],
        event_keywords=[str(item) for item in metadata.get("event_keywords", [])],
        event_type_hints=[pattern.event_type] if pattern.event_type else [],
        event_subtype_hints=[pattern.event_subtype] if pattern.event_subtype else [],
        document_label_hint=pattern.document_label,
    )


def build_pattern_query_from_raw(
    *,
    article_id: str,
    text: str,
    tickers: list[str] | None = None,
    company_names: list[str] | None = None,
    event_keywords: list[str] | None = None,
    event_type_hints: list[str] | None = None,
    event_subtype_hints: list[str] | None = None,
    document_label_hint: str | None = None,
) -> PatternQuery:
    return _make_query(
        article_id=article_id,
        text=normalize_text(text),
        tickers=[item.upper() for item in tickers or []],
        company_names=company_names or [],
        event_keywords=event_keywords or [],
        event_type_hints=[item.upper() for item in event_type_hints or []],
        event_subtype_hints=[item.upper() for item in event_subtype_hints or []],
        document_label_hint=document_label_hint,
    )


def _make_query(
    *,
    article_id: str,
    text: str,
    tickers: list[str],
    company_names: list[str],
    event_keywords: list[str],
    event_type_hints: list[str],
    event_subtype_hints: list[str],
    document_label_hint: str | None,
) -> PatternQuery:
    digest = hashlib.sha1(f"{article_id}:{text}".encode()).hexdigest()[:10]
    return PatternQuery(
        query_id=f"{article_id}_pattern_{digest}",
        article_id=article_id,
        text=normalize_text(text),
        tickers=tickers,
        company_names=company_names,
        event_keywords=event_keywords,
        event_type_hints=event_type_hints,
        event_subtype_hints=event_subtype_hints,
        document_label_hint=document_label_hint,
    )
