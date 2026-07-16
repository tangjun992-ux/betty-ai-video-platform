"""
OIDC / SSO login (enterprise).

Configured via:
  OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_REDIRECT_URI

Optional:
  OIDC_REQUIRED_IN_PRODUCTION=1 — gate readiness in production

Without these env vars, endpoints return 503 with a clear message (no fake SSO).
Uses OIDC discovery when available; falls back to {issuer}/authorize|/token|/userinfo.
"""
from __future__ import annotations

import os
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_password_hash
from app.config import settings
from app.db import get_db
from app.models.user import User
from app.services.audit import record_audit
from app.services.oidc_ready import oidc_configured, oidc_status as _oidc_status, resolve_endpoints, oidc_env

router = APIRouter()

_STATE_COOKIE = "betty_oidc_state"


@router.get("/oidc/status", summary="SSO / OIDC 配置状态")
async def sso_status():
    return _oidc_status(discover=False).public_dict()


@router.get("/oidc/login", summary="发起 OIDC 登录")
async def oidc_login(response: Response):
    if not oidc_configured():
        raise HTTPException(
            status_code=503,
            detail="SSO 未配置（需要 OIDC_ISSUER/CLIENT_ID/SECRET/REDIRECT_URI）",
        )
    e = oidc_env()
    eps = resolve_endpoints(e["issuer"], discover=True)
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": e["client_id"],
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": e["redirect_uri"],
        "state": state,
    }
    url = f"{eps['authorize_url']}?{urlencode(params)}"
    redirect = RedirectResponse(url, status_code=302)
    redirect.set_cookie(
        _STATE_COOKIE,
        state,
        httponly=True,
        samesite="lax",
        max_age=600,
        secure=settings.is_production,
    )
    return redirect


@router.get("/oidc/callback", summary="OIDC 回调换票")
async def oidc_callback(
    request: Request,
    code: str = Query(...),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if not oidc_configured():
        raise HTTPException(status_code=503, detail="SSO 未配置")
    cookie_state = request.cookies.get(_STATE_COOKIE)
    if cookie_state and state and cookie_state != state:
        raise HTTPException(status_code=400, detail="OIDC state 校验失败（可能的 CSRF）")

    e = oidc_env()
    eps = resolve_endpoints(e["issuer"], discover=True)
    async with httpx.AsyncClient(timeout=30) as client:
        token_resp = await client.post(
            eps["token_url"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": e["redirect_uri"],
                "client_id": e["client_id"],
                "client_secret": e["client_secret"],
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"OIDC token exchange failed: {token_resp.text[:200]}",
            )
        tokens = token_resp.json()
        access = tokens.get("access_token")
        ui = await client.get(
            eps["userinfo_url"],
            headers={"Authorization": f"Bearer {access}"},
        )
        if ui.status_code >= 400:
            raise HTTPException(status_code=502, detail="OIDC userinfo failed")
        profile = ui.json()

    email = (profile.get("email") or "").strip().lower()
    sub = str(profile.get("sub") or "")
    name = (
        profile.get("name")
        or profile.get("preferred_username")
        or (email.split("@")[0] if email else f"oidc-{sub[:8]}")
    )
    if not email and not sub:
        raise HTTPException(status_code=400, detail="OIDC profile missing email/sub")

    user = None
    if email:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        username = name[:40]
        base = username
        n = 0
        while True:
            clash = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
            if not clash:
                break
            n += 1
            username = f"{base[:36]}{n}"
        user = User(
            username=username,
            email=email or f"{sub}@oidc.local",
            hashed_password=get_password_hash(secrets.token_urlsafe(24)),
            role="personal",
            is_active=True,
        )
        db.add(user)
        await db.flush()

    await record_audit(
        db,
        action="auth.oidc_login",
        actor_user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        meta={"issuer": e["issuer"], "sub": sub, "email": email},
    )
    await db.commit()
    jwt_token = create_access_token({"sub": str(user.id), "role": user.role})
    origins = settings.CORS_ORIGINS or ["http://localhost:3000"]
    front = origins[0].rstrip("/")
    redirect = RedirectResponse(f"{front}/auth/callback?token={jwt_token}", status_code=302)
    redirect.delete_cookie(_STATE_COOKIE)
    return redirect
