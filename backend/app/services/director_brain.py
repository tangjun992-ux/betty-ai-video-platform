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
