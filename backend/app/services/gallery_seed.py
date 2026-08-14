"""Dev-only gallery seeding when explore is empty."""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.task import Task

logger = logging.getLogger(__name__)
SEED_MARKER = "demo_seed_v2"  # keep in sync with scripts/seed_gallery.py


async def maybe_seed_gallery_dev(db: AsyncSession) -> int:
    """In non-production, seed curated explore content if v2 seeds are missing."""
    if settings.is_production:
        return 0
    try:
        rows = await db.execute(
            select(Task.parameters).where(Task.status == "completed").limit(400)
        )
        for params in rows.scalars().all():
            if isinstance(params, dict) and params.get("seed_marker") == SEED_MARKER:
                return 0
            if isinstance(params, str) and SEED_MARKER in params:
                return 0
        from scripts import seed_gallery as sg
        sg.main()
        logger.info("dev gallery seed completed")
        return 1
    except Exception as e:
        logger.warning("dev gallery seed skipped: %s", e)
        return 0
