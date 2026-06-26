"""M07 Verification node specification."""

from __future__ import annotations

from finevent.api.workflow_registry.types import BuildContext, WorkflowNodeSpec, WorkflowStep


def build_steps(_: BuildContext) -> list[WorkflowStep]:
    # Verification is implemented as a modifier flag for M06 extraction step builder.
    return []


node_spec = WorkflowNodeSpec(
    id="m07_verification",
    milestone="M07",
    title="Verification",
    description="Enable evidence verification and hallucination reduction inside the extraction run.",
    depends_on=("m06_extraction",),
    default_config={},
    expected_artifacts=("runs/extraction",),
    build_steps=build_steps,
    fields=(),
)
