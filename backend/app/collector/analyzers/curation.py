"""
Video Curation Filter — Scores trending topics for short-form video production potential.

Not all trending topics make good videos. This filter evaluates:
  1. Visual potential (can this be shown visually?)
  2. Narrative arc (does it have a clear story?)
  3. Hook strength (how well can it grab attention?)
  4. Production feasibility (can we make this with AI tools?)
  5. Timeliness (is it still relevant?)
  6. Platform fit (which platforms suit this content?)

Output: VideoWorthinessScore 0-1 + recommended content type + production notes.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VideoCurationResult:
    video_worthiness: float        # 0-1, how suitable for short video
    content_type: str              # reaction | commentary | tutorial | news_break | entertainment | explainer | challenge
    visual_potential: float        # Can it be shown visually?
    narrative_score: float         # Does it have a clear story arc?
    production_feasibility: float  # Can AI tools produce this?
    timeliness_score: float        # Is it still fresh?
    suggested_duration: int        # Recommended seconds (15/30/60)
    target_platforms: list[str]    # tiktok | youtube_shorts | instagram_reels
    production_notes: str          # Brief production guidance


# ── Visual potential keyword signals ──
VISUAL_SIGNALS = {
    "strong": [
        r"\b(?:video|clip|footage|animation|demo|trailer|teaser)\b",
        r"\b(?:image|photo|picture|screenshot|visual|render)\b",
        r"\b(?:shows?|reveals?|displays?|demonstrates?|showcasing)\b",
        r"\b(?:watch|look at|check out|see)\b",
        r"\b(?:graph|chart|diagram|infographic|map|timeline)\b",
        r"\b(?:gameplay|reaction|unboxing|review|comparison)\b",
    ],
    "moderate": [
        r"\b(?:new|released?|launch|announced|unveiled|introduced?)\b",
        r"\b(?:update|upgrade|version|feature|change|improvement)\b",
        r"\b(?:vs\.?|versus|compared? to|better than|faster than)\b",
        r"\b(?:how to|tutorial|guide|walkthrough|explanation)\b",
    ],
    "weak": [
        r"\b(?:opinion|thoughts?|take|hot take|unpopular opinion)\b",
        r"\b(?:text|post|thread|comment|discussion|debate|argument)\b",
        r"\b(?:rant|complaint|ranting|complaining)\b",
    ],
}

# ── Narrative arc signals ──
NARRATIVE_SIGNALS = [
    # Story structure
    (r"\b(?:I|we) (?:tried|tested|built|made|created|discovered|found)\b", 0.85),
    (r"\b(?:before|after|then|finally|suddenly|unexpectedly)\b", 0.70),
    (r"\b(?:the result|what happened|you won't believe|plot twist)\b", 0.80),
    # Conflict/resolution
    (r"\b(?:problem|challenge|issue|bug|error|fail|fix|solved?|solution)\b", 0.65),
    # Comparison/contrast
    (r"\b(?:vs\.?|versus|compared|better|worse|faster|slower|cheaper)\b", 0.60),
    # Transformation
    (r"\b(?:changed|transformed|evolved|improved|upgraded|from.*to)\b", 0.75),
    # Discovery
    (r"\b(?:found|discovered|realized|learned|figured out|noticed)\b", 0.70),
]

# ── AI production feasibility by content type ──
PRODUCTION_FEASIBILITY = {
    "news_break": 0.85,     # AI voiceover + stock footage → easy
    "reaction": 0.95,       # Talking head with AI avatar → easy
    "commentary": 0.90,     # Voiceover + visuals → easy
    "tutorial": 0.75,       # Screen recording + AI voice → moderate
    "explainer": 0.80,      # Motion graphics + voice → moderate
    "entertainment": 0.70,  # Needs more creative input
    "challenge": 0.65,      # May need real footage
    "review": 0.85,         # Product shots + voice → moderate
    "comparison": 0.80,     # Side-by-side visuals → moderate
}

# ── Category to content type mapping ──
CATEGORY_CONTENT_MAP = {
    "tech": ["news_break", "tutorial", "explainer", "review"],
    "gaming": ["reaction", "entertainment", "tutorial"],
    "entertainment": ["reaction", "commentary", "entertainment"],
    "news": ["news_break", "commentary"],
    "science": ["explainer", "news_break"],
    "sports": ["reaction", "news_break", "commentary"],
    "creative": ["tutorial", "review", "entertainment"],
}

# ── Platform recommendations by duration ──
PLATFORM_RECS = {
    15: ["tiktok", "youtube_shorts", "instagram_reels"],
    30: ["tiktok", "youtube_shorts", "instagram_reels"],
    60: ["youtube_shorts", "instagram_reels", "tiktok"],
}


class VideoCurationFilter:
    """Evaluates trending topics for short-form video production potential."""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        import re
        I = re.IGNORECASE
        self._visual_strong = [re.compile(p, I) for p in VISUAL_SIGNALS["strong"]]
        self._visual_moderate = [re.compile(p, I) for p in VISUAL_SIGNALS["moderate"]]
        self._visual_weak = [re.compile(p, I) for p in VISUAL_SIGNALS["weak"]]
        self._narrative_rx = [(re.compile(p, I), w) for p, w in NARRATIVE_SIGNALS]

    def evaluate(self, topic: dict) -> VideoCurationResult:
        """Evaluate a topic for short video production potential.

        Args:
            topic: Dict with keys: title, description, source_platform, viral_score,
                   viral_tier, hooks, category, engagement, growth, sentiment
        """
        title = topic.get("title", "")
        desc = topic.get("description", "") or ""
        text = f"{title} {desc}"
        platform = topic.get("source_platform", "")
        hooks = topic.get("hooks", [])
        category = topic.get("category", "")
        tier = topic.get("viral_tier", "noise")

        # 1. Visual potential
        visual = self._score_visual(text)

        # 2. Narrative arc
        narrative = self._score_narrative(text)

        # 3. Hook strength (from existing analysis)
        hook_strength = self._score_hooks(hooks)

        # 4. Content type detection
        content_type = self._detect_content_type(text, category, platform)

        # 5. Production feasibility
        feasibility = PRODUCTION_FEASIBILITY.get(content_type, 0.70)

        # 6. Timeliness (recent = higher)
        timeliness = self._score_timeliness(tier, topic.get("growth", {}))

        # 7. Platform fit
        duration = self._recommend_duration(content_type, narrative, hook_strength)
        platforms = PLATFORM_RECS.get(duration, PLATFORM_RECS[30])

        # ── Composite score ──
        score = (
            visual * 0.30 +
            narrative * 0.25 +
            hook_strength * 0.20 +
            feasibility * 0.15 +
            timeliness * 0.10
        )
        score = round(min(score, 1.0), 4)

        # Production notes
        notes = self._generate_notes(content_type, visual, narrative, platform)

        return VideoCurationResult(
            video_worthiness=score,
            content_type=content_type,
            visual_potential=round(visual, 3),
            narrative_score=round(narrative, 3),
            production_feasibility=round(feasibility, 3),
            timeliness_score=round(timeliness, 3),
            suggested_duration=duration,
            target_platforms=platforms,
            production_notes=notes,
        )

    def evaluate_batch(self, topics: list[dict]) -> list[tuple[dict, VideoCurationResult]]:
        """Evaluate multiple topics, sorted by video worthiness."""
        results = [(t, self.evaluate(t)) for t in topics]
        results.sort(key=lambda x: x[1].video_worthiness, reverse=True)
        return results

    def _score_visual(self, text: str) -> float:
        """Score visual potential 0-1."""
        score = 0.0
        for rx in self._visual_strong:
            if rx.search(text):
                score += 0.25
        for rx in self._visual_moderate:
            if rx.search(text):
                score += 0.15
        for rx in self._visual_weak:
            if rx.search(text):
                score -= 0.10
        return max(0.1, min(1.0, score))

    def _score_narrative(self, text: str) -> float:
        """Score narrative structure 0-1."""
        score = 0.0
        for rx, weight in self._narrative_rx:
            if rx.search(text):
                score += weight * 0.3
        return max(0.1, min(1.0, score))

    def _score_hooks(self, hooks: list) -> float:
        """Derive hook strength from detected hooks."""
        if not hooks:
            return 0.2
        strengths = [h.get("strength", 0.5) for h in hooks]
        return sum(strengths) / len(strengths)

    def _detect_content_type(self, text: str, category: str, platform: str) -> str:
        """Detect the best content type for this topic."""
        import re

        text_lower = text.lower()

        # Strong signals
        if re.search(r"\b(?:review|unboxing|hands.?on|first look)\b", text_lower):
            return "review"
        if re.search(r"\b(?:how to|tutorial|guide|walkthrough|step.by.step|learn)\b", text_lower):
            return "tutorial"
        if re.search(r"\b(?:reaction|reacts? to|my reaction)\b", text_lower):
            return "reaction"
        if re.search(r"\b(?:explain|what is|why|how does|the science)\b", text_lower):
            return "explainer"
        if re.search(r"\b(?:challenge|try|can you|I bet)\b", text_lower):
            return "challenge"
        if re.search(r"\b(?:vs\.?|versus|compared?|better than)\b", text_lower):
            return "comparison"
        if re.search(r"\b(?:just (?:announced|released|dropped|launched)|breaking)\b", text_lower):
            return "news_break"
        if re.search(r"\b(?:opinion|thoughts?|take|hot take|unpopular)\b", text_lower):
            return "commentary"

        # Default by platform
        if platform == "youtube":
            return "review"
        if platform == "tiktok":
            return "entertainment"
        if platform == "reddit":
            return "commentary"

        return "news_break"

    def _score_timeliness(self, tier: str, growth: dict) -> float:
        """Score how timely/urgent this topic is."""
        if tier == "tier_1_breakout":
            return 0.95
        if tier == "tier_2_trending":
            return 0.80
        # Higher growth velocity = more timely
        vel = growth.get("velocity_1h", 0) or 0
        if vel > 1000:
            return 0.90
        if vel > 100:
            return 0.70
        return 0.50

    def _recommend_duration(self, content_type: str, narrative: float, hook_strength: float) -> int:
        """Recommend video duration in seconds."""
        if content_type in ("news_break", "reaction"):
            return 15 if hook_strength > 0.7 else 30
        if content_type in ("tutorial", "explainer"):
            return 60 if narrative > 0.6 else 30
        if content_type == "commentary":
            return 30
        if content_type == "challenge":
            return 15
        return 30

    def _generate_notes(self, content_type: str, visual: float, narrative: float, platform: str) -> str:
        """Generate production guidance notes."""
        notes = []

        if visual < 0.4:
            notes.append("⚠️ Low visual potential — add B-roll or motion graphics")
        if narrative < 0.3:
            notes.append("⚠️ Weak narrative — structure as problem→solution")

        if content_type == "news_break":
            notes.append("📰 Use AI voiceover + stock footage template")
        elif content_type == "reaction":
            notes.append("🎭 Use AI avatar talking-head template")
        elif content_type == "tutorial":
            notes.append("📖 Show step-by-step with screen capture + voice")
        elif content_type == "explainer":
            notes.append("🎬 Use motion graphics + narration template")
        elif content_type == "commentary":
            notes.append("💬 Split-screen: topic visuals + avatar commentary")
        elif content_type == "entertainment":
            notes.append("🎪 Fast cuts, trending audio, meme overlays")
        elif content_type == "challenge":
            notes.append("🏆 Show the challenge + result. Use text overlays.")

        return " | ".join(notes) if notes else "📹 Standard production template"


video_curator = VideoCurationFilter()
