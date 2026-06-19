# Dictionary Governance

## Purpose

`data/dictionaries/` stores metadata dictionaries used by Milestone 01. These
files are not gold labels. They provide deterministic hints for retrieval,
filtering, sampling and quality reports.

CSV files are seed/audit artifacts. The operational long-term copy should live
in PostgreSQL tables created by `infra/postgres/002_ticker_dictionary.sql`.

## Files

| File | Purpose |
| --- | --- |
| `ticker_company_map.csv` | Maps stock tickers to company names, aliases and sector hints. |
| `event_keyword_taxonomy.csv` | Maps financial event trigger phrases to `event_type` and `event_subtype`. |

## Ticker Dictionary Policy

The ticker dictionary is a curated seed list covering high-liquidity and
frequently mentioned Vietnamese listed companies across banking, real estate,
materials, energy, consumer, technology, securities, logistics, healthcare and
insurance.

Before submitting the final dataset, refresh and verify this file against
official exchange/company sources:

- HOSE/HSX listed securities pages: https://www.hsx.vn/
- HNX listed securities pages: https://www.hnx.vn/
- UPCoM/HNX public company pages: https://www.hnx.vn/
- Official investor-relations pages when a company has renamed or changed
  ticker/market.

The `source_note` column intentionally says `seed_verify_exchange_before_submission`
to prevent treating the seed list as a final official exchange master.

## Keyword Taxonomy Policy

The event keyword taxonomy follows `docs/schema/event-schema.md`. Each keyword
is stored in ASCII-folded Vietnamese so matching can be accent-insensitive:

- `trung thau` matches `trúng thầu`.
- `phat hanh trai phieu` matches `phát hành trái phiếu`.
- `bo nhiem` matches `bổ nhiệm`.

Keyword matches are only hints. A keyword such as `giay phep` can be noisy, so
downstream extraction and verification must still require evidence spans.

## Update Rules

1. Add new aliases when crawler logs show many articles with unmapped companies.
2. Add event keywords only when they map to a documented event type/subtype.
3. Keep ambiguous keywords at lower priority.
4. Do not use metadata hints as evaluation labels.
5. Re-run ingestion quality reports after every dictionary update.

## Audit Command

Run this after every dictionary update:

```bash
python -m finevent.ingestion.audit_dictionaries --fail-on-error
```

The command writes `reports/data/dictionary_audit.md`, which is ignored from
git like other generated reports.

## SQL Sync

After applying `infra/postgres/002_ticker_dictionary.sql`, sync the CSV seed into
PostgreSQL:

```bash
python -m finevent.ingestion.sync_ticker_dictionary \
  --csv-path data/dictionaries/ticker_company_map.csv
```

The sync writes:

- `ticker_companies`
- `ticker_company_aliases`
- `ticker_dictionary_sync_runs`

## API Update Flow

When the FastAPI backend is running with the `api` extra installed, ticker
dictionary updates should go through API upsert endpoints instead of manually
editing database rows:

```text
GET  /dictionary/tickers?query=HPG
PUT  /dictionary/tickers/{ticker}
POST /dictionary/tickers/bulk-upsert
```

Example payload for `PUT /dictionary/tickers/HPG`:

```json
{
  "company_name": "Hoa Phat Group",
  "aliases": ["Hoa Phat", "Tap doan Hoa Phat"],
  "sector": "materials_steel",
  "exchange": "HOSE",
  "status": "ACTIVE",
  "source_note": "verified_from_exchange",
  "source_url": "https://www.hsx.vn/",
  "last_verified_at": "2026-06-19T00:00:00+07:00"
}
```
