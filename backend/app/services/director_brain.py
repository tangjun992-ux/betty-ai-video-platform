"""
Director brain — LLM-backed ideate / refine with deterministic rule fallback.

When OPENAI_API_KEY or KIE_API_KEY is set, calls an OpenAI-compatible
chat/completions endpoint. On missing keys or LLM failure, falls back to
the local rule engine (ideate angles / refine_plan).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BRAIN_MODES: dict[str, dict[str, str | None]] = {
    "fast": {"label": "快速", "model": "gpt-4o-mini", "description": "低延迟创意发散"},
    "quality": {"label": "深度", "model": "gpt-4o", "description": "更高质量分镜与迭代"},
    "rules": {"label": "规则", "model": None, "description": "纯本地规则引擎（无 LLM）"},
}


def resolve_brain_model(brain: str | None) -> str | None:
    key = (brain or "fast").strip().lower()
    if key == "rules":
        return None
    spec = BRAIN_MODES.get(key) or BRAIN_MODES["fast"]
    return spec.get("model")


def _llm_credentials() -> Optional[tuple[str, str]]:
    """Return (api_key, base_url) when a chat provider is configured."""
    if getattr(settings, "OPENAI_API_KEY", None):
        base = (settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        return settings.OPENAI_API_KEY, base
    if getattr(settings, "KIE_API_KEY", None):
        # KIE exposes an OpenAI-compatible chat surface under /v1
        return settings.KIE_API_KEY, "https://api.kie.ai/v1"
    return None


async def _chat_json(system: str, user: str, model: str | None = None) -> Optional[Any]:
    creds = _llm_credentials()
    if not creds:
        return None
    api_key, base_url = creds
    llm_model = model or "gpt-4o-mini"
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": llm_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.8,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            return json.loads(content)
    except Exception as e:
        logger.warning("director_brain LLM call failed: %s", e)
        return None


def _expand_narration(brief: str, target: int) -> str:
    """Deterministically expand a short brief into a natural talking-avatar
    narration of roughly ``target`` Chinese chars (structured, on-topic)."""
    core = (brief or "").strip().rstrip("。！？!？")
    if not core:
        return core
    # Structured talking-avatar script: hook → core → craft/effect → scenario → social proof → CTA.
    parts = [
        f"大家好，今天想跟大家认真推荐一下。{core}。",
        "说实话，它的表现真的很让人惊喜，从品质到细节都做得很到位，用起来特别省心。",
        "不管你是第一次接触还是已经关注很久了，都能感受到它带来的实际效果。",
    ]
    if target > 150:
        parts += [
            "它在做工和选材上都很讲究，每一个环节都经过认真打磨，所以呈现出来的质感非常好。",
            "很多细节上的设计也很贴心，真正站在使用者的角度去考虑，体验感非常棒。",
        ]
    parts += [
        "身边很多朋友用过之后都给出了很高的评价，口碑一直都很不错。",
        "如果你也在找一款真正靠谱、值得入手的产品，那它一定不会让你失望。",
        "感兴趣的朋友千万不要错过，现在就去了解一下吧。",
    ]
    text = "".join(parts)
    if len(text) > target:
        text = text[:target].rstrip("，、；：") + "。"
    return text


async def fit_script_to_duration(script: str, duration: int, *, brain: str | None = None) -> str:
    """Size a narration script to roughly ``duration`` seconds of Chinese speech.

    Chinese neural TTS runs ~4.5 chars/sec, so a duration parameter should drive
    the narration length (and therefore the talking-avatar video length). Long
    scripts are trimmed at a sentence boundary; short scripts are expanded to
    reach the target (deterministic, on-topic — KIE chat is not guaranteed).
    """
    s = (script or "").strip()
    if not s:
        return s
    target = max(40, min(int((duration or 10) * 4.5), 320))
    if len(s) >= int(target * 1.05):
        # Trim at a sentence boundary near the target.
        cut = s[:target]
        for sep in "。！？；":
            idx = cut.rfind(sep)
            if idx >= int(target * 0.5):
                return cut[: idx + 1]
        return cut.rstrip("，、；：") + "。"
    if len(s) >= int(target * 0.7):
        return s
    return _expand_narration(s, target)


def _rule_ideate(brief: str) -> list[dict]:
    """Deterministic concept angles when no LLM is available."""
    b = (brief or "").strip()
    angles = [
        ("电影感大片", f"{b}，电影级运镜与调色，史诗氛围，宽银幕构图"),
        ("高能快剪", f"{b}，快节奏踩点剪辑，动感转场，强视觉冲击，竖屏"),
        ("情绪治愈", f"{b}，柔和自然光，舒缓节奏，温暖治愈氛围"),
        ("悬念钩子", f"{b}，强钩子开场加剧情反转，抓住前 3 秒注意力，竖屏"),
        ("高级质感", f"{b}，极简高级质感，精致布光，商业大片级细节"),
    ]
    return [{"title": t, "brief": br} for t, br in angles]


async def ideate(brief: str, *, brain: str | None = None) -> list[dict]:
    """Expand a rough idea into 5 distinct creative concepts `{title, brief}`."""
    b = (brief or "").strip()
    if not b:
        return _rule_ideate("")

    system = (
        "你是 Betty 平台的创意导演助手。根据用户一句话 brief，发散 5 个风格鲜明、"
        "可直接用于后续分镜规划的创意方向。只返回 JSON："
        '{"concepts":[{"title":"短标题","brief":"完整可执行的创作 brief"}, ...]}，'
        "恰好 5 条，title 简洁有辨识度，brief 保留原意图并强化风格差异。"
    )
    result = await _chat_json(system, f"Brief: {b}", model=resolve_brain_model(brain))
    if isinstance(result, dict):
        concepts = result.get("concepts") or []
        out: list[dict] = []
        for c in concepts:
            if isinstance(c, dict) and c.get("title") and c.get("brief"):
                out.append({"title": str(c["title"]).strip(), "brief": str(c["brief"]).strip()})
        if len(out) >= 3:
            while len(out) < 5:
                # Pad with rule angles if LLM returned fewer than 5
                for extra in _rule_ideate(b):
                    if len(out) >= 5:
                        break
                    if extra["title"] not in {x["title"] for x in out}:
                        out.append(extra)
            return out[:5]
    return _rule_ideate(b)


async def refine_with_llm(plan_dict: dict, directive: str, *, brain: str | None = None) -> tuple[dict, list[str]]:
    """Return (updated_plan_dict, changes). Falls back to refine_plan on failure."""
    from app.director import plan_from_dict, refine_plan

    d = (directive or "").strip()
    system = (
        "你是 Betty 导演助手。根据用户自然语言指令修改现有创作计划。"
        "只返回 JSON：{\"plan\": <完整更新后的计划对象>, \"changes\": [\"变更说明\", ...]}。"
        "plan 必须保留原结构字段 brief/intent/summary/total_credits/steps；"
        "steps 每项含 id/action/title/model_id/model_name/reason/prompt/"
        "depends_on/est_credits/status/result/params/skip。"
        "只改指令相关部分，不要无故删除步骤。"
    )
    user_payload = json.dumps({"plan": plan_dict, "directive": d}, ensure_ascii=False)
    result = await _chat_json(system, user_payload, model=resolve_brain_model(brain))
    if isinstance(result, dict):
        plan = result.get("plan")
        changes = result.get("changes") or []
        if isinstance(plan, dict) and isinstance(plan.get("steps"), list) and plan["steps"]:
            change_list = (
                [str(c) for c in changes] if isinstance(changes, list)
                else [str(changes)] if changes else ["已按导演指令更新计划"]
            )
            return plan, change_list

    # Rule-engine fallback
    updated, changes = refine_plan(plan_from_dict(plan_dict), d)
    return updated.to_dict(), changes


# ─── 分镜表生成（LLM 优先 + 内容差异化兜底） ─────────────────────────────

_BEAT_ROLES = [
    ("建立镜头", "wide establishing shot, slow push-in, environment and mood first"),
    ("主体特写", "intimate close-up of the main subject, fine details, shallow depth of field"),
    ("动态镜头", "medium tracking shot following the action, smooth controlled movement"),
    ("情绪高潮", "dramatic peak moment, strong emotional expression, high-tension lighting"),
    ("氛围镜头", "atmospheric insert shot, textured details that enrich the story"),
    ("收尾镜头", "pull-back closing shot, negative space, lingering aftertaste"),
]


def _core_subject(brief: str) -> str:
    """Extract a concise subject phrase (the narrative content, not format words),
    so every shot isn't the whole raw brief."""
    import re as _re
    s = (brief or "").strip()
    # Drop format / genre / duration / quality words.
    s = _re.sub(
        r"(竖屏|横屏|微短剧|短片|短视频|数字人|口播|视频|电影级|画质|一个|一段|一条|高清|4K|\d+\s*秒)",
        "",
        s,
    )
    clauses = [c.strip() for c in _re.split(r"[，。；;,.!?！？、]", s) if c.strip()]
    subj = "，".join(clauses[:2]).strip(" ，,。")
    return (subj or (brief or "").strip())[:48]


def _deterministic_shot_list(brief: str, n: int, styles: list[str]) -> list[dict]:
    """Content-aware fallback: camera/mood-dominant prompts so each shot's visual
    focus actually differs (not the same full brief + a beat label)."""
    subject = _core_subject(brief)
    from app.director import _style_phrase  # lazy to avoid circular import
    sp = _style_phrase(styles)
    shots: list[dict] = []
    for i in range(max(1, n)):
        title, cam = _BEAT_ROLES[i % len(_BEAT_ROLES)]
        # Beat/camera/mood is the dominant content; subject is lighter context.
        prompt = f"{cam}，{title}，{subject}，{sp}风格，电影级布光，高细节"
        shots.append({"title": title, "prompt": prompt, "camera": title})
    return shots


async def generate_shot_list(
    brief: str, n: int, scenario: str | None, styles: list[str], *, brain: str | None = None
) -> list[dict]:
    """Return a per-shot plan `[{title, prompt, camera}]` with differentiated content.

    Uses the director LLM when available (true dynamic storyboard, Yapper/dzine
    parity); otherwise a content-aware deterministic breakdown. Never returns the
    same full brief for every shot.
    """
    b = (brief or "").strip()
    n = max(1, int(n or 1))
    if not b:
        return _deterministic_shot_list(b, n, styles)

    if _llm_credentials():
        style_txt = "、".join(styles) if styles else "电影感"
        system = (
            "你是顶级短视频分镜导演。把用户的创意 brief 拆成连贯分镜脚本。"
            "每个分镜必须：围绕 brief 主题，但画面内容明显不同且有叙事递进"
            "（建立→特写/细节→动作/过程→情绪高潮→空镜点缀→收尾留白）。"
            "只返回 JSON：{\"shots\":[{\"title\":\"中文短标题\","
            "\"prompt\":\"英文生成提示词，具体到主体/动作/景别/运镜/光影/情绪\","
            "\"camera\":\"中文运镜与画面说明\"}]}，"
            f"恰好 {n} 条，不要重复同一画面。"
        )
        user = (
            f"Brief: {b}\n场景类型: {scenario or '通用'}\n风格: {style_txt}\n分镜数: {n}"
        )
        out = await _chat_json(system, user, model=resolve_brain_model(brain))
        if isinstance(out, dict):
            raw = out.get("shots") or []
            shots: list[dict] = []
            for s in raw:
                if isinstance(s, dict) and s.get("prompt"):
                    shots.append({
                        "title": str(s.get("title") or "").strip() or f"分镜 {len(shots)+1}",
                        "prompt": str(s["prompt"]).strip(),
                        "camera": str(s.get("camera") or s.get("title") or "").strip(),
                    })
            if len(shots) >= min(n, 2):
                return shots[:n]
    return _deterministic_shot_list(b, n, styles)
