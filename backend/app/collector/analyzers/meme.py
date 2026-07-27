"""
Meme Recognition Engine — Detects meme patterns in titles, descriptions, and text.

Covers 6 categories of text-detectable memes:
  1. Known meme formats (Drake, Distracted Boyfriend, etc.)
  2. Copypasta (Navy Seal, etc.)
  3. Viral caption structures (POV:, Nobody:, Me:)
  4. Reaction patterns (when you..., that feeling when...)
  5. Hashtag memes (#relatable, #fyp, etc.)
  6. TikTok/Reels audio-trend references

Output: 0.0 (no meme detected) to 1.0 (strong meme match).
Fed into viral_scorer as meme_match_strength (w=0.10).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MemeMatch:
    template: str
    category: str
    confidence: float
    matched_text: str


# ── Category 1: Known meme format names ──
MEME_FORMATS = {
    "distracted_boyfriend": {
        "name": "Distracted Boyfriend",
        "patterns": [r"\bdistracted boyfriend\b", r"guy looking back at.*girl"],
        "weight": 0.90,
        "category": "image_macro",
    },
    "drake_hotline": {
        "name": "Drake Hotline Bling",
        "patterns": [r"\bdrake\b.*\b(?:no|yes|like)\b", r"\bhotline bling\b"],
        "weight": 0.85,
        "category": "image_macro",
    },
    "change_my_mind": {
        "name": "Change My Mind",
        "patterns": [r"\bchange my mind\b", r"\bprove me wrong\b"],
        "weight": 0.80,
        "category": "image_macro",
    },
    "two_buttons": {
        "name": "Two Buttons",
        "patterns": [r"\b(?:sweating.*button|two buttons|difficult choice)\b"],
        "weight": 0.75,
        "category": "image_macro",
    },
    "galaxy_brain": {
        "name": "Galaxy Brain / Expanding Brain",
        "patterns": [r"\b(?:galaxy|expanding|big) brain\b", r"\bwrinkled brain\b"],
        "weight": 0.80,
        "category": "image_macro",
    },
    "this_is_fine": {
        "name": "This Is Fine",
        "patterns": [r"\bthis is fine\b.*\b(?:fire|burning|everything)\b"],
        "weight": 0.85,
        "category": "image_macro",
    },
    "surprised_pikachu": {
        "name": "Surprised Pikachu",
        "patterns": [r"\b(?:surprised )?pikachu\b", r"\*surprised pikachu\*"],
        "weight": 0.85,
        "category": "image_macro",
    },
    "one_does_not_simply": {
        "name": "One Does Not Simply",
        "patterns": [r"\bone does not simply\b"],
        "weight": 0.82,
        "category": "image_macro",
    },
    "roll_safe": {
        "name": "Roll Safe / Think About It",
        "patterns": [r"\b(?:roll safe|can't.*if you|cannot.*if you)\b.*\bthink\b"],
        "weight": 0.78,
        "category": "image_macro",
    },
    "doge": {
        "name": "Doge",
        "patterns": [r"\b(?:such|much|very|so)\b.*\b(?:wow|amaze|doge)\b"],
        "weight": 0.75,
        "category": "image_macro",
    },
    "woman_yelling_at_cat": {
        "name": "Woman Yelling at Cat",
        "patterns": [r"\b(?:woman yelling|cat at table|angry.*cat)\b"],
        "weight": 0.80,
        "category": "image_macro",
    },
    "spiderman_pointing": {
        "name": "Spiderman Pointing",
        "patterns": [r"\b(?:spider.?man pointing|pointing spiderman|they.*the same)\b"],
        "weight": 0.82,
        "category": "image_macro",
    },
    "stonks": {
        "name": "Stonks",
        "patterns": [r"\bstonks?\b", r"\bnot stonks?\b"],
        "weight": 0.78,
        "category": "image_macro",
    },
    "patrick_bateman": {
        "name": "Patrick Bateman / Sigma",
        "patterns": [r"\b(?:patrick bateman|sigma (?:male|grind|face)|literally me)\b"],
        "weight": 0.80,
        "category": "image_macro",
    },
    "gigachad": {
        "name": "Gigachad",
        "patterns": [r"\b(?:gigachad|chad\b(?!\s+[a-z])|average.*enjoyer)\b"],
        "weight": 0.82,
        "category": "image_macro",
    },
    "brain_meme": {
        "name": "Brain Comparison Meme",
        "patterns": [r"\b(?:normal brain|glowing brain|cosmic brain|small brain)\b"],
        "weight": 0.75,
        "category": "comparison",
    },
    "virgin_vs_chad": {
        "name": "Virgin vs Chad",
        "patterns": [r"\b(?:virgin\b.*\bchad|chad\b.*\bvirgin)\b"],
        "weight": 0.85,
        "category": "comparison",
    },
}

# ── Category 2: Copypasta signatures ──
COPYPASTA_PATTERNS = [
    # Navy Seal
    (r"\bwhat the (?:fuck|hell|heck) did you just (?:fucking )?say about me\b", "Navy Seal Copypasta", 0.92),
    (r"\bgraduated top of my class in the navy seals\b", "Navy Seal Copypasta", 0.95),
    (r"\bgorilla warfare\b.*\bentire (?:US )?armed forces\b", "Navy Seal Copypasta", 0.93),
    # Bee Movie
    (r"\baccording to all known laws of aviation\b", "Bee Movie Script", 0.95),
    (r"\bya like jazz\?\b", "Bee Movie", 0.85),
    # Shrek
    (r"\bsomebody once told me\b", "Shrek / All Star", 0.90),
    (r"\bget out of my swamp\b", "Shrek", 0.85),
    # Rick Roll
    (r"\bnever gonna (?:give you up|let you down)\b", "Rick Roll", 0.95),
    # V Sauce
    (r"\bhey,? vsauce,? michael here\b", "VSauce Intro", 0.90),
    # "They did surgery on a grape"
    (r"\bthey did surgery on a grape\b", "Surgery Grape", 0.82),
    # "I have approximate knowledge of many things"
    (r"\bapproximate knowledge of many things\b", "Adventure Time", 0.78),
]

# ── Category 3: Viral caption structures (TikTok/Reels) ──
CAPTION_PATTERNS = [
    (r"^POV:", "POV Format", 0.70, "tiktok_caption"),
    (r"^Nobody:\s*$", "Nobody: Format", 0.72, "tiktok_caption"),
    (r"^Me:", "Me: Format", 0.65, "tiktok_caption"),
    (r"^My honest reaction:", "Reaction Format", 0.68, "tiktok_caption"),
    (r"^When (?:you|she|he|they|I)\b", "When You... Format", 0.62, "tiktok_caption"),
    (r"\bthat feeling when\b", "TFW Format", 0.70, "reaction"),
    (r"\b(?:be like|be all)\b.*\b(?:when|after|before)\b", "Be Like Format", 0.65, "tiktok_caption"),
    (r"\btell me (?:you|your).*without (?:telling|saying)\b", "Tell Me Without...", 0.78, "tiktok_caption"),
    (r"^(?:day|week|month) \d+ of\b", "Day N of... Format", 0.68, "tiktok_caption"),
    (r"\bwait for it\b.*\b(?:end|finale|twist)\b", "Wait For It", 0.60, "anticipation"),
    (r"\b(?:only|just) \d+[%％]? (?:of people |people )?can\b", "Only X% Can", 0.65, "challenge"),
    (r"\bif you know[, ]? you know\b", "IYKYK", 0.75, "insider"),
    (r"\b(?:slay|no cap|fr fr|on god|bet\b|sheesh|bussin|understood the assignment)\b",
     "Gen Z Slang", 0.55, "slang"),
    (r"\b(?:literally me|me fr|it's me|I'm in this)\b", "Literally Me", 0.60, "relatable"),
]

# ── Category 4: Hashtag meme signals ──
HASHTAG_PATTERNS = [
    (r"#(?:meme|memes|dankmemes|memesdaily)", "Meme Hashtags", 0.55),
    (r"#(?:fyp|foryou|foryoupage|viral|trending)", "FYP/Trending Tags", 0.50),
    (r"#(?:relatable|mood|same|felt)", "Relatable Tags", 0.52),
    (r"#(?:copypasta|shitpost|shitposting)", "Shitpost Tags", 0.65),
]

# ── Category 5: Structural meme patterns ──
STRUCTURAL_PATTERNS = [
    # ALL CAPS TITLES (common in meme/shitpost subs)
    (r"^[A-Z\s.!?]{20,}$", "ALL CAPS", 0.40, "formatting"),
    # Excessive emoji
    (r"[\U0001F000-\U0001FFFF]{5,}", "Emoji Spam", 0.45, "formatting"),
    # "X be like" format
    (r"\b\w+ (?:be like|be all)\b", "Be Like Format", 0.55, "caption"),
    # Reaction image descriptions
    (r"\b(?:my face when|MFW|MRW|TFW)\b", "Reaction Image", 0.70, "reaction"),
    # Wojak / NPC references
    (r"\b(?:wojak|NPC|soyjak|doomer|bloomer|coomer)\b", "Wojak Universe", 0.75, "wojak"),
    # "Nobody absolutely nobody" meme
    (r"\b(?:nobody|no one)\b[\s\S]*?\babsolutely (?:nobody|no one)\b", "Nobody: Abs. Nobody:", 0.78, "format"),
]


class MemeRecognizer:
    """Detect meme patterns in text content. Multi-category, weighted confidence."""

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Precompile all regex patterns with IGNORECASE."""
        I = re.IGNORECASE
        self._format_patterns = [
            (re.compile(pat, I), name, w, cat)
            for name, cfg in MEME_FORMATS.items()
            for pat in cfg["patterns"]
            for w, cat in [(cfg["weight"], cfg["category"])]
        ]
        self._copypasta_patterns = [
            (re.compile(pat, I), name, w) for pat, name, w in COPYPASTA_PATTERNS
        ]
        self._caption_patterns = [
            (re.compile(pat, I), name, w, cat) for pat, name, w, cat in CAPTION_PATTERNS
        ]
        self._hashtag_patterns = [
            (re.compile(pat, I), name, w) for pat, name, w in HASHTAG_PATTERNS
        ]
        self._structural_patterns = [
            (re.compile(pat, I), name, w, cat) for pat, name, w, cat in STRUCTURAL_PATTERNS
        ]

    def recognize(self, title: str, description: Optional[str] = None) -> list[MemeMatch]:
        """Detect all meme patterns in content. Returns sorted by confidence."""
        text = title
        if description:
            text += " " + description[:500]
        text = text.strip()
        if not text:
            return []

        matches: list[MemeMatch] = []

        # Category 1: Known formats (highest weight)
        for rx, name, weight, category in self._format_patterns:
            m = rx.search(text)
            if m:
                matches.append(MemeMatch(
                    template=name, category=category,
                    confidence=weight,
                    matched_text=text[max(0, m.start()-30):m.end()+30],
                ))

        # Category 2: Copypasta
        for rx, name, weight in self._copypasta_patterns:
            m = rx.search(text)
            if m:
                matches.append(MemeMatch(
                    template=name, category="copypasta",
                    confidence=weight,
                    matched_text=text[max(0, m.start()-40):m.end()+40],
                ))

        # Category 3: Viral captions
        for rx, name, weight, category in self._caption_patterns:
            m = rx.search(text)
            if m:
                matches.append(MemeMatch(
                    template=name, category=category,
                    confidence=weight,
                    matched_text=m.group()[:60],
                ))

        # Category 4: Hashtags
        for rx, name, weight in self._hashtag_patterns:
            m = rx.search(text)
            if m:
                matches.append(MemeMatch(
                    template=name, category="hashtag",
                    confidence=weight,
                    matched_text=m.group(),
                ))

        # Category 5: Structural
        for rx, name, weight, category in self._structural_patterns:
            m = rx.search(text)
            if m:
                matches.append(MemeMatch(
                    template=name, category=category,
                    confidence=weight,
                    matched_text=m.group()[:60],
                ))

        # Deduplicate by template name (keep highest confidence)
        seen = {}
        for m in matches:
            if m.template not in seen or m.confidence > seen[m.template].confidence:
                seen[m.template] = m

        return sorted(seen.values(), key=lambda x: x.confidence, reverse=True)

    def get_overall_strength(self, matches: list[MemeMatch]) -> float:
        """Compute overall meme strength 0-1 from multiple matches.

        Formula: weighted average of top matches, capped at 1.0.
        Multiple weak matches accumulate less than one strong match.
        """
        if not matches:
            return 0.0

        # Take top 5 matches
        top = matches[:5]
        # Weighted by confidence, diminishing returns for each additional match
        strength = sum(m.confidence * (0.8 ** i) for i, m in enumerate(top))
        return round(min(strength, 1.0), 4)

    def analyze(self, title: str, description: Optional[str] = None) -> tuple[float, list[MemeMatch]]:
        """Full analysis: detect memes and compute overall strength."""
        matches = self.recognize(title, description)
        strength = self.get_overall_strength(matches)
        return strength, matches


meme_recognizer = MemeRecognizer()
