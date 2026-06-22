"""SVG chart generation for evaluation reports.

The project keeps chart generation dependency-free so evaluation can run in the
same minimal Python environment used by the pipeline. The generated SVG files are
static artifacts that Markdown reports and the future admin UI can render
directly.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from finevent.evaluation.metrics import aggregate_error_rows
from finevent.types import JsonDict, PathLike

PALETTE = [
    "#2563eb",
    "#16a34a",
    "#f59e0b",
    "#dc2626",
    "#7c3aed",
    "#0891b2",
    "#db2777",
    "#4b5563",
]


def write_chart_suite(
    *,
    output_dir: PathLike,
    metrics_rows: list[JsonDict],
    hallucination_rows: list[JsonDict],
    error_rows: list[JsonDict],
    per_event_type_rows: list[JsonDict],
    retrieval_metrics_rows: list[JsonDict] | None = None,
) -> dict[str, Path]:
    output_path = Path(output_dir)
    figures_dir = output_path / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "figures_dir": figures_dir,
        "charts_summary": output_path / "charts_summary.md",
        "extraction_metrics": figures_dir / "extraction_metrics.svg",
        "retrieval_metrics": figures_dir / "retrieval_metrics.svg",
        "error_distribution": figures_dir / "error_distribution.svg",
        "event_type_f1": figures_dir / "event_type_f1.svg",
        "grounding_metrics": figures_dir / "grounding_metrics.svg",
    }

    _write_svg(
        paths["extraction_metrics"],
        _metric_chart(
            title="Extraction Metrics",
            rows=metrics_rows,
            fields=[
                ("Event F1", "event_detection_f1"),
                ("Type macro-F1", "event_type_macro_f1"),
                ("Slot F1", "slot_f1"),
                ("JSON valid", "json_validity_rate"),
                ("Schema valid", "schema_compliance_rate"),
            ],
            label_key="config_name",
        ),
    )
    _write_svg(
        paths["retrieval_metrics"],
        _metric_chart(
            title="Retrieval Metrics",
            rows=retrieval_metrics_rows or [],
            fields=[
                ("Recall@5", "recall_at_5"),
                ("MRR", "mrr"),
                ("nDCG@10", "ndcg_at_10"),
            ],
            label_key="retrieval_config",
        ),
    )
    _write_svg(paths["error_distribution"], _error_distribution_chart(error_rows))
    _write_svg(paths["event_type_f1"], _event_type_f1_chart(per_event_type_rows))
    _write_svg(
        paths["grounding_metrics"],
        _metric_chart(
            title="Verification And Grounding Metrics",
            rows=hallucination_rows,
            fields=[
                ("Evidence coverage", "evidence_coverage"),
                ("Unsupported fields", "pre_verification_hallucination_rate"),
                ("Unsupported events", "unsupported_event_rate"),
                ("Groundedness", "groundedness_score"),
            ],
            label_key="config_name",
        ),
    )
    paths["charts_summary"].write_text(_build_charts_summary(), encoding="utf-8")
    return paths


def _metric_chart(
    *,
    title: str,
    rows: list[JsonDict],
    fields: list[tuple[str, str]],
    label_key: str,
) -> str:
    bars: list[tuple[str, float, str]] = []
    for row_index, row in enumerate(rows):
        group = str(row.get(label_key) or f"row_{row_index + 1}")
        for field_index, (label, field_name) in enumerate(fields):
            bars.append(
                (
                    f"{group} - {label}",
                    _float(row.get(field_name)),
                    PALETTE[field_index % len(PALETTE)],
                )
            )
    return _horizontal_bar_chart(
        title=title,
        bars=bars,
        max_value=1.0,
        empty_message="No metric rows available.",
    )


def _error_distribution_chart(error_rows: list[JsonDict]) -> str:
    aggregated = aggregate_error_rows(error_rows)
    bars = [
        (
            str(row.get("error_code") or "UNKNOWN"),
            float(int(row.get("count") or 0)),
            PALETTE[index % len(PALETTE)],
        )
        for index, row in enumerate(
            sorted(aggregated, key=lambda item: int(item.get("count") or 0), reverse=True)
        )
    ]
    max_value = max((value for _, value, _ in bars), default=1.0)
    return _horizontal_bar_chart(
        title="Error Distribution",
        bars=bars,
        max_value=max_value,
        value_format="{:.0f}",
        empty_message="No error rows available.",
    )


def _event_type_f1_chart(rows: list[JsonDict]) -> str:
    selected_rows = sorted(
        rows,
        key=lambda row: (
            _float(row.get("f1")),
            -int(row.get("fn") or 0),
            -int(row.get("fp") or 0),
        ),
    )[:12]
    bars = [
        (
            f"{row.get('config_name', '')} - {row.get('event_type', '')}".strip(" -"),
            _float(row.get("f1")),
            PALETTE[index % len(PALETTE)],
        )
        for index, row in enumerate(selected_rows)
    ]
    return _horizontal_bar_chart(
        title="Weak Event Type F1",
        bars=bars,
        max_value=1.0,
        empty_message="No per-event-type rows available.",
    )


def _horizontal_bar_chart(
    *,
    title: str,
    bars: list[tuple[str, float, str]],
    max_value: float,
    value_format: str = "{:.4f}",
    empty_message: str,
) -> str:
    width = 980
    margin_left = 300
    margin_right = 120
    margin_top = 76
    row_height = 34
    chart_width = width - margin_left - margin_right
    height = max(180, margin_top + 52 + row_height * max(len(bars), 1))
    max_value = max(max_value, 1e-9)

    parts = [
        _svg_header(width, height),
        f'<text x="24" y="36" class="title">{escape(title)}</text>',
        '<line x1="300" y1="56" x2="860" y2="56" class="axis" />',
    ]
    if not bars:
        parts.append(f'<text x="24" y="96" class="muted">{escape(empty_message)}</text>')
        parts.append("</svg>")
        return "\n".join(parts)

    for index, (label, raw_value, color) in enumerate(bars):
        value = max(raw_value, 0.0)
        bar_width = min(value / max_value, 1.0) * chart_width
        y = margin_top + index * row_height
        parts.extend(
            [
                f'<text x="24" y="{y + 16}" class="label">{escape(_shorten(label))}</text>',
                f'<rect x="{margin_left}" y="{y}" width="{chart_width}" height="18" '
                'rx="3" class="bar-bg" />',
                f'<rect x="{margin_left}" y="{y}" width="{bar_width:.2f}" height="18" '
                f'rx="3" fill="{color}" />',
                f'<text x="{margin_left + chart_width + 12}" y="{y + 14}" '
                f'class="value">{escape(value_format.format(raw_value))}</text>',
            ]
        )
    parts.append("</svg>")
    return "\n".join(parts)


def _svg_header(width: int, height: int) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        """
<style>
  svg { background: #ffffff; color: #111827; font-family: Inter, Arial, sans-serif; }
  .title { font-size: 22px; font-weight: 700; fill: #111827; }
  .label { font-size: 12px; fill: #374151; }
  .value { font-size: 12px; font-weight: 600; fill: #111827; }
  .muted { font-size: 13px; fill: #6b7280; }
  .axis { stroke: #d1d5db; stroke-width: 1; }
  .bar-bg { fill: #f3f4f6; }
</style>"""
    )


def _build_charts_summary() -> str:
    return """# Charts Summary

## Quick Reading Order

1. `figures/extraction_metrics.svg` - chất lượng extraction tổng thể.
2. `figures/retrieval_metrics.svg` - so sánh các cấu hình retrieval.
3. `figures/error_distribution.svg` - lỗi nào đang chiếm nhiều nhất.
4. `figures/event_type_f1.svg` - event type yếu nhất cần cải thiện.
5. `figures/grounding_metrics.svg` - groundedness và hallucination metrics.

## Extraction Metrics

![Extraction Metrics](figures/extraction_metrics.svg)

## Retrieval Metrics

![Retrieval Metrics](figures/retrieval_metrics.svg)

## Error Distribution

![Error Distribution](figures/error_distribution.svg)

## Weak Event Type F1

![Weak Event Type F1](figures/event_type_f1.svg)

## Verification And Grounding

![Verification And Grounding Metrics](figures/grounding_metrics.svg)

## Notes

- Các biểu đồ được sinh tự động khi chạy `finevent.evaluation run`.
- Biểu đồ dùng SVG tĩnh để đọc được trong Markdown, browser và admin dashboard.
- Dữ liệu nguồn vẫn là các file CSV/JSONL trong cùng thư mục `reports/evaluation/`.
"""

def _write_svg(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _shorten(value: str, max_length: int = 42) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3].rstrip() + "..."


def _float(value: object) -> float:
    if not isinstance(value, int | float | str) or isinstance(value, bool):
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0
