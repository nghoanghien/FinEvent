"""M05 Pattern library node specification."""

from __future__ import annotations

from finevent.api.workflow_registry.config_helpers import (
    bool_config,
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

embedding_options = [
    {"value": "hash", "label": "hash"},
    {"value": "cloudflare", "label": "cloudflare"},
    {"value": "openai_compatible", "label": "openai_compatible"},
    {"value": "direct_http", "label": "direct_http"},
]


def build_steps(context: BuildContext) -> list[WorkflowStep]:
    config = context.config
    python = context.python
    patterns_path = str_config(config, "patterns_path", "data/patterns/patterns.jsonl")
    pattern_embeddings_path = str_config(
        config,
        "pattern_embeddings_path",
        "data/patterns/pattern_embeddings.jsonl",
    )
    build_command = [
        python,
        "-m",
        "finevent.patterns",
        "build",
        "--articles-path",
        str_config(config, "articles_path", "data/processed/articles_clean.jsonl"),
        "--gold-path",
        str_config(config, "gold_path", "data/labels/events_gold.jsonl"),
        "--patterns-output-path",
        patterns_path,
        "--rejected-patterns-output-path",
        str_config(
            config, "rejected_patterns_path", "data/patterns/patterns_rejected.jsonl"
        ),
        "--embeddings-output-path",
        pattern_embeddings_path,
        "--embedding-cache-path",
        str_config(
            config,
            "pattern_embedding_cache_path",
            "data/patterns/pattern_embedding_cache.jsonl",
        ),
        "--metrics-path",
        str_config(config, "pattern_metrics_path", "reports/evaluation/pattern_metrics.csv"),
        "--report-path",
        str_config(
            config, "pattern_report_path", "reports/evaluation/pattern_library_summary.md"
        ),
        "--embedding-provider",
        str_config(config, "embedding_provider", "hash"),
        "--embedding-dimension",
        str(int_config(config, "embedding_dimension", 128)),
    ]
    model = optional_str_config(config, "embedding_model")
    if model:
        build_command.extend(["--embedding-model", model])
    steps = [
        WorkflowStep(
            step_id="m05_pattern_library",
            milestone="M05",
            name="Pattern library build",
            command=build_command,
            expected_artifacts=(
                patterns_path,
                pattern_embeddings_path,
                str_config(
                    config, "pattern_metrics_path", "reports/evaluation/pattern_metrics.csv"
                ),
                str_config(
                    config,
                    "pattern_report_path",
                    "reports/evaluation/pattern_library_summary.md",
                ),
            ),
        )
    ]
    if bool_config(config, "sync_postgres", True):
        steps.append(
            WorkflowStep(
                step_id="m05_sync_patterns",
                milestone="M05",
                name="Sync patterns to PostgreSQL",
                command=[
                    python,
                    "-m",
                    "finevent.patterns",
                    "sync-postgres",
                    "--patterns-path",
                    patterns_path,
                    "--embeddings-path",
                    pattern_embeddings_path,
                ],
            )
        )
    return steps


node_spec = WorkflowNodeSpec(
    id="m05_patterns",
    milestone="M05",
    title="Pattern library",
    description="Build few-shot pattern records and embeddings from validated gold labels.",
    depends_on=("m02_labeling", "m03_rag"),
    default_config={
        "embedding_provider": "hash",
        "embedding_dimension": 128,
        "sync_postgres": True,
    },
    expected_artifacts=(
        "data/patterns/patterns.jsonl",
        "data/patterns/pattern_embeddings.jsonl",
    ),
    build_steps=build_steps,
    fields=(
        WorkflowFieldSpec(
            key="embedding_provider",
            label="Pattern embedding provider",
            type="select",
            options=embedding_options,
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="embedding_model",
            label="Pattern embedding model",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="embedding_dimension",
            label="Pattern embedding dimension",
            type="number",
            min=1.0,
            step=1.0,
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="sync_postgres",
            label="Sync PostgreSQL",
            type="checkbox",
        ),
    ),
)
