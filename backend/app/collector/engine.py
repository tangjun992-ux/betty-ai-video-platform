"""
Viral Intelligence Engine — Orchestrates collection → analysis → storage pipeline.

v2: Fixed P0 issues
  - N+1 queries → single aggregation for dashboard
  - Race condition → SELECT FOR UPDATE on upsert
  - Bulk operations for analysis pipeline
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, update, text, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.sources.base import CollectResult
from app.collector.sources.reddit import RedditSource
from app.collector.sources.youtube import YouTubeSource
from app.collector.services.collector import collector_service
from app.collector.services.pipeline import analysis_pipeline
from app.collector.services.repository import topic_repo
from app.collector.services.reporter import report_generator
from app.collector.analyzers.viral_score import viral_scorer
from app.collector.analyzers.growth_velocity import growth_tracker
from app.collector.analyzers.sentiment import sentiment_analyzer
from app.collector.analyzers.hook import hook_analyzer
from app.collector.analyzers.novelty import novelty_analyzer
from app.collector.analyzers.prompt_gen import prompt_generator
from app.collector.models import TrendingTopic, ViralSignal, TrendReport
from app.collector.schemas import (
    RawPost, GeneratedPrompt,
    TrendingTopicResponse, DashboardStats,
    EngagementMetrics, GrowthMetrics, SentimentResult, HookPattern,
)

logger = logging.getLogger(__name__)


class ViralEngine:
    """Main orchestrator for the Viral Intelligence System."""

    def __init__(self, db_session_factory=None):
        self.sources = {
            "reddit": collector_service.reddit,
            "youtube": collector_service.youtube,
        }
        self._collector = collector_service
        self._pipeline = analysis_pipeline
        self._repo = topic_repo
        self._reporter = report_generator
        self.db_factory = db_session_factory

    async def collect_and_analyze(self, db: AsyncSession, source: str, **kwargs) -> list[TrendingTopic]:
        """Full pipeline: collect → analyze → persist (delegates to service layer)."""
        # 1. Collect (via CollectorService)
        result: CollectResult = await self._collector.collect(source, **kwargs)

        if not result.success or not result.posts:
            logger.warning("[engine] Collection %s: success=%s count=%d error=%s",
                          source, result.success, result.count, result.error)
            return []

        logger.info("[engine] Collected %d posts from %s in %.0fms",
                    result.count, source, result.duration_ms)

        # 2. Analyze (via AnalysisPipeline)
        analyses = self._pipeline.analyze_batch(result.posts)

        # 3. Persist (via TopicRepository)
        topics = await self._repo.upsert_batch(db, analyses)

        # 4. Signals for breakouts
        signal_count = 0
        for topic in topics:
            signal = await self._repo.add_signal(db, topic)
            if signal: signal_count += 1

        await db.commit()
        logger.info("[engine] Persisted %d topics, %d signals", len(topics), signal_count)
        return topics

    async def generate_prompts(
        self, db: AsyncSession, content_type: str = "video",
        limit: int = 10, viral_tier: Optional[str] = None,
    ) -> list[GeneratedPrompt]:
        """Generate content prompts from top trending topics."""
        topics = await self._repo.get_top(db, tier=viral_tier, limit=min(limit * 3, 150))
        responses = [self._topic_to_response(t) for t in topics]
        return prompt_generator.generate_batch(responses, content_type, limit)

    async def generate_report(self, db: AsyncSession, period: str = "daily") -> TrendReport:
        """Generate a trend report (delegates to ReportGenerator)."""
        return await self._reporter.generate(db, period)

    async def get_dashboard_stats(self, db: AsyncSession) -> DashboardStats:
        """Get dashboard statistics (delegates to TopicRepository aggregation)."""
        agg = await self._repo.dashboard_aggregate(db)
        recent_breakouts = [
            self._topic_to_response(t) for t in agg["recent_breakouts"]
        ]

        return DashboardStats(
            total_topics_tracked=agg["total"],
            breakout_topics=agg["breakouts"],
            trending_topics=agg["trending"],
            signals_last_24h=agg["signals_24h"],
            top_categories=agg["categories"],
            platform_breakdown=agg["platforms"],
            viral_score_distribution={
                "tier_1_breakout": agg["breakouts"],
                "tier_2_trending": agg["trending"],
                "tier_3_emerging": agg["emerging"],
                "noise": agg["noise"],
            },
            recent_breakouts=recent_breakouts,
        )

    @staticmethod
    def _topic_to_response(topic: TrendingTopic) -> TrendingTopicResponse:
        hooks_raw = topic.hooks_detected or []
        hooks = [HookPattern(**h) for h in hooks_raw] if hooks_raw else []

        return TrendingTopicResponse(
            topic_id=topic.topic_id,
            source_platform=topic.source_platform,
            title=topic.title,
            thumbnail_url=topic.thumbnail_url,
            viral_score=topic.viral_score,
            viral_tier=topic.viral_tier,
            engagement=EngagementMetrics(
                upvotes=topic.engagement_upvotes, comments=topic.engagement_comments,
                shares=topic.engagement_shares, views=topic.engagement_views,
                score=topic.engagement_score,
            ),
            growth=GrowthMetrics(
                velocity_1h=topic.growth_velocity_1h, velocity_6h=topic.growth_velocity_6h,
                velocity_24h=topic.growth_velocity_24h, acceleration=topic.growth_acceleration,
            ),
            sentiment=SentimentResult(
                positive=topic.sentiment_positive, negative=topic.sentiment_negative,
                neutral=topic.sentiment_neutral, controversy_index=topic.sentiment_controversy,
                top_positive_keywords=[], top_negative_keywords=[],
            ),
            hooks=hooks,
            meme_matches=topic.meme_matches or [],
            created_at=topic.last_analyzed_at.isoformat() if topic.last_analyzed_at else None,
        )

    @staticmethod
    def _total_engagement(post: RawPost) -> float:
        return post.upvotes * 1.0 + post.comments * 2.0 + post.shares * 3.0 + post.views * 0.01


viral_engine = ViralEngine()
