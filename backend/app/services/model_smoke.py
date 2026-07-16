"""
Model smoke probes — mapping integrity and optional live KIE generation.

Modes:
  mapping (default): verify KIE id map + adapter key + optional createTask accept
  live: paid mini-generation for image models when MODEL_SMOKE_LIVE=1
  live_video: also paid short video when MODEL_SMOKE_LIVE_VIDEO=1 (expensive)
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)


def smoke_mode() -> str:
    if os.getenv("MODEL_SMOKE_LIVE_VIDEO", "").lower() in ("1", "true", "yes"):
        return "live_video"
    if os.getenv("MODEL_SMOKE_LIVE", "").lower() in ("1", "true", "yes"):
        return "live"
    return "mapping"


def probe_model(model_id: str, media_types: list[str], *, mode: str | None = None) -> dict[str, Any]:
    """Probe one model. Returns {ok, latency_ms, error, mode, evidence}."""
    mode = mode or smoke_mode()
    started = time.monotonic()
    try:
        from app.adapters.demo_provider import demo_mode_active
        from app.adapters.kie_adapter import KIE_MODEL_IDS, KieAdapter, _resolve_kie_model_id

        if model_id not in KIE_MODEL_IDS:
            return _fail(started, mode, f"missing KIE map for {model_id}")

        kie_id = _resolve_kie_model_id(model_id)
        if demo_mode_active() or mode == "mapping":
            # Mapping / offline path: prove local capability without paid calls.
            if demo_mode_active():
                from app.adapters.demo_provider import render_demo_image, render_demo_video
                if "video" in media_types:
                    render_demo_video("health smoke", "320x180", 1, "cinematic")
                else:
                    render_demo_image("health smoke", "512x512", "cinematic", index=0)
                return _ok(started, mode, evidence={"kie_id": kie_id, "path": "demo_render"})

            adapter = KieAdapter()
            if not adapter.is_available():
                return _fail(started, mode, "KIE_API_KEY not configured")
            # Mapping mode with key: validate adapter + map only (no paid gen).
            return _ok(started, mode, evidence={"kie_id": kie_id, "path": "mapping_only", "key": True})

        # Live paid path
        adapter = KieAdapter()
        if not adapter.is_available():
            return _fail(started, mode, "KIE_API_KEY not configured for live smoke")

        import asyncio

        async def _live():
            if "image" in media_types:
                res = await adapter.generate_image(
                    "smoke test abstract color square",
                    model_id=model_id,
                    size="512x512",
                    count=1,
                )
                url = getattr(res, "media_url", "") or ""
                if not url:
                    raise RuntimeError("live image smoke returned empty url")
                return {"kie_id": kie_id, "path": "live_image", "url_prefix": url[:48]}
            if "video" in media_types:
                if mode != "live_video":
                    # Live image-only day: video models get mapping+key check only.
                    return {"kie_id": kie_id, "path": "live_skipped_video", "note": "set MODEL_SMOKE_LIVE_VIDEO=1"}
                # Seedance/Kling reject sub-5s durations (422 Invalid duration).
                res = await adapter.generate_video(
                    "smoke test short motion",
                    model_id=model_id,
                    duration=5,
                    resolution="720p",
                )
                url = getattr(res, "media_url", "") or ""
                if not url:
                    raise RuntimeError("live video smoke returned empty url")
                return {"kie_id": kie_id, "path": "live_video", "url_prefix": url[:48]}
            raise RuntimeError(f"unsupported media_types={media_types}")

        evidence = asyncio.run(_live())
        return _ok(started, mode, evidence=evidence)
    except Exception as e:
        logger.warning("probe_model %s failed: %s", model_id, e)
        return _fail(started, mode or "unknown", str(e))


def _ok(started: float, mode: str, *, evidence: dict) -> dict:
    return {
        "ok": True,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "error": "",
        "mode": mode,
        "evidence": evidence,
    }


def _fail(started: float, mode: str, error: str) -> dict:
    return {
        "ok": False,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "error": error,
        "mode": mode,
        "evidence": {},
    }


def run_active_smoke(*, mode: str | None = None) -> dict:
    """Smoke all active catalog models; update model_health."""
    from app.api.models_info import MODELS
    from app.services.model_health import model_health

    mode = mode or smoke_mode()
    active = [m for m in MODELS if m.status == "active"]
    results: dict[str, Any] = {
        "mode": mode,
        "probed": 0,
        "ok": 0,
        "failed": [],
        "quarantined": [],
        "skipped": [],
        "details": [],
        # Honest KPI: only paid gen paths count as "outframe"
        "outframe_ok": 0,
        "outframe_skipped": 0,
    }

    for m in active:
        results["probed"] += 1
        media = list(m.capabilities.media_types or ["image"])
        probe = probe_model(m.id, media, mode=mode)
        results["details"].append({"model_id": m.id, **probe})
        path = (probe.get("evidence") or {}).get("path") or ""
        is_skip = path.startswith("live_skipped")
        is_outframe = path in ("live_image", "live_video")
        is_mapping = path in ("mapping_only", "demo_render")
        if probe["ok"]:
            # Honesty: only paid outframe paths inflate success_rate used by Auto router.
            if is_outframe:
                model_health.record_success(m.id, probe["latency_ms"])
                model_health.clear_quarantine(m.id)
                results["ok"] += 1
                results["outframe_ok"] += 1
            elif is_skip:
                results["skipped"].append(m.id)
                results["outframe_skipped"] += 1
            elif is_mapping:
                # Mapping proves KIE id — clear quarantine but do NOT count as outframe success.
                model_health.clear_quarantine(m.id)
                results["ok"] += 1
            else:
                results["ok"] += 1
        else:
            # Mapping-only failures with demo active shouldn't quarantine production.
            quarantine = mode in ("live", "live_video") or "missing KIE map" in (probe["error"] or "")
            model_health.record_failure(m.id, probe["error"] or "smoke failed", retryable=True)
            results["failed"].append(m.id)
            if quarantine:
                from app.services.model_health import quarantine_ttl_for_reason
                ttl = quarantine_ttl_for_reason(probe["error"] or "")
                model_health.set_quarantine(m.id, reason=probe["error"] or "smoke failed", ttl=ttl)
                results["quarantined"].append(m.id)
                logger.error(
                    "MODEL_HEALTH_ALERT model=%s quarantined ttl=%ss reason=%s",
                    m.id, ttl, probe["error"],
                )
            else:
                logger.warning("model smoke soft-fail: %s — %s", m.id, probe["error"])

    logger.info(
        "model health smoke done: mode=%s probed=%d ok=%d quarantined=%d",
        mode, results["probed"], results["ok"], len(results["quarantined"]),
    )
    results["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        save_last_smoke(results)
    except Exception as e:
        logger.warning("persist last smoke failed: %s", e)
    return results


_LAST_SMOKE_KEY = "model-health:last-smoke"
_LAST_SMOKE_TTL = 7 * 24 * 3600


def save_last_smoke(report: dict) -> None:
    """Persist last smoke report for status/admin surfaces (Redis + memory fallback)."""
    from app.services.model_health import model_health
    import json as _json

    # Truncate evidence URLs for storage size; keep enough for ops.
    slim = {
        "ts": report.get("ts") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": report.get("mode"),
        "probed": report.get("probed", 0),
        "ok": report.get("ok", 0),
        "outframe_ok": report.get("outframe_ok", 0),
        "outframe_skipped": report.get("outframe_skipped", 0),
        "failed": list(report.get("failed") or [])[:50],
        "quarantined": list(report.get("quarantined") or [])[:50],
        "skipped": list(report.get("skipped") or [])[:50],
        "details": [],
    }
    for d in (report.get("details") or [])[:40]:
        ev = d.get("evidence") or {}
        slim["details"].append({
            "model_id": d.get("model_id"),
            "ok": d.get("ok"),
            "latency_ms": d.get("latency_ms"),
            "error": (d.get("error") or "")[:200],
            "mode": d.get("mode"),
            "path": ev.get("path"),
        })
    payload = _json.dumps(slim, ensure_ascii=False)
    try:
        client = model_health._client()
        client.set(_LAST_SMOKE_KEY, payload, ex=_LAST_SMOKE_TTL)
    except Exception:
        with model_health._lock:
            model_health._memory[_LAST_SMOKE_KEY] = slim


def get_last_smoke() -> dict | None:
    """Load last smoke report or None."""
    from app.services.model_health import model_health
    import json as _json

    try:
        client = model_health._client()
        raw = client.get(_LAST_SMOKE_KEY)
        if raw:
            return _json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        pass
    with model_health._lock:
        mem = model_health._memory.get(_LAST_SMOKE_KEY)
        return dict(mem) if isinstance(mem, dict) else None


DEFAULT_LIVE_VIDEO_SAMPLE = ("seedance-2.0-fast", "kling-2.5-turbo")
DEFAULT_LIVE_IMAGE_SAMPLE = ("gpt-image-2", "nano-banana", "nano-banana-pro", "imagen-4")


def run_live_video_sample(models: list[str] | tuple[str, ...] | None = None) -> dict:
    """Shared paid live-video sample (scripts + weekly Beat). Only live_video → outframe_ok."""
    from app.api.models_info import MODELS
    from app.services.model_health import model_health, quarantine_ttl_for_reason

    models = list(models or DEFAULT_LIVE_VIDEO_SAMPLE)
    by_id = {m.id: m for m in MODELS}
    report: dict[str, Any] = {
        "mode": "live_video_sample",
        "probed": 0,
        "ok": 0,
        "outframe_ok": 0,
        "outframe_skipped": 0,
        "failed": [],
        "quarantined": [],
        "skipped": [],
        "details": [],
    }
    for mid in models:
        m = by_id.get(mid)
        if not m:
            report["failed"].append(mid)
            report["details"].append({"model_id": mid, "ok": False, "error": "not in catalog"})
            continue
        report["probed"] += 1
        media = list(m.capabilities.media_types or ["video"])
        probe = probe_model(mid, media, mode="live_video")
        report["details"].append({"model_id": mid, **probe})
        path = (probe.get("evidence") or {}).get("path") or ""
        if probe.get("ok") and path == "live_video":
            model_health.record_success(mid, probe.get("latency_ms") or 0)
            model_health.clear_quarantine(mid)
            report["ok"] += 1
            report["outframe_ok"] += 1
        elif probe.get("ok"):
            report["skipped"].append(mid)
            report["outframe_skipped"] += 1
        else:
            err = probe.get("error") or "live_video sample failed"
            model_health.record_failure(mid, err, retryable=True)
            model_health.set_quarantine(mid, reason=err, ttl=quarantine_ttl_for_reason(err))
            report["failed"].append(mid)
            report["quarantined"].append(mid)

    report["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if report["probed"] > 0 and report["outframe_ok"] == 0:
        logger.error(
            "MODEL_HEALTH_ALERT live_video_sample outframe_ok=0 probed=%s failed=%s",
            report["probed"], report["failed"],
        )
    save_last_smoke(report)
    return report


def run_live_image_sample(models: list[str] | tuple[str, ...] | None = None) -> dict:
    """Paid live-image sample for active image SKUs — feeds Auto router honesty."""
    from app.api.models_info import MODELS
    from app.services.model_health import model_health, quarantine_ttl_for_reason

    models = list(models or DEFAULT_LIVE_IMAGE_SAMPLE)
    by_id = {m.id: m for m in MODELS}
    report: dict[str, Any] = {
        "mode": "live_image_sample",
        "probed": 0,
        "ok": 0,
        "outframe_ok": 0,
        "failed": [],
        "quarantined": [],
        "details": [],
    }
    for mid in models:
        m = by_id.get(mid)
        if not m:
            report["failed"].append(mid)
            report["details"].append({"model_id": mid, "ok": False, "error": "not in catalog"})
            continue
        report["probed"] += 1
        media = list(m.capabilities.media_types or ["image"])
        probe = probe_model(mid, media, mode="live")
        report["details"].append({"model_id": mid, **probe})
        path = (probe.get("evidence") or {}).get("path") or ""
        if probe.get("ok") and path == "live_image":
            model_health.record_success(mid, probe.get("latency_ms") or 0)
            model_health.clear_quarantine(mid)
            report["ok"] += 1
            report["outframe_ok"] += 1
        elif probe.get("ok"):
            # mapping-only under live mode should not happen for image; treat as soft
            report["ok"] += 1
        else:
            err = probe.get("error") or "live_image sample failed"
            model_health.record_failure(mid, err, retryable=True)
            model_health.set_quarantine(mid, reason=err, ttl=quarantine_ttl_for_reason(err))
            report["failed"].append(mid)
            report["quarantined"].append(mid)

    report["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_last_smoke(report)
    return report
