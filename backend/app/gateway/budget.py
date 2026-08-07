"""Gateway spend caps — daily user/team budget guards."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)

PREFIX = "gw-budget"


@dataclass
class BudgetCheckResult:
    allowed: bool
    reason: str = ""
    spent_today: float = 0.0
    cap: float = 0.0


class GatewayBudget:
    """Redis-backed daily spend counters for abuse / cost protection."""

    def __init__(self):
        self._redis = None
        self._memory: dict[str, float] = {}
        self._lock = threading.Lock()

    def _client(self):
        if self._redis is None:
            try:
                import redis
                self._redis = redis.Redis.from_url(
                    settings.REDIS_URL, decode_responses=True, socket_timeout=1,
                )
            except Exception:
                self._redis = False
        return self._redis if self._redis is not False else None

    def _day_key(self, scope: str) -> str:
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"{PREFIX}:{day}:{scope}"

    def _get_spent(self, scope: str) -> float:
        client = self._client()
        if client:
            try:
                return float(client.get(self._day_key(scope)) or 0)
            except Exception:
                pass
        with self._lock:
            return self._memory.get(scope, 0.0)

    def _add_spent(self, scope: str, amount: float) -> None:
        client = self._client()
        key = self._day_key(scope)
        if client:
            try:
                pipe = client.pipeline()
                pipe.incrbyfloat(key, amount)
                pipe.expire(key, 86400 * 2)
                pipe.execute()
                return
            except Exception:
                pass
        with self._lock:
            self._memory[scope] = self._memory.get(scope, 0.0) + amount

    def check(
        self,
        *,
        user_id: int | None = None,
        team_id: str | None = None,
        estimated_cost: float = 0.0,
    ) -> BudgetCheckResult:
        if gateway_registry_kill_blocked():
            return BudgetCheckResult(False, "gateway kill switch active")

        user_cap = float(getattr(settings, "GATEWAY_USER_DAILY_CREDIT_CAP", 0) or 0)
        team_cap = float(getattr(settings, "GATEWAY_TEAM_DAILY_CREDIT_CAP", 0) or 0)

        if team_id and team_cap > 0:
            spent = self._get_spent(f"team:{team_id}")
            if spent + estimated_cost > team_cap:
                return BudgetCheckResult(
                    False,
                    f"团队今日 Gateway 额度已用尽 ({spent:.0f}/{team_cap:.0f} credits)",
                    spent, team_cap,
                )

        if user_id and user_cap > 0:
            spent = self._get_spent(f"user:{user_id}")
            if spent + estimated_cost > user_cap:
                return BudgetCheckResult(
                    False,
                    f"今日 Gateway 额度已用尽 ({spent:.0f}/{user_cap:.0f} credits)",
                    spent, user_cap,
                )

        return BudgetCheckResult(True)

    def record(
        self,
        cost: float,
        *,
        user_id: int | None = None,
        team_id: str | None = None,
    ) -> None:
        if cost <= 0:
            return
        if team_id:
            self._add_spent(f"team:{team_id}", cost)
        if user_id:
            self._add_spent(f"user:{user_id}", cost)

    def status(self, *, user_id: int | None = None, team_id: str | None = None) -> dict:
        user_cap = float(getattr(settings, "GATEWAY_USER_DAILY_CREDIT_CAP", 0) or 0)
        team_cap = float(getattr(settings, "GATEWAY_TEAM_DAILY_CREDIT_CAP", 0) or 0)
        out: dict = {
            "user_daily_cap": user_cap,
            "team_daily_cap": team_cap,
        }
        if user_id:
            spent = self._get_spent(f"user:{user_id}")
            out["user_spent_today"] = spent
            out["user_remaining"] = max(0.0, user_cap - spent) if user_cap > 0 else None
        if team_id:
            spent = self._get_spent(f"team:{team_id}")
            out["team_spent_today"] = spent
            out["team_remaining"] = max(0.0, team_cap - spent) if team_cap > 0 else None
        return out


def gateway_registry_kill_blocked() -> bool:
    from app.gateway.registry import gateway_registry
    return gateway_registry.kill_switch_active()


gateway_budget = GatewayBudget()
