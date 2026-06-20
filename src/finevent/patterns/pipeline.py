"""Milestone 05 pattern library build pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from finevent.jsonl import read_jsonl, write_jsonl
from finevent.patterns.builder import build_patterns_from_gold
from finevent.patterns.embeddings import embed_patterns_with_cache
from finevent.patterns.evaluation import (
    build_pattern_library_summary,
    evaluate_pattern_store,
    write_pattern_metrics_csv,
)
from finevent.patterns.store import PatternStore
from finevent.rag.embeddings import build_embedding_client
from finevent.types import PathLike


@dataclass(frozen=True)
class PatternBuildResult:
    articles_path: Path
    gold_path: Path
    patterns_path: Path
    rejected_patterns_path: Path
    embeddings_path: Path
    metrics_path: Path
    report_path: Path
    pattern_count: int
    rejected_pattern_count: int
    embedding_count: int


def run_pattern_library_build(
    *,
    articles_path: PathLike = "data/processed/articles_clean.jsonl",
    gold_path: PathLike = "data/labels/events_gold.jsonl",
    patterns_output_path: PathLike = "data/patterns/patterns.jsonl",
    rejected_patterns_output_path: PathLike = "data/patterns/patterns_rejected.jsonl",
    embeddings_output_path: PathLike = "data/patterns/pattern_embeddings.jsonl",
    embedding_cache_path: PathLike = "data/patterns/pattern_embedding_cache.jsonl",
    metrics_path: PathLike = "reports/evaluation/pattern_metrics.csv",
    report_path: PathLike = "reports/evaluation/pattern_library_summary.md",
    embedding_provider: str = "hash",
    embedding_model: str | None = None,
    embedding_dimension: int = 128,
) -> PatternBuildResult:
    articles = read_jsonl(articles_path)
    gold_records = read_jsonl(gold_path)
    articles_by_id = {str(article.get("article_id")): article for article in articles}

    all_patterns = build_patterns_from_gold(
        gold_records=gold_records,
        articles_by_id=articles_by_id,
    )
    valid_patterns = [pattern for pattern in all_patterns if not _has_validation_error(pattern)]
    rejected_patterns = [pattern for pattern in all_patterns if _has_validation_error(pattern)]

    write_jsonl(patterns_output_path, (pattern.to_dict() for pattern in valid_patterns))
    write_jsonl(
        rejected_patterns_output_path,
        (pattern.to_dict() for pattern in rejected_patterns),
    )

    client = build_embedding_client(
        provider=embedding_provider,
        model_name=embedding_model,
        dimension=embedding_dimension,
    )
    embeddings = embed_patterns_with_cache(
        valid_patterns,
        client=client,
        output_path=embeddings_output_path,
        cache_path=embedding_cache_path,
    )
    store = PatternStore(
        patterns=valid_patterns,
        embeddings_by_pattern={record.pattern_id: record for record in embeddings},
    )
    metrics = evaluate_pattern_store(store=store, patterns=valid_patterns)
    write_pattern_metrics_csv(metrics_path, metrics)
    _write_text(report_path, build_pattern_library_summary(metrics))

    return PatternBuildResult(
        articles_path=Path(articles_path),
        gold_path=Path(gold_path),
        patterns_path=Path(patterns_output_path),
        rejected_patterns_path=Path(rejected_patterns_output_path),
        embeddings_path=Path(embeddings_output_path),
        metrics_path=Path(metrics_path),
        report_path=Path(report_path),
        pattern_count=len(valid_patterns),
        rejected_pattern_count=len(rejected_patterns),
        embedding_count=len(embeddings),
    )


def _has_validation_error(pattern: object) -> bool:
    validation_errors = getattr(pattern, "validation_errors", [])
    return any(issue.get("severity") == "error" for issue in validation_errors)


def _write_text(path: PathLike, content: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
