"""M04 Retrieval node specification."""

from __future__ import annotations

from finevent.api.workflow_registry.config_helpers import (
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
    command = [
        context.python,
        "-m",
        "finevent.retrieval",
        "compare",
        "--chunks-path",
        str_config(config, "chunks_path", "data/processed/chunks.jsonl"),
        "--bm25-index-path",
        str_config(config, "bm25_index_path", "data/retrieval/bm25_index.pkl"),
        "--embeddings-path",
        str_config(
            config, "retrieval_embeddings_path", "data/retrieval/chunk_embeddings.jsonl"
        ),
        "--gold-path",
        str_config(config, "gold_path", "data/labels/events_gold.jsonl"),
        "--logs-path",
        str_config(config, "retrieval_logs_path", "data/retrieval/retrieval_logs.jsonl"),
        "--metrics-path",
        str_config(
            config, "retrieval_metrics_path", "reports/evaluation/retrieval_metrics.csv"
        ),
        "--error-analysis-path",
        str_config(
            config,
            "retrieval_error_analysis_path",
            "reports/evaluation/retrieval_error_analysis.md",
        ),
        "--query-embedding-provider",
        str_config(config, "embedding_provider", "hash"),
        "--query-embedding-dimension",
        str(int_config(config, "embedding_dimension", 128)),
    ]
    model = optional_str_config(config, "embedding_model")
    if model:
        command.extend(["--query-embedding-model", model])
    return [
        WorkflowStep(
            step_id="m04_retrieval_evaluation",
            milestone="M04",
            name="Retrieval and reranking evaluation",
            command=command,
            expected_artifacts=(
                str_config(
                    config, "retrieval_logs_path", "data/retrieval/retrieval_logs.jsonl"
                ),
                str_config(
                    config, "retrieval_metrics_path", "reports/evaluation/retrieval_metrics.csv"
                ),
                str_config(
                    config,
                    "retrieval_error_analysis_path",
                    "reports/evaluation/retrieval_error_analysis.md",
                ),
            ),
        )
    ]


node_spec = WorkflowNodeSpec(
    id="m04_retrieval",
    milestone="M04",
    title="Retrieval evaluation",
    description="Compare retrieval/reranking strategies against gold labels.",
    depends_on=("m02_labeling", "m03_rag"),
    default_config={
        "embedding_provider": "hash",
        "embedding_dimension": 128,
        "retrieval_metrics_path": "reports/evaluation/retrieval_metrics.csv",
    },
    expected_artifacts=("reports/evaluation/retrieval_metrics.csv",),
    build_steps=build_steps,
    fields=(
        WorkflowFieldSpec(
            key="embedding_provider",
            label="Query embedding provider",
            type="select",
            options=embedding_options,
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="embedding_model",
            label="Query embedding model",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="embedding_dimension",
            label="Query embedding dimension",
            type="number",
            min=1.0,
            step=1.0,
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="retrieval_metrics_path",
            label="Retrieval metrics path",
            type="text",
            configurable=False,
        ),
    ),
)
