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

SOURCE_OPTIONS = [
    {"value": "cafef", "label": "CafeF"},
    {"value": "vietstock", "label": "Vietstock"},
    {"value": "tinnhanhchungkhoan", "label": "Tin nhanh CK"},
    {"value": "nhadautu", "label": "Nhà đầu tư"},
]
DEFAULT_SOURCES = [option["value"] for option in SOURCE_OPTIONS]


def build_steps(context: BuildContext) -> list[WorkflowStep]:
    config = context.config
    command = [
        context.python,
        "-m",
        "finevent.ingestion",
        "--input-html-dir",
        str_config(config, "input_html_dir", "data/raw/html"),
        "--html-manifest-path",
        str_config(config, "html_manifest_path", "data/raw/html_manifest.jsonl"),
        "--raw-output-path",
        str_config(config, "raw_output_path", "data/raw/articles_raw.jsonl"),
        "--clean-output-path",
        str_config(config, "articles_path", "data/processed/articles_clean.jsonl"),
        "--report-path",
        str_config(config, "data_quality_report_path", "reports/data/data_quality_summary.md"),
        "--min-text-chars",
        str(int_config(config, "min_text_chars", 300)),
    ]
    if bool_config(config, "reset_html_snapshots", False):
        command.append("--reset-html-snapshots")
    if bool_config(config, "discover_download", True):
        sources = _source_values(config.get("sources"))
        if not sources:
            raise ValueError("M01 discover_download requires at least one source.")
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
        for source in sources:
            command.extend(["--source", source])
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


def _source_values(value: object) -> list[str]:
    if not isinstance(value, list):
        return DEFAULT_SOURCES
    return [str(item).strip().lower() for item in value if str(item).strip()]


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
        "input_html_dir": "data/raw/html",
        "html_manifest_path": "data/raw/html_manifest.jsonl",
        "sources": DEFAULT_SOURCES,
        "max_articles": 25,
        "max_discovered_urls": 80,
        "discover_download": True,
        "reset_html_snapshots": False,
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
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="input_html_dir",
            label="Local HTML snapshot dir",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="html_manifest_path",
            label="HTML manifest path",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="sources",
            label="Nguồn crawl",
            type="multi-select",
            description="Chỉ áp dụng khi bật Discover + download.",
            options=SOURCE_OPTIONS,
        ),
        WorkflowFieldSpec(
            key="max_articles",
            label="Số bài tải tối đa",
            type="number",
            description="Chỉ áp dụng khi bật Discover + download.",
            min=1.0,
            max=500.0,
            step=1.0,
        ),
        WorkflowFieldSpec(
            key="max_discovered_urls",
            label="URL khám phá tối đa",
            type="number",
            description="Chỉ áp dụng khi bật Discover + download.",
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
            key="reset_html_snapshots",
            label="Reset local HTML snapshots",
            type="checkbox",
            description="Xóa *.html và HTML manifest trước M01; không xóa DB.",
        ),
        WorkflowFieldSpec(
            key="sync_postgres",
            label="Sync PostgreSQL",
            type="checkbox",
        ),
    ),
)
