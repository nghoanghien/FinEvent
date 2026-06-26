"""M01 Ingestion node specification."""

from __future__ import annotations

from finevent.api.workflow_registry.config_helpers import (
    bool_config,
    float_config,
    int_config,
    optional_str_config,
    str_config,
)
from finevent.api.workflow_registry.types import (
    BuildContext,
    WorkflowFieldSpec,
    WorkflowNodeSpec,
    WorkflowStep,
)


def build_steps(context: BuildContext) -> list[WorkflowStep]:
    config = context.config
    command = [
        context.python,
        "-m",
        "finevent.ingestion",
        "--input-html-dir",
        str_config(config, "input_html_dir", "data/raw/html"),
        "--raw-output-path",
        str_config(config, "raw_output_path", "data/raw/articles_raw.jsonl"),
        "--clean-output-path",
        str_config(config, "articles_path", "data/processed/articles_clean.jsonl"),
        "--report-path",
        str_config(config, "data_quality_report_path", "reports/data/data_quality_summary.md"),
        "--min-text-chars",
        str(int_config(config, "min_text_chars", 300)),
    ]
    if bool_config(config, "discover_download", False):
        command.extend(
            [
                "--discover",
                "--max-discovered-urls",
                str(int_config(config, "max_discovered_urls", 80)),
                "--max-download-articles",
                str(int_config(config, "max_articles", 25)),
                "--request-timeout-seconds",
                str(float_config(config, "request_timeout_seconds", 20.0)),
            ]
        )
    seed_pages_path = optional_str_config(config, "seed_pages_path")
    if seed_pages_path:
        command.extend(["--seed-pages-path", seed_pages_path])
    if bool_config(config, "sync_postgres", True):
        command.append("--sync-postgres")
    clean_path = str_config(config, "articles_path", "data/processed/articles_clean.jsonl")
    return [
        WorkflowStep(
            step_id="m01_data_ingestion",
            milestone="M01",
            name="Data ingestion and article sync",
            command=command,
            expected_artifacts=(
                str_config(config, "raw_output_path", "data/raw/articles_raw.jsonl"),
                clean_path,
                str_config(
                    config, "data_quality_report_path", "reports/data/data_quality_summary.md"
                ),
            ),
        )
    ]


node_spec = WorkflowNodeSpec(
    id="m01_ingestion",
    milestone="M01",
    title="Data ingestion",
    description=(
        "Discover/download optional news pages, parse local HTML and sync clean "
        "articles."
    ),
    depends_on=("m00_runtime",),
    default_config={
        "articles_path": "data/processed/articles_clean.jsonl",
        "max_articles": 25,
        "max_discovered_urls": 80,
        "discover_download": False,
        "sync_postgres": True,
        "min_text_chars": 300,
    },
    expected_artifacts=(
        "data/processed/articles_clean.jsonl",
        "reports/data/data_quality_summary.md",
    ),
    build_steps=build_steps,
    fields=(
        WorkflowFieldSpec(
            key="articles_path",
            label="Clean articles path",
            type="text",
        ),
        WorkflowFieldSpec(
            key="max_articles",
            label="Số bài tải/xử lý",
            type="number",
            min=1.0,
            max=500.0,
            step=1.0,
        ),
        WorkflowFieldSpec(
            key="max_discovered_urls",
            label="URL khám phá tối đa",
            type="number",
            min=1.0,
            max=1000.0,
            step=1.0,
        ),
        WorkflowFieldSpec(
            key="min_text_chars",
            label="Độ dài text tối thiểu",
            type="number",
            min=0.0,
            step=50.0,
        ),
        WorkflowFieldSpec(
            key="discover_download",
            label="Discover + download bài mới",
            type="checkbox",
        ),
        WorkflowFieldSpec(
            key="sync_postgres",
            label="Sync PostgreSQL",
            type="checkbox",
        ),
    ),
)
