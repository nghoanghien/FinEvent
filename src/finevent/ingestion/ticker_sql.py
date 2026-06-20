"""PostgreSQL sync helpers for ticker dictionary data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from finevent.ingestion.metadata import CompanyEntry, _ascii_fold, load_company_dictionary
from finevent.ingestion.text import normalize_text
from finevent.logging_utils import create_run_id


@dataclass(frozen=True)
class TickerUpsertPayload:
    ticker: str
    company_name: str
    aliases: tuple[str, ...]
    sector: str | None = None
    exchange: str = "UNKNOWN"
    status: str = "ACTIVE"
    source_note: str | None = None
    source_url: str | None = None
    last_verified_at: str | None = None


@dataclass(frozen=True)
class TickerSyncResult:
    sync_run_id: str
    upserted_companies: int
    upserted_aliases: int


def normalize_alias(alias: str) -> str:
    return _ascii_fold(normalize_text(alias)).lower()


def company_entry_to_payload(entry: CompanyEntry) -> TickerUpsertPayload:
    return TickerUpsertPayload(
        ticker=entry.ticker,
        company_name=entry.company_name,
        aliases=entry.aliases,
        sector=entry.sector,
        source_note=entry.source_note,
        exchange=entry.exchange or "UNKNOWN",
        status=entry.status or "ACTIVE",
        source_url=entry.source_url,
        last_verified_at=entry.last_verified_at,
    )


def sync_ticker_dictionary_csv(
    engine: Any,
    *,
    csv_path: str | Path = "data/dictionaries/ticker_company_map.csv",
) -> TickerSyncResult:
    entries = load_company_dictionary(csv_path)
    payloads = [company_entry_to_payload(entry) for entry in entries]
    return upsert_ticker_payloads(
        engine,
        payloads,
        source_path=str(csv_path),
        source_type="csv_seed",
    )


def upsert_ticker_payloads(
    engine: Any,
    payloads: list[TickerUpsertPayload],
    *,
    source_path: str | None = None,
    source_type: str = "api",
) -> TickerSyncResult:
    sql = _sqlalchemy_text()
    sync_run_id = create_run_id("ticker_sync")
    upserted_aliases = 0

    with engine.begin() as connection:
        connection.execute(
            sql(
                """
                INSERT INTO ticker_dictionary_sync_runs
                    (sync_run_id, source_type, source_path, status)
                VALUES
                    (:sync_run_id, :source_type, :source_path, 'RUNNING')
                """
            ),
            {
                "sync_run_id": sync_run_id,
                "source_type": source_type,
                "source_path": source_path,
            },
        )

        for payload in payloads:
            connection.execute(
                sql(
                    """
                    INSERT INTO ticker_companies (
                        ticker,
                        company_name,
                        sector,
                        exchange,
                        status,
                        source_note,
                        source_url,
                        last_verified_at,
                        updated_at
                    )
                    VALUES (
                        :ticker,
                        :company_name,
                        :sector,
                        :exchange,
                        :status,
                        :source_note,
                        :source_url,
                        CAST(:last_verified_at AS TIMESTAMPTZ),
                        NOW()
                    )
                    ON CONFLICT (ticker)
                    DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        sector = EXCLUDED.sector,
                        exchange = EXCLUDED.exchange,
                        status = EXCLUDED.status,
                        source_note = EXCLUDED.source_note,
                        source_url = EXCLUDED.source_url,
                        last_verified_at = EXCLUDED.last_verified_at,
                        updated_at = NOW()
                    """
                ),
                {
                    "ticker": payload.ticker,
                    "company_name": payload.company_name,
                    "sector": payload.sector,
                    "exchange": payload.exchange,
                    "status": payload.status,
                    "source_note": payload.source_note,
                    "source_url": payload.source_url,
                    "last_verified_at": payload.last_verified_at,
                },
            )
            upserted_aliases += _replace_aliases(connection, sql, payload)

        connection.execute(
            sql(
                """
                UPDATE ticker_dictionary_sync_runs
                SET
                    upserted_companies = :upserted_companies,
                    upserted_aliases = :upserted_aliases,
                    completed_at = NOW(),
                    status = 'SUCCESS'
                WHERE sync_run_id = :sync_run_id
                """
            ),
            {
                "sync_run_id": sync_run_id,
                "upserted_companies": len(payloads),
                "upserted_aliases": upserted_aliases,
            },
        )

    return TickerSyncResult(
        sync_run_id=sync_run_id,
        upserted_companies=len(payloads),
        upserted_aliases=upserted_aliases,
    )


def _replace_aliases(connection: Any, sql: Any, payload: TickerUpsertPayload) -> int:
    connection.execute(
        sql("DELETE FROM ticker_company_aliases WHERE ticker = :ticker"),
        {"ticker": payload.ticker},
    )
    alias_values = [payload.company_name, *payload.aliases]
    seen: set[str] = set()
    inserted = 0
    for alias in alias_values:
        alias_text = normalize_text(alias)
        alias_norm = normalize_alias(alias_text)
        if not alias_text or alias_norm in seen:
            continue
        seen.add(alias_norm)
        connection.execute(
            sql(
                """
                INSERT INTO ticker_company_aliases (ticker, alias, alias_norm)
                VALUES (:ticker, :alias, :alias_norm)
                ON CONFLICT (ticker, alias_norm) DO NOTHING
                """
            ),
            {
                "ticker": payload.ticker,
                "alias": alias_text,
                "alias_norm": alias_norm,
            },
        )
        inserted += 1
    return inserted


def _sqlalchemy_text() -> Any:
    try:
        from sqlalchemy import text
    except ImportError as exc:
        raise RuntimeError(
            "SQLAlchemy is required for ticker dictionary sync. "
            "Install the ingestion or api extra first."
        ) from exc
    return text
