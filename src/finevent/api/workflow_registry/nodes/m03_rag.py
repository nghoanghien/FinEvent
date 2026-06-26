"""M03 RAG preparation node specification."""

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
    embedding_provider = str_config(config, "embedding_provider", "hash")
    embedding_dimension = int_config(config, "embedding_dimension", 128)
    chunks_path = str_config(config, "chunks_path", "data/processed/chunks.jsonl")
    embeddings_path = str_config(
        config,
        "retrieval_embeddings_path",
        "data/retrieval/chunk_embeddings.jsonl",
    )
    steps = [
        WorkflowStep(
            step_id="m03_rag_preparation",
            milestone="M03",
            name="RAG preparation",
            command=[
                python,
                "-m",
                "finevent.rag",
                "prepare",
                "--articles-path",
                str_config(config, "articles_path", "data/processed/articles_clean.jsonl"),
                "--chunks-output-path",
                chunks_path,
                "--retrieval-dir",
                str_config(config, "retrieval_dir", "data/retrieval"),
                "--vector-store-dir",
                str_config(config, "vector_store_dir", "data/vector_store"),
                "--report-path",
                str_config(
                    config, "rag_report_path", "reports/data/rag_preparation_summary.md"
                ),
                "--embedding-provider",
                embedding_provider,
                "--embedding-dimension",
                str(embedding_dimension),
                "--target-words",
                str(int_config(config, "target_words", 420)),
                "--max-words",
                str(int_config(config, "max_words", 620)),
                "--overlap-words",
                str(int_config(config, "overlap_words", 80)),
            ],
            expected_artifacts=(
                chunks_path,
                embeddings_path,
                str_config(config, "bm25_index_path", "data/retrieval/bm25_index.pkl"),
                str_config(
                    config, "rag_report_path", "reports/data/rag_preparation_summary.md"
                ),
            ),
        )
    ]
    model = optional_str_config(config, "embedding_model")
    if model:
        steps[0].command.extend(["--embedding-model", model])
    if bool_config(config, "sync_postgres", True):
        steps.append(
            WorkflowStep(
                step_id="m03_sync_retrieval",
                milestone="M03",
                name="Sync retrieval artifacts",
                command=[
                    python,
                    "-m",
                    "finevent.rag",
                    "sync-postgres",
                    "--articles-path",
                    str_config(config, "articles_path", "data/processed/articles_clean.jsonl"),
                    "--chunks-path",
                    chunks_path,
                    "--embeddings-path",
                    embeddings_path,
                ],
            )
        )
    return steps


node_spec = WorkflowNodeSpec(
    id="m03_rag",
    milestone="M03",
    title="RAG preparation",
    description=(
        "Chunk articles, build embeddings, BM25 and vector artifacts, then sync "
        "retrieval data."
    ),
    depends_on=("m01_ingestion",),
    default_config={
        "embedding_provider": "hash",
        "embedding_dimension": 128,
        "sync_postgres": True,
        "target_words": 420,
        "max_words": 620,
        "overlap_words": 80,
    },
    expected_artifacts=("data/processed/chunks.jsonl", "data/retrieval/bm25_index.pkl"),
    build_steps=build_steps,
    fields=(
        WorkflowFieldSpec(
            key="embedding_provider",
            label="Embedding provider",
            type="select",
            options=embedding_options,
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="embedding_model",
            label="Embedding model",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="embedding_dimension",
            label="Embedding dimension",
            type="number",
            min=1.0,
            step=1.0,
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="target_words",
            label="Target words/chunk",
            type="number",
            min=50.0,
            step=10.0,
        ),
        WorkflowFieldSpec(
            key="max_words",
            label="Max words/chunk",
            type="number",
            min=50.0,
            step=10.0,
        ),
        WorkflowFieldSpec(
            key="overlap_words",
            label="Overlap words",
            type="number",
            min=0.0,
            step=10.0,
        ),
        WorkflowFieldSpec(
            key="sync_postgres",
            label="Sync PostgreSQL",
            type="checkbox",
        ),
    ),
)
