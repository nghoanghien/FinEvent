"""Pattern query construction for few-shot selection."""

from __future__ import annotations

import hashlib

from finevent.ingestion.text import normalize_text
from finevent.patterns.models import PatternQuery, PatternRecord
from finevent.types import JsonDict


def build_pattern_query_from_article(article: JsonDict) -> PatternQuery:
    return build_pattern_queries_from_article(article)[0]


def build_pattern_queries_from_article(
    article: JsonDict,
    *,
    query_mode: str = "legacy",
) -> list[PatternQuery]:
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
    queries = [
        _make_query(
            article_id=article_id,
            query_type="article_pattern",
            text=query_text,
            tickers=tickers,
            company_names=companies,
            event_keywords=keywords,
            event_type_hints=event_types,
            event_subtype_hints=event_subtypes,
            document_label_hint=article.get("document_label_hint"),
        )
    ]
    if query_mode == "event_intent":
        queries.extend(
            _build_event_intent_queries(
                article,
                article_id=article_id,
                title=title,
                body_preview=body_preview,
                tickers=tickers,
                companies=companies,
                event_keywords=keywords,
                event_type_hints=event_types,
                event_subtype_hints=event_subtypes,
            )
        )
    elif query_mode != "legacy":
        raise ValueError(f"Unknown pattern query_mode: {query_mode}")
    return _dedupe_queries(queries) or queries[:1]


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
        query_type="pattern_record",
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
        query_type="raw_pattern",
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
    query_type: str,
    text: str,
    tickers: list[str],
    company_names: list[str],
    event_keywords: list[str],
    event_type_hints: list[str],
    event_subtype_hints: list[str],
    document_label_hint: str | None,
    intent_key: str | None = None,
    intent_event_type: str | None = None,
    intent_subtype_hints: list[str] | None = None,
) -> PatternQuery:
    digest = hashlib.sha1(f"{article_id}:{query_type}:{text}".encode()).hexdigest()[:10]
    return PatternQuery(
        query_id=f"{article_id}_pattern_{digest}",
        article_id=article_id,
        text=normalize_text(text),
        query_type=query_type,
        tickers=tickers,
        company_names=company_names,
        event_keywords=event_keywords,
        event_type_hints=event_type_hints,
        event_subtype_hints=event_subtype_hints,
        document_label_hint=document_label_hint,
        intent_key=intent_key,
        intent_event_type=intent_event_type,
        intent_subtype_hints=intent_subtype_hints or [],
    )


def _build_event_intent_queries(
    article: JsonDict,
    *,
    article_id: str,
    title: str,
    body_preview: str,
    tickers: list[str],
    companies: list[str],
    event_keywords: list[str],
    event_type_hints: list[str],
    event_subtype_hints: list[str],
) -> list[PatternQuery]:
    keyword_groups = _keyword_groups_by_event_type(article)
    queries: list[PatternQuery] = []
    for event_type in event_type_hints:
        group = keyword_groups.get(event_type, {})
        type_keywords = list(group.get("keywords") or event_keywords)
        subtype_hints = list(group.get("subtypes") or event_subtype_hints)
        text = normalize_text(
            " ".join(
                [
                    title,
                    *tickers,
                    *companies,
                    event_type,
                    *subtype_hints,
                    *type_keywords,
                    body_preview,
                ]
            )
        )
        if not text:
            continue
        queries.append(
            _make_query(
                article_id=article_id,
                query_type=f"event_intent_{event_type.lower()}",
                text=text,
                tickers=tickers,
                company_names=companies,
                event_keywords=type_keywords,
                event_type_hints=[event_type],
                event_subtype_hints=subtype_hints,
                document_label_hint=article.get("document_label_hint"),
                intent_key=f"event:{event_type}",
                intent_event_type=event_type,
                intent_subtype_hints=subtype_hints,
            )
        )
    return queries


def _keyword_groups_by_event_type(article: JsonDict) -> dict[str, dict[str, list[str]]]:
    groups: dict[str, dict[str, list[str]]] = {}
    matches = article.get("event_keyword_matches")
    if not isinstance(matches, list):
        return groups
    for raw_match in matches:
        if not isinstance(raw_match, dict):
            continue
        event_type = str(raw_match.get("event_type") or "").upper()
        if not event_type:
            continue
        group = groups.setdefault(event_type, {"keywords": [], "subtypes": []})
        keyword = normalize_text(str(raw_match.get("keyword") or ""))
        if keyword and keyword not in group["keywords"]:
            group["keywords"].append(keyword)
        subtype = str(raw_match.get("event_subtype") or "").upper()
        if subtype and subtype not in group["subtypes"]:
            group["subtypes"].append(subtype)
    return groups


def _dedupe_queries(queries: list[PatternQuery]) -> list[PatternQuery]:
    seen: set[str] = set()
    deduped: list[PatternQuery] = []
    for query in queries:
        key = normalize_text(query.text).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(query)
    return deduped
