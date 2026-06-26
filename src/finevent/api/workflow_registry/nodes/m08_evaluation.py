"""M08 Evaluation reports node specification."""

from __future__ import annotations

from finevent.api.workflow_registry.config_helpers import (
    bool_config,
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
    output_dir = str_config(config, "evaluation_output_dir", "reports/evaluation")
    command = [
        context.python,
        "-m",
        "finevent.evaluation",
        "run",
        "--gold-path",
        str_config(config, "gold_path", "data/labels/events_gold.jsonl"),
        "--output-dir",
        output_dir,
    ]
    predictions_path = optional_str_config(config, "predictions_path") or optional_str_config(
        config,
        "output_path",
    )
    if predictions_path:
        command.extend(["--predictions-path", predictions_path, "--ignore-runs-dir"])
    else:
        command.extend(["--runs-dir", str_config(config, "runs_dir", "runs/extraction")])
    if bool_config(config, "skip_academic_figures", False):
        command.append("--skip-academic-figures")
    return [
        WorkflowStep(
            step_id="m08_evaluation",
            milestone="M08",
            name="Evaluation and reports",
            command=command,
            expected_artifacts=(
                f"{output_dir}/report_index.md",
                f"{output_dir}/charts_summary.md",
                f"{output_dir}/academic_charts_summary.md",
            ),
        )
    ]


node_spec = WorkflowNodeSpec(
    id="m08_evaluation",
    milestone="M08",
    title="Evaluation reports",
    description="Evaluate predictions, hallucination metrics, ablation tables and final charts.",
    depends_on=("m04_retrieval", "m07_verification"),
    default_config={
        "gold_path": "data/labels/events_gold.jsonl",
        "evaluation_output_dir": "reports/evaluation",
        "skip_academic_figures": False,
    },
    expected_artifacts=("reports/evaluation/report_index.md",),
    build_steps=build_steps,
    fields=(
        WorkflowFieldSpec(
            key="gold_path",
            label="Gold labels",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="evaluation_output_dir",
            label="Report output dir",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="skip_academic_figures",
            label="Bỏ qua academic figures",
            type="checkbox",
        ),
    ),
)
