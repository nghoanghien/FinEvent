"""Operational runner for the real M00-M08 workflow."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from finevent.database.cli import apply_migrations, healthcheck, verify_pgvector
from finevent.db import get_sqlalchemy_engine
from finevent.evaluation.pipeline import run_evaluation_pipeline
from finevent.extraction.models import ExtractionRunConfig
from finevent.extraction.run_sql import sync_extraction_state
from finevent.extraction.student import InvokableStudentModel
from finevent.extraction.workflow import (
    ExtractionWorkflowArtifacts,
    build_public_result,
    run_online_extraction_workflow,
)
from finevent.ingestion.article_sql import sync_clean_articles_jsonl
from finevent.ingestion.cli import read_seed_pages
from finevent.ingestion.discovery import default_seed_pages, discover_url_candidates
from finevent.ingestion.download import DEFAULT_HTML_MANIFEST_PATH, download_url_candidates
from finevent.ingestion.pipeline import run_local_html_ingestion
from finevent.ingestion.ticker_sql import sync_ticker_dictionary_csv
from finevent.jsonl import read_jsonl, write_jsonl
from finevent.labeling.event_sql import sync_event_labels_jsonl
from finevent.labeling.pipeline import generate_teacher_prompts, validate_teacher_outputs
from finevent.labeling.teacher_llm import InvokableModel, run_teacher_llm_on_prompts
from finevent.llm import (
    build_student_chat_model_from_env,
    build_teacher_chat_model_from_env,
    load_provider_runtime_config,
)
from finevent.patterns.pattern_sql import sync_pattern_artifacts
from finevent.patterns.pipeline import run_pattern_library_build
from finevent.rag.embeddings import build_embedding_client
from finevent.rag.pipeline import run_rag_preparation
from finevent.rag.rag_sql import sync_retrieval_artifacts
from finevent.retrieval.experiments import run_retrieval_comparison


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run FinEvent live operations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run-m00-m08", help="Run the real M00-M08 pipeline.")
    run.add_argument("--max-articles", type=int, default=25)
    run.add_argument("--max-discovered-urls", type=int, default=80)
    run.add_argument("--request-timeout-seconds", type=float, default=20.0)
    run.add_argument("--skip-download", action="store_true")
    run.add_argument("--seed-pages-path", default=None)
    run.add_argument("--embedding-provider", default="langchain_openai")
    run.add_argument("--embedding-model", default=None)
    run.add_argument("--embedding-dimension", type=int, default=1024)
    run.add_argument("--teacher-max-retries", type=int, default=2)
    run.add_argument("--teacher-retry-sleep-seconds", type=float, default=2.0)
    run.add_argument("--summary-path", default="reports/live_m00_m08_summary.json")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "run-m00-m08":
        result = run_m00_m08(args)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return
    raise SystemExit(f"Unknown command: {args.command}")


def run_m00_m08(args: argparse.Namespace) -> dict[str, Any]:
    engine = get_sqlalchemy_engine()
    provider_config = load_provider_runtime_config()
    summary: dict[str, Any] = {
        "max_articles": args.max_articles,
        "embedding_provider": args.embedding_provider,
        "embedding_model": args.embedding_model or provider_config.embedding_model,
        "steps": {},
    }

    summary["steps"]["m00_database_healthcheck"] = healthcheck(engine)
    summary["steps"]["m00_apply_migrations"] = apply_migrations(engine)
    summary["steps"]["m00_verify_pgvector"] = verify_pgvector(engine)
    ticker_sync = sync_ticker_dictionary_csv(engine)
    summary["steps"]["m01_ticker_dictionary_sync"] = ticker_sync.__dict__

    if not args.skip_download:
        seed_pages = (
            read_seed_pages(args.seed_pages_path)
            if args.seed_pages_path
            else default_seed_pages()
        )
        discovery_result = discover_url_candidates(
            seed_pages=seed_pages,
            max_candidates=args.max_discovered_urls,
            timeout_seconds=args.request_timeout_seconds,
        )
        write_jsonl(
            "data/raw/discovered_urls.jsonl",
            (candidate.to_dict() for candidate in discovery_result.candidates),
        )
        download_records = download_url_candidates(
            discovery_result.candidates,
            output_html_dir="data/raw/html",
            html_manifest_path=DEFAULT_HTML_MANIFEST_PATH,
            timeout_seconds=args.request_timeout_seconds,
            max_records=args.max_articles,
        )
        write_jsonl(
            "data/raw/download_log.jsonl",
            (record.to_dict() for record in download_records),
        )
        summary["steps"]["m01_discovery_download"] = {
            "discovered_count": len(discovery_result.candidates),
            "discovery_error_count": sum(1 for item in discovery_result.diagnostics if item.error),
            "download_count": len(download_records),
            "download_error_count": sum(1 for record in download_records if record.error),
            "discovered_output_path": "data/raw/discovered_urls.jsonl",
            "download_log_path": "data/raw/download_log.jsonl",
        }

    ingestion = run_local_html_ingestion(
        input_html_dir="data/raw/html",
        html_manifest_path=DEFAULT_HTML_MANIFEST_PATH,
        raw_output_path="data/raw/articles_raw.jsonl",
        clean_output_path="data/processed/articles_clean.jsonl",
        report_path="reports/data/data_quality_summary.md",
        min_text_chars=300,
    )
    summary["steps"]["m01_ingestion"] = ingestion.__dict__
    article_sync = sync_clean_articles_jsonl(
        engine,
        articles_path="data/processed/articles_clean.jsonl",
    )
    summary["steps"]["m01_article_postgres_sync"] = article_sync.__dict__

    prompts = generate_teacher_prompts(
        articles_path="data/processed/articles_clean.jsonl",
        prompt_output_path="data/labels/teacher_prompts.jsonl",
        limit=args.max_articles,
    )
    summary["steps"]["m02_generate_prompts"] = prompts.__dict__

    teacher = run_teacher_llm_on_prompts(
        prompt_path="data/labels/teacher_prompts.jsonl",
        output_path="data/labels/teacher_outputs.jsonl",
        teacher_model=cast(InvokableModel, build_teacher_chat_model_from_env()),
        teacher_model_name=provider_config.teacher_model or "teacher_model",
        max_records=args.max_articles,
        max_retries=args.teacher_max_retries,
        retry_sleep_seconds=args.teacher_retry_sleep_seconds,
    )
    summary["steps"]["m02_teacher_labeling"] = teacher.__dict__

    labels = validate_teacher_outputs(
        articles_path="data/processed/articles_clean.jsonl",
        teacher_output_path="data/labels/teacher_outputs.jsonl",
        ai_generated_output_path="data/labels/events_ai_generated.jsonl",
        gold_output_path="data/labels/events_gold.jsonl",
        rejected_output_path="data/labels/events_rejected.jsonl",
        report_path="reports/data/labeling_summary.md",
        accept_ai_as_gold=True,
    )
    summary["steps"]["m02_accept_ai_gold"] = labels.__dict__
    label_sync = sync_event_labels_jsonl(
        engine,
        gold_path="data/labels/events_gold.jsonl",
        rejected_path="data/labels/events_rejected.jsonl",
        source_path="data/labels/events_gold.jsonl",
    )
    summary["steps"]["m02_postgres_sync"] = label_sync.__dict__

    rag = run_rag_preparation(
        articles_path="data/processed/articles_clean.jsonl",
        chunks_output_path="data/processed/chunks.jsonl",
        retrieval_dir="data/retrieval",
        vector_store_dir="data/vector_store",
        report_path="reports/data/rag_preparation_summary.md",
        embedding_provider=args.embedding_provider,
        embedding_model=args.embedding_model,
        embedding_dimension=args.embedding_dimension,
    )
    summary["steps"]["m03_rag_preparation"] = rag.__dict__
    retrieval_sync = sync_retrieval_artifacts(
        engine,
        articles_path="data/processed/articles_clean.jsonl",
        chunks_path="data/processed/chunks.jsonl",
        embeddings_path="data/retrieval/chunk_embeddings.jsonl",
    )
    summary["steps"]["m03_postgres_sync"] = retrieval_sync.__dict__

    retrieval_eval = run_retrieval_comparison(
        chunks_path="data/processed/chunks.jsonl",
        bm25_index_path="data/retrieval/bm25_index.pkl",
        embeddings_path="data/retrieval/chunk_embeddings.jsonl",
        gold_path="data/labels/events_gold.jsonl",
        logs_path="data/retrieval/retrieval_logs.jsonl",
        metrics_path="reports/evaluation/retrieval_metrics.csv",
        error_analysis_path="reports/evaluation/retrieval_error_analysis.md",
        query_embedding_client=build_embedding_client(
            provider=args.embedding_provider,
            model_name=args.embedding_model,
            dimension=args.embedding_dimension,
        ),
    )
    summary["steps"]["m04_retrieval_evaluation"] = retrieval_eval.__dict__

    patterns = run_pattern_library_build(
        articles_path="data/processed/articles_clean.jsonl",
        gold_path="data/labels/events_gold.jsonl",
        patterns_output_path="data/patterns/patterns.jsonl",
        rejected_patterns_output_path="data/patterns/patterns_rejected.jsonl",
        embeddings_output_path="data/patterns/pattern_embeddings.jsonl",
        embedding_cache_path="data/patterns/pattern_embedding_cache.jsonl",
        metrics_path="reports/evaluation/pattern_metrics.csv",
        report_path="reports/evaluation/pattern_library_summary.md",
        embedding_provider=args.embedding_provider,
        embedding_model=args.embedding_model,
        embedding_dimension=args.embedding_dimension,
    )
    summary["steps"]["m05_pattern_library"] = patterns.__dict__
    pattern_sync = sync_pattern_artifacts(
        engine,
        patterns_path="data/patterns/patterns.jsonl",
        embeddings_path="data/patterns/pattern_embeddings.jsonl",
    )
    summary["steps"]["m05_postgres_sync"] = pattern_sync.__dict__

    first_article = _first_article("data/processed/articles_clean.jsonl")
    student_model = cast(InvokableStudentModel, build_student_chat_model_from_env())
    extraction_config = replace(
        ExtractionRunConfig(),
        student_model=provider_config.student_model or "student_model",
    )
    extraction_state = run_online_extraction_workflow(
        {"input_type": "article", "article": first_article},
        config=extraction_config,
        artifacts=ExtractionWorkflowArtifacts(
            retrieval_query_embedding_provider=args.embedding_provider,
            retrieval_query_embedding_model=args.embedding_model,
            retrieval_query_embedding_dimension=args.embedding_dimension,
            pattern_query_embedding_provider=args.embedding_provider,
            pattern_query_embedding_model=args.embedding_model,
            pattern_query_embedding_dimension=args.embedding_dimension,
        ),
        langchain_model=student_model,
    )
    extraction_result = build_public_result(extraction_state)
    extraction_sync = sync_extraction_state(engine, extraction_state)
    summary["steps"]["m06_m07_online_extraction"] = {
        "run_id": extraction_state.run_id,
        "article_id": first_article["article_id"],
        "document_label": extraction_result.get("document_label"),
        "event_count": len(extraction_result.get("events", [])),
        "run_dir": extraction_state.run_dir,
        "postgres_sync": extraction_sync.__dict__,
    }

    evaluation = run_evaluation_pipeline(
        gold_path="data/labels/events_gold.jsonl",
        runs_dir="runs/extraction",
        retrieval_metrics_path="reports/evaluation/retrieval_metrics.csv",
        output_dir="reports/evaluation",
        default_config_name="live_m00_m08",
    )
    summary["steps"]["m08_evaluation"] = evaluation.__dict__

    summary_path = Path(args.summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    summary["summary_path"] = str(summary_path)
    return summary


def _first_article(path: str) -> dict[str, Any]:
    articles = read_jsonl(path)
    if not articles:
        raise RuntimeError(f"No clean articles found in {path}.")
    return articles[0]


if __name__ == "__main__":
    main()
