"""Query rewriting and decomposition for retrieval."""

from __future__ import annotations

import hashlib

from finevent.ingestion.text import normalize_text
from finevent.retrieval.models import RetrievalQuery
from finevent.types import JsonDict


def build_queries_from_article(article: JsonDict) -> list[RetrievalQuery]:
    article_id = str(article.get("article_id") or "input")
    title = normalize_text(str(article.get("title") or ""))
    text = normalize_text(str(article.get("text") or ""))
    tickers = [str(item).upper() for item in article.get("tickers_hint", [])]
    company_names = [str(item) for item in article.get("company_names_hint", [])]
    event_keywords = [str(item) for item in article.get("event_keywords", [])]
    event_type_hints = [str(item).upper() for item in article.get("event_type_hints", [])]
    event_subtype_hints = [str(item).upper() for item in article.get("event_subtype_hints", [])]

    queries: list[RetrievalQuery] = []
    if title:
        queries.append(
            _make_query(
                article_id,
                "title",
                title,
                1.0,
                tickers,
                company_names,
                event_keywords,
                event_type_hints,
                event_subtype_hints,
            )
        )

    ticker_event_text = " ".join([*tickers, *event_keywords, title]).strip()
    if ticker_event_text:
        queries.append(
            _make_query(
                article_id,
                "ticker_event",
                ticker_event_text,
                1.0,
                tickers,
                company_names,
                event_keywords,
                event_type_hints,
                event_subtype_hints,
            )
        )

    company_event_text = " ".join([*company_names, *event_keywords]).strip()
    if company_event_text:
        queries.append(
            _make_query(
                article_id,
                "company_event",
                company_event_text,
                0.85,
                tickers,
                company_names,
                event_keywords,
                event_type_hints,
                event_subtype_hints,
            )
        )

    event_type_text = " ".join([*event_type_hints, *event_subtype_hints, *event_keywords]).strip()
    if event_type_text:
        queries.append(
            _make_query(
                article_id,
                "event_type",
                event_type_text,
                0.65,
                tickers,
                company_names,
                event_keywords,
                event_type_hints,
                event_subtype_hints,
            )
        )

    if text and not queries:
        queries.append(
            _make_query(
                article_id,
                "body_fallback",
                " ".join(text.split()[:80]),
                0.7,
                tickers,
                company_names,
                event_keywords,
                event_type_hints,
                event_subtype_hints,
            )
        )

    return _dedupe_queries(queries)


def build_queries_from_gold_label(gold_record: JsonDict) -> list[RetrievalQuery]:
    label = gold_record.get("label") if isinstance(gold_record.get("label"), dict) else gold_record
    article_id = str(label.get("article_id") or gold_record.get("article_id") or "gold")
    queries: list[RetrievalQuery] = []
    for event_index, event in enumerate(label.get("events", [])):
        if not isinstance(event, dict):
            continue
        ticker = [str(event["ticker"]).upper()] if event.get("ticker") else []
        company = [str(event["company_name"])] if event.get("company_name") else []
        event_type = [str(event["event_type"]).upper()] if event.get("event_type") else []
        event_subtype = [str(event["event_subtype"]).upper()] if event.get("event_subtype") else []
        parts = [
            *ticker,
            *company,
            *event_type,
            *event_subtype,
            str(event.get("event_summary") or ""),
            str(event.get("evidence_span") or ""),
        ]
        queries.append(
            _make_query(
                article_id,
                f"gold_event_{event_index:02d}",
                " ".join(part for part in parts if part).strip(),
                1.0,
                ticker,
                company,
                [],
                event_type,
                event_subtype,
            )
        )
    return _dedupe_queries(queries)


def _make_query(
    article_id: str,
    query_type: str,
    text: str,
    weight: float,
    tickers: list[str],
    company_names: list[str],
    event_keywords: list[str],
    event_type_hints: list[str],
    event_subtype_hints: list[str],
) -> RetrievalQuery:
    digest = hashlib.sha1(f"{article_id}:{query_type}:{text}".encode()).hexdigest()[:10]
    return RetrievalQuery(
        query_id=f"{article_id}_{query_type}_{digest}",
        article_id=article_id,
        text=normalize_text(text),
        query_type=query_type,
        weight=weight,
        tickers=tickers,
        company_names=company_names,
        event_keywords=event_keywords,
        event_type_hints=event_type_hints,
        event_subtype_hints=event_subtype_hints,
    )


def _dedupe_queries(queries: list[RetrievalQuery]) -> list[RetrievalQuery]:
    seen: set[str] = set()
    deduped: list[RetrievalQuery] = []
    for query in queries:
        key = normalize_text(query.text).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(query)
    return deduped
