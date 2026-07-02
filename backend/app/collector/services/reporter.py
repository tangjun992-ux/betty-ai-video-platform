"""
Report Generator — Generates trend reports from analyzed topics.
Stateless, depends on TopicRepository for data access.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.models import TrendReport
from app.collector.services.repository import topic_repo
from app.collector.analyzers.prompt_gen import prompt_generator

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate trend reports with prompt suggestions."""

    async def generate(
        self, db: AsyncSession, period: str = "daily",
    ) -> TrendReport:
        """Generate a trend report for the given period."""
        now = datetime.now(timezone.utc)

        if period == "hourly":
            start, hours = now - timedelta(hours=1), 1
        elif period == "weekly":
            start, hours = now - timedelta(weeks=1), 168
        else:
            start, hours = now - timedelta(days=1), 24

        topics = await topic_repo.get_recent(db, hours=hours, limit=100)

        # Category & platform distribution
        categories, platforms = {}, {}
        for t in topics:
            cat = t.category or "uncategorized"
            categories[cat] = categories.get(cat, 0) + 1
            platforms[t.source_platform] = platforms.get(t.source_platform, 0) + 1

        breakouts = sum(1 for t in topics if t.viral_tier == "tier_1_breakout")
        trending = sum(1 for t in topics if t.viral_tier == "tier_2_trending")
        total = len(topics)

        # Generate prompts for top topics (convert to response objects)
        from app.collector.engine import viral_engine
        responses = [viral_engine._topic_to_response(t) for t in topics[:10]]
        prompts = prompt_generator.generate_diverse(responses, limit=5)
        prompt_dicts = [p.model_dump() for p in prompts]

        summary = (
            f"{period.title()} trend report: {total} topics tracked. "
            f"{breakouts} breakouts, {trending} trending. "
            f"Top platform: {max(platforms, key=platforms.get) if platforms else 'none'}. "
            f"Top category: {max(categories, key=categories.get) if categories else 'none'}."
        )

        report = TrendReport(
            period=period,
            period_start=start,
            period_end=now,
            summary=summary,
            top_topics=[t.to_dict() for t in topics[:20]],
            category_distribution=categories,
            platform_distribution=platforms,
            generated_prompts=prompt_dicts,
            total_signals=total,
            breakout_count=breakouts,
            trending_count=trending,
        )
        db.add(report)
        await db.commit()
        return report


report_generator = ReportGenerator()
