"""Gateway ops API — route table, provider control, budget, kill switch."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.auth import require_admin
from app.config import settings
from app.db import get_db
from app.gateway import gateway_enabled
from app.gateway.budget import gateway_budget
from app.gateway.config import get_routes, validate_routes
from app.gateway.health import provider_health
from app.gateway.kie_keys import kie_key_pool_status
from app.gateway.metrics import gateway_metrics
from app.gateway.provider_limit import gateway_provider_limit
from app.gateway.registry import gateway_registry
from app.gateway.router import route_summary
from app.models.user import User
from app.services.audit import record_audit
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class ProviderAction(BaseModel):
    provider: str
    remote_model: str
    reason: str = ""


class KillSwitchBody(BaseModel):
    active: bool


def _public_health_minimal() -> bool:
    raw = (getattr(settings, "GATEWAY_HEALTH_PUBLIC_MINIMAL", "") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    return settings.is_production


@router.get("/health", summary="Gateway 公开健康摘要（无密钥）")
async def gateway_health_public():
    reg = gateway_registry.snapshot()
    enabled = gateway_enabled() and not reg["kill_switch"]
    if _public_health_minimal():
        return {
            "enabled": enabled,
            "healthy": enabled,
            "route_count": route_summary()["route_count"],
        }
    providers = provider_health.all_snapshots()
    open_circuits = sum(1 for p in providers if p.circuit_open)
    pool = kie_key_pool_status()
    return {
        "enabled": enabled,
        "route_count": route_summary()["route_count"],
        "provider_hops": len(providers),
        "circuits_open": open_circuits,
        "healthy": open_circuits == 0 and enabled,
        "kill_switch": reg["kill_switch"],
        "registry_version": reg["version"],
        "kie_key_pool": {
            "configured": pool.get("configured", 0),
            "pool_enabled": pool.get("pool_enabled", False),
        },
    }


@router.get("/status", summary="Gateway 路由与 Provider 健康（Admin）")
async def gateway_status(_: User = Depends(require_admin)):
    providers = provider_health.all_snapshots()
    backends = []
    try:
        from app.gateway.providers import list_backends
        for name, be in list_backends().items():
            backends.append({"name": name, "configured": be.is_configured()})
    except Exception:
        pass
    return {
        "enabled": gateway_enabled(),
        "kie_key_pool": kie_key_pool_status(),
        "registry": gateway_registry.snapshot(),
        "budget_caps": gateway_budget.status(),
        "provider_limits": gateway_provider_limit.limits_status(),
        "metrics": gateway_metrics.snapshot(),
        "backends": backends,
        "routes": route_summary(),
        "providers": [
            {
                "key": p.key,
                "successes": p.successes,
                "failures": p.failures,
                "consecutive_failures": p.consecutive_failures,
                "circuit_open": p.circuit_open,
                "available": p.available,
                "last_error": p.last_error,
                "admin_disabled": gateway_registry.is_disabled(*p.key.split(":", 1)),
            }
            for p in providers
        ],
    }


@router.post("/reload", summary="重新加载 routes.yaml")
async def reload_routes(
    request: Request,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    errs = validate_routes()
    if errs:
        return {"ok": False, "errors": errs, "route_count": 0}
    routes = get_routes(reload=True)
    await record_audit(
        db, action="admin.gateway.reload", actor_user_id=user.id,
        target_type="gateway", meta={"route_count": len(routes)},
        ip=request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True, "route_count": len(routes), "registry_version": gateway_registry.version()}


@router.post("/providers/disable", summary="紧急下线 Provider SKU")
async def disable_provider(
    body: ProviderAction,
    request: Request,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    key = f"{body.provider}:{body.remote_model}"
    gateway_registry.disable_provider(body.provider, body.remote_model, reason=body.reason)
    await record_audit(
        db, action="admin.gateway.disable_provider", actor_user_id=user.id,
        target_type="gateway_provider", target_id=key,
        meta={"reason": body.reason},
        ip=request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True, "disabled": key}


@router.post("/providers/enable", summary="恢复 Provider SKU")
async def enable_provider(
    body: ProviderAction,
    request: Request,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    key = f"{body.provider}:{body.remote_model}"
    gateway_registry.enable_provider(body.provider, body.remote_model)
    provider_health.record_success(body.provider, body.remote_model)
    await record_audit(
        db, action="admin.gateway.enable_provider", actor_user_id=user.id,
        target_type="gateway_provider", target_id=key,
        ip=request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True, "enabled": key}


@router.post("/providers/reset-circuit", summary="重置 Provider 熔断")
async def reset_circuit(
    body: ProviderAction,
    request: Request,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    key = f"{body.provider}:{body.remote_model}"
    provider_health.record_success(body.provider, body.remote_model)
    await record_audit(
        db, action="admin.gateway.reset_circuit", actor_user_id=user.id,
        target_type="gateway_provider", target_id=key,
        ip=request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True, "reset": key}


@router.post("/kill-switch", summary="全局 Gateway 紧急开关")
async def kill_switch(
    body: KillSwitchBody,
    request: Request,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    gateway_registry.set_kill_switch(body.active)
    await record_audit(
        db, action="admin.gateway.kill_switch", actor_user_id=user.id,
        target_type="gateway", meta={"active": body.active},
        ip=request.client.host if request.client else None,
    )
    await db.commit()
    return {"ok": True, "kill_switch": body.active}


@router.get("/routes", summary="路由表只读列表")
async def list_routes(_: User = Depends(require_admin)):
    return route_summary()
