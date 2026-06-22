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


def write_markdown_report_suite(
    *,
    output_dir: PathLike,
    metrics_rows: list[JsonDict],
    hallucination_rows: list[JsonDict],
    error_rows: list[JsonDict],
    per_event_type_rows: list[JsonDict],
    detailed_rows: list[JsonDict],
    retrieval_metrics_rows: list[JsonDict] | None = None,
) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    paths = {
        "report_index": output_path / "report_index.md",
        "extraction_batch_summary": output_path / "extraction_batch_summary.md",
        "verification_summary": output_path / "verification_summary.md",
        "schema_error_summary": output_path / "schema_error_summary.md",
        "improvement_recommendations": output_path / "improvement_recommendations.md",
    }
    report_files = [
        "eval_summary.md",
        "metrics_by_run.csv",
        "per_event_type_metrics.csv",
        "hallucination_metrics.csv",
        "errors_by_type.csv",
        "error_examples.jsonl",
        "prediction_details.jsonl",
        "retrieval_metrics.csv",
        "retrieval_error_analysis.md",
        "pattern_library_summary.md",
        "pattern_metrics.csv",
    ]
    paths["report_index"].write_text(
        build_report_index(
            report_files=report_files,
            generated_reports=[
                path.name for path in paths.values() if path.name != "report_index.md"
            ],
        ),
        encoding="utf-8",
    )
    paths["extraction_batch_summary"].write_text(
        build_extraction_batch_summary(
            metrics_rows=metrics_rows,
            detailed_rows=detailed_rows,
            per_event_type_rows=per_event_type_rows,
        ),
        encoding="utf-8",
    )
    paths["verification_summary"].write_text(
        build_verification_summary(hallucination_rows=hallucination_rows),
        encoding="utf-8",
    )
    paths["schema_error_summary"].write_text(
        build_schema_error_summary(
            error_rows=error_rows,
            detailed_rows=detailed_rows,
            per_event_type_rows=per_event_type_rows,
        ),
        encoding="utf-8",
    )
    paths["improvement_recommendations"].write_text(
        build_improvement_recommendations(
            metrics_rows=metrics_rows,
            hallucination_rows=hallucination_rows,
            error_rows=error_rows,
            retrieval_metrics_rows=retrieval_metrics_rows or [],
        ),
        encoding="utf-8",
    )
    return paths


def build_report_index(*, report_files: list[str], generated_reports: list[str]) -> str:
    lines = [
        "# Report Index",
        "",
        "## Quick Reading Order",
        "",
        "1. `eval_summary.md` - tổng quan kết quả cuối cùng.",
        "2. `extraction_batch_summary.md` - chất lượng batch extraction M06.",
        "3. `verification_summary.md` - groundedness và hallucination reduction M07.",
        "4. `schema_error_summary.md` - lỗi schema, event type, argument và ticker.",
        "5. `improvement_recommendations.md` - ưu tiên cải thiện tiếp theo.",
        "6. `retrieval_metrics.csv` và `retrieval_error_analysis.md` - đánh giá retrieval M04.",
        "",
        "## Markdown Reports",
        "",
    ]
    for file_name in ["eval_summary.md", *generated_reports, "retrieval_error_analysis.md"]:
        if file_name in report_files or file_name in generated_reports:
            lines.append(f"- [{file_name}]({file_name})")

    lines.extend(["", "## Data Tables And Raw Artifacts", ""])
    for file_name in report_files:
        if file_name.endswith(".md"):
            continue
        lines.append(f"- [{file_name}]({file_name})")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Các report này được sinh lại khi chạy `finevent.evaluation run`.",
            "- Gold labels hiện là AI-generated và được accept sau automatic validation.",
            "- Dùng `error_examples.jsonl` để debug từng article/event cụ thể.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_extraction_batch_summary(
    *,
    metrics_rows: list[JsonDict],
    detailed_rows: list[JsonDict],
    per_event_type_rows: list[JsonDict],
) -> str:
    lines = [
        "# Extraction Batch Summary",
        "",
        "## Overview",
        "",
        "| Config | Articles | Gold Events | Pred Events | Matched | Event F1 | "
        "Type F1 | Slot F1 | JSON Valid | Schema Valid |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in metrics_rows:
        lines.append(
            "| {config_name} | {article_count} | {gold_event_count} | "
            "{predicted_event_count} | {matched_event_count} | {event_detection_f1} | "
            "{event_type_macro_f1} | {slot_f1} | {json_validity_rate} | "
            "{schema_compliance_rate} |".format(
                config_name=row.get("config_name", ""),
                article_count=row.get("article_count", 0),
                gold_event_count=row.get("gold_event_count", 0),
                predicted_event_count=row.get("predicted_event_count", 0),
                matched_event_count=row.get("matched_event_count", 0),
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
            "## Article-Level Outcome",
            "",
            "| Config | Articles | Perfect Count | Partial Count | Empty Prediction Count | "
            "Schema Error Count |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in _article_outcome_rows(detailed_rows):
        lines.append(
            "| {config_name} | {article_count} | {perfect_count} | {partial_count} | "
            "{empty_prediction_count} | {schema_error_count} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Weak Event Types",
            "",
            "| Config | Event Type | TP | FP | FN | Precision | Recall | F1 |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in _worst_event_type_rows(per_event_type_rows):
        lines.append(
            "| {config_name} | {event_type} | {tp} | {fp} | {fn} | {precision} | "
            "{recall} | {f1} |".format(
                config_name=row.get("config_name", ""),
                event_type=row.get("event_type", ""),
                tp=row.get("tp", 0),
                fp=row.get("fp", 0),
                fn=row.get("fn", 0),
                precision=_fmt(row.get("precision")),
                recall=_fmt(row.get("recall")),
                f1=_fmt(row.get("f1")),
            )
        )
    return "\n".join(lines) + "\n"


def build_verification_summary(*, hallucination_rows: list[JsonDict]) -> str:
    lines = [
        "# Verification And Grounding Summary",
        "",
        "## Overview",
        "",
        "| Config | Runs | Runs With Verification | Evidence Coverage | "
        "Unsupported Field Rate | Unsupported Event Rate | Groundedness |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in hallucination_rows:
        lines.append(
            "| {config_name} | {run_count} | {run_count_with_verification} | "
            "{evidence_coverage} | {unsupported_field_rate} | {unsupported_event_rate} | "
            "{groundedness_score} |".format(
                config_name=row.get("config_name", ""),
                run_count=row.get("run_count", 0),
                run_count_with_verification=row.get("run_count_with_verification", 0),
                evidence_coverage=_fmt(row.get("evidence_coverage")),
                unsupported_field_rate=_fmt(row.get("pre_verification_hallucination_rate")),
                unsupported_event_rate=_fmt(row.get("unsupported_event_rate")),
                groundedness_score=_fmt(row.get("groundedness_score")),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `Evidence Coverage` đo tỷ lệ event có evidence span được tìm thấy "
            "trong bài hoặc context.",
            "- `Unsupported Field Rate` cao nghĩa là argument/value được model sinh "
            "nhưng verification không tìm được bằng chứng.",
            "- `Unsupported Event Rate` cao nghĩa là có event bị xem là không đủ grounded.",
            "- `Groundedness` là chỉ báo tổng hợp để ưu tiên debug hallucination.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_schema_error_summary(
    *,
    error_rows: list[JsonDict],
    detailed_rows: list[JsonDict],
    per_event_type_rows: list[JsonDict],
) -> str:
    lines = [
        "# Schema And Error Summary",
        "",
        "## Error Codes",
        "",
        "| Error Code | Count |",
        "| --- | ---: |",
    ]
    for row in aggregate_error_rows(error_rows):
        lines.append(f"| {row.get('error_code')} | {row.get('count')} |")

    lines.extend(
        [
            "",
            "## Schema Health By Config",
            "",
            "| Config | Articles | JSON Invalid | Schema Invalid | "
            "Articles With No Matched Event |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in _article_outcome_rows(detailed_rows):
        lines.append(
            "| {config_name} | {article_count} | {json_invalid_count} | "
            "{schema_error_count} | {no_match_count} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## Most Affected Event Types",
            "",
            "| Config | Event Type | FN | FP | F1 |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in _worst_event_type_rows(per_event_type_rows):
        lines.append(
            "| {config_name} | {event_type} | {fn} | {fp} | {f1} |".format(
                config_name=row.get("config_name", ""),
                event_type=row.get("event_type", ""),
                fn=row.get("fn", 0),
                fp=row.get("fp", 0),
                f1=_fmt(row.get("f1")),
            )
        )
    return "\n".join(lines) + "\n"


def build_improvement_recommendations(
    *,
    metrics_rows: list[JsonDict],
    hallucination_rows: list[JsonDict],
    error_rows: list[JsonDict],
    retrieval_metrics_rows: list[JsonDict],
) -> str:
    best = choose_best_config(_merge_hallucination_into_metrics(metrics_rows, hallucination_rows))
    error_counts = {
        str(row.get("error_code")): int(row.get("count", 0))
        for row in aggregate_error_rows(error_rows)
    }
    retrieval_best = _best_retrieval_row(retrieval_metrics_rows)
    lines = [
        "# Improvement Recommendations",
        "",
        "## Current Reading",
        "",
    ]
    if best:
        lines.extend(
            [
                f"- Best extraction config: `{best.get('config_name')}`.",
                f"- Event F1: {_fmt(best.get('event_detection_f1'))}.",
                f"- Event type macro-F1: {_fmt(best.get('event_type_macro_f1'))}.",
                f"- Slot-F1: {_fmt(best.get('slot_f1'))}.",
                f"- Schema compliance: {_fmt(best.get('schema_compliance_rate'))}.",
                f"- Groundedness: {_fmt(best.get('groundedness_score'))}.",
            ]
        )
    if retrieval_best:
        lines.append(
            "- Best retrieval config: `{}` with Recall@5={}, MRR={}, nDCG@10={}.".format(
                retrieval_best.get("retrieval_config", ""),
                _fmt(retrieval_best.get("recall_at_5")),
                _fmt(retrieval_best.get("mrr")),
                _fmt(retrieval_best.get("ndcg_at_10")),
            )
        )

    lines.extend(["", "## Priority Fixes", ""])
    priorities = _priority_recommendations(best or {}, error_counts)
    for index, item in enumerate(priorities, start=1):
        lines.append(f"{index}. {item}")
    lines.extend(
        [
            "",
            "## Suggested Next Experiments",
            "",
            "- Add an event-candidate enumeration node before final JSON generation.",
            "- Compare smaller context windows versus more retrieved contexts.",
            "- Add schema repair focused on invalid subtype/argument keys.",
            "- Evaluate retrieval with a locked gold split where every article has gold labels.",
            "- Build ablation rows for: no retrieval, retrieval only, pattern only, full workflow.",
        ]
    )
    return "\n".join(lines) + "\n"


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


def _article_outcome_rows(detailed_rows: list[JsonDict]) -> list[JsonDict]:
    grouped: dict[str, list[JsonDict]] = {}
    for row in detailed_rows:
        grouped.setdefault(str(row.get("config_name") or ""), []).append(row)
    rows: list[JsonDict] = []
    for config_name, items in sorted(grouped.items()):
        perfect_count = 0
        partial_count = 0
        empty_prediction_count = 0
        schema_error_count = 0
        json_invalid_count = 0
        no_match_count = 0
        for item in items:
            matched = int(item.get("matched_event_count") or 0)
            gold_count = int(item.get("gold_event_count") or 0)
            pred_count = int(item.get("pred_event_count") or 0)
            schema_valid = int(item.get("schema_valid") or 0)
            json_valid = int(item.get("json_valid") or 0)
            if gold_count == pred_count == matched:
                perfect_count += 1
            elif matched > 0:
                partial_count += 1
            if pred_count == 0:
                empty_prediction_count += 1
            if not schema_valid:
                schema_error_count += 1
            if not json_valid:
                json_invalid_count += 1
            if gold_count > 0 and matched == 0:
                no_match_count += 1
        rows.append(
            {
                "config_name": config_name,
                "article_count": len(items),
                "perfect_count": perfect_count,
                "partial_count": partial_count,
                "empty_prediction_count": empty_prediction_count,
                "schema_error_count": schema_error_count,
                "json_invalid_count": json_invalid_count,
                "no_match_count": no_match_count,
            }
        )
    return rows


def _worst_event_type_rows(rows: list[JsonDict], limit: int = 8) -> list[JsonDict]:
    return sorted(
        rows,
        key=lambda row: (
            float(row.get("f1") or 0.0),
            -int(row.get("fn") or 0),
            -int(row.get("fp") or 0),
        ),
    )[:limit]


def _best_retrieval_row(rows: list[JsonDict]) -> JsonDict | None:
    if not rows:
        return None
    return max(
        rows,
        key=lambda row: (
            _float(row.get("recall_at_5")),
            _float(row.get("mrr")),
            _float(row.get("ndcg_at_10")),
        ),
    )


def _priority_recommendations(best: JsonDict, error_counts: dict[str, int]) -> list[str]:
    recommendations: list[str] = []
    if error_counts.get("E_MISSED_EVENT", 0) > 0:
        recommendations.append(
            "Reduce missed events by adding an explicit event-candidate enumeration step."
        )
    if error_counts.get("E_NO_EVENT_FALSE_POSITIVE", 0) > 0:
        recommendations.append(
            "Add a stricter event/no-event gate before final extraction."
        )
    if error_counts.get("E_UNSUPPORTED_ARGUMENT", 0) > 0:
        recommendations.append(
            "Improve argument grounding by requiring each argument to cite an evidence span."
        )
    if _float(best.get("schema_compliance_rate")) < 0.98:
        recommendations.append(
            "Strengthen schema repair for event subtype, argument keys and required fields."
        )
    if _float(best.get("event_type_macro_f1")) < 0.6:
        recommendations.append(
            "Improve event taxonomy classification with subtype-specific prompts or a classifier."
        )
    if not recommendations:
        recommendations.append("Run ablation studies to identify the next bottleneck.")
    return recommendations


def _float(value: object) -> float:
    if not isinstance(value, int | float | str) or isinstance(value, bool):
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _fmt(value: object) -> str:
    if not isinstance(value, int | float | str) or isinstance(value, bool):
        return "0.0000"
    try:
        return f"{float(value):.4f}"
    except ValueError:
        return "0.0000"
