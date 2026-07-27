"""
Sentiment Analyzer — Comment/description sentiment analysis.
Uses lightweight NLP (TextBlob/VADER) with LLM fallback.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from app.collector.schemas import SentimentResult

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyze sentiment from text content."""

    # Controversy keywords (common in divisive content)
    CONTROVERSY_PATTERNS = [
        r"\bcontrovers(?:y|ial)\b", r"\bdebate\b", r"\bheated\b",
        r"\bfight(?:ing)?\b", r"\bhate\b", r"\blove it or hate it\b",
        r"\bdivisive\b", r"\bpolarizing\b", r"\bbacklash\b",
        r"\boutrage\b", r"\bfurious\b", r"\bcancel(?:led|ing)?\b",
    ]

    # Positive/negative keyword lexicons (lightweight)
    POSITIVE_WORDS = {
        "amazing", "awesome", "love", "great", "best", "incredible",
        "beautiful", "brilliant", "excellent", "fantastic", "wonderful",
        "perfect", "outstanding", "impressive", "stunning", "genius",
        "fire", "goat", "goated", "based", "legendary", "iconic",
    }
    NEGATIVE_WORDS = {
        "terrible", "awful", "hate", "worst", "horrible", "disgusting",
        "trash", "garbage", "pathetic", "stupid", "ugly", "boring",
        "cringe", "lame", "overrated", "mid", "fail", "useless",
        "disappointing", "waste",
    }

    def __init__(self):
        self._vader = None
        self._textblob = None
        self._init_nlp()

    def _init_nlp(self):
        """Try to init VADER or TextBlob. Falls back to lexicon-only."""
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self._vader = SentimentIntensityAnalyzer()
            logger.info("[sentiment] VADER initialized")
            return
        except ImportError:
            pass

        try:
            from textblob import TextBlob
            self._textblob = TextBlob
            logger.info("[sentiment] TextBlob initialized")
            return
        except ImportError:
            logger.info("[sentiment] Using lexicon-only fallback")

    def analyze(self, text: str, comments: Optional[list[str]] = None) -> SentimentResult:
        """Analyze sentiment for a piece of content.

        Args:
            text: Main content text (title + description)
            comments: Optional list of comment texts
        """
        # Analyze main text
        main_pol = self._polarity(text)

        # Analyze comments if available
        comment_pols = [self._polarity(c) for c in (comments or [])]

        # Combine: weighted toward comments if available
        all_pols = [main_pol] + comment_pols

        positive_ratio = sum(1 for p in all_pols if p > 0.05) / max(len(all_pols), 1)
        negative_ratio = sum(1 for p in all_pols if p < -0.05) / max(len(all_pols), 1)
        neutral_ratio = 1.0 - positive_ratio - negative_ratio

        # Controversy: high positive AND high negative (divisive)
        controversy = self._controversy_score(text) if positive_ratio > 0.2 and negative_ratio > 0.2 else 0.0
        if comment_pols:
            controversy = max(controversy, self._comment_controversy(comment_pols))

        # Extract keywords
        pos_keywords = self._extract_keywords(text, self.POSITIVE_WORDS)
        neg_keywords = self._extract_keywords(text, self.NEGATIVE_WORDS)

        return SentimentResult(
            positive=round(positive_ratio, 4),
            negative=round(negative_ratio, 4),
            neutral=round(neutral_ratio, 4),
            controversy_index=round(min(controversy, 1.0), 4),
            top_positive_keywords=list(pos_keywords)[:5],
            top_negative_keywords=list(neg_keywords)[:5],
        )

    def _polarity(self, text: str) -> float:
        """Get polarity score: -1 (negative) to +1 (positive)."""
        if not text:
            return 0.0

        if self._vader:
            return self._vader.polarity_scores(text)["compound"]

        if self._textblob:
            return self._textblob(text).sentiment.polarity

        return self._lexicon_polarity(text)

    def _lexicon_polarity(self, text: str) -> float:
        """Simple lexicon-based polarity fallback."""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))

        pos_count = len(words & self.POSITIVE_WORDS)
        neg_count = len(words & self.NEGATIVE_WORDS)
        total = pos_count + neg_count

        if total == 0:
            return 0.0
        return (pos_count - neg_count) / total

    def _controversy_score(self, text: str) -> float:
        """Score how controversial/divisive the content is."""
        text_lower = text.lower()
        matches = sum(1 for pat in self.CONTROVERSY_PATTERNS
                      if re.search(pat, text_lower, re.IGNORECASE))
        # Normalize
        return min(matches / 3.0, 1.0)

    def _comment_controversy(self, polarities: list[float]) -> float:
        """Measure controversy from comment polarity distribution."""
        if len(polarities) < 2:
            return 0.0
        pos = [p for p in polarities if p > 0.1]
        neg = [p for p in polarities if p < -0.1]
        if not pos or not neg:
            return 0.0
        # High controversy = many strongly positive AND strongly negative comments
        return min((len(pos) + len(neg)) / len(polarities), 1.0)

    def _extract_keywords(self, text: str, lexicon: set[str]) -> set[str]:
        """Extract lexicon words present in text."""
        text_lower = text.lower()
        return {w for w in lexicon if w in text_lower}


# Singleton
sentiment_analyzer = SentimentAnalyzer()
