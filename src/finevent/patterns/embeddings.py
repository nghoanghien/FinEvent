"""Embedding helpers for event pattern records."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

from finevent.ingestion.text import text_hash
from finevent.jsonl import read_jsonl, write_jsonl
from finevent.logging_utils import utc_now_iso
from finevent.patterns.models import PatternEmbeddingRecord, PatternRecord
from finevent.rag.embeddings import EmbeddingClient
from finevent.types import JsonDict, PathLike


def embed_patterns_with_cache(
    patterns: list[PatternRecord],
    *,
    client: EmbeddingClient,
    output_path: PathLike,
    cache_path: PathLike,
    batch_size: int = 32,
) -> list[PatternEmbeddingRecord]:
    cache = _load_embedding_cache(cache_path)
    records: list[PatternEmbeddingRecord] = []
    missing_patterns: list[tuple[PatternRecord, str]] = []

    for pattern in patterns:
        pattern_hash = text_hash(pattern.pattern_text)
        cached = cache.get(_cache_key(client.model_name, pattern_hash))
        if cached:
            records.append(_record_from_cache(pattern, pattern_hash, cached, client=client))
        else:
            missing_patterns.append((pattern, pattern_hash))

    for batch in _batched(missing_patterns, batch_size):
        vectors = client.embed_texts([pattern.pattern_text for pattern, _ in batch])
        for (pattern, pattern_hash), vector in zip(batch, vectors, strict=True):
            record = PatternEmbeddingRecord(
                embedding_id=_embedding_id(client.model_name, pattern_hash),
                pattern_id=pattern.pattern_id,
                embedding_model=client.model_name,
                embedding_dimension=len(vector),
                pattern_hash=pattern_hash,
                vector=vector,
                status="success",
                created_at=utc_now_iso(),
                cache_hit=False,
            )
            records.append(record)
            cache[_cache_key(client.model_name, pattern_hash)] = record.to_dict()

    records.sort(key=lambda item: item.pattern_id)
    write_jsonl(output_path, (record.to_dict() for record in records))
    _write_embedding_cache(cache_path, cache.values())
    return records


def _load_embedding_cache(path: PathLike) -> dict[str, JsonDict]:
    cache_records = read_jsonl(path)
    cache: dict[str, JsonDict] = {}
    for record in cache_records:
        model = str(record.get("embedding_model") or "")
        pattern_hash = str(record.get("pattern_hash") or "")
        if model and pattern_hash and record.get("status") == "success":
            cache[_cache_key(model, pattern_hash)] = record
    return cache


def _write_embedding_cache(path: PathLike, records: Iterable[JsonDict]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    deduped: dict[str, JsonDict] = {}
    for record in records:
        key = _cache_key(str(record.get("embedding_model")), str(record.get("pattern_hash")))
        deduped[key] = record
    write_jsonl(output, deduped.values())


def _record_from_cache(
    pattern: PatternRecord,
    pattern_hash: str,
    cached: JsonDict,
    *,
    client: EmbeddingClient,
) -> PatternEmbeddingRecord:
    vector = [float(value) for value in cached.get("vector", [])]
    return PatternEmbeddingRecord(
        embedding_id=str(
            cached.get("embedding_id") or _embedding_id(client.model_name, pattern_hash)
        ),
        pattern_id=pattern.pattern_id,
        embedding_model=client.model_name,
        embedding_dimension=len(vector),
        pattern_hash=pattern_hash,
        vector=vector,
        status="success",
        created_at=str(cached.get("created_at") or utc_now_iso()),
        cache_hit=True,
    )


def _embedding_id(model_name: str, pattern_hash: str) -> str:
    digest = hashlib.sha1(f"{model_name}:{pattern_hash}".encode()).hexdigest()
    return f"pattern_emb_{digest[:16]}"


def _cache_key(model_name: str, pattern_hash: str) -> str:
    return f"{model_name}::{pattern_hash}"


def _batched(
    items: list[tuple[PatternRecord, str]],
    batch_size: int,
) -> Iterable[list[tuple[PatternRecord, str]]]:
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]
