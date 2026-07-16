"""
WebSocket endpoint for real-time task progress updates.

Uses Redis pub/sub so progress works across multiple API replicas.
Falls back to in-process fan-out when Redis is unavailable (dev/tests).
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)

# Local connections on THIS process only
_subscribers: Dict[str, Set[WebSocket]] = {}
_redis_listener_started = False
_listener_lock = threading.Lock()
_main_loop: Optional[asyncio.AbstractEventLoop] = None

PROGRESS_CHANNEL = "betty:task-progress"


def _redis_client():
    import redis
    from app.config import settings
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2)


async def _local_broadcast(task_id: str, payload: dict) -> None:
    if task_id not in _subscribers:
        return
    dead = set()
    data = json.dumps(payload, ensure_ascii=False)
    for ws in list(_subscribers.get(task_id, set())):
        try:
            await ws.send_text(data)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _subscribers.get(task_id, set()).discard(ws)
    if task_id in _subscribers and not _subscribers[task_id]:
        del _subscribers[task_id]


def _ensure_redis_listener(loop: asyncio.AbstractEventLoop) -> None:
    """Background Redis→local fan-out, scheduled onto the API event loop."""
    global _redis_listener_started, _main_loop
    _main_loop = loop
    with _listener_lock:
        if _redis_listener_started:
            return
        _redis_listener_started = True

    def _loop():
        while True:
            try:
                client = _redis_client()
                pubsub = client.pubsub(ignore_subscribe_messages=True)
                pubsub.subscribe(PROGRESS_CHANNEL)
                for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    raw = message.get("data") or ""
                    try:
                        payload = json.loads(raw)
                    except Exception:
                        continue
                    task_id = payload.get("task_id")
                    if not task_id or _main_loop is None:
                        continue
                    try:
                        fut = asyncio.run_coroutine_threadsafe(
                            _local_broadcast(task_id, payload), _main_loop
                        )
                        fut.result(timeout=5)
                    except Exception as e:
                        logger.debug("ws redis fanout failed: %s", e)
            except Exception as e:
                logger.warning("ws redis listener reconnecting: %s", e)
                import time
                time.sleep(2)

    threading.Thread(target=_loop, name="ws-redis-listener", daemon=True).start()


@router.websocket("/ws/tasks/{task_id}")
async def task_progress_ws(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time task progress updates."""
    await websocket.accept()
    _ensure_redis_listener(asyncio.get_running_loop())

    if task_id not in _subscribers:
        _subscribers[task_id] = set()
    _subscribers[task_id].add(websocket)

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "task_id": task_id}))
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text(json.dumps({"type": "ping", "task_id": task_id}))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        _subscribers.get(task_id, set()).discard(websocket)
        if task_id in _subscribers and not _subscribers[task_id]:
            del _subscribers[task_id]


async def broadcast_task_progress(task_id: str, payload: dict):
    """Publish progress via Redis for all replicas; local fallback if Redis down."""
    payload = dict(payload)
    payload["task_id"] = task_id
    try:
        client = _redis_client()
        client.publish(PROGRESS_CHANNEL, json.dumps(payload, ensure_ascii=False))
        # Ensure listener is up so THIS replica also receives the pub/sub echo.
        if _main_loop is not None:
            _ensure_redis_listener(_main_loop)
        else:
            # No WS yet on this process (worker/Celery) — also try local (no-op if empty).
            await _local_broadcast(task_id, payload)
        return
    except Exception as e:
        logger.debug("ws redis publish failed, local only: %s", e)
        await _local_broadcast(task_id, payload)
