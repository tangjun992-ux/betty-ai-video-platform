"""
Hook Analyzer — Detects viral hook patterns in content titles/descriptions.

13 hook categories with regex + structural detection.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from app.collector.schemas import HookPattern, HookAnalysisResult

logger = logging.getLogger(__name__)

# ── Hook Pattern Definitions ──
HOOK_PATTERNS = {
    "curiosity_gap": {
        "name": "Curiosity Gap",
        "regex": [
            r"(?i)\byou won[‘']t believe\b",
            r"(?i)\bwhat happens next\b",
            r"(?i)\bwait (?:for|until) (?:the|you see)\b",
            r"(?i)\bthis is (?:why|how|what)\b",
            r"(?i)\bthe (?:secret|truth|reason) (?:behind|why|about)\b",
            r"(?i)\bno one (?:is talking|told you|expected)\b",
            r"(?i)\bwatch (?:until|till) the end\b",
            r"(?i)\byou need to see this\b",
        ],
        "weight": 0.85,
    },
    "controversy": {
        "name": "Controversy",
        "regex": [
            r"(?i)\bcontroversial\b",
            r"(?i)\bhot take\b",
            r"(?i)\bunpopular opinion\b",
            r"(?i)\b(?:I|we) (?:need to|have to|must) talk about\b",
            r"(?i)\bcan we talk about\b",
            r"(?i)\bthis is (?:wrong|a problem|out of control)\b",
            r"(?i)\bstop (?:doing|saying|normalizing)\b",
        ],
        "weight": 0.80,
    },
    "pattern_interrupt": {
        "name": "Pattern Interrupt",
        "regex": [
            r"(?i)\b(?:stop|wait|hold up|hold on)\b.*[!?]",
            r"(?i)\bplot twist\b",
            r"(?i)\bunexpected\b",
            r"(?i)\byou thought.*but\b",
            r"(?i)\bI can[‘']t believe\b",
        ],
        "weight": 0.75,
    },
    "social_proof": {
        "name": "Social Proof",
        "regex": [
            r"(?i)\b\d+[.,]?\d*[kKmM]?\s*(?:people|views|followers|subscribers)\b",
            r"(?i)\beveryone (?:is|has|knows)\b",
            r"(?i)\bthe internet (?:is|can[‘']t|freaking)\b",
            r"(?i)\bgoing viral\b",
            r"(?i)\bbreaking the internet\b",
        ],
        "weight": 0.70,
    },
    "scarcity_urgency": {
        "name": "Scarcity / Urgency",
        "regex": [
            r"(?i)\b(?:only|just) \d+ (?:hours?|days?|minutes?) (?:left|remaining|to go)\b",
            r"(?i)\blimited (?:time|offer|edition)\b",
            r"(?i)\bdon[‘']t (?:miss|wait|forget)\b",
            r"(?i)\bact (?:now|fast|quickly)\b",
            r"(?i)\bending soon\b",
            r"(?i)\blast chance\b",
        ],
        "weight": 0.65,
    },
    "story_hook": {
        "name": "Story Hook",
        "regex": [
            r"(?i)\b(?:last|this|one) (?:week|month|year|day|time)\b",
            r"(?i)\bI (?:tried|tested|discovered|found|learned|realized)\b",
            r"(?i)\bhow I (?:built|made|created|achieved|got)\b",
            r"(?i)\bhere[‘']s what (?:happened|I learned|I did)\b",
            r"(?i)\bmy (?:experience|journey|story) with\b",
        ],
        "weight": 0.75,
    },
    "question_hook": {
        "name": "Question Hook",
        "regex": [
            r"^[^.!?]*\?$",  # Ends with question mark
            r"(?i)\b(?:have you ever|did you know|what if|why do|how would)\b",
            r"(?i)\bcan you\??\b",
            r"(?i)\b(?:is this|are we|do you|should we)\b.*\?",
        ],
        "weight": 0.60,
    },
    "statistic_hook": {
        "name": "Statistic Hook",
        "regex": [
            r"(?i)\b\d{1,3}[%％]\b",
            r"(?i)\b\d+ out of \d+\b",
            r"(?i)\bstud(?:y|ies) (?:show|found|reveal)\b",
            r"(?i)\baccording to (?:research|data|statistics|scientists)\b",
            r"(?i)\b(?:over|more than|less than|nearly|almost) \d+[%％]?\b",
        ],
        "weight": 0.70,
    },
    "before_after": {
        "name": "Before / After",
        "regex": [
            r"(?i)\b(?:before|after)\b.*\b(?:before|after)\b",
            r"(?i)\btransformation\b",
            r"(?i)\bglow[- ]up\b",
            r"(?i)\b(?:from|vs\.?|versus)\b.*\b(?:from|vs\.?|versus|to)\b",
            r"(?i)\blevel \d+ (?:to|vs)\b",
        ],
        "weight": 0.75,
    },
    "challenge": {
        "name": "Challenge",
        "regex": [
            r"(?i)\bchallenge\b",
            r"(?i)\bcan you\b",
            r"(?i)\btry (?:this|not to|to)\b",
            r"(?i)\bguess\b",
            r"(?i)\bI bet you\b",
            r"(?i)\bonly \d+[%％]? (?:of people )?can\b",
        ],
        "weight": 0.65,
    },
    "listicle": {
        "name": "Listicle",
        "regex": [
            r"(?i)^\d+\s+(?:things?|ways?|reasons?|tips?|tricks?|facts?|ideas?)\b",
            r"(?i)\b(?:top|best) \d+\b",
            r"(?i)\b\d+ (?:things?|ways?|reasons?|signs?)\b",
        ],
        "weight": 0.55,
    },
    "relatability": {
        "name": "Relatability",
        "regex": [
            r"(?i)\b(?:me|us|everyone|anyone else)\b.*\b(?:when|every time|on a)\b",
            r"(?i)\b(?:I[‘']m|we[‘']re) (?:just|literally|actually|honestly)\b",
            r"(?i)\b(?:be me|POV|it[‘']s giving)\b",
            r"(?i)\bthat feeling when\b",
            r"(?i)\b(?:my|the) (?:face|reaction) when\b",
        ],
        "weight": 0.60,
    },
    "authority": {
        "name": "Authority",
        "regex": [
            r"(?i)\b(?:doctor|professor|scientist|expert|CEO|founder)\b",
            r"(?i)\bI[‘']ve (?:been|spent|studied|worked) \d+ (?:years?|decades?)\b",
            r"(?i)\baccording to (?:Harvard|MIT|NASA|WHO|the UN)\b",
            r"(?i)\bbacked by (?:science|research|data|experts)\b",
        ],
        "weight": 0.60,
    },
}


class HookAnalyzer:
    """Detect viral hook patterns in content."""

    def __init__(self):
        self._compiled = {
            key: [(re.compile(rx, re.IGNORECASE), rx)
                  for rx in pat["regex"]]
            for key, pat in HOOK_PATTERNS.items()
        }

    def analyze(self, title: str, description: Optional[str] = None) -> HookAnalysisResult:
        """Analyze hooks in content title and description."""
        text = title
        if description:
            text += " " + description
        text = text.strip()

        if not text:
            return HookAnalysisResult()

        detected: list[HookPattern] = []

        for hook_key, patterns in self._compiled.items():
            best_strength = 0.0
            matched = ""
            for compiled_rx, raw_rx in patterns:
                m = compiled_rx.search(text)
                if m:
                    strength = self._calc_strength(hook_key, m.group())
                    if strength > best_strength:
                        best_strength = strength
                        matched = text[max(0, m.start()-20):m.end()+20]

            if best_strength > 0:
                detected.append(HookPattern(
                    category=hook_key,
                    pattern=HOOK_PATTERNS[hook_key]["name"],
                    strength=round(best_strength, 3),
                    matched_text=matched,
                ))

        # Sort by strength
        detected.sort(key=lambda h: h.strength, reverse=True)

        # Hook density: hooks per 100 chars
        density = len(detected) / max(len(text) / 100, 1)

        return HookAnalysisResult(
            hooks=detected,
            primary_hook=detected[0] if detected else None,
            hook_density=round(min(density, 1.0), 3),
        )

    def analyze_batch(self, items: list[tuple[str, Optional[str]]]) -> list[HookAnalysisResult]:
        """Analyze multiple items at once."""
        return [self.analyze(title, desc) for title, desc in items]

    def _calc_strength(self, hook_key: str, matched_text: str) -> float:
        """Calculate hook strength based on base weight + match quality."""
        base = HOOK_PATTERNS[hook_key]["weight"]

        # Boost for title-position matches (beginning of content)
        # Since we don't have positional info here, use match length as proxy
        length_boost = min(len(matched_text) / 50, 0.1)

        return min(base + length_boost, 1.0)

    def get_best_hooks_for_prompt(self, hooks: list[HookPattern], limit: int = 3) -> list[dict]:
        """Extract hooks suitable for prompt generation."""
        return [
            {
                "category": h.category,
                "pattern": h.pattern,
                "text": h.matched_text,
                "strength": h.strength,
            }
            for h in sorted(hooks, key=lambda x: x.strength, reverse=True)[:limit]
        ]


# Singleton
hook_analyzer = HookAnalyzer()
