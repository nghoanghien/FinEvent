"""Student extraction utilities.

The production path should call a LangChain chat model with the prompt built by
M06. The deterministic extractor below is a local baseline for tests and smoke
runs when no LLM endpoint is available.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from finevent.ingestion.text import normalize_text
from finevent.schema.taxonomy import load_event_taxonomy
from finevent.types import JsonDict


class InvokableStudentModel(Protocol):
    def invoke(self, prompt: str) -> Any: ...


@dataclass(frozen=True)
class StudentModelResult:
    content: str
    reasoning_trace: JsonDict


POSITIVE_TYPES = {
    "CONTRACT",
    "EXPANSION",
    "LICENSE_APPROVAL",
    "PARTNERSHIP",
    "PRODUCT_SERVICE",
}
NEGATIVE_TYPES = {
    "LEGAL_RISK",
    "ESG_OPERATIONAL_RISK",
}


def run_deterministic_student_extractor(
    *,
    article: JsonDict,
    run_id: str,
    model_name: str,
    prompt_version: str,
) -> str:
    event_type = _first_valid_event_type(article.get("event_type_hints", []))
    has_company_grounding = bool(article.get("tickers_hint") or article.get("company_names_hint"))
    if not event_type or not has_company_grounding:
        return json.dumps(
            {
                "article_id": article["article_id"],
                "document_label": "NO_EVENT",
                "label_reason": _no_event_reason(event_type, has_company_grounding),
                "events": [],
                "warnings": [_no_event_reason(event_type, has_company_grounding)],
                "model_info": _model_info(model_name, prompt_version, run_id),
            },
            ensure_ascii=False,
        )

    taxonomy = load_event_taxonomy()
    event_subtype = _first_valid_subtype(
        event_type,
        article.get("event_subtype_hints", []),
        taxonomy.allowed_subtypes(event_type),
    )
    evidence = _select_evidence(article)
    ticker = _first_or_none(article.get("tickers_hint", []))
    company_name = _first_or_none(article.get("company_names_hint", []))
    event = {
        "event_id": f"{article['article_id']}_e01",
        "ticker": ticker,
        "company_name": company_name,
        "event_type": event_type,
        "event_subtype": event_subtype,
        "event_summary": _summary(article, evidence),
        "event_reason": _event_reason(article, event_type, evidence),
        "event_arguments": _arguments(event_type, article),
        "impact_sentiment": _impact_sentiment(event_type),
        "evidence_span": evidence,
        "source_url": article.get("url") or "",
        "published_at": article.get("published_at"),
        "confidence": _confidence(article, event_type, ticker, evidence),
    }
    return json.dumps(
        {
            "article_id": article["article_id"],
            "document_label": "HAS_EVENT",
            "label_reason": (
                "Bai viet co tin hieu doanh nghiep, loai su kien va bang chung "
                "truc tiep."
            ),
            "events": [event],
            "warnings": ["deterministic_student_baseline"],
            "model_info": _model_info(model_name, prompt_version, run_id),
        },
        ensure_ascii=False,
    )


def run_langchain_student_model(model: InvokableStudentModel, prompt: str) -> str:
    """Call a LangChain model object without implementing provider adapters."""
    return run_langchain_student_model_with_trace(model, prompt).content


def run_langchain_student_model_with_trace(
    model: InvokableStudentModel,
    prompt: str,
) -> StudentModelResult:
    """Call a LangChain model and separate final content from provider reasoning metadata."""
    response = model.invoke(prompt)
    reasoning_content = _response_reasoning_content(response)
    content = getattr(response, "content", response)
    final_content = _stringify_model_content(content)
    return StudentModelResult(
        content=final_content,
        reasoning_trace={
            "source": "langchain_response",
            "has_provider_reasoning": bool(reasoning_content),
            "provider_reasoning_content": reasoning_content or None,
        },
    )


def _stringify_model_content(content: object) -> str:
    if isinstance(content, list):
        return "\n".join(str(part) for part in content)
    return str(content)


def _response_reasoning_content(response: object) -> str:
    for attr_name in ("reasoning_content",):
        value = getattr(response, attr_name, None)
        if value:
            return str(value).strip()
    additional_kwargs = getattr(response, "additional_kwargs", None)
    if isinstance(additional_kwargs, dict):
        value = additional_kwargs.get("reasoning_content")
        if value:
            return str(value).strip()
    response_metadata = getattr(response, "response_metadata", None)
    if isinstance(response_metadata, dict):
        value = response_metadata.get("reasoning_content")
        if value:
            return str(value).strip()
    return ""


def _first_valid_event_type(values: object) -> str | None:
    taxonomy = load_event_taxonomy()
    for value in values if isinstance(values, list) else []:
        event_type = str(value).upper()
        if event_type in taxonomy.event_types and event_type != "UNKNOWN":
            return event_type
    return None


def _first_valid_subtype(
    event_type: str,
    values: object,
    allowed_subtypes: frozenset[str],
) -> str | None:
    for value in values if isinstance(values, list) else []:
        subtype = str(value).upper()
        if subtype in allowed_subtypes:
            return subtype
    return next(iter(sorted(allowed_subtypes)), None) if event_type == "OTHER" else None


def _select_evidence(article: JsonDict) -> str:
    text = normalize_text(str(article.get("text") or ""))
    keywords = [str(item).lower() for item in article.get("event_keywords", [])]
    paragraphs = [paragraph.strip() for paragraph in text.splitlines() if paragraph.strip()]
    for paragraph in paragraphs:
        lower = paragraph.lower()
        if any(keyword.lower() in lower for keyword in keywords):
            return paragraph
    return paragraphs[0] if paragraphs else normalize_text(str(article.get("title") or ""))


def _summary(article: JsonDict, evidence: str) -> str:
    title = normalize_text(str(article.get("title") or ""))
    if title:
        return title
    return evidence[:180]


def _event_reason(article: JsonDict, event_type: str, evidence: str) -> str:
    keywords = ", ".join(str(item) for item in article.get("event_keywords", [])[:3])
    if keywords:
        return f"Bằng chứng chứa tín hiệu {keywords} phù hợp với nhóm sự kiện {event_type}."
    return f"Bằng chứng trong bài hỗ trợ phân loại sự kiện {event_type}: {evidence[:160]}"


def _arguments(event_type: str, article: JsonDict) -> JsonDict:
    text = " ".join(
        part for part in [str(article.get("title") or ""), str(article.get("text") or "")] if part
    )
    arguments: JsonDict = {}
    if event_type in {"CONTRACT", "PARTNERSHIP"}:
        partner = _first_or_none(article.get("company_names_hint", [])[1:])
        if partner:
            arguments["partner"] = partner
    if event_type in {"EXPANSION", "LICENSE_APPROVAL"}:
        project = _phrase_after_keywords(text, ["du an", "nhà máy", "nha may"])
        if project:
            arguments["project"] = project
    if event_type == "LEADERSHIP":
        arguments["role"] = "lanh dao"
    return arguments


def _phrase_after_keywords(text: str, keywords: list[str]) -> str | None:
    folded = normalize_text(text)
    lower = folded.lower()
    for keyword in keywords:
        index = lower.find(keyword)
        if index >= 0:
            return folded[index : index + 90].strip(" .,;:")
    return None


def _impact_sentiment(event_type: str) -> str:
    if event_type in POSITIVE_TYPES:
        return "POSITIVE"
    if event_type in NEGATIVE_TYPES:
        return "NEGATIVE"
    return "NEUTRAL"


def _confidence(article: JsonDict, event_type: str, ticker: str | None, evidence: str) -> float:
    score = 0.52
    if event_type:
        score += 0.15
    if ticker:
        score += 0.10
    if evidence:
        score += 0.12
    if article.get("event_keywords"):
        score += 0.06
    return round(min(score, 0.92), 2)


def _model_info(model_name: str, prompt_version: str, run_id: str) -> JsonDict:
    return {
        "model_name": model_name,
        "prompt_version": prompt_version,
        "run_id": run_id,
    }


def _no_event_reason(event_type: str | None, has_company_grounding: bool) -> str:
    if not event_type:
        return "deterministic_no_event_type_hint"
    if not has_company_grounding:
        return "deterministic_no_company_grounding"
    return "deterministic_no_event"


def _first_or_none(values: object) -> str | None:
    if not isinstance(values, list) or not values:
        return None
    value = values[0]
    return str(value) if value else None
