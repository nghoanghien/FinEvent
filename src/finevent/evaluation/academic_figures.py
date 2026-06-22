"""Academic-quality matplotlib/seaborn figures for evaluation reports."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from finevent.evaluation.metrics import aggregate_error_rows, choose_best_config
from finevent.evaluation.models import GoldRecord
from finevent.types import JsonDict, PathLike

QUALITY_METRICS = [
    ("Event F1", "event_detection_f1"),
    ("Type macro-F1", "event_type_macro_f1"),
    ("Slot F1", "slot_f1"),
    ("JSON valid", "json_validity_rate"),
    ("Schema valid", "schema_compliance_rate"),
]
RETRIEVAL_METRICS = [
    ("Recall@1", "recall_at_1"),
    ("Recall@3", "recall_at_3"),
    ("Recall@5", "recall_at_5"),
    ("Recall@10", "recall_at_10"),
    ("MRR", "mrr"),
    ("nDCG@10", "ndcg_at_10"),
]
GROUNDING_METRICS = [
    ("Evidence coverage", "evidence_coverage"),
    ("Unsupported fields", "pre_verification_hallucination_rate"),
    ("Unsupported events", "unsupported_event_rate"),
    ("Groundedness", "groundedness_score"),
]
PRIMARY_COLOR = "#2563eb"
SECONDARY_COLOR = "#0891b2"
WARNING_COLOR = "#f59e0b"
NEGATIVE_COLOR = "#dc2626"
NEUTRAL_COLOR = "#64748b"


def write_academic_figure_suite(
    *,
    output_dir: PathLike,
    gold_records: dict[str, GoldRecord],
    metrics_rows: list[JsonDict],
    hallucination_rows: list[JsonDict],
    error_rows: list[JsonDict],
    per_event_type_rows: list[JsonDict],
    detailed_rows: list[JsonDict],
    retrieval_metrics_rows: list[JsonDict] | None = None,
) -> dict[str, Path]:
    """Generate publication-friendly PNG/SVG figures from evaluation artifacts."""

    pd, plt, sns = _load_plotting_stack()
    _configure_theme(sns)

    output_path = Path(output_dir)
    figures_dir = output_path / "figures_academic"
    figures_dir.mkdir(parents=True, exist_ok=True)

    article_rows = _article_rows(gold_records)
    event_rows = _event_rows(gold_records)
    paths: dict[str, Path] = {
        "figures_dir": figures_dir,
        "academic_charts_summary": output_path / "academic_charts_summary.md",
    }

    figure_specs = [
        (
            "articles_by_source",
            "dataset/articles_by_source",
            lambda base: _plot_top_count(
                pd,
                plt,
                sns,
                rows=article_rows,
                column="source",
                base_path=base,
                title="Số bài báo theo nguồn dữ liệu",
                xlabel="Số bài báo",
                ylabel="Nguồn",
                color=PRIMARY_COLOR,
            ),
        ),
        (
            "articles_by_date",
            "dataset/articles_by_date",
            lambda base: _plot_date_counts(
                pd,
                plt,
                sns,
                rows=article_rows,
                base_path=base,
                title="Số bài báo theo ngày công bố/thu thập",
            ),
        ),
        (
            "ticker_frequency_top20",
            "dataset/ticker_frequency_top20",
            lambda base: _plot_top_count(
                pd,
                plt,
                sns,
                rows=event_rows,
                column="ticker",
                base_path=base,
                title="Top mã cổ phiếu xuất hiện trong gold labels",
                xlabel="Số sự kiện",
                ylabel="Ticker",
                color=SECONDARY_COLOR,
                top_n=20,
            ),
        ),
        (
            "event_type_distribution",
            "dataset/event_type_distribution",
            lambda base: _plot_top_count(
                pd,
                plt,
                sns,
                rows=event_rows,
                column="event_type",
                base_path=base,
                title="Phân bố loại sự kiện tài chính",
                xlabel="Số sự kiện",
                ylabel="Event type",
                color=PRIMARY_COLOR,
                top_n=24,
            ),
        ),
        (
            "polarity_distribution",
            "dataset/polarity_distribution",
            lambda base: _plot_top_count(
                pd,
                plt,
                sns,
                rows=event_rows,
                column="impact_sentiment",
                base_path=base,
                title="Phân bố chiều hướng tác động",
                xlabel="Số sự kiện",
                ylabel="Impact sentiment",
                color=WARNING_COLOR,
            ),
        ),
        (
            "argument_field_coverage",
            "dataset/argument_field_coverage",
            lambda base: _plot_argument_field_coverage(
                pd,
                plt,
                sns,
                event_rows=event_rows,
                base_path=base,
            ),
        ),
        (
            "retrieval_metrics_comparison",
            "retrieval/retrieval_metrics_comparison",
            lambda base: _plot_metric_comparison(
                pd,
                plt,
                sns,
                rows=retrieval_metrics_rows or [],
                group_column="retrieval_config",
                metric_fields=RETRIEVAL_METRICS,
                base_path=base,
                title="So sánh chất lượng retrieval theo cấu hình",
                empty_message="Chưa có retrieval metrics để vẽ biểu đồ.",
            ),
        ),
        (
            "recall_at_k_curve",
            "retrieval/recall_at_k_curve",
            lambda base: _plot_recall_curve(
                pd,
                plt,
                sns,
                rows=retrieval_metrics_rows or [],
                base_path=base,
            ),
        ),
        (
            "retrieval_ablation",
            "retrieval/retrieval_ablation",
            lambda base: _plot_retrieval_ablation(
                pd,
                plt,
                sns,
                rows=retrieval_metrics_rows or [],
                base_path=base,
            ),
        ),
        (
            "retrieval_failure_by_event_type",
            "retrieval/retrieval_failure_by_event_type",
            lambda base: _plot_retrieval_failure_proxy(
                pd,
                plt,
                sns,
                rows=per_event_type_rows,
                base_path=base,
            ),
        ),
        (
            "extraction_overview",
            "extraction/extraction_overview",
            lambda base: _plot_metric_comparison(
                pd,
                plt,
                sns,
                rows=metrics_rows,
                group_column="config_name",
                metric_fields=QUALITY_METRICS,
                base_path=base,
                title="Chất lượng extraction tổng thể",
                empty_message="Chưa có extraction metrics để vẽ biểu đồ.",
            ),
        ),
        (
            "per_event_type_f1",
            "extraction/per_event_type_f1",
            lambda base: _plot_event_type_f1(
                pd,
                plt,
                sns,
                rows=per_event_type_rows,
                base_path=base,
            ),
        ),
        (
            "gold_vs_pred_event_type",
            "extraction/gold_vs_pred_event_type",
            lambda base: _plot_gold_pred_counts(
                pd,
                plt,
                sns,
                rows=per_event_type_rows,
                base_path=base,
            ),
        ),
        (
            "error_distribution",
            "extraction/error_distribution",
            lambda base: _plot_error_distribution(
                pd,
                plt,
                sns,
                error_rows=error_rows,
                base_path=base,
            ),
        ),
        (
            "schema_error_breakdown",
            "extraction/schema_error_breakdown",
            lambda base: _plot_schema_error_breakdown(
                pd,
                plt,
                sns,
                error_rows=error_rows,
                base_path=base,
            ),
        ),
        (
            "grounding_metrics",
            "verification/grounding_metrics",
            lambda base: _plot_metric_comparison(
                pd,
                plt,
                sns,
                rows=hallucination_rows,
                group_column="config_name",
                metric_fields=GROUNDING_METRICS,
                base_path=base,
                title="Grounding và hallucination metrics",
                empty_message="Chưa có verification metrics để vẽ biểu đồ.",
            ),
        ),
        (
            "unsupported_fields",
            "verification/unsupported_fields",
            lambda base: _plot_unsupported_fields(
                pd,
                plt,
                sns,
                error_rows=error_rows,
                base_path=base,
            ),
        ),
        (
            "verification_before_after",
            "verification/verification_before_after",
            lambda base: _plot_verification_before_after(
                pd,
                plt,
                sns,
                rows=hallucination_rows,
                base_path=base,
            ),
        ),
        (
            "evidence_coverage_by_config",
            "verification/evidence_coverage_by_config",
            lambda base: _plot_metric_comparison(
                pd,
                plt,
                sns,
                rows=hallucination_rows,
                group_column="config_name",
                metric_fields=[("Evidence coverage", "evidence_coverage")],
                base_path=base,
                title="Evidence coverage theo cấu hình extraction",
                empty_message="Chưa có evidence coverage để vẽ biểu đồ.",
            ),
        ),
        (
            "final_quality_dashboard",
            "final_quality_dashboard",
            lambda base: _plot_final_dashboard(
                pd,
                plt,
                metrics_rows=metrics_rows,
                hallucination_rows=hallucination_rows,
                error_rows=error_rows,
                retrieval_metrics_rows=retrieval_metrics_rows or [],
                base_path=base,
            ),
        ),
    ]

    figure_links: list[tuple[str, Path]] = []
    for key, relative_base, writer in figure_specs:
        base_path = figures_dir / relative_base
        png_path = writer(base_path)
        paths[key] = png_path
        figure_links.append((key, png_path))

    paths["academic_charts_summary"].write_text(
        _build_academic_summary(output_path, figure_links),
        encoding="utf-8",
    )
    return paths


def _load_plotting_stack() -> tuple[Any, Any, Any]:
    try:
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
        import pandas as pd
        import seaborn as sns
    except ImportError as exc:
        raise RuntimeError(
            "Academic figures require the evaluation extras: "
            "`python -m pip install -e .[evaluation]` or install pandas, matplotlib, seaborn."
        ) from exc
    return pd, plt, sns


def _configure_theme(sns: Any) -> None:
    sns.set_theme(
        context="notebook",
        style="whitegrid",
        palette=[PRIMARY_COLOR, SECONDARY_COLOR, WARNING_COLOR, NEGATIVE_COLOR, NEUTRAL_COLOR],
    )


def _article_rows(gold_records: dict[str, GoldRecord]) -> list[JsonDict]:
    rows: list[JsonDict] = []
    for article_id, record in sorted(gold_records.items()):
        source = _first_text(
            record.source_record,
            [
                "source",
                "source_name",
                "publisher",
                "domain",
                "site",
                "news_source",
            ],
        )
        date_value = _first_text(
            record.source_record,
            [
                "published_at",
                "published_date",
                "collected_at",
                "crawled_at",
                "created_at",
                "date",
            ],
        )
        rows.append(
            {
                "article_id": article_id,
                "source": source or "UNKNOWN",
                "published_date": _date_bucket(date_value) or "UNKNOWN",
                "document_label": record.document_label,
                "event_count": len(record.events),
            }
        )
    return rows


def _event_rows(gold_records: dict[str, GoldRecord]) -> list[JsonDict]:
    rows: list[JsonDict] = []
    for article_id, record in sorted(gold_records.items()):
        for event in record.events:
            arguments = event.get("event_arguments")
            argument_fields = (
                sorted(str(key) for key, value in arguments.items() if _has_value(value))
                if isinstance(arguments, dict)
                else []
            )
            rows.append(
                {
                    "article_id": article_id,
                    "ticker": _clean_category(event.get("ticker") or event.get("company_name")),
                    "event_type": _clean_category(event.get("event_type")),
                    "event_subtype": _clean_category(event.get("event_subtype")),
                    "impact_sentiment": _clean_category(event.get("impact_sentiment")),
                    "argument_count": len(argument_fields),
                    "argument_fields": argument_fields,
                }
            )
    return rows


def _plot_top_count(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    rows: list[JsonDict],
    column: str,
    base_path: Path,
    title: str,
    xlabel: str,
    ylabel: str,
    color: str,
    top_n: int = 15,
) -> Path:
    frame = pd.DataFrame(rows)
    if frame.empty or column not in frame.columns:
        return _save_empty_plot(plt, base_path, title, f"Không có dữ liệu cho cột `{column}`.")
    counts = (
        frame[column]
        .fillna("UNKNOWN")
        .replace("", "UNKNOWN")
        .value_counts()
        .head(top_n)
        .rename_axis(column)
        .reset_index(name="count")
    )
    if counts.empty:
        return _save_empty_plot(plt, base_path, title, "Không có dữ liệu để vẽ.")

    height = max(4.2, 1.4 + 0.38 * len(counts))
    figure, axis = plt.subplots(figsize=(10.5, height))
    sns.barplot(data=counts, x="count", y=column, ax=axis, color=color)
    axis.set_title(title, fontsize=15, weight="bold", pad=14)
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    _annotate_horizontal_bars(axis)
    return _save_figure(plt, figure, base_path)


def _plot_date_counts(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    rows: list[JsonDict],
    base_path: Path,
    title: str,
) -> Path:
    frame = pd.DataFrame(rows)
    if frame.empty or "published_date" not in frame.columns:
        return _save_empty_plot(plt, base_path, title, "Không có metadata ngày công bố/thu thập.")
    filtered = frame[frame["published_date"].astype(str) != "UNKNOWN"]
    if filtered.empty:
        return _save_empty_plot(plt, base_path, title, "Metadata hiện tại chưa có ngày hợp lệ.")
    counts = (
        filtered["published_date"]
        .value_counts()
        .rename_axis("published_date")
        .reset_index(name="count")
        .sort_values("published_date")
    )

    figure, axis = plt.subplots(figsize=(12, 4.8))
    sns.lineplot(
        data=counts,
        x="published_date",
        y="count",
        marker="o",
        ax=axis,
        color=PRIMARY_COLOR,
    )
    axis.set_title(title, fontsize=15, weight="bold", pad=14)
    axis.set_xlabel("Ngày")
    axis.set_ylabel("Số bài báo")
    axis.tick_params(axis="x", rotation=35)
    return _save_figure(plt, figure, base_path)


def _plot_argument_field_coverage(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    event_rows: list[JsonDict],
    base_path: Path,
) -> Path:
    counter: Counter[str] = Counter()
    for row in event_rows:
        fields = row.get("argument_fields")
        if isinstance(fields, list):
            counter.update(str(field) for field in fields)
    if not counter:
        return _save_empty_plot(
            plt,
            base_path,
            "Độ phủ event arguments",
            "Gold labels hiện tại chưa có event_arguments đủ để thống kê.",
        )
    frame = pd.DataFrame(
        [{"argument_field": field, "count": count} for field, count in counter.most_common(24)]
    )
    height = max(4.2, 1.4 + 0.38 * len(frame))
    figure, axis = plt.subplots(figsize=(10.5, height))
    sns.barplot(data=frame, x="count", y="argument_field", ax=axis, color=SECONDARY_COLOR)
    axis.set_title("Độ phủ event arguments trong gold labels", fontsize=15, weight="bold", pad=14)
    axis.set_xlabel("Số lần xuất hiện")
    axis.set_ylabel("Argument field")
    _annotate_horizontal_bars(axis)
    return _save_figure(plt, figure, base_path)


def _plot_metric_comparison(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    rows: list[JsonDict],
    group_column: str,
    metric_fields: list[tuple[str, str]],
    base_path: Path,
    title: str,
    empty_message: str,
) -> Path:
    frame = pd.DataFrame(rows)
    available = [(label, field) for label, field in metric_fields if field in frame.columns]
    if frame.empty or group_column not in frame.columns or not available:
        return _save_empty_plot(plt, base_path, title, empty_message)
    for _, field in available:
        frame[field] = pd.to_numeric(frame[field], errors="coerce").fillna(0.0)
    long_frame = frame.melt(
        id_vars=[group_column],
        value_vars=[field for _, field in available],
        var_name="metric",
        value_name="value",
    )
    label_map = {field: label for label, field in available}
    long_frame["metric"] = long_frame["metric"].map(label_map)

    height = max(4.8, 1.8 + 0.42 * len(long_frame["metric"].unique()))
    figure, axis = plt.subplots(figsize=(11.5, height))
    sns.barplot(data=long_frame, x="value", y="metric", hue=group_column, ax=axis)
    axis.set_title(title, fontsize=15, weight="bold", pad=14)
    axis.set_xlabel("Giá trị metric")
    axis.set_ylabel("Metric")
    axis.set_xlim(0, max(1.0, float(long_frame["value"].max()) * 1.12))
    axis.legend(title=group_column, loc="lower right")
    _annotate_horizontal_bars(axis, decimals=3)
    return _save_figure(plt, figure, base_path)


def _plot_recall_curve(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    rows: list[JsonDict],
    base_path: Path,
) -> Path:
    frame = pd.DataFrame(rows)
    recall_fields = [
        ("1", "recall_at_1"),
        ("3", "recall_at_3"),
        ("5", "recall_at_5"),
        ("10", "recall_at_10"),
    ]
    available = [(k, field) for k, field in recall_fields if field in frame.columns]
    if frame.empty or "retrieval_config" not in frame.columns or not available:
        return _save_empty_plot(
            plt,
            base_path,
            "Recall@k của retrieval",
            "Chưa có đủ các cột recall_at_k để vẽ đường Recall@k.",
        )
    rows_for_plot = []
    for _, record in frame.iterrows():
        for k_value, field in available:
            rows_for_plot.append(
                {
                    "retrieval_config": record["retrieval_config"],
                    "k": int(k_value),
                    "recall": _to_float(record[field]),
                }
            )
    plot_frame = pd.DataFrame(rows_for_plot)

    figure, axis = plt.subplots(figsize=(10.5, 5.2))
    sns.lineplot(
        data=plot_frame,
        x="k",
        y="recall",
        hue="retrieval_config",
        marker="o",
        ax=axis,
    )
    axis.set_title("Recall@k theo cấu hình retrieval", fontsize=15, weight="bold", pad=14)
    axis.set_xlabel("k")
    axis.set_ylabel("Recall")
    axis.set_ylim(0, 1.05)
    axis.set_xticks(sorted(plot_frame["k"].unique()))
    return _save_figure(plt, figure, base_path)


def _plot_retrieval_ablation(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    rows: list[JsonDict],
    base_path: Path,
) -> Path:
    frame = pd.DataFrame(rows)
    metric = "ndcg_at_10" if "ndcg_at_10" in frame.columns else "recall_at_5"
    if frame.empty or "retrieval_config" not in frame.columns or metric not in frame.columns:
        return _save_empty_plot(
            plt,
            base_path,
            "Ablation retrieval",
            "Chưa có retrieval metrics để so sánh ablation.",
        )
    frame[metric] = pd.to_numeric(frame[metric], errors="coerce").fillna(0.0)
    frame = frame.sort_values(metric, ascending=True)

    figure, axis = plt.subplots(figsize=(10.5, max(4.5, 1.4 + 0.42 * len(frame))))
    sns.barplot(data=frame, x=metric, y="retrieval_config", ax=axis, color=PRIMARY_COLOR)
    axis.set_title(f"Ablation retrieval theo {metric}", fontsize=15, weight="bold", pad=14)
    axis.set_xlabel(metric)
    axis.set_ylabel("Retrieval config")
    axis.set_xlim(0, max(1.0, float(frame[metric].max()) * 1.12))
    _annotate_horizontal_bars(axis, decimals=3)
    return _save_figure(plt, figure, base_path)


def _plot_retrieval_failure_proxy(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    rows: list[JsonDict],
    base_path: Path,
) -> Path:
    frame = pd.DataFrame(rows)
    if frame.empty or "event_type" not in frame.columns or "fn" not in frame.columns:
        return _save_empty_plot(
            plt,
            base_path,
            "Event type có rủi ro miss cao",
            "Chưa có per-event-type false negative để vẽ biểu đồ.",
        )
    frame["fn"] = pd.to_numeric(frame["fn"], errors="coerce").fillna(0).astype(int)
    grouped = (
        frame.groupby("event_type", as_index=False)["fn"]
        .sum()
        .sort_values("fn", ascending=False)
    )
    grouped = grouped[grouped["fn"] > 0].head(20)
    if grouped.empty:
        return _save_empty_plot(
            plt,
            base_path,
            "Event type có rủi ro miss cao",
            "Không có false negative theo event type trong evaluation hiện tại.",
        )
    figure, axis = plt.subplots(figsize=(10.5, max(4.5, 1.4 + 0.42 * len(grouped))))
    sns.barplot(data=grouped, x="fn", y="event_type", ax=axis, color=NEGATIVE_COLOR)
    axis.set_title("Event type hay bị bỏ sót", fontsize=15, weight="bold", pad=14)
    axis.set_xlabel("False negative")
    axis.set_ylabel("Event type")
    _annotate_horizontal_bars(axis, decimals=0)
    return _save_figure(plt, figure, base_path)


def _plot_event_type_f1(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    rows: list[JsonDict],
    base_path: Path,
) -> Path:
    frame = pd.DataFrame(rows)
    if frame.empty or "event_type" not in frame.columns or "f1" not in frame.columns:
        return _save_empty_plot(plt, base_path, "F1 theo event type", "Chưa có per-event-type F1.")
    frame["f1"] = pd.to_numeric(frame["f1"], errors="coerce").fillna(0.0)
    frame = frame.sort_values(["f1", "event_type"], ascending=[True, True]).head(24)
    figure, axis = plt.subplots(figsize=(11.5, max(5.0, 1.4 + 0.42 * len(frame))))
    sns.barplot(data=frame, x="f1", y="event_type", hue="config_name", ax=axis)
    axis.set_title("F1 theo từng loại sự kiện", fontsize=15, weight="bold", pad=14)
    axis.set_xlabel("F1")
    axis.set_ylabel("Event type")
    axis.set_xlim(0, 1.05)
    _annotate_horizontal_bars(axis, decimals=3)
    return _save_figure(plt, figure, base_path)


def _plot_gold_pred_counts(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    rows: list[JsonDict],
    base_path: Path,
) -> Path:
    frame = pd.DataFrame(rows)
    required = {"event_type", "tp", "fp", "fn"}
    if frame.empty or not required.issubset(frame.columns):
        return _save_empty_plot(
            plt,
            base_path,
            "Gold vs predicted event counts",
            "Chưa có đủ TP/FP/FN theo event type.",
        )
    for column in ["tp", "fp", "fn"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).astype(int)
    grouped = frame.groupby("event_type", as_index=False)[["tp", "fp", "fn"]].sum()
    grouped["gold_count"] = grouped["tp"] + grouped["fn"]
    grouped["pred_count"] = grouped["tp"] + grouped["fp"]
    grouped = grouped.sort_values("gold_count", ascending=False).head(24)
    long_frame = grouped.melt(
        id_vars=["event_type"],
        value_vars=["gold_count", "pred_count"],
        var_name="series",
        value_name="count",
    )
    figure, axis = plt.subplots(figsize=(11.5, max(5.0, 1.4 + 0.42 * len(grouped))))
    sns.barplot(data=long_frame, x="count", y="event_type", hue="series", ax=axis)
    axis.set_title(
        "So sánh số lượng gold/predicted theo event type",
        fontsize=15,
        weight="bold",
        pad=14,
    )
    axis.set_xlabel("Số sự kiện")
    axis.set_ylabel("Event type")
    _annotate_horizontal_bars(axis, decimals=0)
    return _save_figure(plt, figure, base_path)


def _plot_error_distribution(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    error_rows: list[JsonDict],
    base_path: Path,
) -> Path:
    aggregated = aggregate_error_rows(error_rows)
    frame = pd.DataFrame(aggregated)
    if frame.empty:
        return _save_empty_plot(
            plt,
            base_path,
            "Phân bố lỗi extraction",
            "Không có lỗi trong batch hiện tại.",
        )
    frame["count"] = pd.to_numeric(frame["count"], errors="coerce").fillna(0).astype(int)
    frame = frame.sort_values("count", ascending=False)
    figure, axis = plt.subplots(figsize=(10.5, max(4.5, 1.4 + 0.42 * len(frame))))
    sns.barplot(data=frame, x="count", y="error_code", ax=axis, color=NEGATIVE_COLOR)
    axis.set_title("Phân bố lỗi extraction", fontsize=15, weight="bold", pad=14)
    axis.set_xlabel("Số lỗi")
    axis.set_ylabel("Error code")
    _annotate_horizontal_bars(axis, decimals=0)
    return _save_figure(plt, figure, base_path)


def _plot_schema_error_breakdown(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    error_rows: list[JsonDict],
    base_path: Path,
) -> Path:
    schema_related = {
        "E_INVALID_JSON",
        "E_SCHEMA_VIOLATION",
        "E_WRONG_TICKER",
        "E_WRONG_EVENT_TYPE",
        "E_WRONG_IMPACT",
        "E_UNSUPPORTED_ARGUMENT",
        "E_BAD_EVIDENCE",
    }
    selected = [
        row for row in error_rows if str(row.get("error_code") or "") in schema_related
    ]
    aggregated = aggregate_error_rows(selected)
    frame = pd.DataFrame(aggregated)
    if frame.empty:
        return _save_empty_plot(
            plt,
            base_path,
            "Schema và field-level error breakdown",
            "Không có lỗi schema/field-level trong batch hiện tại.",
        )
    frame["count"] = pd.to_numeric(frame["count"], errors="coerce").fillna(0).astype(int)
    frame = frame.sort_values("count", ascending=False)
    figure, axis = plt.subplots(figsize=(10.5, max(4.5, 1.4 + 0.42 * len(frame))))
    sns.barplot(data=frame, x="count", y="error_code", ax=axis, color=WARNING_COLOR)
    axis.set_title("Schema và field-level error breakdown", fontsize=15, weight="bold", pad=14)
    axis.set_xlabel("Số lỗi")
    axis.set_ylabel("Error code")
    _annotate_horizontal_bars(axis, decimals=0)
    return _save_figure(plt, figure, base_path)


def _plot_unsupported_fields(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    error_rows: list[JsonDict],
    base_path: Path,
) -> Path:
    fields = [
        str(row.get("details") or "UNKNOWN")
        for row in error_rows
        if row.get("error_code") == "E_UNSUPPORTED_ARGUMENT"
    ]
    counter = Counter(fields)
    if not counter:
        return _save_empty_plot(
            plt,
            base_path,
            "Unsupported fields",
            "Không có unsupported argument field trong verification hiện tại.",
        )
    frame = pd.DataFrame(
        [{"field": field, "count": count} for field, count in counter.most_common(20)]
    )
    figure, axis = plt.subplots(figsize=(10.5, max(4.5, 1.4 + 0.42 * len(frame))))
    sns.barplot(data=frame, x="count", y="field", ax=axis, color=NEGATIVE_COLOR)
    axis.set_title("Unsupported argument fields", fontsize=15, weight="bold", pad=14)
    axis.set_xlabel("Số lần bị đánh dấu unsupported")
    axis.set_ylabel("Field")
    _annotate_horizontal_bars(axis, decimals=0)
    return _save_figure(plt, figure, base_path)


def _plot_verification_before_after(
    pd: Any,
    plt: Any,
    sns: Any,
    *,
    rows: list[JsonDict],
    base_path: Path,
) -> Path:
    frame = pd.DataFrame(rows)
    required = {
        "config_name",
        "pre_verification_hallucination_rate",
        "post_verification_hallucination_rate",
    }
    if frame.empty or not required.issubset(frame.columns):
        return _save_empty_plot(
            plt,
            base_path,
            "Hallucination trước/sau verification",
            "Chưa có đủ pre/post verification metrics.",
        )
    for column in ["pre_verification_hallucination_rate", "post_verification_hallucination_rate"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
    long_frame = frame.melt(
        id_vars=["config_name"],
        value_vars=["pre_verification_hallucination_rate", "post_verification_hallucination_rate"],
        var_name="stage",
        value_name="hallucination_rate",
    )
    long_frame["stage"] = long_frame["stage"].map(
        {
            "pre_verification_hallucination_rate": "Before verification",
            "post_verification_hallucination_rate": "After verification",
        }
    )
    figure, axis = plt.subplots(figsize=(10.5, 5.2))
    sns.barplot(data=long_frame, x="hallucination_rate", y="config_name", hue="stage", ax=axis)
    axis.set_title("Hallucination rate trước/sau verification", fontsize=15, weight="bold", pad=14)
    axis.set_xlabel("Hallucination rate")
    axis.set_ylabel("Config")
    axis.set_xlim(0, max(1.0, float(long_frame["hallucination_rate"].max()) * 1.12))
    _annotate_horizontal_bars(axis, decimals=3)
    return _save_figure(plt, figure, base_path)


def _plot_final_dashboard(
    pd: Any,
    plt: Any,
    *,
    metrics_rows: list[JsonDict],
    hallucination_rows: list[JsonDict],
    error_rows: list[JsonDict],
    retrieval_metrics_rows: list[JsonDict],
    base_path: Path,
) -> Path:
    figure, axes = plt.subplots(2, 2, figsize=(15, 10))
    figure.suptitle("FinEvent-VN Evaluation Dashboard", fontsize=18, weight="bold")
    _draw_quality_panel(pd, axes[0][0], metrics_rows)
    _draw_retrieval_panel(pd, axes[0][1], retrieval_metrics_rows)
    _draw_error_panel(pd, axes[1][0], error_rows)
    _draw_grounding_panel(pd, axes[1][1], hallucination_rows)
    return _save_figure(plt, figure, base_path)


def _draw_quality_panel(pd: Any, axis: Any, rows: list[JsonDict]) -> None:
    best = choose_best_config(rows)
    if not best:
        _empty_axis(axis, "Extraction quality", "Không có metrics.")
        return
    labels = [label for label, _ in QUALITY_METRICS]
    values = [_to_float(best.get(field)) for _, field in QUALITY_METRICS]
    axis.barh(labels, values, color=PRIMARY_COLOR)
    axis.set_xlim(0, 1)
    axis.set_title(f"Best extraction config: {best.get('config_name', '')}")
    axis.set_xlabel("Score")
    _annotate_axis_bars(axis, decimals=3)


def _draw_retrieval_panel(pd: Any, axis: Any, rows: list[JsonDict]) -> None:
    frame = pd.DataFrame(rows)
    if frame.empty or "retrieval_config" not in frame.columns:
        _empty_axis(axis, "Retrieval quality", "Không có retrieval metrics.")
        return
    metric = "ndcg_at_10" if "ndcg_at_10" in frame.columns else "recall_at_5"
    if metric not in frame.columns:
        _empty_axis(axis, "Retrieval quality", "Thiếu nDCG@10/Recall@5.")
        return
    frame[metric] = pd.to_numeric(frame[metric], errors="coerce").fillna(0.0)
    frame = frame.sort_values(metric).tail(8)
    axis.barh(frame["retrieval_config"], frame[metric], color=SECONDARY_COLOR)
    axis.set_xlim(0, max(1.0, float(frame[metric].max()) * 1.12))
    axis.set_title(f"Retrieval comparison by {metric}")
    axis.set_xlabel(metric)
    _annotate_axis_bars(axis, decimals=3)


def _draw_error_panel(pd: Any, axis: Any, error_rows: list[JsonDict]) -> None:
    frame = pd.DataFrame(aggregate_error_rows(error_rows))
    if frame.empty:
        _empty_axis(axis, "Error distribution", "Không có lỗi.")
        return
    frame["count"] = pd.to_numeric(frame["count"], errors="coerce").fillna(0).astype(int)
    frame = frame.sort_values("count").tail(8)
    axis.barh(frame["error_code"], frame["count"], color=NEGATIVE_COLOR)
    axis.set_title("Top error codes")
    axis.set_xlabel("Count")
    _annotate_axis_bars(axis, decimals=0)


def _draw_grounding_panel(pd: Any, axis: Any, rows: list[JsonDict]) -> None:
    frame = pd.DataFrame(rows)
    available = [(label, field) for label, field in GROUNDING_METRICS if field in frame.columns]
    if frame.empty or not available:
        _empty_axis(axis, "Grounding metrics", "Không có verification metrics.")
        return
    best = choose_best_config(rows) or rows[0]
    labels = [label for label, _ in available]
    values = [_to_float(best.get(field)) for _, field in available]
    axis.barh(labels, values, color=WARNING_COLOR)
    axis.set_xlim(0, 1)
    axis.set_title(f"Grounding config: {best.get('config_name', '')}")
    axis.set_xlabel("Score / rate")
    _annotate_axis_bars(axis, decimals=3)


def _save_empty_plot(plt: Any, base_path: Path, title: str, message: str) -> Path:
    figure, axis = plt.subplots(figsize=(10.5, 4.2))
    _empty_axis(axis, title, message)
    return _save_figure(plt, figure, base_path)


def _empty_axis(axis: Any, title: str, message: str) -> None:
    axis.axis("off")
    axis.set_title(title, fontsize=15, weight="bold", pad=14)
    axis.text(
        0.5,
        0.5,
        message,
        ha="center",
        va="center",
        fontsize=12,
        color="#475569",
        transform=axis.transAxes,
    )


def _save_figure(plt: Any, figure: Any, base_path: Path) -> Path:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    png_path = base_path.with_suffix(".png")
    svg_path = base_path.with_suffix(".svg")
    figure.tight_layout()
    figure.savefig(png_path, dpi=180, bbox_inches="tight")
    figure.savefig(svg_path, bbox_inches="tight")
    plt.close(figure)
    return png_path


def _annotate_horizontal_bars(axis: Any, *, decimals: int = 0) -> None:
    for container in axis.containers:
        axis.bar_label(container, fmt=f"%.{decimals}f", padding=3, fontsize=9)


def _annotate_axis_bars(axis: Any, *, decimals: int = 0) -> None:
    for container in axis.containers:
        axis.bar_label(container, fmt=f"%.{decimals}f", padding=3, fontsize=9)


def _build_academic_summary(output_path: Path, figure_links: list[tuple[str, Path]]) -> str:
    lines = [
        "# Academic Charts Summary",
        "",
        "Bộ biểu đồ này được sinh bằng `pandas`, `matplotlib` và `seaborn` để phục vụ "
        "báo cáo học thuật, slide bảo vệ và dashboard quản trị. Các biểu đồ SVG nhẹ "
        "trong `charts_summary.md` vẫn được giữ cho report viewer tối giản.",
        "",
        "## Quick Reading Order",
        "",
        "1. `figures_academic/final_quality_dashboard.png` - dashboard tổng hợp kết quả.",
        "2. Nhóm `dataset/` - kiểm tra phân bố dữ liệu và gold labels.",
        "3. Nhóm `retrieval/` - đánh giá chất lượng tìm kiếm/ngữ cảnh.",
        "4. Nhóm `extraction/` - đánh giá extraction, schema và lỗi theo event type.",
        "5. Nhóm `verification/` - đánh giá groundedness và hallucination reduction.",
        "",
        "## Figures",
        "",
    ]
    for title, path in figure_links:
        relative = path.relative_to(output_path).as_posix()
        lines.extend([f"### {title}", "", f"![{title}]({relative})", ""])
    lines.extend(
        [
            "## Ghi chú",
            "",
            "- PNG dùng cho báo cáo/slide vì ổn định khi copy qua Word/PowerPoint.",
            "- SVG được sinh song song cùng tên để nhúng vào web/admin UI khi cần.",
            "- Nếu một biểu đồ báo thiếu dữ liệu, nguyên nhân thường là pipeline trước đó "
            "chưa sinh artifact tương ứng.",
        ]
    )
    return "\n".join(lines) + "\n"


def _first_text(record: JsonDict, keys: list[str]) -> str:
    for key in keys:
        value = record.get(key)
        if _has_value(value):
            return str(value)
        metadata = record.get("metadata")
        if isinstance(metadata, dict) and _has_value(metadata.get(key)):
            return str(metadata[key])
        article = record.get("article")
        if isinstance(article, dict) and _has_value(article.get(key)):
            return str(article[key])
    return ""


def _date_bucket(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    return stripped[:10]


def _clean_category(value: object) -> str:
    if not _has_value(value):
        return "UNKNOWN"
    return str(value).strip() or "UNKNOWN"


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _to_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0
