"""
Analysis Pipeline — Chained steps: growth → sentiment → hook → novelty → viral score.
Pure functions, no DB access, testable in isolation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.collector.analyzers.viral_score import viral_scorer
from app.collector.analyzers.growth_velocity import growth_tracker
from app.collector.analyzers.sentiment import sentiment_analyzer
from app.collector.analyzers.hook import hook_analyzer, HookPattern
from app.collector.analyzers.novelty import novelty_analyzer
from app.collector.analyzers.meme import meme_recognizer, MemeMatch
from app.collector.schemas import RawPost, ViralScoreResult, SentimentResult, GrowthMetrics

logger = logging.getLogger(__name__)


class AnalysisResult:
    """Complete analysis output for a single post."""
    __slots__ = ("post", "viral", "sentiment", "growth", "hooks", "novelty", "meme_strength", "meme_matches", "engagement")

    def __init__(self, post, viral, sentiment, growth, hooks, novelty, meme_strength, meme_matches, engagement):
        self.post = post
        self.viral = viral
        self.sentiment = sentiment
        self.growth = growth
        self.hooks = hooks
        self.novelty = novelty
        self.meme_strength = meme_strength
        self.meme_matches = meme_matches
        self.engagement = engagement


class AnalysisPipeline:
    """Chain of analysis steps for a single post. Stateless, testable."""

    def analyze(self, post: RawPost) -> AnalysisResult:
        """Run full analysis pipeline on a single post.

        Order: engagement → growth → sentiment → hooks → novelty → viral score.
        """
        # 1. Engagement
        engagement = self._total_engagement(post)
        growth_tracker.record(post.source_id, engagement)

        # 2. Growth metrics
        growth = growth_tracker.calculate(post.source_id)

        # 3. Sentiment
        text = f"{post.title} {post.description or ''}"
        sentiment = sentiment_analyzer.analyze(text)

        # 4. Hook detection
        hooks = hook_analyzer.analyze(post.title, post.description)

        # 5. Novelty
        novelty = novelty_analyzer.compute(post)

        # 6. Meme recognition
        meme_strength, meme_matches = meme_recognizer.analyze(post.title, post.description)

        # 7. Viral score
        sent_polarity = 0.5 + (sentiment.positive - sentiment.negative) * 0.5
        sent_polarity = max(0.0, min(1.0, sent_polarity))

        viral = viral_scorer.score(
            post=post, growth=growth,
            sentiment_polarity=sent_polarity,
            sentiment_controversy=sentiment.controversy_index,
            novelty_score=novelty,
            meme_match_strength=meme_strength,
        )

        # Record for future novelty comparison
        novelty_analyzer.add_to_history(
            post.title, post.description,
            post.source_created_at or datetime.now(timezone.utc),
        )

        return AnalysisResult(post, viral, sentiment, growth, hooks.hooks, novelty, meme_strength, meme_matches, engagement)

    def analyze_batch(self, posts: list[RawPost]) -> list[AnalysisResult]:
        """Analyze multiple posts. Failures are logged but don't stop the batch."""
        results = []
        for post in posts:
            try:
                results.append(self.analyze(post))
            except Exception as e:
                logger.exception("[pipeline] Analysis failed for %s/%s: %s",
                               post.source_platform, post.source_id, e)
        return results

    @staticmethod
    def _total_engagement(post: RawPost) -> float:
        return post.upvotes * 1.0 + post.comments * 2.0 + post.shares * 3.0 + post.views * 0.01


analysis_pipeline = AnalysisPipeline()
