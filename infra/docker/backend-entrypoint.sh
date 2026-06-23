#!/usr/bin/env sh
set -eu

DB_WAIT_TIMEOUT_SECONDS="${FINEVENT_DB_WAIT_TIMEOUT_SECONDS:-120}"
DB_WAIT_INTERVAL_SECONDS="${FINEVENT_DB_WAIT_INTERVAL_SECONDS:-2}"

echo "[finevent-backend] Waiting for PostgreSQL/pgvector..."
deadline=$(( $(date +%s) + DB_WAIT_TIMEOUT_SECONDS ))

while true; do
  if python -m finevent.database.cli healthcheck >/tmp/finevent-db-healthcheck.json 2>/tmp/finevent-db-healthcheck.err; then
    echo "[finevent-backend] Database connection is ready."
    break
  fi

  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "[finevent-backend] Timed out waiting for database." >&2
    echo "[finevent-backend] Last healthcheck error:" >&2
    cat /tmp/finevent-db-healthcheck.err >&2 || true
    exit 1
  fi

  sleep "$DB_WAIT_INTERVAL_SECONDS"
done

if [ "${FINEVENT_SKIP_DB_MIGRATIONS:-false}" != "true" ]; then
  echo "[finevent-backend] Applying database migrations..."
  python -m finevent.database.cli apply-migrations

  echo "[finevent-backend] Verifying pgvector..."
  python -m finevent.database.cli verify-pgvector
else
  echo "[finevent-backend] Skipping database migrations because FINEVENT_SKIP_DB_MIGRATIONS=true."
fi

echo "[finevent-backend] Starting API: $*"
exec "$@"
