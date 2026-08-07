"""Gateway ops API — route table + provider health."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth import require_admin
from app.gateway import gateway_enabled
from app.gateway.health import provider_health
from app.gateway.router import route_summary
from app.models.user import User

router = APIRouter()


@router.get("/status", summary="Gateway 路由与 Provider 健康")
async def gateway_status(_: User = Depends(require_admin)):
    """Ops snapshot: enabled flag, routes, provider circuit states."""
    providers = provider_health.all_snapshots()
    return {
        "enabled": gateway_enabled(),
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
