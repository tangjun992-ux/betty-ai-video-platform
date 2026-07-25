# Security audit — betty-ai-video-platform

Scope: backend (FastAPI/Celery), frontend (Next.js), Docker/CI config.
Categories reviewed: hardcoded secrets, SQL injection, input validation, dependencies,
CORS, debug endpoints, authentication/authorization.

## Critical — fixed in this change

| # | Issue | Where | Fix |
|---|-------|-------|-----|
| 1 | Live KIE API key committed to the repo | `backend/test_kie_direct.py` | Key removed; the script now requires `KIE_API_KEY` from the environment. **The key is in git history and must be revoked.** |
| 2 | Payment callbacks trusted without signature verification — forged `POST /billing/pay/notify/{provider}` granted credits | `backend/app/api/billing.py`, `backend/app/services/payments.py` | Alipay RSA2 signature verification and WeChat Pay v3 signed/encrypted callback verification added; unverified callbacks are rejected (400) and never grant credits. Orders are also matched on provider. |
| 3 | Sandbox "mock confirm" endpoint could grant paid credits in production | `POST /billing/pay/mock-confirm/{order_no}` | Returns 404 when `ENV=production`. Dev-grant checkout path and unconfigured-provider order creation are also blocked in production. |
| 4 | Broken object-level authorization (IDOR): any caller could read/cancel tasks, read/modify/delete projects, read/modify/delete director sessions, delete library items belonging to others by ID | `api/tasks.py`, `api/projects.py`, `api/director.py`, `api/library.py` | All lookups now filter by the resolved caller (`resolve_user_id`); unknown/foreign IDs return 404. `POST /director/sessions` no longer takes `user_id` from the request body, and `GET /director/sessions` no longer takes it from the query string. |
| 5 | Path traversal in media URL → local path resolution: `/api/v1/media/../../etc/passwd` could be read by the ffmpeg composer/renderer | `app/tasks/timeline_tasks.py`, `app/adapters/demo_provider.py` | Paths are resolved and required to stay inside the media storage root. |
| 6 | SSRF: server fetched arbitrary user/provider URLs (with redirects) — reachable loopback, RFC1918 and `169.254.169.254` metadata | `app/services/media_store.py`, `api/generate.py` | `is_safe_remote_url()` resolves the host and rejects private/loopback/link-local/reserved targets; redirects are followed manually so every hop is re-checked. `image_url` / `webhook_url` are validated at the API boundary. |
| 7 | Insecure production defaults could ship silently (dev JWT signing secret, wildcard CORS) | `app/config.py`, `app/main.py`, `docker-compose.prod.yml` | `settings.validate_production()` runs at startup and refuses to boot in production with a known/short `JWT_SECRET` or `*` in `CORS_ORIGINS`; `allow_credentials` is disabled if origins are `*`. Prod compose now fails fast when `JWT_SECRET` / `POSTGRES_PASSWORD` are unset instead of falling back to `change-me-in-production` / `postgres`. |
| 8 | Vulnerable frontend dependencies (7 advisories, incl. critical `@auth/core`/`next-auth` auth bypass and Next.js issues) | `frontend/package.json` | `npm audit fix` + `next` 15.1.0 → 15.5.21 (build verified). |

## High / medium — hardened here

- **SQL identifier interpolation** in the Celery `_update_task` helpers (`UPDATE tasks SET {field} = :val`).
  Values were already parameterized, but column names were not validated. All six task modules now reject
  any field that is not an actual `Task` column.
- **No brute-force protection on auth**: `POST /auth/register` and `/auth/login` had no rate limit and no
  password/length constraints. Added rate limits (5/min register, 10/min login) and min-8-char passwords
  with bounded field lengths. `verify_password` now uses `hmac.compare_digest` and no longer raises on a
  malformed stored hash.
- **Unauthenticated/unlimited uploads**: `POST /upload` stored files under user 0 with no rate limit —
  now scoped to the resolved user and rate limited.
- **Gallery like/report** endpoints were unauthenticated and unlimited (vote/report-takedown abuse) —
  rate limited.
- **Rate limiter Redis target** was hardcoded to `localhost:6379` — now uses `settings.REDIS_URL`, so the
  limiter actually shares state across workers in Docker instead of silently falling back to per-process
  in-memory counters.

## Known issues NOT fixed (need product decisions)

1. **Guest account 0 is a shared identity.** Unauthenticated callers all resolve to `user_id = 0`, so
   guests still share tasks, projects, library items and credits with each other. The ownership checks
   added above stop cross-*account* access, not guest-to-guest access. Fixing this properly means either
   requiring auth on those routes or issuing per-guest tokens.
2. **`GET /metrics` is public** and exposes operational internals; it should be restricted to the
   monitoring network or put behind auth.
3. **`X-Forwarded-For` is trusted unconditionally** by the rate limiter; if the API is reachable without
   going through the reverse proxy, IP buckets can be spoofed. Trust only the proxy's client IP.
4. **Remaining npm advisories** (`next`, `postcss`, `sharp`, `next-auth`) have no non-breaking fixed
   release available at the time of this audit — re-run `npm audit` once upstream ships one.
5. **Upload content sniffing**: uploads are validated by extension and size only; magic-byte/content-type
   validation and streaming (rather than `await file.read()` into memory) would be better.
6. **Development compose** uses `postgres`/`postgres` credentials — fine for local use, but must never be
   used as the production compose file.

## Action required outside the codebase

- **Revoke the KIE API key `e56cda27…` immediately.** It is present in git history (commit `592d04f`) and
  must be considered compromised; removing it from the working tree is not enough.
- Set `JWT_SECRET` (32+ random chars), `POSTGRES_PASSWORD` and explicit `CORS_ORIGINS` in the production
  environment — the app and prod compose file now refuse to start without them.
- Configure real WeChat/Alipay merchant credentials before enabling payments in production; without them
  checkout is now rejected instead of granting free credits.
