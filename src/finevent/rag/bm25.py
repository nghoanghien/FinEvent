"""Small BM25 implementation for offline lexical retrieval."""

from __future__ import annotations

import math
import pickle
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from finevent.rag.models import ChunkRecord
from finevent.rag.tokenization import retrieval_text_from_parts, tokenize_for_retrieval
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class Bm25SearchResult:
    chunk_id: str
    article_id: str
    score: float
    rank: int
    title: str | None
    chunk_level: str
    text_preview: str

    def to_dict(self) -> JsonDict:
        return asdict(self)


@dataclass
class Bm25Index:
    chunk_ids: list[str]
    article_ids: list[str]
    titles: list[str | None]
    chunk_levels: list[str]
    texts: list[str]
    tokenized_documents: list[list[str]]
    document_frequencies: dict[str, int]
    average_document_length: float
    k1: float = 1.5
    b: float = 0.75

    @classmethod
    def from_chunks(cls, chunks: list[ChunkRecord]) -> Bm25Index:
        tokenized_documents = [
            tokenize_for_retrieval(_retrieval_text(chunk)) for chunk in chunks
        ]
        document_frequencies: Counter[str] = Counter()
        for tokens in tokenized_documents:
            document_frequencies.update(set(tokens))
        average_document_length = (
            sum(len(tokens) for tokens in tokenized_documents) / len(tokenized_documents)
            if tokenized_documents
            else 0.0
        )
        return cls(
            chunk_ids=[chunk.chunk_id for chunk in chunks],
            article_ids=[chunk.article_id for chunk in chunks],
            titles=[chunk.title for chunk in chunks],
            chunk_levels=[chunk.chunk_level for chunk in chunks],
            texts=[chunk.text for chunk in chunks],
            tokenized_documents=tokenized_documents,
            document_frequencies=dict(document_frequencies),
            average_document_length=average_document_length,
        )

    def search(self, query: str, *, top_k: int = 5) -> list[Bm25SearchResult]:
        query_tokens = tokenize_for_retrieval(query)
        scored: list[tuple[int, float]] = []
        for index, document_tokens in enumerate(self.tokenized_documents):
            score = self._score(query_tokens, document_tokens)
            if score > 0:
                scored.append((index, score))
        scored.sort(key=lambda item: item[1], reverse=True)
        return [
            Bm25SearchResult(
                chunk_id=self.chunk_ids[index],
                article_id=self.article_ids[index],
                score=score,
                rank=rank,
                title=self.titles[index],
                chunk_level=self.chunk_levels[index],
                text_preview=self.texts[index][:240],
            )
            for rank, (index, score) in enumerate(scored[:top_k], start=1)
        ]

    def _score(self, query_tokens: list[str], document_tokens: list[str]) -> float:
        if not query_tokens or not document_tokens or self.average_document_length <= 0:
            return 0.0
        token_counts = Counter(document_tokens)
        document_length = len(document_tokens)
        score = 0.0
        total_documents = len(self.tokenized_documents)
        for token in query_tokens:
            term_frequency = token_counts[token]
            if term_frequency <= 0:
                continue
            doc_frequency = self.document_frequencies.get(token, 0)
            inverse_document_frequency = math.log(
                1 + (total_documents - doc_frequency + 0.5) / (doc_frequency + 0.5)
            )
            numerator = term_frequency * (self.k1 + 1)
            denominator = term_frequency + self.k1 * (
                1 - self.b + self.b * document_length / self.average_document_length
            )
            score += inverse_document_frequency * numerator / denominator
        return score


def build_bm25_index(chunks: list[ChunkRecord], output_path: PathLike) -> Bm25Index:
    index = Bm25Index.from_chunks(chunks)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as file:
        pickle.dump(index, file)
    return index


def load_bm25_index(path: PathLike) -> Bm25Index:
    with Path(path).open("rb") as file:
        loaded = pickle.load(file)
    if not isinstance(loaded, Bm25Index):
        raise ValueError(f"BM25 pickle does not contain Bm25Index: {path}")
    return loaded


def _retrieval_text(chunk: ChunkRecord) -> str:
    return retrieval_text_from_parts(
        title=chunk.title,
        text=chunk.text,
        metadata=chunk.metadata,
        tickers_hint=chunk.tickers_hint,
        company_names_hint=chunk.company_names_hint,
        event_keywords=chunk.event_keywords,
        event_type_hints=chunk.event_type_hints,
    )
