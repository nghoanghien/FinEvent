"""Retrieval evaluation metrics and relevance set construction."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from finevent.jsonl import read_jsonl
from finevent.rag.models import ChunkRecord
from finevent.rag.pipeline import chunks_from_jsonl
from finevent.rag.tokenization import ascii_fold
from finevent.retrieval.models import RetrievalCandidate, RetrievalQuery
from finevent.retrieval.querying import build_queries_from_gold_label
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class RetrievalEvalCase:
    case_id: str
    article_id: str
    event_id: str
    queries: list[RetrievalQuery]
    relevant_chunk_ids: set[str]
    evidence_span: str
    event_type: str | None
    article_event_types: set[str] = field(default_factory=set)
    article_event_relevant_chunk_ids: dict[str, set[str]] = field(default_factory=dict)


def build_eval_cases_from_gold(
    *,
    gold_path: PathLike,
    chunks_path: PathLike,
) -> list[RetrievalEvalCase]:
    gold_records = read_jsonl(gold_path)
    chunks = chunks_from_jsonl(chunks_path)
    chunks_by_article: dict[str, list[ChunkRecord]] = {}
    for chunk in chunks:
        chunks_by_article.setdefault(chunk.article_id, []).append(chunk)

    cases: list[RetrievalEvalCase] = []
    for gold_record in gold_records:
        label = (
            gold_record.get("label")
            if isinstance(gold_record.get("label"), dict)
            else gold_record
        )
        if not isinstance(label, dict):
            continue
        queries = build_queries_from_gold_label(gold_record)
        article_event_types: set[str] = set()
        article_event_relevant_chunk_ids: dict[str, set[str]] = {}
        event_rows = [event for event in label.get("events", []) if isinstance(event, dict)]
        for event_index, event in enumerate(event_rows):
            article_id = str(label.get("article_id") or gold_record.get("article_id"))
            event_id = str(event.get("event_id") or f"{article_id}_event_{event_index:02d}")
            event_type = str(event.get("event_type") or "").upper()
            if event_type:
                article_event_types.add(event_type)
            event_relevant_chunks = _relevant_chunks_for_event(
                chunks_by_article.get(article_id, []),
                evidence_span=str(event.get("evidence_span") or ""),
            )
            if not event_relevant_chunks:
                event_relevant_chunks = {
                    chunk.chunk_id
                    for chunk in chunks_by_article.get(article_id, [])
                    if chunk.chunk_level == "document"
                }
            article_event_relevant_chunk_ids[event_id] = event_relevant_chunks
        for event_index, event in enumerate(event_rows):
            article_id = str(label.get("article_id") or gold_record.get("article_id"))
            event_id = str(event.get("event_id") or f"{article_id}_event_{event_index:02d}")
            evidence_span = str(event.get("evidence_span") or "")
            relevant_chunk_ids = _relevant_chunks_for_event(
                chunks_by_article.get(article_id, []),
                evidence_span=evidence_span,
            )
            if not relevant_chunk_ids:
                relevant_chunk_ids = {
                    chunk.chunk_id
                    for chunk in chunks_by_article.get(article_id, [])
                    if chunk.chunk_level == "document"
                }
            cases.append(
                RetrievalEvalCase(
                    case_id=event_id,
                    article_id=article_id,
                    event_id=event_id,
                    queries=queries,
                    relevant_chunk_ids=relevant_chunk_ids,
                    evidence_span=evidence_span,
                    event_type=event.get("event_type"),
                    article_event_types=article_event_types,
                    article_event_relevant_chunk_ids=article_event_relevant_chunk_ids,
                )
            )
    return cases


def evaluate_results(
    *,
    candidates: list[RetrievalCandidate],
    relevant_chunk_ids: set[str],
    k_values: tuple[int, ...] = (5, 10),
    event_types: set[str] | None = None,
    event_relevant_chunk_ids: dict[str, set[str]] | None = None,
) -> JsonDict:
    retrieved_ids = [candidate.chunk_id for candidate in candidates]
    relevant_count = len(relevant_chunk_ids)
    metrics: JsonDict = {}
    for k in k_values:
        top_k = retrieved_ids[:k]
        hits = sum(1 for chunk_id in top_k if chunk_id in relevant_chunk_ids)
        metrics[f"recall_at_{k}"] = hits / relevant_count if relevant_count else 0.0
        metrics[f"precision_at_{k}"] = hits / k if k else 0.0
        metrics[f"ndcg_at_{k}"] = _ndcg_at_k(top_k, relevant_chunk_ids, k)
        metrics.update(
            _context_diversity_metrics(
                candidates[:k],
                retrieved_ids=top_k,
                event_types=event_types or set(),
                event_relevant_chunk_ids=event_relevant_chunk_ids or {},
                k=k,
            )
        )
    metrics["mrr"] = _mrr(retrieved_ids, relevant_chunk_ids)
    metrics["first_relevant_rank"] = _first_relevant_rank(retrieved_ids, relevant_chunk_ids)
    return metrics


def aggregate_metric_rows(rows: list[JsonDict]) -> list[JsonDict]:
    grouped: dict[str, list[JsonDict]] = {}
    for row in rows:
        grouped.setdefault(str(row["retrieval_config"]), []).append(row)

    aggregated: list[JsonDict] = []
    metric_names = [
        "recall_at_5",
        "recall_at_10",
        "precision_at_5",
        "precision_at_10",
        "mrr",
        "ndcg_at_5",
        "ndcg_at_10",
        "event_type_coverage_at_5",
        "event_type_coverage_at_10",
        "event_evidence_coverage_at_5",
        "event_evidence_coverage_at_10",
        "unique_event_types_at_5",
        "unique_event_types_at_10",
        "dominance_ratio_at_5",
        "dominance_ratio_at_10",
    ]
    for config_name, config_rows in sorted(grouped.items()):
        output: JsonDict = {
            "retrieval_config": config_name,
            "case_count": len(config_rows),
        }
        for metric_name in metric_names:
            output[metric_name] = _mean(float(row.get(metric_name, 0.0)) for row in config_rows)
        aggregated.append(output)
    return aggregated


def write_metrics_csv(path: PathLike, rows: list[JsonDict]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return output_path
    fieldnames = list(rows[0].keys())
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def build_error_analysis(
    *,
    detailed_rows: list[JsonDict],
    top_misses: int = 20,
) -> str:
    missed = [
        row
        for row in detailed_rows
        if float(row.get("recall_at_5", 0.0)) <= 0.0
        and str(row.get("retrieval_config")) != "aggregate"
    ]
    lines = [
        "# Retrieval Error Analysis",
        "",
        "## Overview",
        "",
        f"- Evaluated rows: {len(detailed_rows)}",
        f"- Missed cases at top 5: {len(missed)}",
        "",
        "## Top Misses",
        "",
        "| Retrieval config | Case ID | Event type | First relevant rank |",
        "| --- | --- | --- | ---: |",
    ]
    for row in missed[:top_misses]:
        lines.append(
            "| {retrieval_config} | {case_id} | {event_type} | {first_relevant_rank} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Misses here mean no relevant evidence chunk appeared in top 5.",
            "- With a tiny fixture corpus, metrics mainly verify pipeline correctness.",
            (
                "- On the real corpus, compare BM25, dense, hybrid, metadata-aware "
                "and reranked configs."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def load_chunks_for_eval(path: PathLike) -> list[ChunkRecord]:
    return chunks_from_jsonl(path)


def _relevant_chunks_for_event(chunks: list[ChunkRecord], *, evidence_span: str) -> set[str]:
    if not evidence_span:
        return set()
    folded_evidence = ascii_fold(evidence_span).lower()
    relevant: set[str] = set()
    for chunk in chunks:
        folded_text = ascii_fold(chunk.text).lower()
        if folded_evidence in folded_text:
            relevant.add(chunk.chunk_id)
    return relevant


def _context_diversity_metrics(
    candidates: list[RetrievalCandidate],
    *,
    retrieved_ids: list[str],
    event_types: set[str],
    event_relevant_chunk_ids: dict[str, set[str]],
    k: int,
) -> JsonDict:
    candidate_event_types = [
        _candidate_event_types(candidate, event_types) for candidate in candidates
    ]
    covered_event_types = set().union(*candidate_event_types) if candidate_event_types else set()
    event_type_count = len(event_types)
    event_evidence_hits = sum(
        1
        for relevant_chunk_ids in event_relevant_chunk_ids.values()
        if set(retrieved_ids) & relevant_chunk_ids
    )
    event_counter: dict[str, int] = {}
    for types_for_candidate in candidate_event_types:
        for event_type in types_for_candidate:
            event_counter[event_type] = event_counter.get(event_type, 0) + 1
    mention_count = sum(event_counter.values())
    dominance_ratio = max(event_counter.values()) / mention_count if mention_count else 0.0
    return {
        f"event_type_coverage_at_{k}": (
            len(covered_event_types & event_types) / event_type_count if event_type_count else 0.0
        ),
        f"event_evidence_coverage_at_{k}": (
            event_evidence_hits / len(event_relevant_chunk_ids)
            if event_relevant_chunk_ids
            else 0.0
        ),
        f"unique_event_types_at_{k}": len(covered_event_types),
        f"dominance_ratio_at_{k}": dominance_ratio,
    }


def _candidate_event_types(
    candidate: RetrievalCandidate,
    gold_event_types: set[str],
) -> set[str]:
    matched_intent_types = {
        str(event_type).upper()
        for event_type in candidate.score_breakdown.get("matched_intent_event_types", [])
        if event_type
    }
    metadata_types = {
        str(event_type).upper()
        for event_type in candidate.metadata.get("event_type_hints", [])
        if event_type
    }
    event_types = matched_intent_types or metadata_types
    if gold_event_types:
        matched = event_types & gold_event_types
        if matched:
            return matched
    return event_types


def _mrr(retrieved_ids: list[str], relevant_chunk_ids: set[str]) -> float:
    rank = _first_relevant_rank(retrieved_ids, relevant_chunk_ids)
    return 1 / rank if rank else 0.0


def _first_relevant_rank(retrieved_ids: list[str], relevant_chunk_ids: set[str]) -> int:
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_chunk_ids:
            return rank
    return 0


def _ndcg_at_k(retrieved_ids: list[str], relevant_chunk_ids: set[str], k: int) -> float:
    dcg = 0.0
    for index, chunk_id in enumerate(retrieved_ids[:k], start=1):
        gain = 1.0 if chunk_id in relevant_chunk_ids else 0.0
        dcg += gain / math.log2(index + 1)
    ideal_hits = min(len(relevant_chunk_ids), k)
    ideal_dcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def _mean(values: Iterable[float]) -> float:
    collected = list(values)
    return sum(collected) / len(collected) if collected else 0.0
