"""Database operations for the PostgreSQL/pgvector runtime."""

from __future__ import annotations

import argparse
import json
from typing import Any

from finevent.database.catalog import MIGRATION_ORDER, table_names
from finevent.database.engine import get_database_url, get_sqlalchemy_engine
from finevent.paths import repo_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage FinEvent PostgreSQL/pgvector runtime.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("healthcheck", help="Check database connectivity.")
    subparsers.add_parser("apply-migrations", help="Apply infra/postgres SQL migrations in order.")
    subparsers.add_parser("verify-pgvector", help="Verify that the vector extension is installed.")
    subparsers.add_parser("summary", help="Print database URL and table/extension summary.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    engine = get_sqlalchemy_engine()

    if args.command == "healthcheck":
        print(json.dumps(healthcheck(engine), ensure_ascii=False, indent=2))
        return
    if args.command == "apply-migrations":
        print(json.dumps(apply_migrations(engine), ensure_ascii=False, indent=2))
        return
    if args.command == "verify-pgvector":
        print(json.dumps(verify_pgvector(engine), ensure_ascii=False, indent=2))
        return
    if args.command == "summary":
        print(json.dumps(database_summary(engine), ensure_ascii=False, indent=2))
        return
    raise SystemExit(f"Unknown command: {args.command}")


def healthcheck(engine: Any) -> dict[str, object]:
    sql = _sqlalchemy_text()
    with engine.connect() as connection:
        value = connection.execute(sql("SELECT 1")).scalar_one()
    return {"status": "ok", "select_1": value}


def apply_migrations(engine: Any) -> dict[str, object]:
    sql_dir = repo_root() / "infra" / "postgres"
    applied: list[str] = []
    sql_text = _sqlalchemy_text()
    with engine.begin() as connection:
        for migration_name in MIGRATION_ORDER:
            migration_path = sql_dir / migration_name
            if not migration_path.exists():
                raise FileNotFoundError(f"Missing PostgreSQL migration: {migration_path}")
            for statement in _split_sql_statements(migration_path.read_text(encoding="utf-8")):
                connection.execute(sql_text(statement))
            applied.append(migration_name)
    return {"status": "ok", "applied": applied}


def verify_pgvector(engine: Any) -> dict[str, object]:
    sql = _sqlalchemy_text()
    with engine.connect() as connection:
        extension = connection.execute(
            sql("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one_or_none()
        vector_type = connection.execute(
            sql("SELECT typname FROM pg_type WHERE typname = 'vector'")
        ).scalar_one_or_none()
    if extension != "vector" or vector_type != "vector":
        raise RuntimeError(
            "pgvector is not available. Start the Docker Compose database and run "
            "`finevent-db apply-migrations`."
        )
    return {"status": "ok", "extension": extension, "type": vector_type}


def database_summary(engine: Any) -> dict[str, object]:
    sql = _sqlalchemy_text()
    with engine.connect() as connection:
        existing_tables = [
            row[0]
            for row in connection.execute(
                sql(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                    """
                )
            )
        ]
        vector_installed = bool(
            connection.execute(
                sql("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ).scalar_one_or_none()
        )
    return {
        "database_url": _redact_database_url(get_database_url()),
        "vector_installed": vector_installed,
        "expected_table_count": len(table_names()),
        "existing_table_count": len(existing_tables),
        "existing_tables": existing_tables,
    }


def _sqlalchemy_text() -> Any:
    try:
        from sqlalchemy import text
    except ImportError as exc:
        raise RuntimeError("Install the db extra before running database commands.") from exc
    return text


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


def _redact_database_url(url: str) -> str:
    if "@" not in url or "://" not in url:
        return url
    scheme, rest = url.split("://", 1)
    credentials, host = rest.split("@", 1)
    user = credentials.split(":", 1)[0]
    return f"{scheme}://{user}:***@{host}"


if __name__ == "__main__":
    main()
