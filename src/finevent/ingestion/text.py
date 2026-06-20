"""Text normalization and hashing utilities."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from html import unescape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {"fbclid", "gclid"}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", unescape(text or ""))
    normalized = normalized.replace("\xa0", " ")
    normalized = re.sub(r"[ \t\r\f\v]+", " ", normalized)
    normalized = re.sub(r"\n\s*\n+", "\n\n", normalized)
    normalized = "\n".join(line.strip() for line in normalized.splitlines())
    return normalized.strip()


def text_hash(text: str) -> str:
    normalized = normalize_text(text).lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def stable_article_id(source: str, url: str, text: str) -> str:
    source_part = re.sub(r"[^a-z0-9]+", "_", source.lower()).strip("_") or "unknown"
    digest = hashlib.sha1(f"{canonical_url(url)}\n{text_hash(text)}".encode()).hexdigest()
    return f"{source_part}_{digest[:12]}"


def canonical_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query_items = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key in TRACKING_QUERY_KEYS or any(
            key.startswith(prefix) for prefix in TRACKING_QUERY_PREFIXES
        ):
            continue
        query_items.append((key, value))
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path.rstrip("/"),
            urlencode(sorted(query_items)),
            "",
        )
    )


def vietnamese_character_ratio(text: str) -> float:
    if not text:
        return 0.0
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    marked_letters = sum(1 for char in letters if char in "đĐ" or ord(char) > 127)
    return marked_letters / len(letters)
