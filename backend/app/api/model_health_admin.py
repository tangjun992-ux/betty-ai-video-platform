"""
Model health admin API — review quarantined models and restore routing.

Requires admin privileges (same gate as moderation admin).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_admin
from app.models.user import User
from app.services.model_health import model_health

router = APIRouter()


class QuarantineDecision(BaseModel):
    reason: str | None = Field(None, description="Optional review note")


@router.get("/quarantined", summary="隔离中的模型列表")
async def list_quarantined(
    _: User = Depends(require_admin),
):
    """List models currently quarantined by smoke tests or circuit breaker."""
    from app.api.models_info import MODELS

    items = []
    for m in MODELS:
        snap = model_health.snapshot(m.id)
        if model_health.is_quarantined(m.id) or snap.circuit_open:
            items.append({
                "model_id": m.id,
                "name": m.name,
                "status": m.status,
                "quarantined": model_health.is_quarantined(m.id),
                "circuit_open": snap.circuit_open,
                "health": snap.public_dict(),
            })
    return {"total": len(items), "models": items}


@router.post("/{model_id}/clear-quarantine", summary="解除模型隔离（复核通过）")
async def clear_quarantine(
    model_id: str,
    _: User = Depends(require_admin),
):
    if not model_id.strip():
        raise HTTPException(status_code=400, detail="model_id required")
    model_health.clear_quarantine(model_id)
    model_health.reset(model_id)
    return {"model_id": model_id, "quarantined": False, "circuit_open": False}


@router.post("/{model_id}/quarantine", summary="手动隔离模型")
async def manual_quarantine(
    model_id: str,
    body: QuarantineDecision,
    _: User = Depends(require_admin),
):
    reason = body.reason or "manual admin quarantine"
    model_health.set_quarantine(model_id, reason=reason)
    return {"model_id": model_id, "quarantined": True, "reason": reason}
