"""Load user/team/cost context for Gateway calls from Celery workers."""
from __future__ import annotations

from app.tasks.task_db import get_task_gateway_context


def gateway_call_kwargs(db_task_id: str, *, include_cost: bool = True) -> dict:
    """Standard kwargs for gateway.generate_* / execute_route from a task row."""
    ctx = get_task_gateway_context(db_task_id)
    return {
        "trace_id": db_task_id,
        "user_id": ctx.get("user_id"),
        "team_id": ctx.get("team_id"),
        "estimated_cost": float(ctx.get("estimated_cost") or 0) if include_cost else 0.0,
    }
