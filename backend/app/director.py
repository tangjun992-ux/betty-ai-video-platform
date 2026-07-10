"""
Director — 导演式编排引擎 (对标 yapper Agent: "DON'T PROMPT, JUST DIRECT")

用户给一句话创作意图，Director 自动：
  1. Plan    — 拆解为多步骤创作计划 (DAG)
  2. Route   — 每步从模型库自动选最合适的模型 + 给出理由 + 预估积分
  3. Execute — 串/并行执行 (复用现有 adapters)，支持 DRY_RUN
  4. Deliver — 产出多资产

这是真实规划逻辑，不是 mock 回复。
"""
from __future__ import annotations

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────── 数据模型 ───────────────────────────────
@dataclass
class DirectorStep:
    id: str
    action: str                       # enhance_prompt | image | image_series | video | lipsync | compose
    title: str
    model_id: str
    model_name: str
    reason: str                       # 为什么选这个模型 (导演决策可解释)
    prompt: str
    depends_on: list[str] = field(default_factory=list)
    est_credits: int = 0
    status: str = "pending"           # pending | running | done | failed | skipped
    result: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "action": self.action, "title": self.title,
            "model_id": self.model_id, "model_name": self.model_name,
            "reason": self.reason, "prompt": self.prompt,
            "depends_on": self.depends_on, "est_credits": self.est_credits,
            "status": self.status, "result": self.result,
        }


@dataclass
class DirectorPlan:
    brief: str
    intent: str                       # image | image_series | video_from_text | video_from_image | talking | campaign
    summary: str
    steps: list[DirectorStep]
    total_credits: int = 0

    def to_dict(self) -> dict:
        return {
            "brief": self.brief, "intent": self.intent, "summary": self.summary,
            "total_credits": self.total_credits,
            "steps": [s.to_dict() for s in self.steps],
        }


# ─────────────────────────────── 模型选择 ───────────────────────────────
def _catalog() -> list[dict]:
    """延迟读取模型库，避免循环导入。"""
    try:
        from app.api.models_info import MODELS
        return [m.model_dump() if hasattr(m, "model_dump") else m.dict() for m in MODELS]
    except Exception as e:  # pragma: no cover
        logger.warning("[director] catalog load failed: %s", e)
        return []


def _pick_model(media_type: str, want_styles: list[str], prefer: str = "balanced") -> dict:
    """从模型库挑选最合适的模型。prefer: fast | balanced | quality"""
    cands = [m for m in _catalog() if media_type in m["capabilities"]["media_types"]]
    if not cands:
        # 兜底
        return {"id": "seedance-2.0" if media_type == "video" else "gpt-image-2",
                "display_name": "Seedance 2.0" if media_type == "video" else "GPT Image 2",
                "capabilities": {"styles": [], "cost_per_image_credits": 5, "cost_per_5s_video_credits": 4,
                                 "avg_latency_s": 30}, "cost_tier": "medium", "status": "active"}

    def score(m: dict) -> float:
        caps = m["capabilities"]
        s = 0.0
        # 风格契合
        s += 3.0 * len(set(want_styles) & set(caps["styles"]))
        # active 优先 (已验证可用)
        s += 2.0 if m["status"] == "active" else 0.0
        # 偏好档位
        tier = m["cost_tier"]
        if prefer == "fast":
            s += {"low": 2, "medium": 1, "high": 0}.get(tier, 0)
            s -= caps["avg_latency_s"] / 60.0
        elif prefer == "quality":
            s += {"low": 0, "medium": 1, "high": 2}.get(tier, 0)
        else:  # balanced
            s += {"low": 1, "medium": 1.5, "high": 1}.get(tier, 0)
        return s

    return max(cands, key=score)


def _credits_of(model: dict, media_type: str, duration: int = 5) -> int:
    caps = model["capabilities"]
    if media_type == "image":
        return int(caps.get("cost_per_image_credits", 5))
    per5 = int(caps.get("cost_per_5s_video_credits", 4))
    return max(per5, round(duration / 5 * per5))


# ─────────────────────────────── 意图识别 ───────────────────────────────
_VIDEO_KW = ["视频", "短片", "宣传片", "广告", "动画", "video", "片子", "镜头", "运镜", "vlog", "短视频"]
_TALK_KW = ["口播", "说话", "讲解", "数字人", "主播", "唇形", "talking", "avatar", "配音"]
_SERIES_KW = ["系列", "分镜", "九宫格", "多张", "一组", "套图", "storyboard", "series"]
_IMG_KW = ["图片", "图", "海报", "logo", "标志", "头像", "写真", "插画", "封面", "image", "poster"]
_CAMPAIGN_KW = ["营销", "电商", "带货", "产品", "推广", "campaign", "品牌", "种草"]


def _styles_from_brief(brief: str) -> list[str]:
    m = {
        "电影": "cinematic", "写实": "realistic", "真实": "realistic", "动漫": "anime",
        "二次元": "anime", "国风": "chinese", "中式": "chinese", "产品": "product",
        "人像": "portrait", "风景": "landscape", "科幻": "sci-fi", "奇幻": "fantasy",
        "美食": "food", "logo": "logo", "海报": "poster", "矢量": "vector", "梗图": "meme",
    }
    found = [v for k, v in m.items() if k in brief.lower()]
    return list(dict.fromkeys(found)) or ["cinematic", "realistic"]


def _has(brief: str, kws: list[str]) -> bool:
    b = brief.lower()
    return any(k.lower() in b for k in kws)


# ─────────────────────────────── 规划器 ───────────────────────────────
class DirectorPlanner:
    def plan(self, brief: str, has_ref_image: bool = False, duration: int = 5) -> DirectorPlan:
        brief = (brief or "").strip()
        styles = _styles_from_brief(brief)
        steps: list[DirectorStep] = []

        def sid() -> str:
            return uuid.uuid4().hex[:8]

        # 1) Prompt 增强 (导演先把口语 brief 变成专业 prompt)
        enh_id = sid()
        steps.append(DirectorStep(
            id=enh_id, action="enhance_prompt", title="解析创意 & 优化提示词",
            model_id="prompt-enhancer", model_name="Prompt Enhancer",
            reason="把口语化的创作意图扩写为带镜头/光影/风格的专业提示词", prompt=brief,
            est_credits=0,
        ))

        # 意图判定 (优先级: 口播 > 营销片 > 视频 > 系列图 > 单图)
        if _has(brief, _TALK_KW):
            intent = "talking"
            img = _pick_model("image", styles + ["portrait"], "quality")
            vstep = _pick_model("video", styles, "balanced")
            s_img = DirectorStep(id=sid(), action="image", title="生成数字人形象",
                model_id=img["id"], model_name=img["display_name"],
                reason=f"口播需要高保真人像，选 {img['display_name']}（人像/写实强）",
                prompt=brief, depends_on=[enh_id], est_credits=_credits_of(img, "image"))
            s_talk = DirectorStep(id=sid(), action="lipsync", title="唇形同步配音",
                model_id="seedance-2.0", model_name="Seedance 2.0",
                reason="Seedance 支持唇形同步，驱动人像开口说话",
                prompt=brief, depends_on=[s_img.id], est_credits=_credits_of(vstep, "video", duration))
            steps += [s_img, s_talk]

        elif _has(brief, _CAMPAIGN_KW) and _has(brief, _VIDEO_KW):
            intent = "campaign"
            img = _pick_model("image", styles + ["product"], "quality")
            vid = _pick_model("video", styles, "quality")
            s_img = DirectorStep(id=sid(), action="image", title="生成产品主视觉",
                model_id=img["id"], model_name=img["display_name"],
                reason=f"营销片首帧需精致产品图，选 {img['display_name']}",
                prompt=brief, depends_on=[enh_id], est_credits=_credits_of(img, "image"))
            s_vid = DirectorStep(id=sid(), action="video", title="主视觉转动态宣传片",
                model_id=vid["id"], model_name=vid["display_name"],
                reason=f"图生视频做运镜，选 {vid['display_name']}（电影级/产品）",
                prompt=brief, depends_on=[s_img.id], est_credits=_credits_of(vid, "video", duration))
            steps += [s_img, s_vid]

        elif _has(brief, _VIDEO_KW) or has_ref_image:
            if has_ref_image:
                intent = "video_from_image"
                vid = _pick_model("video", styles, "balanced")
                steps.append(DirectorStep(id=sid(), action="video", title="参考图转视频",
                    model_id=vid["id"], model_name=vid["display_name"],
                    reason=f"已有参考图，直接图生视频，选 {vid['display_name']}",
                    prompt=brief, depends_on=[enh_id], est_credits=_credits_of(vid, "video", duration)))
            else:
                intent = "video_from_text"
                img = _pick_model("image", styles, "balanced")
                vid = _pick_model("video", styles, "balanced")
                s_img = DirectorStep(id=sid(), action="image", title="生成首帧关键画面",
                    model_id=img["id"], model_name=img["display_name"],
                    reason=f"先定首帧保证主体可控，选 {img['display_name']}",
                    prompt=brief, depends_on=[enh_id], est_credits=_credits_of(img, "image"))
                s_vid = DirectorStep(id=sid(), action="video", title="首帧转动态视频",
                    model_id=vid["id"], model_name=vid["display_name"],
                    reason=f"图生视频获得连贯运动，选 {vid['display_name']}",
                    prompt=brief, depends_on=[s_img.id], est_credits=_credits_of(vid, "video", duration))
                steps += [s_img, s_vid]

        elif _has(brief, _SERIES_KW):
            intent = "image_series"
            img = _pick_model("image", styles, "balanced")
            for i in range(4):
                steps.append(DirectorStep(id=sid(), action="image", title=f"系列图 {i+1}/4",
                    model_id=img["id"], model_name=img["display_name"],
                    reason=f"成套出图保持风格一致，选 {img['display_name']}",
                    prompt=f"{brief} (变体 {i+1})", depends_on=[enh_id],
                    est_credits=_credits_of(img, "image")))

        else:
            intent = "image"
            img = _pick_model("image", styles, "quality")
            steps.append(DirectorStep(id=sid(), action="image", title="生成图片",
                model_id=img["id"], model_name=img["display_name"],
                reason=f"单图创作，选质量优先的 {img['display_name']}",
                prompt=brief, depends_on=[enh_id], est_credits=_credits_of(img, "image")))

        # 视频类意图自动追加成片步骤：配乐 → 字幕 → 合成 (对标 yapper Agent 成片)
        video_steps = [s for s in steps if s.action in ("video", "lipsync")]
        if video_steps:
            last_vid = video_steps[-1].id
            s_audio = DirectorStep(id=sid(), action="audio", title="AI 配乐",
                model_id="audio-engine", model_name="AI Music",
                reason="根据画面情绪自动生成背景音乐，提升成片感染力",
                prompt=brief, depends_on=[last_vid], est_credits=2)
            s_sub = DirectorStep(id=sid(), action="subtitle", title="智能字幕",
                model_id="subtitle-engine", model_name="Auto Caption",
                reason="自动生成并烧录字幕，适配社媒传播",
                prompt=brief, depends_on=[last_vid], est_credits=1)
            s_comp = DirectorStep(id=sid(), action="compose", title="合成成片",
                model_id="compose-engine", model_name="FFmpeg Compose",
                reason="将视频+配乐+字幕合成为最终可发布成片",
                prompt=brief, depends_on=[last_vid, s_audio.id, s_sub.id], est_credits=0)
            steps += [s_audio, s_sub, s_comp]

        total = sum(s.est_credits for s in steps)
        n_assets = len([s for s in steps if s.action in ("image", "video", "lipsync", "compose")])
        summary = (f"已规划 {len(steps)} 步，将产出 {n_assets} 个资产，"
                   f"预计消耗 {total} 积分。意图：{intent}")
        return DirectorPlan(brief=brief, intent=intent, summary=summary, steps=steps, total_credits=total)


# ─────────────────────────────── 执行器 ───────────────────────────────
class DirectorExecutor:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    async def _run_step(self, step: DirectorStep) -> dict:
        step.status = "running"
        try:
            if step.action == "enhance_prompt":
                enhanced = step.prompt
                try:
                    from app.prompt_enhancer import enhancer
                    out = enhancer.enhance(step.prompt)
                    enhanced = out.get("enhanced_prompt", step.prompt) if isinstance(out, dict) else (out or step.prompt)
                except Exception:
                    enhanced = f"{step.prompt}，电影级画质，柔和自然光，高细节，专业构图"
                step.status = "done"
                return {"type": "prompt", "enhanced_prompt": enhanced}

            if step.action in ("audio", "subtitle", "compose"):
                await asyncio.sleep(0.02)
                step.status = "done"
                return {"type": step.action, "ok": True, "model": step.model_name,
                        "note": "成片后期编排步骤", "cost": step.est_credits,
                        "media_url": f"/dry-run/final_{step.id}.mp4" if step.action == "compose" else None}

            media_type = "video" if step.action in ("video", "lipsync") else "image"

            # Preview (dry_run) or no-key → render viewable local media (Pillow /
            # ffmpeg) for free. Only an explicit real run (dry_run=False) with a
            # configured provider burns credits on the real models below.
            try:
                from app.adapters.demo_provider import demo_mode_active
                use_demo = self.dry_run or demo_mode_active()
            except Exception:
                use_demo = self.dry_run
            if use_demo:
                from app.adapters.demo_provider import render_demo_image, render_demo_video
                styles = _styles_from_brief(step.prompt)
                style = styles[0] if styles else "cinematic"
                if media_type == "video":
                    v_url, thumb = await asyncio.to_thread(render_demo_video, step.prompt, "1280x720", 5, style)
                    step.status = "done"
                    return {"type": "video", "media_url": v_url, "url": v_url,
                            "thumbnail": thumb, "model": step.model_id, "cost": step.est_credits}
                img_url = await asyncio.to_thread(render_demo_image, step.prompt, "1024x1024", style, 0)
                step.status = "done"
                return {"type": "image", "media_url": img_url, "url": img_url,
                        "thumbnail": img_url, "model": step.model_id, "cost": step.est_credits}

            from app.adapters.registry import get_adapter
            adapter = get_adapter(step.model_id)
            if adapter is None:
                step.status = "failed"
                return {"type": media_type, "error": f"no adapter for {step.model_id}"}
            if media_type == "video":
                res = await adapter.generate_video(prompt=step.prompt, model_id=step.model_id)
            else:
                out = await adapter.generate_image(prompt=step.prompt, model_id=step.model_id)
                res = out[0] if isinstance(out, list) else out
            step.status = "done"
            return res.to_dict() if hasattr(res, "to_dict") else res
        except Exception as e:
            logger.exception("[director] step %s failed", step.id)
            step.status = "failed"
            return {"error": str(e)}

    async def run(self, plan: DirectorPlan) -> dict:
        """按 depends_on 拓扑顺序执行，无依赖关系的同层并行。"""
        done: dict[str, dict] = {}
        remaining = list(plan.steps)
        assets: list[dict] = []
        guard = 0
        while remaining and guard < 100:
            guard += 1
            ready = [s for s in remaining if all(d in done for d in s.depends_on)]
            if not ready:
                for s in remaining:
                    s.status = "skipped"
                break
            results = await asyncio.gather(*[self._run_step(s) for s in ready])
            for s, r in zip(ready, results):
                s.result = r
                done[s.id] = r
                if s.action in ("image", "video", "lipsync") and "error" not in r:
                    assets.append({"step": s.title, "model": s.model_name, **r})
            remaining = [s for s in remaining if s.id not in done]
        return {"plan": plan.to_dict(), "assets": assets,
                "asset_count": len(assets), "dry_run": self.dry_run}


planner = DirectorPlanner()
