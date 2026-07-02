"""
Viral Intelligence System — Celery Tasks
Background jobs for collection, analysis, and report generation.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

from celery import Celery
from celery_app import app as celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.collector.tasks.collect_reddit",
    queue="collector_q",
    max_retries=2,
    acks_late=True,
    default_retry_delay=60,
)
def collect_reddit(
    self,
    subreddit: str | None = None,
    category: str | None = None,
    limit: int = 25,
    time_filter: str = "day",
) -> dict:
    """Collect trending content from Reddit and run analysis pipeline."""
    from app.collector.engine import viral_engine

    async def _run():
        from app.db import async_session
        async with async_session() as db:
            topics = await viral_engine.collect_and_analyze(
                db, "reddit",
                subreddit=subreddit,
                category=category,
                limit=limit,
                time_filter=time_filter,
            )
            await db.commit()
            breakouts = [t.to_dict() for t in topics if t.viral_tier == "tier_1_breakout"]
            return {
                "source": "reddit",
                "collected": len(topics),
                "breakouts": len(breakouts),
                "top_topics": breakouts[:5],
            }

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.exception("[celery] Reddit collection failed")
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="app.collector.tasks.collect_youtube",
    queue="collector_q",
    max_retries=2,
    acks_late=True,
    default_retry_delay=120,
)
def collect_youtube(
    self,
    query: str | None = None,
    category: str | None = None,
    limit: int = 25,
) -> dict:
    """Collect trending content from YouTube and run analysis pipeline."""
    from app.collector.engine import viral_engine

    async def _run():
        from app.db import async_session
        async with async_session() as db:
            topics = await viral_engine.collect_and_analyze(
                db, "youtube",
                query=query,
                category=category,
                limit=limit,
            )
            await db.commit()
            breakouts = [t.to_dict() for t in topics if t.viral_tier == "tier_1_breakout"]
            return {
                "source": "youtube",
                "collected": len(topics),
                "breakouts": len(breakouts),
                "top_topics": breakouts[:5],
            }

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.exception("[celery] YouTube collection failed")
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="app.collector.tasks.collect_tiktok",
    queue="collector_q",
    max_retries=1,
    acks_late=True,
    default_retry_delay=180,
)
def collect_tiktok(
    self,
    region: str = "US",
    limit: int = 25,
) -> dict:
    """Collect trending TikTok content via Apify and run analysis pipeline."""
    from app.collector.engine import viral_engine

    async def _run():
        from app.db import async_session
        async with async_session() as db:
            topics = await viral_engine.collect_and_analyze(
                db, "tiktok", region=region, limit=limit, scrape_type="trending",
            )
            await db.commit()
            breakouts = [t.to_dict() for t in topics if t.viral_tier == "tier_1_breakout"]
            return {
                "source": "tiktok",
                "collected": len(topics),
                "breakouts": len(breakouts),
                "top_topics": breakouts[:5],
            }

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.exception("[celery] TikTok collection failed")
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="app.collector.tasks.collect_x",
    queue="collector_q",
    max_retries=1,
    acks_late=True,
    default_retry_delay=300,
)
def collect_x(
    self,
    query: str | None = None,
    limit: int = 25,
) -> dict:
    """Collect trending content from X via Playwright and run analysis pipeline."""
    from app.collector.engine import viral_engine

    async def _run():
        from app.db import async_session
        async with async_session() as db:
            topics = await viral_engine.collect_and_analyze(
                db, "x", query=query, limit=limit,
            )
            await db.commit()
            breakouts = [t.to_dict() for t in topics if t.viral_tier == "tier_1_breakout"]
            return {
                "source": "x",
                "collected": len(topics),
                "breakouts": len(breakouts),
                "top_topics": breakouts[:5],
            }

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.exception("[celery] X collection failed")
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="app.collector.tasks.collect_all",
    queue="collector_q",
    max_retries=1,
    acks_late=True,
)
def collect_all(self) -> dict:
    """Collect from all available sources."""
    results = {}
    errors = []

    # Reddit
    try:
        r = collect_reddit.delay(category="tech", limit=25)
        results["reddit"] = {"task_id": r.id, "status": "submitted"}
    except Exception as e:
        errors.append(f"reddit: {e}")

    # YouTube
    try:
        y = collect_youtube.delay(limit=25)
        results["youtube"] = {"task_id": y.id, "status": "submitted"}
    except Exception as e:
        errors.append(f"youtube: {e}")

    # TikTok
    try:
        t = collect_tiktok.delay(region="US", limit=25)
        results["tiktok"] = {"task_id": t.id, "status": "submitted"}
    except Exception as e:
        errors.append(f"tiktok: {e}")

    # X
    try:
        x = collect_x.delay(limit=25)
        results["x"] = {"task_id": x.id, "status": "submitted"}
    except Exception as e:
        errors.append(f"x: {e}")

    return {
        "submitted": len(results),
        "tasks": results,
        "errors": errors if errors else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@celery_app.task(
    bind=True,
    name="app.collector.tasks.generate_daily_report",
    queue="collector_q",
    max_retries=1,
    acks_late=True,
)
def generate_daily_report(self, period: str = "daily") -> dict:
    """Generate a trend report."""
    from app.collector.engine import viral_engine

    async def _run():
        from app.db import async_session
        async with async_session() as db:
            report = await viral_engine.generate_report(db, period)
            await db.commit()
            return report.to_dict()

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.exception("[celery] Report generation failed")
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="app.collector.tasks.cleanup_old_topics",
    queue="collector_q",
    max_retries=1,
    acks_late=True,
)
def cleanup_old_topics(self, days: int = 7) -> dict:
    """Remove topics older than N days (keep only breakouts)."""
    from sqlalchemy import delete
    from datetime import timedelta
    from app.db import async_session
    from app.collector.models import TrendingTopic

    async def _run():
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        async with async_session() as db:
            result = await db.execute(
                delete(TrendingTopic)
                .where(TrendingTopic.last_analyzed_at < cutoff)
                .where(TrendingTopic.viral_tier.in_(["tier_3_emerging", "noise"]))
            )
            await db.commit()
            return {"deleted": result.rowcount, "cutoff": cutoff.isoformat()}

    return asyncio.run(_run())
