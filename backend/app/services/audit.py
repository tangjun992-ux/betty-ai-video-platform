"""
Audit log — enterprise action trail (team / billing / admin).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from sqlalchemy import Column, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

logger = logging.getLogger(__name__)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    actor_user_id = Column(Integer, nullable=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    target_type = Column(String(40), nullable=True)
    target_id = Column(String(80), nullable=True, index=True)
    meta_json = Column(Text, nullable=True)
    ip = Column(String(64), nullable=True)


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    actor_user_id: Optional[int] = None,
    target_type: str | None = None,
    target_id: str | None = None,
    meta: dict[str, Any] | None = None,
    ip: str | None = None,
) -> AuditLog:
    row = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        meta_json=json.dumps(meta or {}, ensure_ascii=False),
        ip=ip,
    )
    db.add(row)
    await db.flush()
    logger.info("audit action=%s actor=%s target=%s:%s", action, actor_user_id, target_type, target_id)
    return row


async def list_audit(
    db: AsyncSession, *, limit: int = 50, action: str | None = None,
) -> list[dict]:
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(min(max(limit, 1), 200))
    if action:
        q = q.where(AuditLog.action == action)
    rows = (await db.execute(q)).scalars().all()
    out = []
    for r in rows:
        meta = {}
        if r.meta_json:
            try:
                meta = json.loads(r.meta_json)
            except Exception:
                meta = {}
        out.append({
            "id": r.id,
            "actor_user_id": r.actor_user_id,
            "action": r.action,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "meta": meta,
            "ip": r.ip,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        })
    return out
