"""M02 Teacher labeling node specification."""

from __future__ import annotations

from finevent.api.workflow_registry.config_helpers import (
    bool_config,
    extend_optional_int,
    float_config,
    int_config,
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
    python = context.python
    steps: list[WorkflowStep] = []
    prompt_path = str_config(config, "teacher_prompt_path", "data/labels/teacher_prompts.jsonl")
    teacher_output_path = str_config(
        config, "teacher_output_path", "data/labels/teacher_outputs.jsonl"
    )
    gold_path = str_config(config, "gold_path", "data/labels/events_gold.jsonl")
    rejected_path = str_config(config, "rejected_labels_path", "data/labels/events_rejected.jsonl")
    if bool_config(config, "generate_prompts", True):
        command = [
            python,
            "-m",
            "finevent.labeling",
            "generate-prompts",
            "--articles-path",
            str_config(config, "articles_path", "data/processed/articles_clean.jsonl"),
            "--prompt-output-path",
            prompt_path,
        ]
        extend_optional_int(command, "--limit", config, "max_articles")
        steps.append(
            WorkflowStep(
                step_id="m02_generate_teacher_prompts",
                milestone="M02",
                name="Generate teacher prompts",
                command=command,
                expected_artifacts=(prompt_path,),
            )
        )
    if bool_config(config, "run_teacher", True):
        command = [
            python,
            "-m",
            "finevent.labeling",
            "run-teacher",
            "--prompt-path",
            prompt_path,
            "--output-path",
            teacher_output_path,
            "--max-retries",
            str(int_config(config, "teacher_max_retries", 2)),
            "--retry-sleep-seconds",
            str(float_config(config, "teacher_retry_sleep_seconds", 2.0)),
        ]
        extend_optional_int(command, "--max-records", config, "max_articles")
        steps.append(
            WorkflowStep(
                step_id="m02_teacher_labeling",
                milestone="M02",
                name="Teacher LLM labeling",
                command=command,
                expected_artifacts=(teacher_output_path,),
            )
        )
    if bool_config(config, "validate_labels", True):
        command = [
            python,
            "-m",
            "finevent.labeling",
            "validate",
            "--articles-path",
            str_config(config, "articles_path", "data/processed/articles_clean.jsonl"),
            "--teacher-output-path",
            teacher_output_path,
            "--ai-generated-output-path",
            str_config(
                config, "ai_generated_labels_path", "data/labels/events_ai_generated.jsonl"
            ),
            "--gold-output-path",
            gold_path,
            "--rejected-output-path",
            rejected_path,
            "--report-path",
            str_config(config, "labeling_report_path", "reports/data/labeling_summary.md"),
        ]
        if bool_config(config, "strict_validation", True):
            command.append("--strict-validation")
        steps.append(
            WorkflowStep(
                step_id="m02_validate_labels",
                milestone="M02",
                name="Validate labels and build gold set",
                command=command,
                expected_artifacts=(
                    gold_path,
                    rejected_path,
                    str_config(config, "labeling_report_path", "reports/data/labeling_summary.md"),
                ),
            )
        )
    if bool_config(config, "sync_postgres", True):
        steps.append(
            WorkflowStep(
                step_id="m02_sync_labels",
                milestone="M02",
                name="Sync labels to PostgreSQL",
                command=[
                    python,
                    "-m",
                    "finevent.labeling",
                    "sync-postgres",
                    "--gold-path",
                    gold_path,
                    "--rejected-path",
                    rejected_path,
                    "--source-path",
                    gold_path,
                ],
            )
        )
    return steps


node_spec = WorkflowNodeSpec(
    id="m02_labeling",
    milestone="M02",
    title="Teacher labeling",
    description="Generate prompts, call teacher model, validate labels and sync gold labels.",
    depends_on=("m01_ingestion",),
    default_config={
        "generate_prompts": True,
        "run_teacher": True,
        "validate_labels": True,
        "sync_postgres": True,
        "max_articles": 25,
        "gold_path": "data/labels/events_gold.jsonl",
        "teacher_prompt_path": "data/labels/teacher_prompts.jsonl",
        "teacher_output_path": "data/labels/teacher_outputs.jsonl",
        "teacher_max_retries": 2,
        "teacher_retry_sleep_seconds": 2.0,
        "strict_validation": True,
    },
    expected_artifacts=("data/labels/events_gold.jsonl", "reports/data/labeling_summary.md"),
    build_steps=build_steps,
    fields=(
        WorkflowFieldSpec(
            key="max_articles",
            label="Số bài teacher xử lý tối đa",
            type="number",
            description=(
                "Giới hạn số bài tạo prompt và số prompt gọi teacher; retry không "
                "tính vào giới hạn này."
            ),
            min=1.0,
            max=500.0,
            step=1.0,
        ),
        WorkflowFieldSpec(
            key="gold_path",
            label="Gold labels path",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="teacher_prompt_path",
            label="Teacher prompts path",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="teacher_output_path",
            label="Teacher outputs path",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="teacher_max_retries",
            label="Teacher max retries",
            type="number",
            description="Số lần thử lại cho mỗi prompt khi teacher LLM lỗi.",
            min=0.0,
            max=10.0,
            step=1.0,
        ),
        WorkflowFieldSpec(
            key="generate_prompts",
            label="Generate prompts",
            type="checkbox",
            description="Tạo teacher_prompts.jsonl từ clean articles.",
        ),
        WorkflowFieldSpec(
            key="run_teacher",
            label="Call teacher LLM",
            type="checkbox",
            description="Gọi teacher LLM trên prompt đã tạo để sinh raw outputs.",
        ),
        WorkflowFieldSpec(
            key="validate_labels",
            label="Validate labels",
            type="checkbox",
            description=(
                "Parse teacher outputs, validate schema/taxonomy và tạo "
                "gold/rejected labels."
            ),
        ),
        WorkflowFieldSpec(
            key="strict_validation",
            label="Strict validation",
            type="checkbox",
            description="Chỉ đưa label PASS vào gold; label có lỗi sẽ vào rejected.",
        ),
        WorkflowFieldSpec(
            key="sync_postgres",
            label="Sync PostgreSQL",
            type="checkbox",
        ),
    ),
)
