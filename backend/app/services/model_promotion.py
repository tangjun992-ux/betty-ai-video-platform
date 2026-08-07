"""Runtime model status promotion (admin) with catalog integrity checks."""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Literal

from fastapi import HTTPException

logger = logging.getLogger(__name__)

from app.services.model_catalog import (
    GATEWAY_GUESS_IDS,
    GATEWAY_MAPPED_BETA_IDS,
    GATEWAY_VERIFIED_IDS,
)

_EXCHANGE_TTL_S = 120
_oidc_exchange: dict[str, tuple[str, float]] = {}


def store_oidc_exchange(code: str, jwt_token: str) -> None:
    _purge_oidc_exchange()
    _oidc_exchange[code] = (jwt_token, time.time())


def take_oidc_exchange(code: str) -> str | None:
    _purge_oidc_exchange()
    row = _oidc_exchange.pop(code, None)
    if not row:
        return None
    token, created = row
    if time.time() - created > _EXCHANGE_TTL_S:
        return None
    return token


def _purge_oidc_exchange() -> None:
    now = time.time()
    expired = [k for k, (_, ts) in _oidc_exchange.items() if now - ts > _EXCHANGE_TTL_S]
    for k in expired:
        _oidc_exchange.pop(k, None)


def _find_model(model_id: str):
    from app.api.models_info import MODELS

    for m in MODELS:
        if m.id == model_id:
            return m
    return None


def promote_model(model_id: str, *, note: str | None = None) -> dict:
    """Promote beta/mapped model to active after admin review."""
    mid = model_id.strip()
    m = _find_model(mid)
    if not m:
        raise HTTPException(status_code=404, detail=f"模型不存在: {mid}")
    if mid in GATEWAY_GUESS_IDS:
        raise HTTPException(status_code=400, detail=f"{mid} 仍为未验真 guess SKU，禁止晋升 active")
    if mid not in GATEWAY_VERIFIED_IDS and mid not in GATEWAY_MAPPED_BETA_IDS:
        raise HTTPException(status_code=400, detail=f"{mid} 不在可晋升白名单（需 KIE 映射）")
    if m.status == "active":
        return {"model_id": mid, "status": "active", "already": True, "note": note}
    m.status = "active"
    from app.services.model_health import model_health

    model_health.clear_quarantine(mid)
    return {"model_id": mid, "status": "active", "already": False, "note": note}


_OUTFRAME_PATHS = frozenset({
    "live_image", "live_video", "live_image_gateway", "live_video_gateway",
})


def auto_promote_enabled() -> bool:
    return os.getenv("MODEL_SMOKE_AUTO_PROMOTE", "").strip().lower() in ("1", "true", "yes", "on")


def maybe_auto_promote_from_smoke(report: dict[str, Any]) -> dict[str, Any]:
    """Promote mapped-beta models that passed paid outframe smoke (gated by env)."""
    if not auto_promote_enabled():
        return {"skipped": True, "reason": "MODEL_SMOKE_AUTO_PROMOTE not enabled", "promoted": []}
    if report.get("skipped"):
        return {"skipped": True, "reason": report.get("reason") or "smoke skipped", "promoted": []}

    promoted: list[str] = []
    already: list[str] = []
    for detail in report.get("details") or []:
        if not detail.get("ok"):
            continue
        path = (detail.get("evidence") or {}).get("path") or detail.get("path") or ""
        if path not in _OUTFRAME_PATHS:
            continue
        mid = detail.get("model_id")
        if not mid or mid not in GATEWAY_MAPPED_BETA_IDS:
            continue
        try:
            r = promote_model(mid, note="auto-promote from smoke outframe")
            if r.get("already"):
                already.append(mid)
            else:
                promoted.append(mid)
                logger.info("auto-promoted model %s from smoke (path=%s)", mid, path)
        except HTTPException as e:
            logger.warning("auto-promote skipped %s: %s", mid, e.detail)

    return {"skipped": False, "promoted": promoted, "already_active": already, "count": len(promoted)}


_MAPPING_PROMOTE_PATHS = frozenset({
    "mapping_only", "demo_render",
})


def mapping_promote_enabled() -> bool:
    return os.getenv("MODEL_SMOKE_MAPPING_PROMOTE", "").strip().lower() in ("1", "true", "yes", "on")


def maybe_promote_from_mapping_smoke(report: dict[str, Any]) -> dict[str, Any]:
    """Promote mapped-beta models that passed mapping smoke (gated; not outframe)."""
    if not mapping_promote_enabled():
        return {"skipped": True, "reason": "MODEL_SMOKE_MAPPING_PROMOTE not enabled", "promoted": []}
    if report.get("skipped"):
        return {"skipped": True, "reason": report.get("reason") or "smoke skipped", "promoted": []}

    promoted: list[str] = []
    for detail in report.get("details") or []:
        if not detail.get("ok"):
            continue
        path = (detail.get("evidence") or {}).get("path") or detail.get("path") or ""
        if path not in _MAPPING_PROMOTE_PATHS:
            continue
        mid = detail.get("model_id")
        if not mid or mid not in GATEWAY_MAPPED_BETA_IDS:
            continue
        try:
            r = promote_model(mid, note="auto-promote from mapping smoke")
            if not r.get("already"):
                promoted.append(mid)
                logger.info("mapping auto-promoted model %s (path=%s)", mid, path)
        except HTTPException as e:
            logger.warning("mapping auto-promote skipped %s: %s", mid, e.detail)

    return {"skipped": False, "promoted": promoted, "count": len(promoted)}


def demote_model(model_id: str, *, to: Literal["beta", "lab"] = "beta", note: str | None = None) -> dict:
    mid = model_id.strip()
    m = _find_model(mid)
    if not m:
        raise HTTPException(status_code=404, detail=f"模型不存在: {mid}")
    if mid in GATEWAY_VERIFIED_IDS and to != "beta":
        raise HTTPException(status_code=400, detail=f"{mid} 为已验真 SKU，仅可降级至 beta")
    m.status = to
    return {"model_id": mid, "status": to, "note": note}
