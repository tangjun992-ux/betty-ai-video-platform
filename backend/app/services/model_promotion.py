"""Runtime model status promotion (admin) with catalog integrity checks."""
from __future__ import annotations

import time
from typing import Literal

from fastapi import HTTPException

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


def demote_model(model_id: str, *, to: Literal["beta", "lab"] = "beta", note: str | None = None) -> dict:
    mid = model_id.strip()
    m = _find_model(mid)
    if not m:
        raise HTTPException(status_code=404, detail=f"模型不存在: {mid}")
    if mid in GATEWAY_VERIFIED_IDS and to != "beta":
        raise HTTPException(status_code=400, detail=f"{mid} 为已验真 SKU，仅可降级至 beta")
    m.status = to
    return {"model_id": mid, "status": to, "note": note}
