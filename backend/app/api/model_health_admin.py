"""
Model health admin API — review quarantined models and restore routing.

Requires admin privileges (same gate as moderation admin).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.db import get_db
from app.models.user import User
from app.services.model_health import model_health

router = APIRouter()


class QuarantineDecision(BaseModel):
    reason: str | None = Field(None, description="Optional review note")


class PromoteRequest(BaseModel):
    note: str | None = Field(None, description="Audit note for promotion")


@router.get("/promotable", summary="可晋升 active 的 beta 模型")
async def list_promotable(_: User = Depends(require_admin)):
    from app.api.models_info import MODELS
    from app.services.model_catalog import GATEWAY_MAPPED_BETA_IDS, GATEWAY_VERIFIED_IDS

    items = []
    for m in MODELS:
        if m.status == "beta" and m.id in GATEWAY_MAPPED_BETA_IDS:
            items.append({"model_id": m.id, "display_name": m.display_name, "status": m.status})
    return {
        "verified_active_count": sum(1 for m in MODELS if m.status == "active"),
        "promotable": items,
        "verified_set_size": len(GATEWAY_VERIFIED_IDS),
    }


@router.post("/{model_id}/promote", summary="晋升模型至 active（需 KIE 映射白名单）")
async def promote_model_endpoint(
    model_id: str,
    body: PromoteRequest | None = None,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services.model_promotion import promote_model
    from app.services.audit import record_audit

    result = promote_model(model_id, note=body.note if body else None)
    await record_audit(
        db,
        action="admin.promote_model",
        actor_user_id=user.id,
        target_type="model",
        target_id=model_id,
        meta=result,
    )
    await db.commit()
    return result


@router.post("/{model_id}/demote", summary="降级模型至 beta/lab")
async def demote_model_endpoint(
    model_id: str,
    body: QuarantineDecision,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services.model_promotion import demote_model
    from app.services.audit import record_audit

    result = demote_model(model_id, note=body.reason)
    await record_audit(
        db,
        action="admin.demote_model",
        actor_user_id=user.id,
        target_type="model",
        target_id=model_id,
        meta=result,
    )
    await db.commit()
    return result


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
                "name": m.name if hasattr(m, "name") else m.display_name,
                "status": m.status,
                "quarantined": model_health.is_quarantined(m.id),
                "circuit_open": snap.circuit_open,
                "health": snap.public_dict(),
            })
    return {"total": len(items), "models": items}


@router.get("/catalog", summary="目录诚信与验真状态")
async def admin_catalog(_: User = Depends(require_admin)):
    from app.services.model_catalog import catalog_integrity
    return catalog_integrity()


class SmokeRequest(BaseModel):
    mode: str | None = Field(None, description="mapping | live | live_video")


@router.post("/smoke", summary="触发模型健康冒烟（可 live）")
async def trigger_smoke(
    body: SmokeRequest | None = None,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services.model_smoke import run_active_smoke
    from app.services.audit import record_audit

    mode = (body.mode if body else None) or None
    result = run_active_smoke(mode=mode)
    await record_audit(
        db,
        action="admin.model_smoke",
        actor_user_id=user.id,
        target_type="catalog",
        meta={"mode": result.get("mode"), "ok": result.get("ok"), "failed": result.get("failed")},
    )
    await db.commit()
    return result


@router.get("/last-smoke", summary="最近一次模型冒烟报告")
async def last_smoke(_: User = Depends(require_admin)):
    from app.services.model_smoke import get_last_smoke
    report = get_last_smoke()
    if not report:
        return {"available": False, "report": None}
    return {"available": True, "report": report}


@router.get("/audit", summary="管理审计日志")
async def admin_audit(
    limit: int = 50,
    action: str | None = None,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services.audit import list_audit
    rows = await list_audit(db, limit=limit, action=action)
    return {"total": len(rows), "items": rows}


@router.post("/{model_id}/clear-quarantine", summary="解除模型隔离（复核通过）")
async def clear_quarantine(
    model_id: str,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if not model_id.strip():
        raise HTTPException(status_code=400, detail="model_id required")
    model_health.clear_quarantine(model_id)
    model_health.reset(model_id)
    from app.services.audit import record_audit
    await record_audit(
        db,
        action="admin.clear_quarantine",
        actor_user_id=user.id,
        target_type="model",
        target_id=model_id,
    )
    await db.commit()
    return {"model_id": model_id, "quarantined": False, "circuit_open": False}


@router.post("/{model_id}/quarantine", summary="手动隔离模型")
async def manual_quarantine(
    model_id: str,
    body: QuarantineDecision,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    reason = body.reason or "manual admin quarantine"
    model_health.set_quarantine(model_id, reason=reason)
    from app.services.audit import record_audit
    await record_audit(
        db,
        action="admin.quarantine",
        actor_user_id=user.id,
        target_type="model",
        target_id=model_id,
        meta={"reason": reason},
    )
    await db.commit()
    return {"model_id": model_id, "quarantined": True, "reason": reason}
