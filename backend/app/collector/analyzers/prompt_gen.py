"""
Viral Prompt Generator — Converts trending topics into Director-compatible briefs.
The bridge from Viral Intelligence → Content Production.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.collector.schemas import (
    HookPattern, SentimentResult, ViralScoreResult,
    GeneratedPrompt, TrendingTopicResponse,
)

logger = logging.getLogger(__name__)

# Content type templates
PROMPT_TEMPLATES = {
    "video": """Create a short viral video about: {title}

Context: This topic is {tier} ({viral_score} viral score) on {platform}.
Hook strategy: {hook_strategy}
Sentiment: {sentiment_summary}
Why this works: {viral_context}

Make it: {tone} style, {duration}-seconds, optimized for {platform}.
Focus on the first 3 seconds — use a {primary_hook} pattern.""",

    "image_series": """Create a viral image series about: {title}

Context: This topic is trending on {platform} with {viral_score} score.
Hook strategy: {hook_strategy}
Viral angle: {viral_context}

Generate 4 images as a swipeable carousel.
Style: {tone}, platform-optimized for {platform}.""",

    "talking": """Create a talking-head commentary about: {title}

Context: This is a {tier} topic blowing up on {platform}.
Hook strategy: {hook_strategy}
Sentiment angle: {sentiment_summary}

Record a 60-second opinion piece.
Tone: {tone}. Start with: {primary_hook} hook.""",

    "campaign": """Create a marketing campaign around: {title}

Context: This is trending with {viral_score} viral potential on {platform}.
Hook strategy: {hook_strategy}
Viral mechanism: {viral_context}

Campaign assets: 1 hero video + 3 supporting images.
Style: {tone}, call-to-action driven.
Target sentiment: {sentiment_angle}.""",
}

# Tone selection based on sentiment
SENTIMENT_TONES = {
    "positive": ["inspirational", "uplifting", "energetic"],
    "negative": ["critical", "investigative", "edgy"],
    "neutral": ["informative", "educational", "balanced"],
    "controversial": ["provocative", "debate-style", "bold"],
}


class PromptGenerator:
    """Generate production-ready briefs from trending topics."""

    def __init__(self):
        pass

    def generate(
        self,
        topic: TrendingTopicResponse,
        content_type: str = "video",
        duration: int = 30,
    ) -> GeneratedPrompt:
        """Generate a single prompt from a trending topic."""
        tone = self._pick_tone(topic.sentiment)
        hook_strategy = self._build_hook_strategy(topic.hooks)
        primary_hook = topic.hooks[0].pattern if topic.hooks else "Curiosity Gap"
        sentiment_summary = self._summarize_sentiment(topic.sentiment)

        template = PROMPT_TEMPLATES.get(content_type, PROMPT_TEMPLATES["video"])
        brief = template.format(
            title=topic.title,
            tier=topic.viral_tier.replace("_", " ").title(),
            viral_score=topic.viral_score,
            platform=topic.source_platform,
            hook_strategy=hook_strategy,
            sentiment_summary=sentiment_summary,
            viral_context=self._build_viral_context(topic),
            tone=tone,
            duration=duration,
            primary_hook=primary_hook,
            sentiment_angle=self._sentiment_angle(topic.sentiment),
        )

        return GeneratedPrompt(
            topic_id=topic.topic_id,
            topic_title=topic.title,
            platform=topic.source_platform,
            content_type=content_type,
            brief=brief.strip(),
            hooks_to_use=[h.pattern for h in topic.hooks[:3]],
            viral_context=self._build_viral_context(topic),
            estimated_viral_score=topic.viral_score,
        )

    def generate_batch(
        self,
        topics: list[TrendingTopicResponse],
        content_type: str = "video",
        limit: int = 10,
    ) -> list[GeneratedPrompt]:
        """Generate prompts for multiple topics, sorted by viral potential."""
        # Sort by viral score descending
        sorted_topics = sorted(topics, key=lambda t: t.viral_score, reverse=True)
        return [
            self.generate(t, content_type)
            for t in sorted_topics[:limit]
        ]

    def generate_diverse(
        self,
        topics: list[TrendingTopicResponse],
        limit: int = 10,
    ) -> list[GeneratedPrompt]:
        """Generate prompts with diverse content types."""
        type_rotation = ["video", "image_series", "talking", "campaign"]
        sorted_topics = sorted(topics, key=lambda t: t.viral_score, reverse=True)
        prompts = []
        for i, topic in enumerate(sorted_topics[:limit]):
            ct = type_rotation[i % len(type_rotation)]
            prompts.append(self.generate(topic, ct))
        return prompts

    def _pick_tone(self, sentiment: SentimentResult) -> str:
        """Pick tone based on sentiment profile."""
        import random
        if sentiment.controversy_index > 0.5:
            return random.choice(SENTIMENT_TONES["controversial"])
        if sentiment.positive > 0.5:
            return random.choice(SENTIMENT_TONES["positive"])
        if sentiment.negative > 0.5:
            return random.choice(SENTIMENT_TONES["negative"])
        return random.choice(SENTIMENT_TONES["neutral"])

    def _build_hook_strategy(self, hooks: list[HookPattern]) -> str:
        """Build a hook strategy description."""
        if not hooks:
            return "Curiosity-driven opening with a question"
        primary = hooks[0].pattern
        secondary = hooks[1].pattern if len(hooks) > 1 else "strong visual"
        return f"Lead with {primary}, reinforce with {secondary}"

    def _summarize_sentiment(self, s: SentimentResult) -> str:
        """Summarize sentiment for prompt context."""
        if s.controversy_index > 0.5:
            return f"Highly divisive ({s.positive:.0%} positive vs {s.negative:.0%} negative)"
        if s.positive > 0.6:
            return f"Overwhelmingly positive ({s.positive:.0%})"
        if s.negative > 0.6:
            return f"Predominantly negative ({s.negative:.0%})"
        return f"Mixed reception ({s.positive:.0%} positive)"

    def _sentiment_angle(self, s: SentimentResult) -> str:
        """Determine best sentiment approach for content."""
        if s.controversy_index > 0.4:
            return "both sides — present the debate"
        if s.positive > s.negative:
            return "positive / aspirational"
        return "critical / analytical"

    def _build_viral_context(self, topic: TrendingTopicResponse) -> str:
        """Build viral context explanation."""
        parts = [f"Ranking: {topic.viral_tier.replace('_', ' ').title()}"]
        if topic.growth.velocity_1h:
            parts.append(f"Growth: {topic.growth.velocity_1h:.0f} engagements/hour")
        if topic.hooks:
            parts.append(f"Best hook: {topic.hooks[0].pattern}")
        return ". ".join(parts)


# Singleton
prompt_generator = PromptGenerator()
