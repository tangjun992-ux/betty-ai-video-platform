"""
Developer platform — API key management + public API.

- Key CRUD is authenticated by the user's session (JWT). The full secret is
  returned only once at creation.
- The public API authenticates with the secret (X-API-Key or Bearer) and is
  scoped to the owning user's account (credits + assets), matching the web app.
"""
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.auth import get_current_user
from app.rate_limiter import rate_limit

router = APIRouter()


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


class CreateKeyRequest(BaseModel):
    name: str = Field("默认密钥", max_length=120)


@router.post("/developer/keys", summary="创建 API 密钥")
async def create_key(req: CreateKeyRequest, current_user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    # secret shown once: sk_betty_<random>; store only the hash + a public id.
    rand = secrets.token_hex(24)
    secret = f"sk_betty_{rand}"
    key_id = "betty_" + rand[:12]
    row = ApiKey(key_id=key_id, key_hash=_hash(secret), user_id=current_user.id, name=req.name.strip() or "默认密钥")
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {
        "id": row.key_id,
        "name": row.name,
        "secret": secret,  # only returned here, never retrievable again
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "message": "请立即复制并妥善保存，密钥只显示这一次。",
    }


@router.get("/developer/keys", summary="列出 API 密钥")
async def list_keys(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(ApiKey).where(ApiKey.user_id == current_user.id, ApiKey.revoked == False)  # noqa: E712
        .order_by(desc(ApiKey.created_at))
    )
    return {"keys": [{
        "id": k.key_id,
        "name": k.name,
        "masked": f"sk_betty_{k.key_id.split('_')[-1]}…",
        "created_at": k.created_at.isoformat() if k.created_at else "",
        "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
    } for k in res.scalars().all()]}


@router.delete("/developer/keys/{key_id}", summary="吊销 API 密钥")
async def revoke_key(key_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ApiKey).where(ApiKey.key_id == key_id, ApiKey.user_id == current_user.id))
    k = res.scalar_one_or_none()
    if not k:
        raise HTTPException(status_code=404, detail="密钥不存在")
    k.revoked = True
    await db.commit()
    return {"revoked": key_id}


async def require_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> int:
    """Resolve the API key → owning user id. Accepts X-API-Key or Bearer sk_..."""
    secret = x_api_key
    if not secret and authorization and authorization.lower().startswith("bearer "):
        tok = authorization[7:]
        if tok.startswith("sk_betty_"):
            secret = tok
    if not secret:
        raise HTTPException(status_code=401, detail="缺少 API 密钥（X-API-Key 或 Bearer sk_betty_...）")
    res = await db.execute(select(ApiKey).where(ApiKey.key_hash == _hash(secret), ApiKey.revoked == False))  # noqa: E712
    k = res.scalar_one_or_none()
    if not k:
        raise HTTPException(status_code=401, detail="无效或已吊销的 API 密钥")
    k.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    return k.user_id


from app.api.generate import GenerateRequest, submit_generation  # no cycle: generate doesn't import developer


@router.post("/public/generate", summary="公开 API：提交生成（X-API-Key 鉴权）",
             dependencies=[Depends(rate_limit("public_generate", rpm=30, rph=300))])
async def public_generate(
    req: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    key_user: int = Depends(require_api_key),
):
    """Public generation endpoint — reuses the full web pipeline (routing,
    moderation, cost, dispatch) scoped to the API key's owner."""
    return await submit_generation(req, db=db, user_id=key_user)
