"""Director free preview for digital-human briefs must stay on-subject and honest."""
from __future__ import annotations

import asyncio
from pathlib import Path

from PIL import Image


BRIEF = "一个竖屏数字人口播视频，自然口型同步，正面棚拍形象，讲解产品卖点"


def test_styles_prefer_portrait_for_talking_brief():
    from app.director import _styles_from_brief

    styles = _styles_from_brief(BRIEF)
    assert styles[0] == "portrait", styles


def test_demo_image_for_talking_is_portrait_stub_not_landscape():
    from app.adapters.demo_provider import render_demo_image, _local_media_path

    url = render_demo_image(
        BRIEF + "｜数字人半身像，正面视角，专业棚拍布光",
        "720x1280",
        "portrait",
        seed="79d97bd087fc",
    )
    path = _local_media_path(url)
    assert path and Path(path).is_file()
    im = Image.open(path).convert("RGB")
    # Portrait stub has a dark studio-ish center-top (backdrop) and skin-toned head region
    w, h = im.size
    cx, cy = w // 2, int(h * 0.38)
    head = im.getpixel((cx, cy))
    # Skin-ish (not Mediterranean terracotta roof red/orange dominant)
    assert head[0] > 120 and head[1] > 100, head
    # Top-left should be dark studio/banner — not bright coastal sky
    corner = im.getpixel((10, 10))
    assert sum(corner) < 120, corner
    # Center of former landscape seed would be colorful roofs; stub head is skin-tone block
    assert max(head) - min(head) < 90, head


def test_director_talking_preview_assets_honest():
    from app.director import DirectorPlanner, DirectorExecutor

    plan = DirectorPlanner().plan(BRIEF, duration=15)
    assert plan.intent == "talking"
    assert any(s.action == "lipsync" for s in plan.steps)
    assert any("数字人" in (s.title or "") for s in plan.steps)

    async def _run():
        ex = DirectorExecutor(dry_run=True)
        assets = []
        async for ev in ex.run_stream(plan):
            if ev.get("type") == "step_done" and ev.get("asset"):
                assets.append(ev["asset"])
        return assets

    assets = asyncio.run(_run())
    # Preview honesty applies to generated media steps — not finish packaging (compose).
    media = [
        a for a in assets
        if a.get("type") in ("image", "video", "audio")
        and not a.get("final")
        and a.get("model") != "FFmpeg Compose"
    ]
    assert media, assets
    for a in media:
        if a.get("type") == "audio" and a.get("mode") == "demo_tone":
            assert a.get("honesty") == "offline_preview_not_tts"
            continue
        assert a.get("honesty"), a
        label = a.get("model") or ""
        assert "本地预览" in label or "DEMO" in label.upper() or "占位" in label, label
        # Must not present planned provider names as the executed model
        assert not label.startswith("GPT"), label
        assert not label.startswith("Kling"), label
        assert a.get("mode") in (
            "portrait_stub", "ken_burns", "stock_or_gradient", "demo_tone", "demo_preview",
        )
    img = next(a for a in media if a.get("type") == "image")
    assert img.get("mode") == "portrait_stub"
    assert "占位" in (img.get("model") or "") or "预览" in (img.get("model") or "")
    # Packaging ladder must still produce a social-ready final in preview
    finals = [a for a in assets if a.get("final")]
    assert finals, assets
    assert finals[-1].get("export_preset") == "portrait_9_16"
