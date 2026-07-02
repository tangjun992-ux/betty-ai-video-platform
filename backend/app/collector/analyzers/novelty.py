"""
Novelty Analyzer — Computes how novel a topic is vs. recent trending history.

Uses lightweight keyword extraction + Jaccard similarity (no heavy NLP deps).
Score: 0 = identical to existing trends, 1 = completely novel.

Algorithm:
  1. Extract keywords from title + description (noun phrases, bigrams, named entities)
  2. Compare against recent topics' keyword sets using Jaccard similarity
  3. Novelty = 1 - max_jaccard_similarity
  4. Apply temporal decay — older topics matter less for novelty comparison
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Optional, Set

from app.collector.schemas import RawPost

logger = logging.getLogger(__name__)

# Common stopwords to filter (Chinese + English)
STOPWORDS: Set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "both", "each", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "just", "because", "but", "and", "or",
    "if", "while", "about", "until", "also", "this", "that", "these",
    "those", "it", "its", "he", "she", "they", "them", "we", "you",
    "me", "my", "your", "his", "her", "their", "our", "i", "am",
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
    "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
    "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它",
    "们", "那", "什么", "怎么", "哪", "吗", "吧", "啊", "呢",
}

# Viral/buzz words that inflate false similarity
BUZZ_STOPWORDS: Set[str] = {
    "viral", "trending", "video", "watch", "new", "best", "top",
    "amazing", "incredible", "must", "see", "check", "out",
}


class NoveltyAnalyzer:
    """Compute topic novelty against recent trending history."""

    def __init__(self, window_size: int = 500, decay_hours: float = 24.0):
        """
        Args:
            window_size: Max recent topics to compare against
            decay_hours: Half-life for temporal relevance decay
        """
        self.window_size = window_size
        self.decay_hours = decay_hours
        # In-memory cache of recent topic keyword sets
        self._recent_topics: list[tuple[Set[str], datetime]] = []
        self._max_cache = window_size * 2

    def compute(self, post: RawPost, recent_topics: Optional[list[dict]] = None) -> float:
        """Compute novelty score for a post.

        Args:
            post: The post to evaluate
            recent_topics: Optional list of recent topic dicts with 'title' and 'created_at'
                          If None, uses internal cache from prior add_to_history() calls.

        Returns:
            Novelty score 0.0 (identical to existing) to 1.0 (completely novel).
        """
        post_keywords = self._extract_keywords(post.title, post.description)

        if not post_keywords:
            return 0.5  # Can't determine

        # Get comparison set
        if recent_topics:
            comparison = self._topics_to_keyword_sets(recent_topics, post.source_created_at)
        else:
            comparison = self._get_recent_sets(post.source_created_at)

        if not comparison:
            return 0.85  # No history → highly novel

        # Compute max Jaccard similarity (with temporal decay)
        max_similarity = 0.0
        for kw_set, topic_time in comparison:
            sim = self._jaccard(post_keywords, kw_set)
            # Apply temporal decay: older topics = less relevant for novelty
            if topic_time and post.source_created_at:
                hours_ago = (post.source_created_at - topic_time).total_seconds() / 3600
                if hours_ago > 0:
                    decay = 2 ** (-hours_ago / self.decay_hours)
                    sim *= decay
            max_similarity = max(max_similarity, sim)

        novelty = 1.0 - max_similarity
        # Clamp and round
        return round(max(0.0, min(1.0, novelty)), 4)

    def add_to_history(self, title: str, description: Optional[str], timestamp: datetime):
        """Record a topic for future novelty comparison."""
        keywords = self._extract_keywords(title, description)
        if keywords:
            self._recent_topics.append((keywords, timestamp))
            # Prune old entries
            if len(self._recent_topics) > self._max_cache:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=self.decay_hours * 4)
                self._recent_topics = [
                    (kw, ts) for kw, ts in self._recent_topics
                    if ts > cutoff
                ][-self.window_size:]

    def _extract_keywords(self, title: str, description: Optional[str] = None) -> Set[str]:
        """Extract meaningful keywords from text."""
        text = title
        if description:
            text += " " + description[:500]

        # Tokenize: words 3+ chars, filter stopwords and buzzwords
        words = re.findall(r'\b[a-zA-Z\u4e00-\u9fff]{3,}\b', text.lower())

        # Count frequency
        counter = Counter(w for w in words if w not in STOPWORDS and w not in BUZZ_STOPWORDS)

        # Extract top keywords + bigrams
        keywords = set()

        # Top unigrams by frequency
        for word, _ in counter.most_common(15):
            keywords.add(word)

        # Bigrams (for phrases like "machine learning")
        tokens = [w for w in words if w not in STOPWORDS]
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]}_{tokens[i+1]}"
            if len(bigram) >= 7:
                keywords.add(bigram)

        return keywords

    def _jaccard(self, set_a: Set[str], set_b: Set[str]) -> float:
        """Jaccard similarity: |A∩B| / |A∪B|."""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def _topics_to_keyword_sets(
        self, topics: list[dict], reference_time: Optional[datetime],
    ) -> list[tuple[Set[str], Optional[datetime]]]:
        """Convert topic dicts to keyword sets with timestamps."""
        result = []
        for t in topics[:self.window_size]:
            kw = self._extract_keywords(t.get("title", ""), t.get("description"))
            if kw:
                ts = t.get("created_at")
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        ts = None
                result.append((kw, ts))
        return result

    def _get_recent_sets(
        self, reference_time: Optional[datetime],
    ) -> list[tuple[Set[str], Optional[datetime]]]:
        """Get recent keyword sets from internal cache, with temporal filter."""
        if not reference_time:
            return [(kw, ts) for kw, ts in self._recent_topics]

        cutoff = reference_time - timedelta(hours=self.decay_hours * 3)
        return [
            (kw, ts) for kw, ts in self._recent_topics
            if ts >= cutoff and ts <= reference_time
        ][-self.window_size:]

    def clear(self):
        """Clear history cache."""
        self._recent_topics.clear()


# Singleton
novelty_analyzer = NoveltyAnalyzer()
