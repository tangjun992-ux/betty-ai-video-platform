"""
Shared helpers for Celery task modules: sync DB access, async bridging and
best-effort WebSocket progress broadcasting.
"""
import asyncio
import json
import logging
import os
from typing import Any, Awaitable, Callable, TypeVar

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar("T")


def get_db_url_sync() -> str:
    """Return DATABASE_URL with async drivers rewritten to their sync variants."""
    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    if db_url.startswith("sqlite+aiosqlite"):
        db_url = db_url.replace("sqlite+aiosqlite", "sqlite")
    elif db_url.startswith("postgresql+asyncpg"):
        db_url = db_url.replace("postgresql+asyncpg", "postgresql")
    return db_url


def update_task(db_task_id: str, **kwargs: Any) -> int | None:
    """Update non-None columns of the tasks row identified by task_id."""
    engine = create_engine(get_db_url_sync())
    with Session(engine) as session:
        stmt = text("SELECT id FROM tasks WHERE task_id = :tid")
        row = session.execute(stmt, {"tid": db_task_id}).first()
        if not row:
            return None
        task_pk = row[0]
        for field, value in kwargs.items():
            if value is not None:
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                session.execute(
                    text(f"UPDATE tasks SET {field} = :val WHERE id = :id"),
                    {"val": value, "id": task_pk},
                )
        session.commit()
        return task_pk


def load_adapters() -> Callable[..., Any]:
    """Lazy load adapters with error handling."""
    from app.adapters.registry import get_adapter, _load_all_adapters
    _load_all_adapters()
    return get_adapter


def run_async(coro: Awaitable[T]) -> T:
    """Run async code in a sync Celery context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def broadcast_progress(
    task_id: str,
    progress: int,
    stage: str,
    message: str = "",
    preview_url: str = "",
) -> None:
    """Send a real-time progress update via WebSocket (fire-and-forget)."""
    try:
        from app.api.websocket import broadcast_task_progress

        payload: dict[str, Any] = {
            "type": "progress",
            "progress": progress,
            "current_stage": stage,
            "message": message or stage,
        }
        if preview_url:
            payload["preview_url"] = preview_url

        run_async(broadcast_task_progress(task_id, payload))
    except Exception:
        pass  # WebSocket broadcast is best-effort, don't fail the task


def chdir_backend_root() -> None:
    """Ensure the worker CWD is the backend root (relative storage paths)."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if backend_dir not in os.getcwd():
        os.chdir(backend_dir)
