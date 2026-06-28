"""M04 Retrieval node specification."""

from __future__ import annotations

from finevent.api.workflow_registry.config_helpers import (
    bool_config,
    extend_optional_int,
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
        "run-batch",
        "--chunks-path",
        str_config(config, "chunks_path", "data/processed/chunks.jsonl"),
        "--bm25-index-path",
        str_config(config, "bm25_index_path", "data/retrieval/bm25_index.pkl"),
        "--embeddings-path",
        str_config(
            config, "retrieval_embeddings_path", "data/retrieval/chunk_embeddings.jsonl"
        ),
        "--articles-path",
        str_config(config, "articles_path", "data/processed/articles_clean.jsonl"),
        "--gold-path",
        str_config(config, "gold_path", "data/labels/events_gold.jsonl"),
        "--output-path",
        str_config(config, "retrieval_results_path", "data/retrieval/online_contexts.jsonl"),
        "--logs-path",
        str_config(
            config,
            "retrieval_logs_path",
            "data/retrieval/online_retrieval_logs.jsonl",
        ),
        "--metrics-path",
        str_config(
            config,
            "retrieval_metrics_path",
            "reports/evaluation/online_retrieval_metrics.csv",
        ),
        "--error-analysis-path",
        str_config(
            config,
            "retrieval_error_analysis_path",
            "reports/evaluation/online_retrieval_error_analysis.md",
        ),
        "--config",
        str_config(config, "retrieval_config", "metadata_aware_hybrid"),
        "--max-contexts",
        str(int_config(config, "max_contexts", 10)),
        "--llm-rerank-mode",
        str_config(config, "llm_rerank_mode", "student_env"),
        "--llm-rerank-top-n",
        str(int_config(config, "llm_rerank_top_n", 15)),
        "--llm-rerank-max-query-article-chars",
        str(int_config(config, "llm_rerank_max_query_article_chars", 2400)),
        "--llm-rerank-max-candidate-chars",
        str(int_config(config, "llm_rerank_max_candidate_chars", 900)),
        "--llm-rerank-max-retries",
        str(int_config(config, "llm_rerank_max_retries", 1)),
        "--query-embedding-provider",
        str_config(config, "embedding_provider", "hash"),
        "--query-embedding-dimension",
        str(int_config(config, "embedding_dimension", 128)),
    ]
    model = optional_str_config(config, "embedding_model")
    if model:
        command.extend(["--query-embedding-model", model])
    extend_optional_int(command, "--limit", config, "limit")
    command.extend(["--offset", str(int_config(config, "offset", 0))])
    retrieval_results_path = str_config(
        config,
        "retrieval_results_path",
        "data/retrieval/online_contexts.jsonl",
    )
    steps = [
        WorkflowStep(
            step_id="m04_online_retrieval",
            milestone="M04",
            name="Online retrieval contexts",
            command=command,
            expected_artifacts=(
                str_config(
                    config,
                    "retrieval_results_path",
                    "data/retrieval/online_contexts.jsonl",
                ),
                str_config(
                    config,
                    "retrieval_logs_path",
                    "data/retrieval/online_retrieval_logs.jsonl",
                ),
                str_config(
                    config,
                    "retrieval_metrics_path",
                    "reports/evaluation/online_retrieval_metrics.csv",
                ),
                str_config(
                    config,
                    "retrieval_error_analysis_path",
                    "reports/evaluation/online_retrieval_error_analysis.md",
                ),
            ),
        )
    ]
    if bool_config(config, "sync_postgres", True):
        steps.append(
            WorkflowStep(
                step_id="m04_sync_retrieval_runs",
                milestone="M04",
                name="Sync online retrieval runs",
                command=[
                    context.python,
                    "-m",
                    "finevent.retrieval",
                    "sync-postgres",
                    "--retrieval-results-path",
                    retrieval_results_path,
                ],
            )
        )
    return steps


node_spec = WorkflowNodeSpec(
    id="m04_retrieval",
    milestone="M04",
    title="Online retrieval contexts",
    description=(
        "Tạo context pack M04 bằng recipe scoring/rerank kết hợp BM25, "
        "dense embeddings, metadata và pattern refs gắn trên chunk."
    ),
    depends_on=("m02_labeling", "m03_rag"),
    default_config={
        "embedding_provider": "hash",
        "embedding_dimension": 128,
        "retrieval_config": "metadata_aware_hybrid",
        "max_contexts": 10,
        "llm_rerank_mode": "student_env",
        "llm_rerank_top_n": 15,
        "llm_rerank_max_query_article_chars": 2400,
        "llm_rerank_max_candidate_chars": 900,
        "llm_rerank_max_retries": 1,
        "offset": 0,
        "sync_postgres": True,
        "retrieval_results_path": "data/retrieval/online_contexts.jsonl",
        "retrieval_metrics_path": "reports/evaluation/online_retrieval_metrics.csv",
    },
    expected_artifacts=("data/retrieval/online_contexts.jsonl",),
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
            key="retrieval_config",
            label="Công thức retrieval/rerank",
            type="select",
            description=(
                "Chọn recipe tạo context pack cho M06. Các recipe hybrid vẫn kết hợp "
                "BM25, dense embedding, metadata, rule/LLM rerank và coverage/MMR; "
                "đây không phải lựa chọn một nguồn retrieve duy nhất."
            ),
            options=[
                {"value": name, "label": name}
                for name in (
                    "bm25_only",
                    "dense_only",
                    "hybrid",
                    "metadata_aware_hybrid",
                    "rule_aware_rerank",
                    "llm_reasoning_rerank",
                    "multi_event_aware_hybrid",
                )
            ],
        ),
        WorkflowFieldSpec(
            key="max_contexts",
            label="Max contexts",
            type="number",
            min=1.0,
            max=20.0,
            step=1.0,
        ),
        WorkflowFieldSpec(
            key="llm_rerank_mode",
            label="LLM listwise rerank",
            type="select",
            description=(
                "Mặc định dùng student model từ env để rerank listwise như bước cuối, "
                "sau scoring/strategy selection và trước khi ghi context cho M06. "
                "Dùng deterministic cho smoke test."
            ),
            options=[
                {"value": "student_env", "label": "student_env"},
                {"value": "deterministic", "label": "deterministic"},
                {"value": "off", "label": "off"},
            ],
        ),
        WorkflowFieldSpec(
            key="llm_rerank_top_n",
            label="Số candidate LLM rerank",
            type="number",
            description=(
                "Số candidate trong pool trước LLM rerank, mặc định 15. "
                "Với multi-event, coverage/MMR chạy trước rồi LLM lọc lại pool này."
            ),
            min=1.0,
            max=30.0,
            step=1.0,
        ),
        WorkflowFieldSpec(
            key="llm_rerank_max_query_article_chars",
            label="Query article chars",
            type="number",
            configurable=False,
            min=500.0,
            step=100.0,
        ),
        WorkflowFieldSpec(
            key="llm_rerank_max_candidate_chars",
            label="Candidate chunk chars",
            type="number",
            configurable=False,
            min=200.0,
            step=100.0,
        ),
        WorkflowFieldSpec(
            key="llm_rerank_max_retries",
            label="LLM rerank retries",
            type="number",
            configurable=False,
            min=0.0,
            step=1.0,
        ),
        WorkflowFieldSpec(
            key="retrieval_results_path",
            label="Retrieval contexts path",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="retrieval_metrics_path",
            label="Retrieval metrics path",
            type="text",
            configurable=False,
        ),
        WorkflowFieldSpec(
            key="sync_postgres",
            label="Sync PostgreSQL",
            type="checkbox",
        ),
    ),
)
