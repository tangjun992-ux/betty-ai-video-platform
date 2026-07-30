#!/usr/bin/env bash
# Container entrypoint: bring the schema up to date, then hand off to the
# service command (API / worker / beat). Migrations are idempotent, but to
# avoid concurrent `alembic upgrade` races across replicas only ONE role should
# run them — set RUN_MIGRATIONS=1 on a single service (the API) and
# RUN_MIGRATIONS=0 on workers/beat.
set -euo pipefail

RUN_MIGRATIONS="${RUN_MIGRATIONS:-1}"

if [ "${RUN_MIGRATIONS}" = "1" ]; then
  echo "[entrypoint] Waiting for database, then running 'alembic upgrade head'..."
  # Retry a few times in case the DB container is still coming up.
  for attempt in 1 2 3 4 5 6 7 8; do
    if alembic upgrade head; then
      echo "[entrypoint] Migrations applied."
      break
    fi
    echo "[entrypoint] alembic upgrade failed (attempt ${attempt}); retrying in 3s..."
    sleep 3
    if [ "${attempt}" = "8" ]; then
      echo "[entrypoint] ERROR: migrations did not apply after retries." >&2
      exit 1
    fi
  done
else
  echo "[entrypoint] RUN_MIGRATIONS=0 — skipping migrations for this role."
fi

exec "$@"
