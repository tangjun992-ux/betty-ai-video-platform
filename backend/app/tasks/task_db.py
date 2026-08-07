"""
Shared sync DB helpers for Celery task workers.

Centralizes task row updates and fires terminal-state hooks
(webhook delivery + user email notifications).
"""
from __future__ import annotations

import json
import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_TERMINAL = frozenset({"completed", "failed", "cancelled"})
_TASK_COLUMNS: frozenset[str] | None = None


def _valid_task_columns(engine) -> frozenset[str]:
    """Real column names on the tasks table (cached) — so an unknown kwarg like
    a stray ``result_url`` can never crash the whole update and fail a task that
    actually succeeded."""
    global _TASK_COLUMNS
    if _TASK_COLUMNS is None:
        try:
            from sqlalchemy import inspect as _inspect
            _TASK_COLUMNS = frozenset(c["name"] for c in _inspect(engine).get_columns("tasks"))
        except Exception:
            _TASK_COLUMNS = frozenset()
    return _TASK_COLUMNS


def get_db_url_sync() -> str:
    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    if db_url.startswith("sqlite+aiosqlite"):
        db_url = db_url.replace("sqlite+aiosqlite", "sqlite")
    elif db_url.startswith("postgresql+asyncpg"):
        db_url = db_url.replace("postgresql+asyncpg", "postgresql")
    return db_url


def update_task(db_task_id: str, **kwargs):
    """Update a task row by public task_id. Fires hooks on terminal status."""
    engine = create_engine(get_db_url_sync())
    with Session(engine) as session:
        row = session.execute(
            text("SELECT id FROM tasks WHERE task_id = :tid"),
            {"tid": db_task_id},
        ).first()
        if not row:
            return None
        task_pk = row[0]
        valid_cols = _valid_task_columns(engine)
        for field, value in kwargs.items():
            if value is not None:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                # Only allow known column names to avoid SQL injection via kwargs.
                if not field.replace("_", "").isalnum():
                    continue
                # Skip kwargs that aren't real columns (e.g. a stray result_url)
                # so one bad field can't crash the update and fail the task.
                if valid_cols and field not in valid_cols:
                    logger.warning("update_task: skipping unknown column %r", field)
                    continue
                session.execute(
                    text(f"UPDATE tasks SET {field} = :val WHERE id = :id"),
                    {"val": value, "id": task_pk},
                )
        session.commit()

    status = kwargs.get("status")
    if status in _TERMINAL:
        try:
            from app.services.task_hooks import on_task_terminal
            on_task_terminal(db_task_id, status=status)
        except Exception as e:
            logger.warning("task terminal hooks failed for %s: %s", db_task_id, e)
    return task_pk


def get_task_gateway_context(db_task_id: str) -> dict:
    """user_id, team_id (from consumption txn), estimated_cost for budget guards."""
    engine = create_engine(get_db_url_sync())
    with Session(engine) as session:
        row = session.execute(
            text(
                "SELECT t.user_id, t.estimated_cost, t.status, t.parameters, "
                "(SELECT team_id FROM transactions WHERE task_id = t.task_id "
                " AND type = 'consumption' ORDER BY id DESC LIMIT 1) AS team_id "
                "FROM tasks t WHERE t.task_id = :tid"
            ),
            {"tid": db_task_id},
        ).mappings().first()
        if not row:
            return {}
        params = row["parameters"]
        if isinstance(params, str) and params:
            try:
                params = json.loads(params)
            except Exception:
                params = {}
        elif not isinstance(params, dict):
            params = {}
        team_id = row.get("team_id")
        if not team_id and isinstance(params, dict):
            team_id = params.get("team_id")
        return {
            "user_id": row.get("user_id"),
            "team_id": str(team_id) if team_id else None,
            "estimated_cost": float(row.get("estimated_cost") or 0),
            "status": row.get("status"),
            "parameters": params,
        }


def update_task_parameters_gateway_meta(db_task_id: str, gateway_meta: dict) -> None:
    """Merge gateway routing metadata into tasks.parameters.gateway."""
    engine = create_engine(get_db_url_sync())
    with Session(engine) as session:
        row = session.execute(
            text("SELECT parameters FROM tasks WHERE task_id = :tid"),
            {"tid": db_task_id},
        ).first()
        if not row:
            return
        raw = row[0]
        if isinstance(raw, str) and raw:
            try:
                params = json.loads(raw)
            except Exception:
                params = {}
        elif isinstance(raw, dict):
            params = dict(raw)
        else:
            params = {}
        params["gateway"] = gateway_meta
        session.execute(
            text("UPDATE tasks SET parameters = :p WHERE task_id = :tid"),
            {"p": json.dumps(params, ensure_ascii=False), "tid": db_task_id},
        )
        session.commit()
