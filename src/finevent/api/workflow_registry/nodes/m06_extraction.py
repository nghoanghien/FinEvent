"""M06 Student extraction node specification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from finevent.api.artifacts import artifact_relative_path, get_workspace_root
from finevent.api.workflow_registry.config_helpers import (
    bool_config,
    extend_optional_int,
    int_config,
    str_config,
)
from finevent.api.workflow_registry.types import (
    BuildContext,
    WorkflowFieldSpec,
    WorkflowNodeSpec,
    WorkflowStep,
)
from finevent.retrieval.models import DEFAULT_RETRIEVAL_CONFIGS

article_sources_options = [
    {"value": "cafef", "label": "CafeF"},
    {"value": "vietstock", "label": "Vietstock"},
    {"value": "tinnhanhchungkhoan", "label": "Tin nhanh CK"},
    {"value": "nhadautu", "label": "Nhà đầu tư"},
]

retrieval_config_options = [{"value": name, "label": name} for name in DEFAULT_RETRIEVAL_CONFIGS]


def build_steps(context: BuildContext) -> list[WorkflowStep]:
    config = context.config
    articles_path = _student_articles_path(config, run_id=context.run_id)
    output_path = str_config(config, "output_path", "data/extraction/student_predictions.jsonl")
    command = [
        context.python,
        "-m",
        "finevent.extraction",
        "run-batch",
        "--articles-path",
        articles_path,
        "--output-path",
        output_path,
        "--student-provider",
        str_config(config, "student_provider", "deterministic"),
        "--retrieval-config",
        str_config(config, "retrieval_config", "metadata_aware_hybrid"),
        "--max-contexts",
        str(int_config(config, "max_contexts", 5)),
        "--retrieval-results-path",
        str_config(config, "retrieval_results_path", "data/retrieval/online_contexts.jsonl"),
    ]
    extend_optional_int(command, "--limit", config, "limit")
    command.extend(["--offset", str(int_config(config, "offset", 0))])
    if not bool_config(config, "use_retrieval", True):
        command.append("--disable-retrieval")
    if not context.selected("m07_verification"):
        command.append("--disable-verification")
    if bool_config(config, "sync_postgres", True):
        command.append("--sync-postgres")
    return [
        WorkflowStep(
            step_id=(
                "m06_m07_extraction_verification"
                if context.selected("m07_verification")
                else "m06_student_batch_extraction"
            ),
            milestone="M06/M07" if context.selected("m07_verification") else "M06",
            name=(
                "Student batch extraction with verification"
                if context.selected("m07_verification")
                else "Student batch extraction"
            ),
            command=command,
            expected_artifacts=(output_path,),
        )
    ]


def _student_articles_path(config: dict[str, Any], *, run_id: str | None) -> str:
    articles_path = str_config(config, "articles_path", "data/processed/articles_clean.jsonl")
    sources = _source_filter_values(config.get("sources"))
    if not sources or run_id is None:
        return articles_path
    return artifact_relative_path(_write_source_filtered_articles(articles_path, sources, run_id))


def _source_filter_values(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).strip().lower() for item in value if str(item).strip()}


def _write_source_filtered_articles(articles_path: str, sources: set[str], run_id: str) -> Path:
    source_path = _workspace_path(articles_path)
    output_path = (
        get_workspace_root() / "runs" / "admin" / run_id / "inputs" / "articles_filtered.jsonl"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with (
        source_path.open("r", encoding="utf-8") as source_file,
        output_path.open(
            "w",
            encoding="utf-8",
        ) as output_file,
    ):
        for line in source_file:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(record.get("source") or "").strip().lower() in sources:
                output_file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return output_path


def _workspace_path(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = get_workspace_root() / candidate
    candidate = candidate.resolve()
    workspace_root = get_workspace_root().resolve()
    if not candidate.is_relative_to(workspace_root):
        raise ValueError("Workflow input path must stay inside the workspace.")
    return candidate


node_spec = WorkflowNodeSpec(
    id="m06_extraction",
    milestone="M06",
    title="Student extraction",
    description="Run student model extraction using retrieval contexts produced by M04.",
    depends_on=("m04_retrieval",),
    default_config={
        "limit": 10,
        "offset": 0,
        "sources": ["cafef"],
        "output_path": "data/extraction/student_predictions.jsonl",
        "student_provider": "deterministic",
        "sync_postgres": True,
        "use_retrieval": True,
        "retrieval_config": "metadata_aware_hybrid",
        "retrieval_results_path": "data/retrieval/online_contexts.jsonl",
        "max_contexts": 5,
    },
    expected_artifacts=("data/extraction/student_predictions.jsonl",),
    build_steps=build_steps,
    fields=(
        WorkflowFieldSpec(
            key="sources",
            label="Nguồn bài",
            type="multi-select",
            options=article_sources_options,
        ),
        WorkflowFieldSpec(
            key="limit",
            label="Số bài chạy",
            type="number",
            min=1.0,
            max=500.0,
            step=1.0,
        ),
        WorkflowFieldSpec(
            key="offset",
            label="Offset",
            type="number",
            min=0.0,
            step=1.0,
        ),
        WorkflowFieldSpec(
            key="output_path",
            label="Predictions output",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="student_provider",
            label="Student provider",
            type="select",
            options=[
                {"value": "deterministic", "label": "deterministic"},
                {"value": "env", "label": "env"},
            ],
        ),
        WorkflowFieldSpec(
            key="use_retrieval",
            label="Use retrieval",
            type="checkbox",
        ),
        WorkflowFieldSpec(
            key="retrieval_config",
            label="Công thức retrieval đã dùng ở M04",
            type="select",
            description=(
                "M06 không chạy retrieval lại. Giá trị này chỉ dùng để chọn record "
                "trong online_contexts.jsonl khớp article_id + retrieval_config; "
                "nên giữ giống M04."
            ),
            options=retrieval_config_options,
        ),
        WorkflowFieldSpec(
            key="retrieval_results_path",
            label="Retrieval contexts path",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="max_contexts",
            label="Max contexts",
            type="number",
            description="Nên dùng 8-10 khi strategy multi-event được chọn.",
            min=1.0,
            max=20.0,
            step=1.0,
        ),
        WorkflowFieldSpec(
            key="sync_postgres",
            label="Sync PostgreSQL",
            type="checkbox",
        ),
    ),
)
