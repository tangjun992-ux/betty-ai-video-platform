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
        for field, value in kwargs.items():
            if value is not None:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                # Only allow known column names to avoid SQL injection via kwargs.
                if not field.replace("_", "").isalnum():
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
