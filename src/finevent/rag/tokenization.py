"""Lightweight Vietnamese-friendly tokenization for retrieval indexes."""

from __future__ import annotations

import re
import unicodedata

from finevent.ingestion.text import normalize_text

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
    folded = ascii_fold(normalize_text(text)).lower()
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
