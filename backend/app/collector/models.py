"""
Viral Intelligence System — DB Models
Extends Betty's existing SQLAlchemy Base.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, String, Text, Float, Integer, JSON, DateTime,
    ForeignKey, Index, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


# ─────────────────────────────── Enums ───────────────────────────────
class SignalTier(str, enum.Enum):
    TIER_1_BREAKOUT = "tier_1_breakout"
    TIER_2_TRENDING = "tier_2_trending"
    TIER_3_EMERGING = "tier_3_emerging"
    NOISE = "noise"


class SourcePlatform(str, enum.Enum):
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    X = "x"


class SignalType(str, enum.Enum):
    ENGAGEMENT_SPIKE = "engagement_spike"
    SENTIMENT_SHIFT = "sentiment_shift"
    VELOCITY_BREAKOUT = "velocity_breakout"
    MEME_SURGE = "meme_surge"


class HookCategory(str, enum.Enum):
    CURIOSITY_GAP = "curiosity_gap"
    CONTROVERSY = "controversy"
    PATTERN_INTERRUPT = "pattern_interrupt"
    SOCIAL_PROOF = "social_proof"
    SCARCITY_URGENCY = "scarcity_urgency"
    STORY_HOOK = "story_hook"
    QUESTION_HOOK = "question_hook"
    STATISTIC_HOOK = "statistic_hook"
    BEFORE_AFTER = "before_after"
    CHALLENGE = "challenge"
    LISTICLE = "listicle"
    RELATABILITY = "relatability"
    AUTHORITY = "authority"


# ─────────────────────────────── Models ───────────────────────────────
class TrendingTopic(Base):
    """A trending topic discovered from any source platform."""
    __tablename__ = "trending_topics"

    topic_id = Column(String(36), unique=True, nullable=False, index=True,
                      default=lambda: uuid.uuid4().hex)
    source_platform = Column(String(20), nullable=False, index=True)
    source_id = Column(String(255), nullable=False)
    source_url = Column(String(2048), nullable=True)
    thumbnail_url = Column(String(2048), nullable=True)

    # Content
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    subreddit = Column(String(100), nullable=True)  # Reddit-specific
    channel = Column(String(255), nullable=True)     # YouTube-specific
    category = Column(String(100), nullable=True, index=True)

    # Engagement snapshot
    engagement_upvotes = Column(Integer, default=0)
    engagement_comments = Column(Integer, default=0)
    engagement_shares = Column(Integer, default=0)
    engagement_views = Column(Integer, default=0)
    engagement_score = Column(Float, default=0.0)  # computed

    # Growth metrics
    growth_velocity_1h = Column(Float, nullable=True)
    growth_velocity_6h = Column(Float, nullable=True)
    growth_velocity_24h = Column(Float, nullable=True)
    growth_acceleration = Column(Float, nullable=True)

    # Viral scoring
    viral_score = Column(Float, default=0.0, index=True)
    viral_tier = Column(String(20), default="noise", index=True)
    breakout_probability = Column(Float, nullable=True)

    # Sentiment
    sentiment_positive = Column(Float, default=0.0)
    sentiment_negative = Column(Float, default=0.0)
    sentiment_neutral = Column(Float, default=0.0)
    sentiment_controversy = Column(Float, default=0.0)  # 0-1, higher = more divisive

    # Hook analysis
    hooks_detected = Column(JSON, nullable=True)  # [{pattern, strength, category, text}]

    # Meme detection
    meme_matches = Column(JSON, nullable=True)  # [{template, confidence, text}]

    # Raw source data (for debugging / re-analysis)
    raw_data = Column(JSON, nullable=True)

    # Timestamps
    source_created_at = Column(DateTime(timezone=True), nullable=True)
    first_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_analyzed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    signals = relationship("ViralSignal", back_populates="topic", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_trending_viral_score", "viral_score"),
        Index("ix_trending_source_platform_created", "source_platform", "source_created_at"),
        Index("ix_trending_viral_tier_score", "viral_tier", "viral_score"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "topic_id": self.topic_id,
            "source_platform": self.source_platform,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "thumbnail_url": self.thumbnail_url,
            "title": self.title,
            "description": self.description,
            "author": self.author,
            "subreddit": self.subreddit,
            "channel": self.channel,
            "category": self.category,
            "engagement": {
                "upvotes": self.engagement_upvotes,
                "comments": self.engagement_comments,
                "shares": self.engagement_shares,
                "views": self.engagement_views,
                "score": self.engagement_score,
            },
            "growth": {
                "velocity_1h": self.growth_velocity_1h,
                "velocity_6h": self.growth_velocity_6h,
                "velocity_24h": self.growth_velocity_24h,
                "acceleration": self.growth_acceleration,
            },
            "viral": {
                "score": self.viral_score,
                "tier": self.viral_tier,
                "breakout_probability": self.breakout_probability,
            },
            "sentiment": {
                "positive": self.sentiment_positive,
                "negative": self.sentiment_negative,
                "neutral": self.sentiment_neutral,
                "controversy": self.sentiment_controversy,
            },
            "hooks_detected": self.hooks_detected or [],
            "meme_matches": self.meme_matches or [],
            "source_created_at": self.source_created_at.isoformat() if self.source_created_at else None,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_analyzed_at": self.last_analyzed_at.isoformat() if self.last_analyzed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ViralSignal(Base):
    """Individual viral detection event."""
    __tablename__ = "viral_signals"

    signal_id = Column(String(36), unique=True, nullable=False, index=True,
                       default=lambda: uuid.uuid4().hex)
    topic_id = Column(String(36), ForeignKey("trending_topics.topic_id"), nullable=False, index=True)
    signal_type = Column(String(30), nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    evidence = Column(JSON, nullable=True)
    triggered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship
    topic = relationship("TrendingTopic", back_populates="signals")

    __table_args__ = (
        Index("ix_signals_topic_type", "topic_id", "signal_type"),
    )

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "topic_id": self.topic_id,
            "signal_type": self.signal_type,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
        }


class TrendReport(Base):
    """Aggregated trend report (hourly/daily/weekly)."""
    __tablename__ = "trend_reports"

    report_id = Column(String(36), unique=True, nullable=False, index=True,
                       default=lambda: uuid.uuid4().hex)
    period = Column(String(20), nullable=False)  # hourly, daily, weekly
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    summary = Column(Text, nullable=True)
    top_topics = Column(JSON, nullable=True)       # top N topics with scores
    category_distribution = Column(JSON, nullable=True)
    platform_distribution = Column(JSON, nullable=True)
    generated_prompts = Column(JSON, nullable=True)  # AI-generated content prompts
    total_signals = Column(Integer, default=0)
    breakout_count = Column(Integer, default=0)
    trending_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_reports_period", "period", "period_start"),
    )

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "period": self.period,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "summary": self.summary,
            "top_topics": self.top_topics or [],
            "category_distribution": self.category_distribution or {},
            "platform_distribution": self.platform_distribution or {},
            "generated_prompts": self.generated_prompts or [],
            "total_signals": self.total_signals,
            "breakout_count": self.breakout_count,
            "trending_count": self.trending_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
