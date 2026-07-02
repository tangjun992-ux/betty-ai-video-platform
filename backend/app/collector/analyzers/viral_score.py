"""
Viral Score Engine — Multi-dimensional scoring algorithm.

V = w1·E_norm + w2·G_norm + w3·S_norm + w4·N_norm + w5·M_norm
"""
from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass, field
from typing import Optional

from app.collector.schemas import RawPost, ViralScoreResult, EngagementMetrics, GrowthMetrics

logger = logging.getLogger(__name__)

# Default weights (sum = 1.0)
DEFAULT_WEIGHTS: dict[str, float] = {
    "engagement": 0.30,
    "growth": 0.30,
    "sentiment": 0.15,
    "novelty": 0.15,
    "meme": 0.10,
}

# A/B test weight profiles
WEIGHT_PRESETS: dict[str, dict[str, float]] = {
    "balanced": {  # Current default
        "engagement": 0.30, "growth": 0.30, "sentiment": 0.15, "novelty": 0.15, "meme": 0.10,
    },
    "engagement_heavy": {  # Prioritize raw popularity
        "engagement": 0.45, "growth": 0.25, "sentiment": 0.10, "novelty": 0.10, "meme": 0.10,
    },
    "growth_heavy": {  # Prioritize velocity/momentum
        "engagement": 0.20, "growth": 0.45, "sentiment": 0.15, "novelty": 0.10, "meme": 0.10,
    },
    "novelty_first": {  # Prioritize fresh/unique content
        "engagement": 0.20, "growth": 0.20, "sentiment": 0.10, "novelty": 0.40, "meme": 0.10,
    },
    "meme_aware": {  # Meme-heavy platforms (TikTok/X)
        "engagement": 0.25, "growth": 0.20, "sentiment": 0.10, "novelty": 0.15, "meme": 0.30,
    },
    "sentiment_driven": {  # Controversial/discussion content
        "engagement": 0.20, "growth": 0.20, "sentiment": 0.35, "novelty": 0.15, "meme": 0.10,
    },
}

# Preset name for active weights (set via env VIS_WEIGHT_PROFILE)
ACTIVE_PRESET: str = os.getenv("VIS_WEIGHT_PROFILE", "balanced")

# Tier thresholds
TIER_THRESHOLDS = {
    "tier_1_breakout": 0.80,
    "tier_2_trending": 0.60,
    "tier_3_emerging": 0.40,
}


@dataclass
class ViralConfig:
    weights: dict[str, float] = field(default_factory=lambda: dict(WEIGHT_PRESETS.get(ACTIVE_PRESET, DEFAULT_WEIGHTS)))
    profile: str = ACTIVE_PRESET
    tier_thresholds: dict[str, float] = field(default_factory=lambda: dict(TIER_THRESHOLDS))
    engagement_decay_hours: float = 48.0
    min_engagement_for_scoring: int = 10
    breakout_velocity_threshold: float = 2.5


class ViralScorer:
    """Calculate viral score for content items."""

    def __init__(self, config: Optional[ViralConfig] = None):
        self.config = config or ViralConfig()

    def score(
        self,
        post: RawPost,
        growth: Optional[GrowthMetrics] = None,
        sentiment_polarity: float = 0.5,  # 0=negative, 1=positive
        sentiment_controversy: float = 0.0,
        novelty_score: float = 0.5,
        meme_match_strength: float = 0.0,
        historical_max_engagement: float = 1.0,
        historical_max_velocity: float = 1.0,
    ) -> ViralScoreResult:
        """Calculate viral score with full component breakdown."""
        w = self.config.weights

        # ── E: Normalized Engagement ──
        e_raw = self._engagement_score(post)
        e_norm = min(e_raw / max(historical_max_engagement, 1), 1.0)
        # Apply freshness decay
        hours_ago = self._hours_since(post.source_created_at)
        if hours_ago is not None and hours_ago > 0:
            decay = math.exp(-hours_ago * math.log(2) / self.config.engagement_decay_hours)
            e_norm *= decay

        # ── G: Growth Velocity (normalized) ──
        g_raw = growth.velocity_1h if growth else 0.0
        g_norm = min(g_raw / max(historical_max_velocity, 1), 1.0) if g_raw else 0.0

        # ── S: Sentiment Polarity ──
        s_norm = abs(sentiment_polarity - 0.5) * 2  # Scale so 0 or 1 → 1.0, 0.5 → 0
        # Boost controversial content (high engagement driver)
        s_norm = min(s_norm + sentiment_controversy * 0.3, 1.0)

        # ── N: Novelty ──
        n_norm = min(novelty_score, 1.0)

        # ── M: Meme Match ──
        m_norm = min(meme_match_strength, 1.0)

        # ── Compute weighted score ──
        score = (
            w["engagement"] * e_norm +
            w["growth"] * g_norm +
            w["sentiment"] * s_norm +
            w["novelty"] * n_norm +
            w["meme"] * m_norm
        )

        # ── Tier assignment ──
        tier = self._assign_tier(score)
        breakout_prob = self._breakout_probability(score, g_norm, e_norm)

        return ViralScoreResult(
            score=round(score, 4),
            tier=tier,
            breakout_probability=round(breakout_prob, 4) if breakout_prob is not None else None,
            components={
                "engagement": round(e_norm, 4),
                "growth": round(g_norm, 4),
                "sentiment": round(s_norm, 4),
                "novelty": round(n_norm, 4),
                "meme": round(m_norm, 4),
                "raw_engagement": e_raw,
                "raw_growth": g_raw,
            },
        )

    def score_batch(
        self,
        posts: list[RawPost],
        growth_map: dict[str, GrowthMetrics],
        sentiment_map: dict[str, tuple[float, float]],
        novelty_map: dict[str, float],
        meme_map: dict[str, float],
    ) -> list[tuple[RawPost, ViralScoreResult]]:
        """Batch score multiple posts with shared historical maxes."""
        if not posts:
            return []

        # Compute window maxes for normalization
        all_engagement = [self._engagement_score(p) for p in posts]
        all_velocity = [growth_map.get(p.source_id, GrowthMetrics()).velocity_1h or 0 for p in posts]

        max_eng = max(all_engagement) if all_engagement else 1
        max_vel = max(all_velocity) if all_velocity else 1

        results = []
        for post in posts:
            growth = growth_map.get(post.source_id, GrowthMetrics())
            sent_pol, sent_cont = sentiment_map.get(post.source_id, (0.5, 0.0))
            novelty = novelty_map.get(post.source_id, 0.5)
            meme = meme_map.get(post.source_id, 0.0)

            vs = self.score(
                post=post,
                growth=growth,
                sentiment_polarity=sent_pol,
                sentiment_controversy=sent_cont,
                novelty_score=novelty,
                meme_match_strength=meme,
                historical_max_engagement=max_eng,
                historical_max_velocity=max_vel,
            )
            results.append((post, vs))

        # Sort by score descending
        results.sort(key=lambda x: x[1].score, reverse=True)
        return results

    def _engagement_score(self, post: RawPost) -> float:
        """Compute raw engagement score from post metrics."""
        # Weighted engagement: views (low weight) + upvotes + comments*2 + shares*3
        score = (
            post.upvotes * 1.0 +
            post.comments * 2.0 +
            post.shares * 3.0 +
            post.views * 0.01
        )
        return max(score, 1.0)  # Minimum 1 to avoid division issues

    def _assign_tier(self, score: float) -> str:
        thresholds = self.config.tier_thresholds
        if score >= thresholds.get("tier_1_breakout", 0.80):
            return "tier_1_breakout"
        elif score >= thresholds.get("tier_2_trending", 0.60):
            return "tier_2_trending"
        elif score >= thresholds.get("tier_3_emerging", 0.40):
            return "tier_3_emerging"
        return "noise"

    def _breakout_probability(
        self, score: float, g_norm: float, e_norm: float,
    ) -> Optional[float]:
        """Estimate probability this content will break out further."""
        # Logistic-style function based on score + growth momentum
        if g_norm <= 0 or e_norm <= 0:
            return None

        # Breakout = high score AND accelerating growth
        x = score * 3 + g_norm * 2 - 1.5
        prob = 1.0 / (1.0 + math.exp(-x))
        return round(prob, 4)

    @staticmethod
    def _hours_since(dt) -> Optional[float]:
        """Hours since a datetime, or None."""
        if dt is None:
            return None
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).total_seconds() / 3600


# Singleton
viral_scorer = ViralScorer()
