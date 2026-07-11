"""
Observability — request tracing, structured access logs, and optional Sentry.

- RequestContextMiddleware: assigns an X-Request-ID, times each request, and
  emits a structured (JSON) access log line; sets the id on the response.
- init_sentry(): activates Sentry error reporting when SENTRY_DSN is configured
  (no-op otherwise, and gracefully skipped if sentry-sdk isn't installed).
"""
from __future__ import annotations

import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings

logger = logging.getLogger("betty.access")


def configure_logging() -> None:
    level = getattr(logging, (settings.LOG_LEVEL or "INFO").upper(), logging.INFO)
    root = logging.getLogger()
    if not root.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        root.addHandler(h)
    root.setLevel(level)


def init_sentry() -> bool:
    """Initialise Sentry when a DSN is set. Returns True if active."""
    if not settings.SENTRY_DSN:
        return False
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENV,
            traces_sample_rate=0.1,
            release=f"betty@{settings.APP_VERSION}",
        )
        logger.info("sentry initialised")
        return True
    except Exception as e:  # sentry-sdk missing or misconfigured — never block boot
        logger.warning("sentry init skipped: %s", e)
        return False


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = rid
        start = time.monotonic()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            dur_ms = int((time.monotonic() - start) * 1000)
            path = request.url.path
            # Skip noisy static media in access logs
            if not path.startswith("/api/v1/media"):
                try:
                    logger.info(json.dumps({
                        "evt": "http",
                        "rid": rid,
                        "method": request.method,
                        "path": path,
                        "status": status,
                        "ms": dur_ms,
                        "ip": (request.client.host if request.client else None),
                    }, ensure_ascii=False))
                except Exception:
                    pass
