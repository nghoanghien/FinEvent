"""Pattern library evaluation and reporting helpers."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from finevent.patterns.models import PatternCandidate, PatternRecord
from finevent.patterns.querying import build_pattern_query_from_pattern
from finevent.patterns.store import PatternStore
from finevent.types import JsonDict, PathLike


def evaluate_pattern_store(
    *,
    store: PatternStore,
    patterns: list[PatternRecord],
    k_values: tuple[int, ...] = (3, 5),
) -> JsonDict:
    detailed_rows = _build_detailed_rows(store=store, patterns=patterns, k_values=k_values)
    event_patterns = [pattern for pattern in patterns if pattern.document_label == "HAS_EVENT"]
    event_types = {pattern.event_type for pattern in event_patterns if pattern.event_type}
    event_subtypes = {pattern.event_subtype for pattern in event_patterns if pattern.event_subtype}
    metrics: JsonDict = {
        "metric_scope": "pattern_selection_default",
        "pattern_count": len(patterns),
        "event_pattern_count": len(event_patterns),
        "no_event_pattern_count": sum(
            1 for pattern in patterns if pattern.document_label == "NO_EVENT"
        ),
        "event_type_coverage": len(event_types),
        "event_subtype_coverage": len(event_subtypes),
        "avg_selected_patterns": _mean(float(row["selected_count"]) for row in detailed_rows),
        "mrr": _mean(float(row["reciprocal_rank"]) for row in detailed_rows),
    }
    for k in k_values:
        metrics[f"same_type_recall_at_{k}"] = _mean(
            float(row[f"same_type_hit_at_{k}"]) for row in detailed_rows
        )
        metrics[f"same_subtype_recall_at_{k}"] = _mean(
            float(row[f"same_subtype_hit_at_{k}"]) for row in detailed_rows
        )
    return metrics


def write_pattern_metrics_csv(path: PathLike, metrics: JsonDict) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(metrics.keys()))
        writer.writeheader()
        writer.writerow(metrics)
    return output_path


def build_pattern_library_summary(metrics: JsonDict) -> str:
    lines = [
        "# Pattern Library Summary",
        "",
        "## Overview",
        "",
        f"- Pattern count: {metrics.get('pattern_count', 0)}",
        f"- Event pattern count: {metrics.get('event_pattern_count', 0)}",
        f"- NO_EVENT pattern count: {metrics.get('no_event_pattern_count', 0)}",
        f"- Event type coverage: {metrics.get('event_type_coverage', 0)}",
        f"- Event subtype coverage: {metrics.get('event_subtype_coverage', 0)}",
        "",
        "## Selection Metrics",
        "",
        f"- MRR: {float(metrics.get('mrr', 0.0)):.4f}",
        f"- Same-type recall@3: {float(metrics.get('same_type_recall_at_3', 0.0)):.4f}",
        f"- Same-subtype recall@3: {float(metrics.get('same_subtype_recall_at_3', 0.0)):.4f}",
        "",
        "## Notes",
        "",
        "- Gold labels are AI-generated and accepted after automatic validation.",
        "- These metrics verify pattern library mechanics on local artifacts.",
    ]
    return "\n".join(lines) + "\n"


def _build_detailed_rows(
    *,
    store: PatternStore,
    patterns: list[PatternRecord],
    k_values: tuple[int, ...],
) -> list[JsonDict]:
    rows: list[JsonDict] = []
    max_k = max(k_values) if k_values else 5
    for pattern in patterns:
        query = build_pattern_query_from_pattern(pattern)
        candidates = store.select_patterns(query, top_k=max_k)
        row: JsonDict = {
            "pattern_id": pattern.pattern_id,
            "event_type": pattern.event_type,
            "event_subtype": pattern.event_subtype,
            "document_label": pattern.document_label,
            "selected_count": len(candidates),
            "reciprocal_rank": _reciprocal_rank(pattern, candidates),
        }
        for k in k_values:
            top_k = candidates[:k]
            row[f"same_type_hit_at_{k}"] = int(_has_same_event_type(pattern, top_k))
            row[f"same_subtype_hit_at_{k}"] = int(_has_same_event_subtype(pattern, top_k))
        rows.append(row)
    return rows


def _reciprocal_rank(pattern: PatternRecord, candidates: list[PatternCandidate]) -> float:
    for rank, candidate in enumerate(candidates, start=1):
        if candidate.pattern_id == pattern.pattern_id:
            return 1.0 / rank
    return 0.0


def _has_same_event_type(pattern: PatternRecord, candidates: list[PatternCandidate]) -> bool:
    for candidate in candidates:
        if pattern.document_label == "NO_EVENT" and candidate.document_label == "NO_EVENT":
            return True
        if pattern.event_type and candidate.event_type == pattern.event_type:
            return True
    return False


def _has_same_event_subtype(pattern: PatternRecord, candidates: list[PatternCandidate]) -> bool:
    for candidate in candidates:
        if pattern.document_label == "NO_EVENT" and candidate.document_label == "NO_EVENT":
            return True
        if pattern.event_subtype and candidate.event_subtype == pattern.event_subtype:
            return True
    return False


def _mean(values: Iterable[float]) -> float:
    collected = list(values)
    return sum(collected) / len(collected) if collected else 0.0
