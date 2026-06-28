"""Build gold-derived pattern records for chunk mapping."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from finevent.jsonl import read_jsonl, write_jsonl
from finevent.patterns.builder import build_patterns_from_gold
from finevent.types import JsonDict, PathLike


@dataclass(frozen=True)
class PatternBuildResult:
    articles_path: Path
    gold_path: Path
    patterns_path: Path
    rejected_patterns_path: Path
    metrics_path: Path
    report_path: Path
    pattern_count: int
    rejected_pattern_count: int


def run_pattern_library_build(
    *,
    articles_path: PathLike = "data/processed/articles_clean.jsonl",
    gold_path: PathLike = "data/labels/events_gold.jsonl",
    patterns_output_path: PathLike = "data/patterns/patterns.jsonl",
    rejected_patterns_output_path: PathLike = "data/patterns/patterns_rejected.jsonl",
    metrics_path: PathLike = "reports/evaluation/pattern_metrics.csv",
    report_path: PathLike = "reports/evaluation/pattern_library_summary.md",
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

    metrics = {
        "metric_scope": "pattern_library",
        "pattern_count": len(valid_patterns),
        "event_pattern_count": sum(1 for item in valid_patterns if item.pattern_kind == "event"),
        "no_event_pattern_count": sum(
            1 for item in valid_patterns if item.pattern_kind == "no_event"
        ),
        "rejected_pattern_count": len(rejected_patterns),
    }
    write_pattern_metrics_csv(metrics_path, metrics)
    _write_text(report_path, build_pattern_library_summary(metrics))

    return PatternBuildResult(
        articles_path=Path(articles_path),
        gold_path=Path(gold_path),
        patterns_path=Path(patterns_output_path),
        rejected_patterns_path=Path(rejected_patterns_output_path),
        metrics_path=Path(metrics_path),
        report_path=Path(report_path),
        pattern_count=len(valid_patterns),
        rejected_pattern_count=len(rejected_patterns),
    )


def _has_validation_error(pattern: object) -> bool:
    validation_errors = getattr(pattern, "validation_errors", [])
    return any(issue.get("severity") == "error" for issue in validation_errors)


def _write_text(path: PathLike, content: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def write_pattern_metrics_csv(path: PathLike, metrics: JsonDict) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(metrics))
        writer.writeheader()
        writer.writerow(metrics)
    return output_path


def build_pattern_library_summary(metrics: JsonDict) -> str:
    return "\n".join(
        [
            "# Pattern Record Summary",
            "",
            "## Overview",
            "",
            f"- Valid patterns: {metrics.get('pattern_count', 0)}",
            f"- Event patterns: {metrics.get('event_pattern_count', 0)}",
            f"- NO_EVENT patterns: {metrics.get('no_event_pattern_count', 0)}",
            f"- Rejected patterns: {metrics.get('rejected_pattern_count', 0)}",
            "",
            (
                "Patterns are attached to chunks during M03 and consumed through "
                "M04 retrieval contexts."
            ),
        ]
    )
