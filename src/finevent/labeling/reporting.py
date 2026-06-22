"""Reporting helpers for AI-generated label validation."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from finevent.types import JsonDict, PathLike


def build_labeling_summary(
    *,
    ai_generated_records: list[JsonDict],
    gold_records: list[JsonDict],
    rejected_records: list[JsonDict],
) -> str:
    total = len(ai_generated_records)
    accepted_count = len(gold_records)
    strict_pass_count = sum(
        1 for record in gold_records if record.get("validation_status") == "PASS"
    )
    auto_accepted_with_issues = sum(
        1
        for record in gold_records
        if record.get("validation_status") == "AUTO_ACCEPTED_WITH_ISSUES"
    )
    rejected_count = len(rejected_records)
    document_label_counts = Counter(
        record.get("label", {}).get("document_label")
        for record in gold_records
        if record.get("label")
    )
    event_type_counts = Counter(
        event.get("event_type")
        for record in gold_records
        for event in record.get("label", {}).get("events", [])
    )
    subtype_counts = Counter(
        event.get("event_subtype")
        for record in gold_records
        for event in record.get("label", {}).get("events", [])
        if event.get("event_subtype")
    )
    sentiment_counts = Counter(
        event.get("impact_sentiment")
        for record in gold_records
        for event in record.get("label", {}).get("events", [])
    )
    rejected_error_counts = Counter(
        issue.get("code")
        for record in rejected_records
        for issue in record.get("validation_errors", [])
        if issue.get("severity", "error") == "error"
    )
    validation_issue_counts = Counter(
        issue.get("code")
        for record in ai_generated_records
        for issue in record.get("validation_errors", [])
        if issue.get("code")
    )
    warning_counts = Counter(
        issue.get("code")
        for record in ai_generated_records
        for issue in record.get("validation_errors", [])
        if issue.get("severity") == "warning"
    )

    lines = [
        "# AI Labeling Summary",
        "",
        "## Overview",
        "",
        f"- AI-generated label records: {total}",
        f"- Gold accepted count: {accepted_count}",
        f"- Strict validation pass count: {strict_pass_count}",
        f"- Auto-accepted with validation issues: {auto_accepted_with_issues}",
        f"- Rejected count: {rejected_count}",
        f"- Gold acceptance rate: {_rate(accepted_count, total):.2%}",
        f"- Strict validation pass rate: {_rate(strict_pass_count, total):.2%}",
        f"- Rejection rate: {_rate(rejected_count, total):.2%}",
        "",
        "## Document Labels In Gold Set",
        "",
        "| Document label | Count |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {label} | {count} |" for label, count in sorted(document_label_counts.items()))
    lines.extend(
        [
            "",
            "## Event Type Coverage In Gold Set",
            "",
            "| Event type | Count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(
        f"| {event_type} | {count} |" for event_type, count in event_type_counts.most_common()
    )
    lines.extend(
        [
            "",
            "## Event Subtype Coverage In Gold Set",
            "",
            "| Event subtype | Count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(f"| {subtype} | {count} |" for subtype, count in subtype_counts.most_common())
    lines.extend(
        [
            "",
            "## Impact Sentiment Distribution",
            "",
            "| Impact sentiment | Count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(
        f"| {sentiment} | {count} |" for sentiment, count in sentiment_counts.most_common()
    )
    lines.extend(
        [
            "",
            "## Validation Issues Across AI Labels",
            "",
            "| Validation issue | Count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(f"| {code} | {count} |" for code, count in validation_issue_counts.most_common())
    lines.extend(
        [
            "",
            "## Rejection Reasons",
            "",
            "| Validation error | Count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(f"| {code} | {count} |" for code, count in rejected_error_counts.most_common())
    lines.extend(
        [
            "",
            "## Validation Warnings",
            "",
            "| Warning | Count |",
            "| --- | ---: |",
        ]
    )
    lines.extend(f"| {code} | {count} |" for code, count in warning_counts.most_common())
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Parseable AI-generated labels are accepted as operational gold labels.",
            "- Validation issues are retained for audit and error analysis.",
            "- There is no human review step in this milestone.",
            (
                "- Rejected labels should be repaired by an AI repair prompt "
                "or regenerated by the teacher model."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_labeling_summary(path: PathLike, content: str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0
