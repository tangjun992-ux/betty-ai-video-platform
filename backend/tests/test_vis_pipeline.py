"""
VIS Pipeline Unit Tests

Tests the pure-function analysis pipeline:
  - Viral Score algorithm
  - Growth velocity calculation
  - Sentiment analysis
  - Hook detection
  - Novelty scoring
  - Meme recognition
  - Prompt generation

Run: pytest tests/test_vis_pipeline.py -v
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

# Add project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.collector.schemas import RawPost, GrowthMetrics
from app.collector.analyzers.viral_score import ViralScorer, ViralConfig, WEIGHT_PRESETS
from app.collector.analyzers.growth_velocity import GrowthVelocityTracker
from app.collector.analyzers.sentiment import SentimentAnalyzer
from app.collector.analyzers.hook import HookAnalyzer
from app.collector.analyzers.novelty import NoveltyAnalyzer
from app.collector.analyzers.meme import MemeRecognizer
from app.collector.analyzers.prompt_gen import PromptGenerator
from app.collector.schemas import TrendingTopicResponse, EngagementMetrics, SentimentResult, HookPattern


# ═══════════════════ Helpers ═══════════════════
def make_post(
    title: str = "Test post",
    desc: str = "",
    upvotes: int = 100,
    comments: int = 50,
    shares: int = 20,
    views: int = 5000,
    platform: str = "reddit",
) -> RawPost:
    return RawPost(
        source_platform=platform,
        source_id=f"test_{hash(title) % 100000}",
        source_url=f"https://{platform}.com/test",
        title=title,
        description=desc,
        upvotes=upvotes,
        comments=comments,
        shares=shares,
        views=views,
        source_created_at=datetime.now(timezone.utc),
    )


# ═══════════════════ Viral Score Tests ═══════════════════
class TestViralScore:
    def test_basic_scoring(self):
        scorer = ViralScorer()
        post = make_post(upvotes=500, comments=200, shares=100, views=20000)
        result = scorer.score(post=post)

        assert 0 <= result.score <= 1
        assert result.tier in ("tier_1_breakout", "tier_2_trending", "tier_3_emerging", "noise")
        assert "engagement" in result.components
        assert "growth" in result.components
        assert "sentiment" in result.components

    def test_high_engagement_scores_higher(self):
        scorer = ViralScorer()
        low = make_post(upvotes=10, comments=5, shares=1, views=100)
        high = make_post(upvotes=5000, comments=2000, shares=1000, views=500000)

        low_result = scorer.score(post=low)
        high_result = scorer.score(post=high)

        assert high_result.score >= low_result.score, f"{high_result.score} < {low_result.score}"

    def test_weight_presets_different(self):
        balanced = ViralScorer(ViralConfig(weights=WEIGHT_PRESETS["balanced"]))
        engagement = ViralScorer(ViralConfig(weights=WEIGHT_PRESETS["engagement_heavy"]))

        post = make_post(upvotes=10000, comments=5000, shares=2000, views=1000000)
        b_score = balanced.score(post=post).score
        e_score = engagement.score(post=post).score

        # engagement_heavy should rank high-engagement content higher
        assert e_score >= b_score, f"engagement_heavy={e_score} should >= balanced={b_score}"

    def test_tier_thresholds(self):
        scorer = ViralScorer()
        # No engagement should be noise
        post = make_post(upvotes=0, comments=0, shares=0, views=0)
        result = scorer.score(post=post)
        assert result.tier == "noise"

    def test_growth_boosts_score(self):
        scorer = ViralScorer()
        post = make_post(upvotes=100, comments=50)
        no_growth = scorer.score(post=post)

        growth = GrowthMetrics(velocity_1h=500, velocity_6h=2000, velocity_24h=10000)
        with_growth = scorer.score(post=post, growth=growth)

        assert with_growth.components["growth"] > no_growth.components["growth"]


# ═══════════════════ Growth Velocity Tests ═══════════════════
class TestGrowthVelocity:
    def test_cold_start_returns_zero(self):
        tracker = GrowthVelocityTracker()
        result = tracker.calculate("new_topic_123")
        assert result.velocity_1h == 0.0
        assert result.velocity_6h == 0.0

    def test_basic_velocity(self):
        tracker = GrowthVelocityTracker()
        now = datetime.now(timezone.utc)

        tracker.record("test_1", 100, now)
        tracker.record("test_1", 200, now)

        result = tracker.calculate("test_1")
        # Growth from 100 -> 200 over near-zero time = very high velocity
        assert result.velocity_1h is not None
        assert result.velocity_1h > 0

    def test_no_breakout_on_cold_start(self):
        tracker = GrowthVelocityTracker()
        is_breakout, z = tracker.detect_breakout("unknown")
        assert is_breakout is False

    def test_memory_cleanup(self):
        tracker = GrowthVelocityTracker()
        for i in range(300):
            tracker.record("bulk_test", i, datetime.now(timezone.utc))
        snaps = tracker._get_snapshots("bulk_test")
        assert len(snaps) <= 200


# ═══════════════════ Sentiment Tests ═══════════════════
class TestSentiment:
    def test_positive_text(self):
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("This is amazing and beautiful!")
        assert result.positive > result.negative

    def test_negative_text(self):
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("This is terrible and horrible garbage!")
        assert result.negative > result.positive

    def test_empty_text(self):
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("")
        assert result.neutral >= 0.5

    def test_controversy_detection(self):
        analyzer = SentimentAnalyzer()
        # Controversy is detected from multiple comments with opposing views
        result = analyzer.analyze(
            "A topic that divides people",
            comments=["This is amazing!", "I love this!", "This is terrible!", "Hate it!", "So bad!"],
        )
        assert result.controversy_index > 0


# ═══════════════════ Hook Detection Tests ═══════════════════
class TestHookDetection:
    def test_curiosity_gap(self):
        analyzer = HookAnalyzer()
        result = analyzer.analyze("You won't believe what happens next")
        hooks = [h.pattern for h in result.hooks]
        assert "Curiosity Gap" in hooks

    def test_question_hook(self):
        analyzer = HookAnalyzer()
        result = analyzer.analyze("Have you ever wondered why?")
        hooks = [h.category for h in result.hooks]
        assert "question_hook" in hooks

    def test_story_hook(self):
        analyzer = HookAnalyzer()
        result = analyzer.analyze("Last week I discovered something incredible")
        hooks = [h.pattern for h in result.hooks]
        assert "Story Hook" in hooks

    def test_listicle(self):
        analyzer = HookAnalyzer()
        result = analyzer.analyze("5 things you need to know about AI")
        hooks = [h.category for h in result.hooks]
        assert "listicle" in hooks

    def test_primary_hook_assigned(self):
        analyzer = HookAnalyzer()
        result = analyzer.analyze("You won't believe what happens next! 5 reasons why!")
        assert result.primary_hook is not None
        assert result.hook_density > 0


# ═══════════════════ Novelty Tests ═══════════════════
class TestNovelty:
    def test_no_history_high_novelty(self):
        analyzer = NoveltyAnalyzer()
        post = make_post("Brand new topic never seen before")
        score = analyzer.compute(post)
        assert score > 0.5, f"Expected high novelty, got {score}"

    def test_duplicate_title_low_novelty(self):
        analyzer = NoveltyAnalyzer()
        same_title = "Python 3.13 released with new features"
        analyzer.add_to_history(same_title, None, datetime.now(timezone.utc))
        post = make_post(same_title)
        score = analyzer.compute(post)
        assert score < 0.5, f"Expected low novelty for duplicate, got {score}"

    def test_keywords_extracted(self):
        analyzer = NoveltyAnalyzer()
        keywords = analyzer._extract_keywords("Machine learning models improve healthcare outcomes", None)
        assert len(keywords) > 0
        assert "machine" in keywords or "learning" in keywords or "healthcare" in keywords


# ═══════════════════ Meme Recognition Tests ═══════════════════
class TestMemeRecognition:
    def test_pov_format(self):
        recognizer = MemeRecognizer()
        strength, matches = recognizer.analyze("POV: You're the main character")
        assert strength > 0
        assert any("POV" in m.template for m in matches)

    def test_drake_format(self):
        recognizer = MemeRecognizer()
        strength, matches = recognizer.analyze("Drake says no to this, yes to that")
        assert strength > 0 or len(matches) > 0

    def test_nobody_format(self):
        recognizer = MemeRecognizer()
        strength, matches = recognizer.analyze("Nobody:\nAbsolutely nobody:\nMe:")
        assert strength > 0

    def test_copypasta_detection(self):
        recognizer = MemeRecognizer()
        strength, matches = recognizer.analyze("What the fuck did you just say about me")
        assert strength > 0

    def test_no_meme_plain_text(self):
        recognizer = MemeRecognizer()
        strength, matches = recognizer.analyze("Regular news update about technology advances")
        # May get low confidence from weak patterns, but should be minimal
        assert strength < 0.5, f"Expected low meme strength for plain text, got {strength}"

    def test_doge_format(self):
        recognizer = MemeRecognizer()
        strength, matches = recognizer.analyze("Such code. Very Python. Wow.")
        assert strength > 0


# ═══════════════════ Prompt Generation Tests ═══════════════════
class TestPromptGeneration:
    def test_generate_single_prompt(self):
        gen = PromptGenerator()
        topic = TrendingTopicResponse(
            topic_id="test_1",
            source_platform="reddit",
            title="AI generates realistic video from text",
            viral_score=0.85,
            viral_tier="tier_1_breakout",
            engagement=EngagementMetrics(upvotes=1000, comments=500, shares=200, views=50000, score=1500),
            growth=GrowthMetrics(velocity_1h=100, velocity_6h=500, velocity_24h=2000, acceleration=10),
            sentiment=SentimentResult(positive=0.7, negative=0.1, neutral=0.2, controversy_index=0.1),
            hooks=[HookPattern(category="curiosity_gap", pattern="Curiosity Gap", strength=0.85, matched_text="test")],
        )
        result = gen.generate(topic, content_type="video")
        assert result.topic_id == "test_1"
        assert result.content_type == "video"
        assert len(result.brief) > 50

    def test_generate_batch(self):
        gen = PromptGenerator()
        topics = [
            TrendingTopicResponse(
                topic_id=f"t_{i}",
                source_platform="youtube",
                title=f"Trending topic {i}",
                viral_score=0.7 + i * 0.05,
                viral_tier="tier_2_trending",
                engagement=EngagementMetrics(upvotes=100, comments=50, shares=20, views=5000, score=150),
                growth=GrowthMetrics(),
                sentiment=SentimentResult(positive=0.5, negative=0.2, neutral=0.3, controversy_index=0),
                hooks=[],
            )
            for i in range(5)
        ]
        results = gen.generate_batch(topics, limit=3)
        assert len(results) == 3
        assert results[0].estimated_viral_score >= results[-1].estimated_viral_score


# ═══════════════════ Integration ═══════════════════
class TestPipelineIntegration:
    """End-to-end: raw post → full analysis chain."""

    def test_full_pipeline(self):
        """Verify all analyzers chain without errors."""
        post = make_post(
            title="POV: You just wrote perfect unit tests",
            desc="Nobody:\nMe: writing tests at 3am",
            upvotes=2000, comments=800, shares=500, views=100000,
        )

        # Run each step
        from app.collector.analyzers.growth_velocity import growth_tracker
        from app.collector.analyzers.sentiment import sentiment_analyzer
        from app.collector.analyzers.hook import hook_analyzer
        from app.collector.analyzers.novelty import novelty_analyzer
        from app.collector.analyzers.meme import meme_recognizer
        from app.collector.analyzers.viral_score import viral_scorer

        # Growth
        engagement = post.upvotes * 1 + post.comments * 2 + post.shares * 3
        growth_tracker.record(post.source_id, engagement)
        growth = growth_tracker.calculate(post.source_id)

        # Sentiment
        text = f"{post.title} {post.description or ''}"
        sentiment = sentiment_analyzer.analyze(text)
        assert 0 <= sentiment.positive <= 1

        # Hooks
        hooks = hook_analyzer.analyze(post.title, post.description)
        assert len(hooks.hooks) > 0, "Should detect hook patterns"

        # Novelty
        novelty = novelty_analyzer.compute(post)
        assert 0 <= novelty <= 1

        # Meme
        meme_strength, meme_matches = meme_recognizer.analyze(post.title, post.description)
        assert 0 <= meme_strength <= 1
        assert len(meme_matches) > 0, "POV + Nobody format should match"

        # Viral score
        sent_pol = 0.5 + (sentiment.positive - sentiment.negative) * 0.5
        viral = viral_scorer.score(
            post=post, growth=growth,
            sentiment_polarity=max(0, min(1, sent_pol)),
            sentiment_controversy=sentiment.controversy_index,
            novelty_score=novelty,
            meme_match_strength=meme_strength,
        )
        assert viral.score > 0.3, f"Should score above 0.3, got {viral.score}"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
