"""Report writers for evaluation and ablation outputs."""

from __future__ import annotations

import csv
from pathlib import Path

from finevent.evaluation.metrics import aggregate_error_rows, choose_best_config
from finevent.jsonl import write_jsonl
from finevent.types import JsonDict, PathLike


def write_csv(path: PathLike, rows: list[JsonDict]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _fieldnames(rows)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        if not fieldnames:
            file.write("")
            return output_path
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return output_path


def write_error_outputs(
    *,
    errors_by_type_path: PathLike,
    error_examples_path: PathLike,
    error_rows: list[JsonDict],
) -> tuple[Path, Path]:
    summary_path = write_csv(errors_by_type_path, aggregate_error_rows(error_rows))
    examples_path = Path(error_examples_path)
    write_jsonl(examples_path, error_rows)
    return summary_path, examples_path


def build_evaluation_summary(
    *,
    metrics_rows: list[JsonDict],
    hallucination_rows: list[JsonDict],
    error_rows: list[JsonDict],
    retrieval_metrics_rows: list[JsonDict] | None = None,
) -> str:
    best = choose_best_config(_merge_hallucination_into_metrics(metrics_rows, hallucination_rows))
    error_summary = aggregate_error_rows(error_rows)
    retrieval_rows = retrieval_metrics_rows or []

    lines = [
        "# Evaluation Summary",
        "",
        "## Overview",
        "",
        f"- Evaluated configs: {len(metrics_rows)}",
        f"- Total error examples: {len(error_rows)}",
        f"- Retrieval metric rows loaded: {len(retrieval_rows)}",
    ]
    if best:
        lines.extend(
            [
                f"- Best config: `{best.get('config_name')}`",
                f"- Best event type macro-F1: {_fmt(best.get('event_type_macro_f1'))}",
                f"- Best slot-F1: {_fmt(best.get('slot_f1'))}",
                f"- Best groundedness score: {_fmt(best.get('groundedness_score'))}",
            ]
        )

    lines.extend(
        [
            "",
            "## Metrics By Config",
            "",
            "| Config | Articles | Event F1 | Type Macro-F1 | Slot F1 | "
            "JSON Valid | Schema Valid |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in metrics_rows:
        lines.append(
            "| {config_name} | {article_count} | {event_detection_f1} | "
            "{event_type_macro_f1} | {slot_f1} | {json_validity_rate} | "
            "{schema_compliance_rate} |".format(
                config_name=row.get("config_name", ""),
                article_count=row.get("article_count", 0),
                event_detection_f1=_fmt(row.get("event_detection_f1")),
                event_type_macro_f1=_fmt(row.get("event_type_macro_f1")),
                slot_f1=_fmt(row.get("slot_f1")),
                json_validity_rate=_fmt(row.get("json_validity_rate")),
                schema_compliance_rate=_fmt(row.get("schema_compliance_rate")),
            )
        )

    lines.extend(
        [
            "",
            "## Hallucination Metrics",
            "",
            "| Config | Evidence Coverage | Unsupported Field Rate | "
            "Unsupported Event Rate | Groundedness |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in hallucination_rows:
        lines.append(
            "| {config_name} | {evidence_coverage} | {unsupported_field_rate} | "
            "{unsupported_event_rate} | {groundedness_score} |".format(
                config_name=row.get("config_name", ""),
                evidence_coverage=_fmt(row.get("evidence_coverage")),
                unsupported_field_rate=_fmt(row.get("pre_verification_hallucination_rate")),
                unsupported_event_rate=_fmt(row.get("unsupported_event_rate")),
                groundedness_score=_fmt(row.get("groundedness_score")),
            )
        )

    lines.extend(
        [
            "",
            "## Error Analysis",
            "",
            "| Error Code | Count |",
            "| --- | ---: |",
        ]
    )
    for row in error_summary:
        lines.append(f"| {row.get('error_code')} | {row.get('count')} |")

    if retrieval_rows:
        lines.extend(
            [
                "",
                "## Retrieval Metrics",
                "",
                "| Retrieval Config | Recall@5 | MRR | nDCG@10 |",
                "| --- | ---: | ---: | ---: |",
            ]
        )
        for row in retrieval_rows:
            lines.append(
                "| {retrieval_config} | {recall_at_5} | {mrr} | {ndcg_at_10} |".format(
                    retrieval_config=row.get("retrieval_config", ""),
                    recall_at_5=_fmt(row.get("recall_at_5")),
                    mrr=_fmt(row.get("mrr")),
                    ndcg_at_10=_fmt(row.get("ndcg_at_10")),
                )
            )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Gold labels are AI-generated and accepted after automatic validation.",
            "- Metrics measure agreement with AI-generated gold labels, not human expert labels.",
            "- Ablation configs should be compared on the same locked test split.",
        ]
    )
    return "\n".join(lines) + "\n"


def _merge_hallucination_into_metrics(
    metrics_rows: list[JsonDict],
    hallucination_rows: list[JsonDict],
) -> list[JsonDict]:
    hallucination_by_config = {
        str(row.get("config_name")): row for row in hallucination_rows
    }
    merged = []
    for row in metrics_rows:
        config_name = str(row.get("config_name"))
        merged.append({**row, **hallucination_by_config.get(config_name, {})})
    return merged


def _fieldnames(rows: list[JsonDict]) -> list[str]:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames


def _fmt(value: object) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return "0.0000"
