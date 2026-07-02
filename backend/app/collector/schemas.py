"""
Viral Intelligence System — Pydantic Schemas
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ─────────────────────────────── Source Schemas ───────────────────────────────
class RawPost(BaseModel):
    """Normalized raw post from any source."""
    source_platform: str
    source_id: str
    source_url: str
    title: str
    description: Optional[str] = None
    author: Optional[str] = None
    thumbnail_url: Optional[str] = None

    # Platform-specific
    subreddit: Optional[str] = None
    channel: Optional[str] = None
    category: Optional[str] = None

    # Engagement
    upvotes: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0

    # Metadata
    source_created_at: Optional[datetime] = None
    raw_data: Optional[dict] = None


class CollectRequest(BaseModel):
    source: str = Field(..., description="reddit | youtube")
    subreddit: Optional[str] = None
    query: Optional[str] = None
    limit: int = Field(default=25, ge=1, le=100)
    time_filter: str = Field(default="day", description="hour | day | week | month | year | all")


# ─────────────────────────────── Analysis Schemas ───────────────────────────────
class EngagementMetrics(BaseModel):
    upvotes: int = 0
    comments: int = 0
    shares: int = 0
    views: int = 0
    score: float = 0.0


class GrowthMetrics(BaseModel):
    velocity_1h: Optional[float] = None
    velocity_6h: Optional[float] = None
    velocity_24h: Optional[float] = None
    acceleration: Optional[float] = None


class ViralScoreResult(BaseModel):
    score: float
    tier: str  # tier_1_breakout | tier_2_trending | tier_3_emerging | noise
    breakout_probability: Optional[float] = None
    components: dict = Field(default_factory=dict)  # E, G, S, N, M sub-scores


class SentimentResult(BaseModel):
    positive: float
    negative: float
    neutral: float
    controversy_index: float
    top_positive_keywords: list[str] = Field(default_factory=list)
    top_negative_keywords: list[str] = Field(default_factory=list)


class HookPattern(BaseModel):
    category: str
    pattern: str
    strength: float  # 0-1
    matched_text: str


class HookAnalysisResult(BaseModel):
    hooks: list[HookPattern] = Field(default_factory=list)
    primary_hook: Optional[HookPattern] = None
    hook_density: float = 0.0  # hooks per text length


class MemeMatch(BaseModel):
    template: str
    confidence: float
    matched_text: str = ""
    category: Optional[str] = None


class TopicAnalysis(BaseModel):
    topic_id: str
    viral: ViralScoreResult
    sentiment: SentimentResult
    hooks: HookAnalysisResult
    memes: list[MemeMatch] = Field(default_factory=list)
    growth: GrowthMetrics


# ─────────────────────────────── Prompt Generation ───────────────────────────────
class GeneratedPrompt(BaseModel):
    topic_id: str
    topic_title: str
    platform: str
    content_type: str  # video | image_series | talking | campaign
    brief: str  # Director-compatible brief
    hooks_to_use: list[str]
    viral_context: str  # why this will perform
    estimated_viral_score: float


class PromptGenRequest(BaseModel):
    topic_ids: list[str] = Field(default_factory=list)
    viral_tier: Optional[str] = None  # filter by tier
    content_type: Optional[str] = None  # video | image | talking | campaign
    limit: int = Field(default=5, ge=1, le=20)


# ─────────────────────────────── Trend Responses ───────────────────────────────
class TrendingTopicResponse(BaseModel):
    topic_id: str
    source_platform: str
    title: str
    thumbnail_url: Optional[str] = None
    viral_score: float
    viral_tier: str
    engagement: EngagementMetrics
    growth: GrowthMetrics
    sentiment: SentimentResult
    hooks: list[HookPattern]
    meme_matches: list[MemeMatch] = Field(default_factory=list)
    created_at: Optional[str] = None


class TrendReportResponse(BaseModel):
    report_id: str
    period: str
    period_start: str
    period_end: str
    summary: Optional[str] = None
    top_topics: list[dict]
    generated_prompts: list[dict]
    total_signals: int
    breakout_count: int
    trending_count: int


# ─────────────────────────────── Dashboard ───────────────────────────────
class DashboardStats(BaseModel):
    total_topics_tracked: int
    breakout_topics: int
    trending_topics: int
    signals_last_24h: int
    top_categories: list[dict]
    platform_breakdown: dict[str, int]
    viral_score_distribution: dict[str, int]
    recent_breakouts: list[TrendingTopicResponse]
