"""
Content moderation — shared prompt/asset safety checks used across generation
entry points (generate, director, image tools) and the public gallery.

This is a fast, deterministic keyword/regex policy engine (no external calls) that
returns a category + human-readable reason. It is the pre-generation gate; a
future async ML classifier can plug into `check_prompt` without changing callers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ModerationResult:
    allowed: bool
    category: Optional[str] = None   # sexual | minors | violence | hate | deepfake | illegal
    reason: Optional[str] = None


# Category → (patterns, user-facing reason). Word-boundary matched to reduce
# false positives (e.g. "class" won't trigger "ass").
_POLICY: list[tuple[str, str, list[str]]] = [
    ("minors", "内容不合规：涉及未成年人的不当内容被严格禁止。", [
        r"\bchild\b", r"\bchildren\b", r"\bminor\b", r"\bunderage\b", r"\bloli\b",
        r"\bshota\b", r"\bkid\b.*\b(nude|sexy|nsfw)\b", r"未成年", r"幼女", r"萝莉",
    ]),
    ("sexual", "内容不合规：提示词包含色情/露骨性内容，请修改后重试。", [
        r"\bnude\b", r"\bnaked\b", r"\bnsfw\b", r"\bporn\w*\b", r"\bxxx\b", r"\bsex\b",
        r"\berotic\b", r"\bexplicit\b", r"\bhentai\b", r"\bdoujin\b", r"\bcum\b",
        r"\bgenital\w*\b", r"\bcamel toe\b", r"色情", r"裸体", r"情色", r"性爱", r"淫",
    ]),
    ("deepfake", "内容不合规：禁止未经授权深度伪造真实人物（换脸/拟声）。", [
        r"deepfake", r"face[- ]?swap.*\b(celebrity|president|politician)\b",
        r"(elon musk|trump|biden|taylor swift).*\b(nude|nsfw|naked|kiss)\b",
        r"换脸", r"深度伪造",
    ]),
    ("violence", "内容不合规：提示词包含极端暴力/血腥或危险行为内容。", [
        r"\bgore\b", r"\bbeheading\b", r"\bdismember\w*\b", r"\btorture\b",
        r"\bmassacre\b", r"\bchild abuse\b", r"血腥", r"斩首", r"虐杀",
    ]),
    ("hate", "内容不合规：提示词包含仇恨/歧视性内容。", [
        r"\bnazi\b", r"\bkkk\b", r"\bgenocide\b", r"种族灭绝", r"纳粹",
    ]),
    ("illegal", "内容不合规：提示词涉及违法或危险物品（武器/毒品/爆炸物等）。", [
        r"\bhow to make a bomb\b", r"\bied\b", r"\bmeth recipe\b",
        r"制造炸弹", r"制毒",
    ]),
]

_COMPILED = [(cat, reason, [re.compile(p, re.IGNORECASE) for p in pats])
             for cat, reason, pats in _POLICY]


def check_prompt(text: str) -> ModerationResult:
    """Pre-generation gate. Returns allowed=False with a category+reason on hit."""
    if not text:
        return ModerationResult(allowed=True)
    for category, reason, patterns in _COMPILED:
        for pat in patterns:
            if pat.search(text):
                return ModerationResult(allowed=False, category=category, reason=reason)
    return ModerationResult(allowed=True)


def is_safe(text: str) -> bool:
    """Boolean convenience wrapper (e.g. for gallery display filtering)."""
    return check_prompt(text or "").allowed
