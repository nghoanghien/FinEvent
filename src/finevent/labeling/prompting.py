"""Prompt builders for teacher labeling and repair."""

from __future__ import annotations

import json

from finevent.schema.taxonomy import EventTaxonomy, load_event_taxonomy
from finevent.types import JsonDict

PROMPT_VERSION = "m02_teacher_v1"


def build_teacher_prompt(
    article_record: JsonDict,
    *,
    taxonomy: EventTaxonomy | None = None,
    prompt_version: str = PROMPT_VERSION,
) -> str:
    taxonomy = taxonomy or load_event_taxonomy()
    compact_taxonomy = taxonomy.compact_prompt_view()
    article_payload = {
        "article_id": article_record.get("article_id"),
        "source": article_record.get("source"),
        "url": article_record.get("url"),
        "title": article_record.get("title"),
        "published_at": article_record.get("published_at"),
        "tickers_hint": article_record.get("tickers_hint", []),
        "company_names_hint": article_record.get("company_names_hint", []),
        "event_type_hints": article_record.get("event_type_hints", []),
        "event_subtype_hints": article_record.get("event_subtype_hints", []),
        "text": article_record.get("text", ""),
    }

    return "\n".join(
        [
            "You are a strict Vietnamese financial corporate event extraction teacher model.",
            "Return only valid JSON. Do not wrap the JSON in Markdown.",
            "",
            "Task:",
            "- Read the article and produce a document-level event label.",
            "- Accept only concrete corporate events grounded in the article.",
            (
                "- If the article has no concrete corporate event, "
                "set document_label=NO_EVENT and events=[]."
            ),
            (
                "- Use impact_sentiment only for direction of impact: "
                "POSITIVE, NEGATIVE, NEUTRAL, or MIXED."
            ),
            "- Do not output impact magnitude or severity.",
            "- Every event must have an evidence_span copied from or closely matching the article.",
            "- Do not infer facts that are not present in title, text, URL metadata, or hints.",
            "- If event_subtype is uncertain, set event_subtype=null instead of guessing.",
            "- event_arguments must contain only reusable slots supported by evidence.",
            (
                "- Always include label_reason: one concise Vietnamese sentence "
                "explaining the document label."
            ),
            (
                "- For every event, include event_reason: one concise Vietnamese "
                "sentence grounded in evidence."
            ),
            "",
            "Required JSON shape:",
            json.dumps(_required_shape(prompt_version), ensure_ascii=False, indent=2),
            "",
            "Taxonomy:",
            json.dumps(compact_taxonomy, ensure_ascii=False, indent=2),
            "",
            "Article:",
            json.dumps(article_payload, ensure_ascii=False, indent=2),
        ]
    )


def build_repair_prompt(
    *,
    article_record: JsonDict,
    raw_output: object,
    validation_errors: list[JsonDict],
    taxonomy: EventTaxonomy | None = None,
) -> str:
    taxonomy = taxonomy or load_event_taxonomy()
    repair_payload = {
        "article": {
            "article_id": article_record.get("article_id"),
            "source": article_record.get("source"),
            "url": article_record.get("url"),
            "title": article_record.get("title"),
            "published_at": article_record.get("published_at"),
            "tickers_hint": article_record.get("tickers_hint", []),
            "company_names_hint": article_record.get("company_names_hint", []),
            "text": article_record.get("text", ""),
        },
        "raw_output": raw_output,
        "validation_errors": validation_errors,
        "taxonomy": taxonomy.compact_prompt_view(),
    }
    return "\n".join(
        [
            "Repair the event label JSON so it passes validation.",
            "Return only valid JSON. Do not add new facts.",
            "If evidence is invalid, choose a span from the article.",
            "If a subtype is invalid or unsupported by evidence, set event_subtype=null.",
            "If no grounded event remains, return document_label=NO_EVENT and events=[].",
            "",
            json.dumps(repair_payload, ensure_ascii=False, indent=2),
        ]
    )


def _required_shape(prompt_version: str) -> JsonDict:
    return {
        "article_id": "<same as input article_id>",
        "document_label": "HAS_EVENT | NO_EVENT | UNCERTAIN",
        "label_reason": "one concise grounded Vietnamese reason for document_label",
        "events": [
            {
                "event_id": "<article_id>_e01",
                "ticker": "string or null",
                "company_name": "string or null",
                "event_type": "one taxonomy event type",
                "event_subtype": "one valid subtype or null",
                "event_summary": "one short grounded Vietnamese summary",
                "event_reason": "one concise grounded Vietnamese reason for this event",
                "event_arguments": {},
                "impact_sentiment": "POSITIVE | NEGATIVE | NEUTRAL | MIXED",
                "evidence_span": "sentence or short paragraph from the article",
                "source_url": "<article url>",
                "published_at": "<article published_at or null>",
                "confidence": 0.0,
            }
        ],
        "warnings": [],
        "model_info": {
            "model_name": "<teacher model name>",
            "prompt_version": prompt_version,
            "run_id": "<labeling run id>",
        },
    }
