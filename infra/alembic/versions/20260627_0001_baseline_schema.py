"""Baseline PostgreSQL schema.

Revision ID: 20260627_0001
Revises:
Create Date: 2026-06-27
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "20260627_0001"
down_revision = None
branch_labels = None
depends_on = None

BASELINE_SQL_FILES = (
    "001_articles.sql",
    "002_ticker_dictionary.sql",
    "003_event_labels.sql",
    "004_retrieval.sql",
    "005_event_patterns.sql",
    "006_extraction_runs.sql",
    "007_verification_reports.sql",
)


def upgrade() -> None:
    sql_dir = Path(__file__).resolve().parents[3] / "infra" / "postgres"
    for sql_file in BASELINE_SQL_FILES:
        sql_path = sql_dir / sql_file
        if not sql_path.exists():
            raise FileNotFoundError(f"Missing baseline SQL file: {sql_path}")
        for statement in _split_sql_statements(sql_path.read_text(encoding="utf-8")):
            op.execute(statement)
    op.execute("ALTER TABLE IF EXISTS articles ADD COLUMN IF NOT EXISTS raw_html_path TEXT")


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for the baseline schema revision.")


def _split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False
    previous = ""
    for char in sql:
        if char == "'" and previous != "\\":
            in_single_quote = not in_single_quote
        if char == ";" and not in_single_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
        previous = char
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements
