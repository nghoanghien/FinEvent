"""FastAPI endpoints for operational project APIs."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from finevent.api.cors import get_allowed_origins
from finevent.api.job_runner import ensure_dispatcher_started, reconcile_interrupted_runs
from finevent.db import get_sqlalchemy_engine
from finevent.ingestion.ticker_sql import TickerUpsertPayload, upsert_ticker_payloads

try:
    from fastapi import FastAPI, HTTPException, Query, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    from sqlalchemy import text
except ImportError as exc:  # pragma: no cover - exercised only when API extra is missing
    raise RuntimeError("Install the api extra before running the FastAPI app.") from exc

from finevent.api.admin_db import router as admin_db_router
from finevent.api.admin_health import router as admin_health_router
from finevent.api.admin_outputs import router as admin_outputs_router
from finevent.api.admin_reports import router as admin_reports_router
from finevent.api.admin_runs import router as admin_runs_router
from finevent.api.admin_workflows import router as admin_workflows_router
from finevent.api.auth import admin_auth_middleware


class TickerUpsertRequest(BaseModel):
    ticker: str | None = Field(default=None, min_length=2, max_length=10)
    company_name: str
    aliases: list[str] = Field(default_factory=list)
    sector: str | None = None
    exchange: str = "UNKNOWN"
    status: str = "ACTIVE"
    source_note: str | None = "api_update"
    source_url: str | None = None
    last_verified_at: str | None = None


class BulkTickerUpsertRequest(BaseModel):
    records: list[TickerUpsertRequest]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    reconcile_interrupted_runs()
    ensure_dispatcher_started()
    yield


app = FastAPI(title="FinEvent-VN API", version="0.1.0", lifespan=lifespan)
allowed_origins = get_allowed_origins()
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", "X-Admin-API-Key"],
    )
app.middleware("http")(admin_auth_middleware)
app.include_router(admin_health_router)
app.include_router(admin_reports_router)
app.include_router(admin_runs_router)
app.include_router(admin_workflows_router)
app.include_router(admin_db_router)
app.include_router(admin_outputs_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error_code" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "HTTP_ERROR",
            "message": str(exc.detail),
            "details": {},
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dictionary/tickers")
def search_tickers(
    query: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, Any]]:
    search_query = f"%{query.lower()}%" if query else None
    sql = text(
        """
        SELECT
            ticker,
            company_name,
            sector,
            exchange,
            status,
            source_note,
            source_url,
            last_verified_at,
            aliases
        FROM ticker_company_search
        WHERE
            :query IS NULL
            OR lower(ticker) LIKE :query
            OR lower(company_name) LIKE :query
            OR EXISTS (
                SELECT 1
                FROM jsonb_array_elements_text(aliases) alias
                WHERE lower(alias) LIKE :query
            )
        ORDER BY ticker
        LIMIT :limit
        """
    )
    with get_sqlalchemy_engine().begin() as connection:
        rows = connection.execute(sql, {"query": search_query, "limit": limit}).mappings().all()
    return [dict(row) for row in rows]


@app.put("/dictionary/tickers/{ticker}")
def upsert_ticker(ticker: str, payload: TickerUpsertRequest) -> dict[str, Any]:
    record = _to_payload(payload, ticker_override=ticker)
    result = upsert_ticker_payloads(get_sqlalchemy_engine(), [record], source_type="api")
    return {
        "sync_run_id": result.sync_run_id,
        "upserted_companies": result.upserted_companies,
        "upserted_aliases": result.upserted_aliases,
    }


@app.post("/dictionary/tickers/bulk-upsert")
def bulk_upsert_tickers(payload: BulkTickerUpsertRequest) -> dict[str, Any]:
    records = [_to_payload(record) for record in payload.records]
    result = upsert_ticker_payloads(get_sqlalchemy_engine(), records, source_type="api_bulk")
    return {
        "sync_run_id": result.sync_run_id,
        "upserted_companies": result.upserted_companies,
        "upserted_aliases": result.upserted_aliases,
    }


def _to_payload(
    request: TickerUpsertRequest,
    *,
    ticker_override: str | None = None,
) -> TickerUpsertPayload:
    ticker = ticker_override or request.ticker
    if not ticker:
        raise HTTPException(status_code=422, detail="ticker is required")
    return TickerUpsertPayload(
        ticker=ticker.upper(),
        company_name=request.company_name,
        aliases=tuple(request.aliases),
        sector=request.sector,
        exchange=request.exchange.upper(),
        status=request.status.upper(),
        source_note=request.source_note,
        source_url=request.source_url,
        last_verified_at=request.last_verified_at,
    )
