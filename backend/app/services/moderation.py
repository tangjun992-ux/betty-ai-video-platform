"""
Content moderation — shared prompt/asset safety checks used across generation
entry points (generate, director, image tools) and the public gallery.

This is a fast, deterministic keyword/regex policy engine (no external calls) that
returns a category + human-readable reason + risk_score. It is the pre-generation
gate; a future async ML classifier can plug into `check_prompt` without changing callers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# Category severity weights for risk_score aggregation (0–1).
_CATEGORY_WEIGHT: dict[str, float] = {
    "minors": 1.0,
    "sexual": 0.85,
    "deepfake": 0.8,
    "violence": 0.75,
    "hate": 0.7,
    "illegal": 0.9,
}


@dataclass
class ModerationResult:
    allowed: bool
    category: Optional[str] = None   # sexual | minors | violence | hate | deepfake | illegal
    reason: Optional[str] = None
    risk_score: float = 0.0          # 0 (safe) → 1 (blocked / high risk)
    categories: list[str] = field(default_factory=list)

    def public_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "category": self.category,
            "categories": self.categories,
            "reason": self.reason,
            "risk_score": round(self.risk_score, 3),
        }


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
    """Pre-generation gate. Returns allowed=False with category/reason/risk on hit."""
    if not text:
        return ModerationResult(allowed=True, risk_score=0.0, categories=[])

    # Layer 1: fast keyword policy
    keyword = _check_keywords(text)
    if not keyword.allowed:
        return keyword

    # Layer 2: OpenAI Moderation API when configured (classification model)
    ml = _check_openai_moderation(text)
    if ml and not ml.allowed:
        return ml

    return ModerationResult(allowed=True, risk_score=0.0, categories=[])


def _check_keywords(text: str) -> ModerationResult:
    if not text:
        return ModerationResult(allowed=True, risk_score=0.0, categories=[])
    hits: list[tuple[str, str]] = []
    for category, reason, patterns in _COMPILED:
        for pat in patterns:
            if pat.search(text):
                hits.append((category, reason))
                break

    if not hits:
        return ModerationResult(allowed=True, risk_score=0.0, categories=[])

    categories = list(dict.fromkeys(c for c, _ in hits))
    primary_cat, primary_reason = hits[0]
    risk = min(1.0, max(_CATEGORY_WEIGHT.get(c, 0.6) for c in categories))
    # Slight bump when multiple categories fire.
    if len(categories) > 1:
        risk = min(1.0, risk + 0.05 * (len(categories) - 1))

    return ModerationResult(
        allowed=False,
        category=primary_cat,
        reason=primary_reason,
        risk_score=risk,
        categories=categories,
    )


def _check_openai_moderation(text: str) -> ModerationResult | None:
    """Optional ML classifier via OpenAI Moderation API."""
    try:
        from app.config import settings
        key = getattr(settings, "OPENAI_API_KEY", None)
        if not key:
            return None
        import httpx
        base = (getattr(settings, "OPENAI_BASE_URL", None) or "https://api.openai.com/v1").rstrip("/")
        resp = httpx.post(
            f"{base}/moderations",
            headers={"Authorization": f"Bearer {key}"},
            json={"input": text},
            timeout=8.0,
        )
        resp.raise_for_status()
        data = resp.json()
        result = (data.get("results") or [{}])[0]
        if result.get("flagged"):
            cats = [k for k, v in (result.get("categories") or {}).items() if v]
            score = float((result.get("category_scores") or {}).get(cats[0], 0.85) if cats else 0.85)
            return ModerationResult(
                allowed=False,
                category=cats[0] if cats else "policy",
                reason="内容不合规：AI 安全模型检测到潜在违规内容，请修改后重试。",
                risk_score=min(1.0, score),
                categories=cats,
            )
    except Exception:
        return None
    return None


def is_safe(text: str) -> bool:
    """Boolean convenience wrapper (e.g. for gallery display filtering)."""
    return check_prompt(text or "").allowed


def score_prompt(text: str) -> dict:
    """Public scoring helper for admin / tooling."""
    return check_prompt(text or "").public_dict()
