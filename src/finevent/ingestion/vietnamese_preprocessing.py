"""Vietnamese text normalization for financial-news ingestion and model prompts."""

from __future__ import annotations

import importlib
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any

from finevent.ingestion.text import normalize_text
from finevent.types import JsonDict

PREPROCESSING_VERSION = "vi_preprocess_v1"
PRESERVED_TOKEN_RE = re.compile(
    r"(?<!\w)(?:[A-ZĐ]{2,}(?:[_/-][A-ZĐ0-9]+)*|[A-ZĐ]+&[A-ZĐ]+)(?!\w)"
)

FINANCIAL_ABBREVIATIONS = {
    "đhđcđ": "đại hội đồng cổ đông",
    "đhcđ": "đại hội đồng cổ đông",
    "dhcd": "đại hội đồng cổ đông",
    "dhđcd": "đại hội đồng cổ đông",
    "hđqt": "hội đồng quản trị",
    "hdqt": "hội đồng quản trị",
    "bctc": "báo cáo tài chính",
    "ctcp": "công ty cổ phần",
    "cp": "cổ phiếu",
    "tnhh": "trách nhiệm hữu hạn",
    "ubcknn": "ủy ban chứng khoán nhà nước",
    "ttck": "thị trường chứng khoán",
}


@dataclass(frozen=True)
class VietnamesePreprocessingConfig:
    enabled: bool = True
    use_viet_normalizer: bool = True
    use_domain_fallbacks: bool = True


@dataclass(frozen=True)
class VietnamesePreprocessingResult:
    normalized_text: str
    version: str
    tools: JsonDict
    warnings: list[str]

    def to_metadata(self) -> JsonDict:
        return asdict(self)


def preprocess_vietnamese_text(
    text: str,
    *,
    config: VietnamesePreprocessingConfig | None = None,
) -> VietnamesePreprocessingResult:
    """Normalize Vietnamese financial text without changing natural word boundaries."""
    resolved_config = config or VietnamesePreprocessingConfig()
    normalized = normalize_text(text)
    warnings: list[str] = []
    tools: JsonDict = {
        "unicode_normalizer": "python_unicodedata_nfc",
        "viet_normalizer": None,
        "domain_normalizer": None,
    }
    if not resolved_config.enabled:
        return VietnamesePreprocessingResult(
            normalized_text=normalized,
            version=PREPROCESSING_VERSION,
            tools=tools,
            warnings=["vietnamese_preprocessing_disabled"],
        )

    if resolved_config.use_viet_normalizer:
        viet_result = _normalize_with_vietnormalizer(normalized)
        if viet_result is None:
            warnings.append("vietnormalizer_unavailable")
        else:
            normalized = normalize_text(viet_result)
            tools["viet_normalizer"] = "vietnormalizer"

    if resolved_config.use_domain_fallbacks:
        normalized = _normalize_financial_domain_text(normalized)
        tools["domain_normalizer"] = "finevent_financial_rules"

    return VietnamesePreprocessingResult(
        normalized_text=normalized,
        version=PREPROCESSING_VERSION,
        tools=tools,
        warnings=warnings,
    )


def _normalize_with_vietnormalizer(text: str) -> str | None:
    normalizer = _vietnormalizer_callable()
    if normalizer is None:
        return None
    try:
        protected_text, preserved_tokens = _protect_financial_tokens(text)
        normalized = str(normalizer(protected_text))
        return _restore_financial_tokens(normalized, preserved_tokens)
    except Exception:
        return None


def _protect_financial_tokens(text: str) -> tuple[str, dict[str, str]]:
    preserved: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        placeholder = f"zzfineventpreserve{len(preserved)}zz"
        preserved[placeholder] = match.group(0)
        return placeholder

    return PRESERVED_TOKEN_RE.sub(replace, text), preserved


def _restore_financial_tokens(text: str, preserved_tokens: dict[str, str]) -> str:
    restored = text
    for placeholder, original in preserved_tokens.items():
        restored = restored.replace(placeholder, original)
    return restored


@lru_cache(maxsize=1)
def _vietnormalizer_callable() -> Any | None:
    try:
        module = importlib.import_module("vietnormalizer")
    except ImportError:
        return None
    for function_name in ("normalize", "normalize_text", "text_normalize"):
        function = getattr(module, function_name, None)
        if callable(function):
            return _wrap_vietnormalizer_call(function)
    for class_name in (
        "VietnameseNormalizer",
        "VietNormalizer",
        "TextNormalizer",
        "Normalizer",
    ):
        normalizer_class = getattr(module, class_name, None)
        if normalizer_class is None:
            continue
        init_attempts = (
            {"enable_transliteration": False},
            {},
        )
        instance = None
        for init_kwargs in init_attempts:
            try:
                instance = normalizer_class(**init_kwargs)
                break
            except Exception:
                continue
        if instance is None:
            continue
        for method_name in ("normalize", "normalize_text", "text_normalize"):
            method = getattr(instance, method_name, None)
            if callable(method):
                return _wrap_vietnormalizer_call(method)
    return None


def _wrap_vietnormalizer_call(function: Any) -> Any:
    def normalize(text: str) -> str:
        try:
            return str(
                function(
                    text,
                    enable_preprocessing=False,
                    enable_transliteration=False,
                )
            )
        except TypeError:
            try:
                return str(function(text, enable_preprocessing=False))
            except TypeError:
                return str(function(text))

    return normalize


def _normalize_financial_domain_text(text: str) -> str:
    normalized = normalize_text(text)
    normalized = _expand_financial_abbreviations(normalized)
    normalized = _normalize_financial_numbers(normalized)
    normalized = _normalize_currency_units(normalized)
    return normalize_text(normalized)


def _expand_financial_abbreviations(text: str) -> str:
    normalized = text
    for abbreviation, replacement in sorted(
        FINANCIAL_ABBREVIATIONS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        normalized = re.sub(
            rf"(?<!\w){re.escape(abbreviation)}(?!\w)",
            replacement,
            normalized,
            flags=re.IGNORECASE,
        )
    return normalized


def _normalize_financial_numbers(text: str) -> str:
    normalized = re.sub(
        r"(?<!\w)(\d{1,3}(?:\.\d{3})+)(,\d+)?",
        _normalize_thousand_grouped_number,
        text,
    )
    normalized = re.sub(
        (
            r"(?<!\w)(\d+),(\d+)"
            r"(?=\s*(?:%|tỷ|ty|triệu|trieu|nghìn|nghin|đồng|dong|vnd|vnđ))"
        ),
        r"\1.\2",
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized


def _normalize_thousand_grouped_number(match: re.Match[str]) -> str:
    integer = match.group(1).replace(".", "")
    decimal = match.group(2)
    if decimal:
        return integer + "." + decimal.lstrip(",")
    return integer


def _normalize_currency_units(text: str) -> str:
    normalized = re.sub(r"(?<=\d)\s*(?:vnđ|vnd|đ)\b", " đồng", text, flags=re.IGNORECASE)
    normalized = re.sub(r"\btr\.?\s*đ\b", "triệu đồng", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\btỷ\s*đ\b", "tỷ đồng", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bty\s*đ\b", "tỷ đồng", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\btr\.?\s*vnd\b", "triệu đồng", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\btỷ\s*vnd\b", "tỷ đồng", normalized, flags=re.IGNORECASE)
    return normalized
