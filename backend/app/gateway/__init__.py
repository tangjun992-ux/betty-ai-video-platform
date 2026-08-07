"""Betty Model API Gateway — multi-provider routing with failover."""
from app.gateway.facade import GatewayFacade, gateway, gateway_enabled
from app.gateway.types import Capability, GatewayExecutionResult

__all__ = [
    "GatewayFacade",
    "gateway",
    "gateway_enabled",
    "Capability",
    "GatewayExecutionResult",
]
