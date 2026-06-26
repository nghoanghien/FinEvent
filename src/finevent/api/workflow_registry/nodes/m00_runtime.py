"""M00 Runtime and database node specification."""

from __future__ import annotations

from finevent.api.workflow_registry.types import BuildContext, WorkflowNodeSpec, WorkflowStep


def build_steps(context: BuildContext) -> list[WorkflowStep]:
    python = context.python
    return [
        WorkflowStep(
            step_id="m00_database_healthcheck",
            milestone="M00",
            name="Database healthcheck",
            command=[python, "-m", "finevent.database.cli", "healthcheck"],
        ),
        WorkflowStep(
            step_id="m00_apply_migrations",
            milestone="M00",
            name="Apply PostgreSQL migrations",
            command=[python, "-m", "finevent.database.cli", "apply-migrations"],
        ),
        WorkflowStep(
            step_id="m00_verify_pgvector",
            milestone="M00",
            name="Verify pgvector",
            command=[python, "-m", "finevent.database.cli", "verify-pgvector"],
        ),
    ]


node_spec = WorkflowNodeSpec(
    id="m00_runtime",
    milestone="M00",
    title="Runtime and database",
    description="Healthcheck PostgreSQL, apply migrations and verify pgvector.",
    depends_on=(),
    default_config={},
    expected_artifacts=(),
    build_steps=build_steps,
    fields=(),
)
