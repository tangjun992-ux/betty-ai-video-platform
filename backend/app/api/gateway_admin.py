"""Gateway ops API — route table + provider health."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_admin
from app.gateway import gateway_enabled
from app.gateway.health import provider_health
from app.gateway.kie_keys import kie_key_pool_status
from app.gateway.router import route_summary
from app.models.user import User

router = APIRouter()


@router.get("/health", summary="Gateway 公开健康摘要（无密钥）")
async def gateway_health_public():
    """Lightweight health for load balancers / uptime monitors."""
    providers = provider_health.all_snapshots()
    open_circuits = sum(1 for p in providers if p.circuit_open)
    return {
        "enabled": gateway_enabled(),
        "route_count": route_summary()["route_count"],
        "provider_hops": len(providers),
        "circuits_open": open_circuits,
        "healthy": open_circuits == 0 and gateway_enabled(),
        "kie_key_pool": kie_key_pool_status(),
    }


@router.get("/status", summary="Gateway 路由与 Provider 健康")
async def gateway_status(_: User = Depends(require_admin)):
    """Ops snapshot: enabled flag, routes, provider circuit states."""
    providers = provider_health.all_snapshots()
    return {
        "enabled": gateway_enabled(),
        "kie_key_pool": kie_key_pool_status(),
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
            }
            for p in providers
        ],
    }
