"""Lightweight Vietnamese-friendly tokenization for retrieval indexes."""

from __future__ import annotations

import re
import unicodedata

from finevent.ingestion.text import normalize_text
from finevent.ingestion.vietnamese_preprocessing import (
    preprocess_vietnamese_text,
)
from finevent.types import JsonDict

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)?", flags=re.UNICODE)
VIETNAMESE_STOPWORDS = {
    "a",
    "an",
    "anh",
    "ba",
    "ban",
    "bang",
    "bi",
    "bo",
    "cac",
    "cai",
    "cho",
    "co",
    "cua",
    "da",
    "dang",
    "de",
    "den",
    "duoc",
    "duong",
    "gan",
    "giua",
    "hai",
    "hay",
    "hon",
    "khi",
    "la",
    "lai",
    "len",
    "mot",
    "nay",
    "nen",
    "nhieu",
    "nhung",
    "o",
    "qua",
    "sau",
    "se",
    "tai",
    "theo",
    "thi",
    "trong",
    "tu",
    "va",
    "vao",
    "ve",
    "voi",
}


def tokenize_for_retrieval(text: str, *, remove_stopwords: bool = True) -> list[str]:
    preprocessed = preprocess_vietnamese_text(text)
    token_text = preprocessed.normalized_text
    folded = ascii_fold(normalize_text(token_text)).lower()
    tokens = [match.group(0) for match in TOKEN_RE.finditer(folded)]
    if remove_stopwords:
        tokens = [token for token in tokens if token not in VIETNAMESE_STOPWORDS and len(token) > 1]
    return tokens


def ascii_fold(text: str) -> str:
    replacements = {
        "\u0111": "d",
        "\u0110": "D",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )


def retrieval_text_from_parts(
    *,
    title: str | None,
    text: str,
    metadata: JsonDict | None = None,
    tickers_hint: list[str] | None = None,
    company_names_hint: list[str] | None = None,
    event_keywords: list[str] | None = None,
    event_type_hints: list[str] | None = None,
) -> str:
    parts = [
        title or "",
        text,
        " ".join(tickers_hint or []),
        " ".join(company_names_hint or []),
        " ".join(event_keywords or []),
        " ".join(event_type_hints or []),
    ]
    return "\n".join(part for part in parts if part)
