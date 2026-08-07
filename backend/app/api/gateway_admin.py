"""Gateway ops API — route table, provider control, budget, kill switch."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth import require_admin
from app.gateway import gateway_enabled
from app.gateway.budget import gateway_budget
from app.gateway.config import get_routes
from app.gateway.health import provider_health
from app.gateway.kie_keys import kie_key_pool_status
from app.gateway.metrics import gateway_metrics
from app.gateway.registry import gateway_registry
from app.gateway.router import route_summary
from app.models.user import User

router = APIRouter()


class ProviderAction(BaseModel):
    provider: str
    remote_model: str
    reason: str = ""


class KillSwitchBody(BaseModel):
    active: bool


@router.get("/health", summary="Gateway 公开健康摘要（无密钥）")
async def gateway_health_public():
    providers = provider_health.all_snapshots()
    open_circuits = sum(1 for p in providers if p.circuit_open)
    reg = gateway_registry.snapshot()
    return {
        "enabled": gateway_enabled() and not reg["kill_switch"],
        "route_count": route_summary()["route_count"],
        "provider_hops": len(providers),
        "circuits_open": open_circuits,
        "healthy": open_circuits == 0 and gateway_enabled() and not reg["kill_switch"],
        "kill_switch": reg["kill_switch"],
        "registry_version": reg["version"],
        "kie_key_pool": kie_key_pool_status(),
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
        "budget_caps": {
            "user_daily": gateway_budget.status().get("user_daily_cap"),
            "team_daily": gateway_budget.status().get("team_daily_cap"),
        },
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
async def reload_routes(_: User = Depends(require_admin)):
    routes = get_routes(reload=True)
    return {"ok": True, "route_count": len(routes), "registry_version": gateway_registry.version()}


@router.post("/providers/disable", summary="紧急下线 Provider SKU")
async def disable_provider(body: ProviderAction, _: User = Depends(require_admin)):
    gateway_registry.disable_provider(body.provider, body.remote_model, reason=body.reason)
    return {"ok": True, "disabled": f"{body.provider}:{body.remote_model}"}


@router.post("/providers/enable", summary="恢复 Provider SKU")
async def enable_provider(body: ProviderAction, _: User = Depends(require_admin)):
    gateway_registry.enable_provider(body.provider, body.remote_model)
    provider_health.record_success(body.provider, body.remote_model)
    return {"ok": True, "enabled": f"{body.provider}:{body.remote_model}"}


@router.post("/providers/reset-circuit", summary="重置 Provider 熔断")
async def reset_circuit(body: ProviderAction, _: User = Depends(require_admin)):
    provider_health.record_success(body.provider, body.remote_model)
    return {"ok": True, "reset": f"{body.provider}:{body.remote_model}"}


@router.post("/kill-switch", summary="全局 Gateway 紧急开关")
async def kill_switch(body: KillSwitchBody, _: User = Depends(require_admin)):
    gateway_registry.set_kill_switch(body.active)
    return {"ok": True, "kill_switch": body.active}


@router.get("/routes", summary="路由表只读列表")
async def list_routes(_: User = Depends(require_admin)):
    return route_summary()
