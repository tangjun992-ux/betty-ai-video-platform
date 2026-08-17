"""Hosted MCP connector — Streamable HTTP JSON-RPC 2.0.

Yapper ships https://yapper.so/mcp/connector with account OAuth.
Betty's honest equivalent: the same tool surface over JSON-RPC, authenticated
with an existing `sk_betty_` API key (not a fake OAuth login).

Unauthenticated methods: initialize / tools/list / ping / notifications/*.
Spend and account tools require X-API-Key or Bearer sk_betty_...
"""
from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.api_key import ApiKey
from app.models.billing import UserBalance
from app.models.task import Task
from app.models.user import User

router = APIRouter()

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "betty"
SERVER_VERSION = "0.1.0"

HONESTY = (
    "Hosted MCP JSON-RPC。鉴权是 sk_betty_ API Key，不是 Yapper 式账号 OAuth。"
    "list_models 只返回已验证 active 货架，不宣称 54+ / Seedance 2.5 / Sora / Veo。"
    "generate 走与 Web 相同的入队管线；未配置上游 Key 或无 Redis/Celery 时会诚实失败。"
    "quote ETA 来自目录均时，不是实时 SLA。"
)


def _hash(secret: str) -> str:
    import hashlib
    return hashlib.sha256(secret.encode()).hexdigest()


def _rpc_result(req_id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _rpc_error(req_id: Any, code: int, message: str, data: Any = None) -> dict:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def _tool_text(payload: Any, is_error: bool = False) -> dict:
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return {"content": [{"type": "text", "text": text}], "isError": bool(is_error)}


TOOLS = [
    {
        "name": "list_models",
        "description": "List Betty verified (active) image/video models. Lab SKUs are excluded.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "media_type": {"type": "string", "description": "optional filter: image | video"},
            },
        },
    },
    {
        "name": "get_credits",
        "description": "Read the API-key owner's credit balance. Requires API key.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "quote_generation",
        "description": "Dry-run quote (credits + catalog ETA). Does not create a task. Requires API key.",
        "inputSchema": {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": {"type": "string"},
                "media_type": {"type": "string", "default": "auto"},
                "model": {"type": "string", "default": "auto"},
                "duration": {"type": "integer", "default": 5},
                "count": {"type": "integer", "default": 1},
            },
        },
    },
    {
        "name": "generate",
        "description": "Enqueue image or video generation on the same pipeline as the web app. Requires API key.",
        "inputSchema": {
            "type": "object",
            "required": ["prompt"],
            "properties": {
                "prompt": {"type": "string"},
                "media_type": {"type": "string", "default": "auto"},
                "model": {"type": "string", "default": "auto"},
                "duration": {"type": "integer", "default": 5},
                "count": {"type": "integer", "default": 1},
                "webhook_url": {"type": "string"},
            },
        },
    },
    {
        "name": "get_task",
        "description": "Poll a generation task owned by the API-key account. Requires API key.",
        "inputSchema": {
            "type": "object",
            "required": ["task_id"],
            "properties": {"task_id": {"type": "string"}},
        },
    },
    {
        "name": "list_assets",
        "description": "List recent completed assets for the API-key owner. Requires API key.",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 12}},
        },
    },
]


def _extract_secret(x_api_key: Optional[str], authorization: Optional[str]) -> Optional[str]:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        tok = authorization[7:].strip()
        if tok.startswith("sk_betty_"):
            return tok
    return None


async def _user_id_from_secret(db: AsyncSession, secret: str) -> Optional[int]:
    from datetime import datetime, timezone
    res = await db.execute(select(ApiKey).where(ApiKey.key_hash == _hash(secret), ApiKey.revoked == False))  # noqa: E712
    key = res.scalar_one_or_none()
    if not key:
        return None
    key.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return int(key.user_id)


def _public_model_row(m: dict) -> dict:
    caps = m.get("capabilities") or {}
    return {
        "id": m.get("id"),
        "display_name": m.get("display_name") or m.get("id"),
        "media_types": caps.get("media_types") or [],
        "status": "active",
        "cost_per_image_credits": caps.get("cost_per_image_credits"),
        "cost_per_5s_video_credits": caps.get("cost_per_5s_video_credits"),
    }


async def _active_models(media_type: Optional[str] = None) -> dict:
    from app.api.models_info import list_models
    catalog = await list_models(status="active")
    rows = [_public_model_row(m) for m in (catalog.get("active") or catalog.get("models") or [])]
    if media_type in ("image", "video"):
        rows = [r for r in rows if media_type in (r.get("media_types") or [])]
    return {
        "active_count": len(rows),
        "models": rows,
        "honesty": "仅已验证 active；lab/beta 不计可售。不是 Yapper 的 54+ 叙事。",
    }


async def _credits(db: AsyncSession, user_id: int) -> dict:
    bal = (await db.execute(select(UserBalance).where(UserBalance.user_id == user_id))).scalar_one_or_none()
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if bal is None:
        return {"user_id": user_id, "credits": 0, "role": user.role if user else "free"}
    return {
        "user_id": user_id,
        "credits": (bal.credits or 0) + (bal.daily_credits or 0),
        "purchased_credits": bal.credits,
        "daily_credits": bal.daily_credits,
        "role": user.role if user else "free",
    }


async def _quote(db: AsyncSession, user_id: int, args: dict) -> dict:
    from app.api.generate import GenerateRequest, quote_generation
    req = GenerateRequest(
        prompt=str(args.get("prompt") or "").strip() or " ",
        media_type=str(args.get("media_type") or "auto"),
        model=str(args.get("model") or "auto"),
        duration=int(args.get("duration") or 5),
        count=int(args.get("count") or 1),
    )
    quoted = await quote_generation(req, db, user_id)
    if hasattr(quoted, "model_dump"):
        return quoted.model_dump()
    return dict(quoted)


async def _generate(db: AsyncSession, user_id: int, args: dict) -> dict:
    from app.api.generate import GenerateRequest, execute_generation
    req = GenerateRequest(
        prompt=str(args.get("prompt") or "").strip(),
        media_type=str(args.get("media_type") or "auto"),
        model=str(args.get("model") or "auto"),
        duration=int(args.get("duration") or 5),
        count=int(args.get("count") or 1),
        webhook_url=args.get("webhook_url"),
    )
    return await execute_generation(req, db, user_id, team_id=None)


async def _get_task(db: AsyncSession, user_id: int, task_id: str) -> dict:
    task = (await db.execute(select(Task).where(Task.task_id == task_id))).scalar_one_or_none()
    if not task:
        raise ValueError(f"Task {task_id} not found")
    if task.user_id != user_id:
        raise PermissionError("无权访问此任务")
    results = task.results if isinstance(task.results, list) else None
    return {
        "task_id": task.task_id,
        "status": task.status,
        "progress": task.progress,
        "model": task.selected_model,
        "error_message": task.error_message,
        "results": results,
    }


async def _list_assets(db: AsyncSession, user_id: int, limit: int) -> dict:
    res = await db.execute(
        select(Task)
        .where(Task.user_id == user_id, Task.status == "completed")
        .order_by(desc(Task.created_at))
        .limit(max(1, min(limit, 50)))
    )
    items = []
    for t in res.scalars().all():
        results = t.results if isinstance(t.results, list) else []
        url = None
        if results and isinstance(results[0], dict):
            url = results[0].get("url") or results[0].get("media_url")
        items.append({
            "task_id": t.task_id,
            "media_type": t.media_type,
            "model": t.selected_model,
            "url": url,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return {"count": len(items), "items": items}


def _manifest(request: Request) -> dict:
    origin = str(request.base_url).rstrip("/")
    return {
        "name": SERVER_NAME,
        "version": SERVER_VERSION,
        "transport": "streamable-http",
        "protocol": "MCP JSON-RPC 2.0",
        "protocol_version": PROTOCOL_VERSION,
        "endpoint": f"{origin}/api/v1/mcp/connector",
        "product_page": "/mcp",
        "rest": {
            "generate": "/api/v1/public/generate",
            "quote": "/api/v1/public/quote",
            "models": "/api/v1/public/models",
            "credits": "/api/v1/public/credits",
            "task": "/api/v1/public/tasks/{task_id}",
            "assets": "/api/v1/public/assets",
            "keys": "/developer",
        },
        "auth": {
            "type": "api_key",
            "oauth": False,
            "headers": ["Authorization: Bearer sk_betty_...", "X-API-Key: sk_betty_..."],
            "note": "Yapper 托管连接器可账号登录；Betty 使用已有开发者 API Key，不伪造 OAuth。",
        },
        "tools": [t["name"] for t in TOOLS],
        "honesty": HONESTY,
    }


@router.get("/mcp/connector", summary="MCP 连接器发现（人类/客户端）")
@router.get("/mcp", summary="MCP 发现（别名）")
async def mcp_discover(request: Request):
    return _manifest(request)


@router.post("/mcp/connector", summary="MCP Streamable HTTP JSON-RPC")
@router.post("/mcp", summary="MCP JSON-RPC 别名")
async def mcp_rpc(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_rpc_error(None, -32700, "Parse error"), status_code=400)
    if not isinstance(body, dict):
        return JSONResponse(_rpc_error(None, -32600, "Invalid Request"), status_code=400)

    req_id = body.get("id")
    method = str(body.get("method") or "")
    params = body.get("params") or {}
    if not isinstance(params, dict):
        params = {}

    # Notifications have no id — acknowledge with 204-equivalent empty object.
    if req_id is None and method.startswith("notifications/"):
        return JSONResponse({"ok": True})

    if method == "initialize":
        return _rpc_result(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": HONESTY,
        })
    if method in ("ping", "notifications/initialized"):
        return _rpc_result(req_id, {})
    if method == "tools/list":
        return _rpc_result(req_id, {"tools": TOOLS})

    if method != "tools/call":
        return JSONResponse(_rpc_error(req_id, -32601, f"Method not found: {method}"), status_code=404)

    name = str(params.get("name") or "")
    args = params.get("arguments") or {}
    if not isinstance(args, dict):
        args = {}

    secret = _extract_secret(x_api_key, authorization)
    user_id = await _user_id_from_secret(db, secret) if secret else None

    try:
        if name == "list_models":
            return _rpc_result(req_id, _tool_text(await _active_models(args.get("media_type"))))

        if user_id is None:
            return JSONResponse(
                _rpc_error(req_id, -32001, "需要 API Key（Bearer sk_betty_... 或 X-API-Key）。Betty MCP 不提供账号 OAuth。"),
                status_code=401,
            )

        if name == "get_credits":
            return _rpc_result(req_id, _tool_text(await _credits(db, user_id)))
        if name == "quote_generation":
            if not str(args.get("prompt") or "").strip():
                return _rpc_result(req_id, _tool_text({"error": "prompt required"}, True))
            return _rpc_result(req_id, _tool_text(await _quote(db, user_id, args)))
        if name == "generate":
            if not str(args.get("prompt") or "").strip():
                return _rpc_result(req_id, _tool_text({"error": "prompt required"}, True))
            return _rpc_result(req_id, _tool_text(await _generate(db, user_id, args)))
        if name == "get_task":
            tid = str(args.get("task_id") or "").strip()
            if not tid:
                return _rpc_result(req_id, _tool_text({"error": "task_id required"}, True))
            return _rpc_result(req_id, _tool_text(await _get_task(db, user_id, tid)))
        if name == "list_assets":
            return _rpc_result(req_id, _tool_text(await _list_assets(db, user_id, int(args.get("limit") or 12))))
        return JSONResponse(_rpc_error(req_id, -32601, f"Unknown tool: {name}"), status_code=404)
    except PermissionError as e:
        return JSONResponse(_rpc_error(req_id, -32003, str(e)), status_code=403)
    except ValueError as e:
        return JSONResponse(_rpc_error(req_id, -32004, str(e)), status_code=404)
    except Exception as e:
        from fastapi import HTTPException
        if isinstance(e, HTTPException):
            return _rpc_result(req_id, _tool_text({"error": e.detail, "status": e.status_code}, True))
        return _rpc_result(req_id, _tool_text({"error": str(e)}, True))
