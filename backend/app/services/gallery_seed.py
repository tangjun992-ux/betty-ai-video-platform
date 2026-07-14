"""Dev-only gallery seeding when explore is empty."""
from __future__ import annotations

import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.task import Task

logger = logging.getLogger(__name__)
SEED_MARKER = "demo_seed_v1"


async def maybe_seed_gallery_dev(db: AsyncSession) -> int:
    """In non-production, seed curated explore content if gallery would be empty."""
    if settings.is_production:
        return 0
    try:
        r = await db.execute(select(func.count()).select_from(Task).where(Task.status == "completed"))
        if (r.scalar() or 0) >= 8:
            return 0
        from scripts import seed_gallery as sg
        sg.main()
        logger.info("dev gallery seed completed")
        return 1
    except Exception as e:
        logger.warning("dev gallery seed skipped: %s", e)
        return 0
