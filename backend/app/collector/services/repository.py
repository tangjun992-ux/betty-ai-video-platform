"""
Topic Repository — Data access layer for TrendingTopic/ViralSignal/TrendReport.
Encapsulates all DB queries, no analysis logic.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.models import TrendingTopic, ViralSignal, TrendReport
from app.collector.services.pipeline import AnalysisResult

logger = logging.getLogger(__name__)


class TopicRepository:
    """Data access for trending topics. Stateless (gets db per call)."""

    async def upsert(self, db: AsyncSession, result: AnalysisResult) -> TrendingTopic:
        """INSERT or UPDATE a topic from analysis result. Uses SELECT FOR UPDATE."""
        post = result.post
        hooks = result.hooks
        h = [hp.model_dump() for hp in (hooks or [])]
        now = datetime.now(timezone.utc)

        existing = (
            await db.execute(
                select(TrendingTopic)
                .where(TrendingTopic.topic_id == post.source_id)
                .with_for_update()
            )
        ).scalar_one_or_none()

        if existing:
            existing.engagement_upvotes = post.upvotes
            existing.engagement_comments = post.comments
            existing.engagement_shares = post.shares
            existing.engagement_views = post.views
            existing.engagement_score = result.engagement
            existing.growth_velocity_1h = result.growth.velocity_1h
            existing.growth_velocity_6h = result.growth.velocity_6h
            existing.growth_velocity_24h = result.growth.velocity_24h
            existing.growth_acceleration = result.growth.acceleration
            existing.viral_score = result.viral.score
            existing.viral_tier = result.viral.tier
            existing.breakout_probability = result.viral.breakout_probability
            existing.sentiment_positive = result.sentiment.positive
            existing.sentiment_negative = result.sentiment.negative
            existing.sentiment_neutral = result.sentiment.neutral
            existing.sentiment_controversy = result.sentiment.controversy_index
            existing.hooks_detected = h
            existing.meme_matches = [{"template": m.template, "category": m.category, "confidence": m.confidence}
                                     for m in (result.meme_matches or [])]
            existing.last_analyzed_at = now
            existing.raw_data = post.raw_data if post.raw_data else None
            return existing

        topic = TrendingTopic(
            topic_id=post.source_id,
            source_platform=post.source_platform,
            source_id=post.source_id,
            source_url=post.source_url,
            thumbnail_url=post.thumbnail_url,
            title=post.title,
            description=post.description,
            author=post.author,
            subreddit=post.subreddit,
            channel=post.channel,
            engagement_upvotes=post.upvotes,
            engagement_comments=post.comments,
            engagement_shares=post.shares,
            engagement_views=post.views,
            engagement_score=result.engagement,
            growth_velocity_1h=result.growth.velocity_1h,
            growth_velocity_6h=result.growth.velocity_6h,
            growth_velocity_24h=result.growth.velocity_24h,
            growth_acceleration=result.growth.acceleration,
            viral_score=result.viral.score,
            viral_tier=result.viral.tier,
            breakout_probability=result.viral.breakout_probability,
            sentiment_positive=result.sentiment.positive,
            sentiment_negative=result.sentiment.negative,
            sentiment_neutral=result.sentiment.neutral,
            sentiment_controversy=result.sentiment.controversy_index,
            hooks_detected=h,
            meme_matches=[{"template": m.template, "category": m.category, "confidence": m.confidence}
                         for m in (result.meme_matches or [])],
            source_created_at=post.source_created_at,
            last_analyzed_at=now,
            raw_data=post.raw_data if post.raw_data else None,
        )
        db.add(topic)
        return topic

    async def upsert_batch(self, db: AsyncSession, results: list[AnalysisResult]) -> list[TrendingTopic]:
        """Upsert multiple analysis results."""
        topics = []
        for result in results:
            try:
                topic = await self.upsert(db, result)
                topics.append(topic)
            except Exception as e:
                logger.exception("[repo] Upsert failed for %s", result.post.source_id)
        return topics

    async def add_signal(self, db: AsyncSession, topic: TrendingTopic) -> Optional[ViralSignal]:
        """Create a viral signal for breakout/trending topics."""
        if topic.viral_tier not in ("tier_1_breakout", "tier_2_trending"):
            return None
        signal = ViralSignal(
            topic_id=topic.topic_id,
            signal_type="velocity_breakout" if (topic.breakout_probability or 0) > 0.7
            else "engagement_spike",
            confidence=topic.breakout_probability or topic.viral_score,
            evidence={"score": topic.viral_score, "tier": topic.viral_tier, "growth_1h": topic.growth_velocity_1h},
        )
        db.add(signal)
        return signal

    async def query(
        self, db: AsyncSession,
        tier: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[TrendingTopic]:
        """Query trending topics with filters."""
        q = select(TrendingTopic)
        if tier: q = q.where(TrendingTopic.viral_tier == tier)
        if source: q = q.where(TrendingTopic.source_platform == source)
        q = q.order_by(TrendingTopic.viral_score.desc()).offset(offset).limit(limit)
        return (await db.execute(q)).scalars().all()

    async def get_by_id(self, db: AsyncSession, topic_id: str) -> Optional[TrendingTopic]:
        return (await db.execute(
            select(TrendingTopic).where(TrendingTopic.topic_id == topic_id)
        )).scalar_one_or_none()

    async def get_top(self, db: AsyncSession, tier: Optional[str] = None, limit: int = 10) -> list[TrendingTopic]:
        q = select(TrendingTopic)
        if tier: q = q.where(TrendingTopic.viral_tier == tier)
        q = q.order_by(TrendingTopic.viral_score.desc()).limit(limit)
        return (await db.execute(q)).scalars().all()

    async def get_recent(self, db: AsyncSession, hours: int = 24, limit: int = 100) -> list[TrendingTopic]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return (await db.execute(
            select(TrendingTopic)
            .where(TrendingTopic.last_analyzed_at >= cutoff)
            .order_by(TrendingTopic.viral_score.desc())
            .limit(limit)
        )).scalars().all()

    async def get_signals(self, db: AsyncSession, signal_type: Optional[str] = None, limit: int = 50) -> list[ViralSignal]:
        q = select(ViralSignal)
        if signal_type: q = q.where(ViralSignal.signal_type == signal_type)
        q = q.order_by(ViralSignal.triggered_at.desc()).limit(limit)
        return (await db.execute(q)).scalars().all()

    async def count_signals_since(self, db: AsyncSession, since: datetime) -> int:
        return (await db.execute(
            select(func.count(ViralSignal.id)).where(ViralSignal.triggered_at >= since)
        )).scalar() or 0

    async def dashboard_aggregate(self, db: AsyncSession) -> dict:
        """Single aggregation query for dashboard stats."""
        from sqlalchemy import case as sa_case
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(hours=24)

        agg = (await db.execute(select(
            func.count(TrendingTopic.id).label("total"),
            func.sum(sa_case((TrendingTopic.viral_tier == "tier_1_breakout", 1), else_=0)).label("breakouts"),
            func.sum(sa_case((TrendingTopic.viral_tier == "tier_2_trending", 1), else_=0)).label("trending"),
            func.sum(sa_case((TrendingTopic.viral_tier == "tier_3_emerging", 1), else_=0)).label("emerging"),
            func.sum(sa_case((TrendingTopic.viral_tier == "noise", 1), else_=0)).label("noise_count"),
        ))).one_or_none()

        platforms = dict((await db.execute(
            select(TrendingTopic.source_platform, func.count(TrendingTopic.id).label("cnt"))
            .where(TrendingTopic.last_analyzed_at >= day_ago)
            .group_by(TrendingTopic.source_platform)
        )).all())

        categories = (await db.execute(
            select(TrendingTopic.category, func.count(TrendingTopic.id).label("cnt"))
            .where(TrendingTopic.last_analyzed_at >= day_ago)
            .group_by(TrendingTopic.category)
            .order_by(func.count(TrendingTopic.id).desc())
            .limit(10)
        )).all()

        breakouts = (await db.execute(
            select(TrendingTopic)
            .where(TrendingTopic.viral_tier == "tier_1_breakout")
            .order_by(TrendingTopic.viral_score.desc())
            .limit(5)
        )).scalars().all()

        signals_24h = await self.count_signals_since(db, day_ago)

        return {
            "total": agg.total if agg else 0,
            "breakouts": int(agg.breakouts or 0) if agg else 0,
            "trending": int(agg.trending or 0) if agg else 0,
            "emerging": int(agg.emerging or 0) if agg else 0,
            "noise": int(agg.noise_count or 0) if agg else 0,
            "platforms": dict(platforms),
            "categories": [{"category": (r.category or "uncategorized"), "count": r.cnt} for r in categories],
            "signals_24h": signals_24h,
            "recent_breakouts": breakouts,
        }


topic_repo = TopicRepository()
