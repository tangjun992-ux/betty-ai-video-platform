"""
WebSocket endpoint for real-time task progress updates.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
from typing import Dict, Set

router = APIRouter()

# Connected clients: task_id -> set of websockets
_subscribers: Dict[str, Set[WebSocket]] = {}


@router.websocket("/ws/tasks/{task_id}")
async def task_progress_ws(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time task progress updates."""
    await websocket.accept()

    if task_id not in _subscribers:
        _subscribers[task_id] = set()
    _subscribers[task_id].add(websocket)

    try:
        while True:
            # Keep connection alive, client can send heartbeat
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # Client can send "ping"
                if data == "ping":
                    await _broadcast(task_id, {"type": "pong"})
            except asyncio.TimeoutError:
                await _broadcast(task_id, {"type": "ping"})
    except WebSocketDisconnect:
        _subscribers[task_id].discard(websocket)
        if not _subscribers[task_id]:
            del _subscribers[task_id]


async def broadcast_task_progress(task_id: str, payload: dict):
    """Send progress update to all subscribers of a task."""
    if task_id not in _subscribers:
        return
    payload["task_id"] = task_id
    dead = set()
    for ws in _subscribers[task_id]:
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            dead.add(ws)
    for ws in dead:
        _subscribers[task_id].discard(ws)
    if not _subscribers[task_id]:
        del _subscribers[task_id]
