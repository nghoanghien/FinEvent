from __future__ import annotations

import re
from pathlib import Path

import pytest

import finevent.database
from finevent.database.catalog import BASELINE_SQL_FILES, TABLE_COLUMNS, table_names
from finevent.database.cli import build_parser


def test_database_package_imports_without_sqlalchemy() -> None:
    assert finevent.database.get_database_url
    assert "articles" in table_names()


def test_database_cli_has_runtime_commands() -> None:
    parser = build_parser()

    assert parser.parse_args(["healthcheck"]).command == "healthcheck"
    assert parser.parse_args(["apply-migrations"]).command == "apply-migrations"
    assert parser.parse_args(["verify-pgvector"]).command == "verify-pgvector"


def test_database_catalog_covers_postgres_baseline_tables() -> None:
    migration_dir = Path("infra/postgres")
    discovered_tables: set[str] = set()
    for migration_name in BASELINE_SQL_FILES:
        sql_path = migration_dir / migration_name
        assert sql_path.exists(), f"Missing baseline SQL file: {migration_name}"
        sql = sql_path.read_text(encoding="utf-8")
        discovered_tables.update(
            match.group(1)
            for match in re.finditer(
                r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([a-zA-Z0-9_]+)",
                sql,
                flags=re.IGNORECASE,
            )
        )

    assert discovered_tables
    assert discovered_tables <= set(TABLE_COLUMNS)


def test_database_catalog_has_key_relationship_tables() -> None:
    required_tables = {
        "financial_news_documents",
        "financial_news_chunks",
        "financial_news_chunk_embeddings",
        "event_labeling_runs",
        "events_gold",
        "event_patterns",
        "event_pattern_embeddings",
        "extraction_runs",
        "extraction_node_traces",
    }

    assert required_tables <= set(table_names())
    assert "article_id" in TABLE_COLUMNS["financial_news_chunks"]
    assert "pattern_id" in TABLE_COLUMNS["event_pattern_embeddings"]
    assert "run_id" in TABLE_COLUMNS["extraction_node_traces"]


def test_sqlalchemy_metadata_matches_catalog_when_db_extra_is_installed() -> None:
    pytest.importorskip("sqlalchemy")
    from finevent.database.schema import metadata

    assert set(metadata.tables) == set(TABLE_COLUMNS)
    for table_name, columns in TABLE_COLUMNS.items():
        assert set(columns) == set(metadata.tables[table_name].columns.keys())


def test_alembic_skeleton_exists() -> None:
    assert Path("alembic.ini").exists()
    assert Path("infra/alembic/env.py").exists()
    assert Path("infra/alembic/script.py.mako").exists()
    assert Path("infra/alembic/versions/20260627_0001_baseline_schema.py").exists()
