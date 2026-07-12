# AGENTS.md

## Cursor Cloud specific instructions

This repo is a single product ("Betty", an AI image/video generation platform) with two
parts: a Python **backend** (`backend/`, FastAPI + Celery) and a Next.js **frontend**
(`frontend/`). See `docker-compose.yml` for the canonical service list and
`scripts/boot.py` for a full-stack boot reference.

### Environment already provisioned by the update script
The startup update script creates `backend/.venv` and installs backend + frontend deps.
It also installs `aiosqlite`, `pytest`, and `pytest-asyncio` (see below for why). System
packages `redis-server` and `python3.12-venv` are baked into the VM snapshot (do NOT add
them to the update script).

### Running the services (dev mode)
Redis must be running first (`redis-cli ping` should return `PONG`; if not, start it with
`sudo redis-server --daemonize yes`). Then, from the repo root:

- **Backend API** (`backend/`): `PYTHONPATH=. LOCAL_MODE=true .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Celery worker** (`backend/`): `PYTHONPATH=. LOCAL_MODE=true .venv/bin/python -m celery -A celery_app worker -Q video_q,image_q,pipeline_q,collector_q,celery --concurrency=4 --loglevel=info`
- **Frontend** (`frontend/`): `npm run dev` (serves on port 3000; the app calls the API via `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` from `.env.local`).

Run each long-lived service in its own tmux session.

### Non-obvious gotchas
- **Database defaults to SQLite, not Postgres.** `backend/app/config.py` falls back to
  `sqlite+aiosqlite:///./dev.db` when `DATABASE_URL` is unset. This requires the
  `aiosqlite` driver, which is **missing from `backend/requirements.txt`** — the update
  script installs it explicitly. Tables are auto-created on backend startup via
  `init_db()`, so no Alembic migration is needed for local dev. Docker/prod use Postgres
  instead (`docker-compose.yml`).
- **No Docker / Postgres in the cloud VM.** Run the services natively (as above) rather
  than via `docker compose`.
- **AI generation needs provider API keys.** Registering users, prompt analysis, model
  routing, and task queueing all work with no keys, but a submitted generation will reach
  the Celery worker and then **fail at the provider step** unless a key (e.g. `KIE_API_KEY`,
  set as an env var / secret) is present. A failed generation with no keys is expected.
- **Feed/gallery are global, not per-user isolated** — tasks from other sessions show up
  in a new account's feed.

### Lint / test caveats
- **Frontend lint is NOT configured.** `npm run lint` (`next lint`) prompts interactively
  because there is no ESLint config in the repo; it cannot run non-interactively.
- **Frontend tests:** `npm test` (vitest) works. One suite
  (`src/components/cosmic/__tests__/debug.test.tsx`) is an empty file and reports as a
  failed suite — pre-existing, unrelated to environment.
- **Backend tests** (`backend/tests/`) require the backend to already be running on
  `localhost:8000` (they make live HTTP calls). Run with `.venv/bin/python -m pytest`.
  Several assertions in `tests/test_api.py` are stale vs. the current API response shapes
  and fail regardless of environment — this is a pre-existing code/test mismatch.
