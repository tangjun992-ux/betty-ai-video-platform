"""
OIDC / SSO login skeleton (enterprise).

Configured via:
  OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_REDIRECT_URI

Without these env vars, endpoints return 503 with a clear message (no fake SSO).
"""
from __future__ import annotations

import os
import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_password_hash
from app.config import settings
from app.db import get_db
from app.models.user import User
from app.services.audit import record_audit

router = APIRouter()


def oidc_configured() -> bool:
    return bool(
        os.getenv("OIDC_ISSUER")
        and os.getenv("OIDC_CLIENT_ID")
        and os.getenv("OIDC_CLIENT_SECRET")
        and os.getenv("OIDC_REDIRECT_URI")
    )


def oidc_status() -> dict:
    return {
        "configured": oidc_configured(),
        "issuer": os.getenv("OIDC_ISSUER", ""),
        "client_id_set": bool(os.getenv("OIDC_CLIENT_ID")),
        "redirect_uri": os.getenv("OIDC_REDIRECT_URI", ""),
    }


@router.get("/oidc/status", summary="SSO / OIDC 配置状态")
async def sso_status():
    return oidc_status()


@router.get("/oidc/login", summary="发起 OIDC 登录")
async def oidc_login():
    if not oidc_configured():
        raise HTTPException(status_code=503, detail="SSO 未配置（需要 OIDC_ISSUER/CLIENT_ID/SECRET/REDIRECT_URI）")
    issuer = os.getenv("OIDC_ISSUER", "").rstrip("/")
    state = secrets.token_urlsafe(24)
    # Authorization endpoint convention: {issuer}/authorize
    params = {
        "client_id": os.getenv("OIDC_CLIENT_ID"),
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": os.getenv("OIDC_REDIRECT_URI"),
        "state": state,
    }
    url = f"{issuer}/authorize?{urlencode(params)}"
    return RedirectResponse(url, status_code=302)


@router.get("/oidc/callback", summary="OIDC 回调换票")
async def oidc_callback(
    code: str = Query(...),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if not oidc_configured():
        raise HTTPException(status_code=503, detail="SSO 未配置")
    issuer = os.getenv("OIDC_ISSUER", "").rstrip("/")
    token_url = f"{issuer}/token"
    async with httpx.AsyncClient(timeout=30) as client:
        token_resp = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": os.getenv("OIDC_REDIRECT_URI"),
                "client_id": os.getenv("OIDC_CLIENT_ID"),
                "client_secret": os.getenv("OIDC_CLIENT_SECRET"),
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"OIDC token exchange failed: {token_resp.text[:200]}")
        tokens = token_resp.json()
        access = tokens.get("access_token")
        # Userinfo
        ui = await client.get(
            f"{issuer}/userinfo",
            headers={"Authorization": f"Bearer {access}"},
        )
        if ui.status_code >= 400:
            raise HTTPException(status_code=502, detail="OIDC userinfo failed")
        profile = ui.json()

    email = (profile.get("email") or "").strip().lower()
    sub = str(profile.get("sub") or "")
    name = profile.get("name") or profile.get("preferred_username") or (email.split("@")[0] if email else f"oidc-{sub[:8]}")
    if not email and not sub:
        raise HTTPException(status_code=400, detail="OIDC profile missing email/sub")

    # Find or create user
    user = None
    if email:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        username = name[:40]
        # ensure unique username
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
        meta={"issuer": issuer, "sub": sub, "email": email},
    )
    await db.commit()
    jwt_token = create_access_token({"sub": str(user.id), "role": user.role})
    # Redirect to frontend with token fragment (SPA picks it up)
    front = settings.STRIPE_SUCCESS_URL.split("?")[0].rsplit("/", 1)[0] if settings.STRIPE_SUCCESS_URL else "http://localhost:3000"
    # Prefer PUBLIC frontend from CORS first origin
    origins = settings.CORS_ORIGINS or ["http://localhost:3000"]
    front = origins[0].rstrip("/")
    return RedirectResponse(f"{front}/auth/callback?token={jwt_token}", status_code=302)
