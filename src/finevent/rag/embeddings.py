"""Embedding clients and cache helpers for RAG preparation."""

from __future__ import annotations

import hashlib
import math
import os
from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from finevent.ingestion.text import text_hash
from finevent.jsonl import read_jsonl, write_jsonl
from finevent.logging_utils import utc_now_iso
from finevent.rag.models import ChunkRecord, EmbeddingRecord
from finevent.rag.tokenization import retrieval_text_from_parts, tokenize_for_retrieval
from finevent.types import JsonDict, PathLike

DEFAULT_HASH_EMBEDDING_MODEL = "local_hash_embedding_v1"


class EmbeddingClient(ABC):
    model_name: str
    dimension: int

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""


class HashEmbeddingClient(EmbeddingClient):
    """Deterministic local embedding for smoke tests and offline baselines."""

    def __init__(self, *, model_name: str = DEFAULT_HASH_EMBEDDING_MODEL, dimension: int = 128):
        self.model_name = model_name
        self.dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = tokenize_for_retrieval(text, remove_stopwords=False)
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], byteorder="big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [round(value / norm, 8) for value in vector]


class CloudflareEmbeddingClient(EmbeddingClient):
    """Cloudflare Workers AI embedding client.

    This client is intentionally imported lazily so the project can run tests
    without network dependencies. Required environment variables:

    - `CLOUDFLARE_ACCOUNT_ID`
    - `CLOUDFLARE_API_TOKEN`
    """

    def __init__(
        self,
        *,
        model_name: str,
        dimension: int,
        account_id: str | None = None,
        api_token: str | None = None,
        timeout_seconds: float = 30.0,
    ):
        self.model_name = model_name
        self.dimension = dimension
        self.account_id = account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID")
        self.api_token = api_token or os.getenv("CLOUDFLARE_API_TOKEN")
        self.timeout_seconds = timeout_seconds
        if not self.account_id or not self.api_token:
            raise ValueError("Cloudflare embedding requires CLOUDFLARE_ACCOUNT_ID and API token.")

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("Install the rag extra to use Cloudflare embeddings.") from exc

        url = (
            "https://api.cloudflare.com/client/v4/accounts/"
            f"{self.account_id}/ai/run/{self.model_name}"
        )
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {self.api_token}"},
            json={"text": texts},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        vectors = _extract_cloudflare_vectors(payload)
        if len(vectors) != len(texts):
            raise ValueError("Cloudflare embedding response count does not match request count.")
        return vectors


class LangChainEmbeddingClient(EmbeddingClient):
    """Embedding adapter for LangChain embedding objects."""

    def __init__(
        self,
        *,
        embedding_model: Any,
        model_name: str,
        dimension: int = 0,
    ):
        self.embedding_model = embedding_model
        self.model_name = model_name
        self.dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if hasattr(self.embedding_model, "embed_documents"):
            vectors = self.embedding_model.embed_documents(texts)
        elif hasattr(self.embedding_model, "embed_texts"):
            vectors = self.embedding_model.embed_texts(texts)
        else:
            raise TypeError("Embedding model must expose embed_documents or embed_texts.")
        return [[float(value) for value in vector] for vector in vectors]


def build_embedding_client(
    *,
    provider: str = "hash",
    model_name: str | None = None,
    dimension: int = 128,
) -> EmbeddingClient:
    if provider == "hash":
        return HashEmbeddingClient(
            model_name=model_name or DEFAULT_HASH_EMBEDDING_MODEL,
            dimension=dimension,
        )
    if provider == "cloudflare":
        return CloudflareEmbeddingClient(
            model_name=model_name or "@cf/baai/bge-m3",
            dimension=dimension,
        )
    if provider in {"openai_compatible", "langchain_openai", "direct_http"}:
        from finevent.llm import build_openai_compatible_embeddings_from_env

        embedding_model = build_openai_compatible_embeddings_from_env(
            model=model_name,
            provider="direct_http" if provider == "direct_http" else provider,
        )
        return LangChainEmbeddingClient(
            embedding_model=embedding_model,
            model_name=model_name
            or str(getattr(embedding_model, "model", "openai_compatible_embedding")),
            dimension=dimension,
        )
    raise ValueError(f"Unsupported embedding provider: {provider}")


def embed_chunks_with_cache(
    chunks: list[ChunkRecord],
    *,
    client: EmbeddingClient,
    output_path: PathLike,
    cache_path: PathLike,
    batch_size: int = 32,
) -> list[EmbeddingRecord]:
    cache = _load_embedding_cache(cache_path)
    records: list[EmbeddingRecord] = []
    missing_chunks: list[ChunkRecord] = []

    for chunk in chunks:
        embedding_text_hash = _embedding_text_hash(chunk)
        cache_key = _cache_key(client.model_name, embedding_text_hash)
        cached = cache.get(cache_key)
        if cached:
            records.append(_record_from_cache(chunk, cached, client=client))
        else:
            missing_chunks.append(chunk)

    for batch in _batched(missing_chunks, batch_size):
        embedding_texts = [_embedding_text(chunk) for chunk in batch]
        vectors = client.embed_texts(embedding_texts)
        for chunk, vector in zip(batch, vectors, strict=True):
            embedding_text_hash = text_hash(_embedding_text(chunk))
            record = EmbeddingRecord(
                embedding_id=_embedding_id(client.model_name, chunk.chunk_id),
                chunk_id=chunk.chunk_id,
                article_id=chunk.article_id,
                embedding_model=client.model_name,
                embedding_dimension=len(vector),
                content_hash=chunk.content_hash,
                chunk_hash=embedding_text_hash,
                vector=vector,
                status="success",
                created_at=utc_now_iso(),
                cache_hit=False,
            )
            records.append(record)
            cache[_cache_key(client.model_name, embedding_text_hash)] = record.to_dict()

    records.sort(key=lambda item: item.chunk_id)
    write_jsonl(output_path, (record.to_dict() for record in records))
    _write_embedding_cache(cache_path, cache.values())
    return records


def _load_embedding_cache(path: PathLike) -> dict[str, JsonDict]:
    cache_records = read_jsonl(path)
    cache: dict[str, JsonDict] = {}
    for record in cache_records:
        model = str(record.get("embedding_model") or "")
        chunk_hash = str(record.get("chunk_hash") or "")
        if model and chunk_hash and record.get("status") == "success":
            cache[_cache_key(model, chunk_hash)] = record
    return cache


def _embedding_text(chunk: ChunkRecord) -> str:
    return retrieval_text_from_parts(
        title=chunk.title,
        text=chunk.text,
        metadata=chunk.metadata,
        tickers_hint=chunk.tickers_hint,
        company_names_hint=chunk.company_names_hint,
        event_keywords=chunk.event_keywords,
        event_type_hints=chunk.event_type_hints,
    )


def _embedding_text_hash(chunk: ChunkRecord) -> str:
    return text_hash(_embedding_text(chunk))


def _write_embedding_cache(path: PathLike, records: Iterable[JsonDict]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    deduped: dict[str, JsonDict] = {}
    for record in records:
        key = _cache_key(str(record.get("embedding_model")), str(record.get("chunk_hash")))
        deduped[key] = record
    write_jsonl(output, deduped.values())


def _record_from_cache(
    chunk: ChunkRecord,
    cached: JsonDict,
    *,
    client: EmbeddingClient,
) -> EmbeddingRecord:
    vector = [float(value) for value in cached.get("vector", [])]
    return EmbeddingRecord(
        embedding_id=_embedding_id(client.model_name, chunk.chunk_id),
        chunk_id=chunk.chunk_id,
        article_id=chunk.article_id,
        embedding_model=client.model_name,
        embedding_dimension=len(vector),
        content_hash=chunk.content_hash,
        chunk_hash=chunk.chunk_hash,
        vector=vector,
        status="success",
        created_at=str(cached.get("created_at") or utc_now_iso()),
        cache_hit=True,
    )


def _extract_cloudflare_vectors(payload: JsonDict) -> list[list[float]]:
    result = payload.get("result") if isinstance(payload, dict) else None
    if isinstance(result, dict):
        data = result.get("data")
        if isinstance(data, list):
            return [[float(value) for value in vector] for vector in data]
    if isinstance(result, list):
        return [[float(value) for value in vector] for vector in result]
    raise ValueError("Unsupported Cloudflare embedding response shape.")


def _embedding_id(model_name: str, chunk_hash: str) -> str:
    digest = hashlib.sha1(f"{model_name}:{chunk_hash}".encode()).hexdigest()
    return f"emb_{digest[:16]}"


def _cache_key(model_name: str, chunk_hash: str) -> str:
    return f"{model_name}::{chunk_hash}"


def _batched(items: list[ChunkRecord], batch_size: int) -> Iterable[list[ChunkRecord]]:
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]
