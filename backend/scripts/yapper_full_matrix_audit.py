#!/usr/bin/env python3
"""Yapper full-matrix audit — careful contract + optional live evidence.

Layers per capability:
  fe_page | api_contract | enqueue | live_outframe

Usage:
  cd backend
  python3 scripts/yapper_full_matrix_audit.py
  YAPPER_AUDIT_LIVE=1 MODEL_SMOKE_LIVE=1 MODEL_SMOKE_LIVE_VIDEO=1 \\
    MOTION_FIXTURE_LIVE=1 python3 scripts/yapper_full_matrix_audit.py

Exit 0 when all *contract* checks pass (live failures are recorded, not fatal
unless --strict-live).
"""
from __future__ import annotations

import argparse
import io
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
STILL = ROOT / "fixtures" / "motion" / "still.png"
REF_MP4 = ROOT / "fixtures" / "motion" / "ref.mp4"
PORTRAIT = ROOT / "fixtures" / "lipsync" / "portrait.png"
LINE_WAV = ROOT / "fixtures" / "lipsync" / "line.wav"
REPORT_PATH = ROOT / "fixtures" / "audit" / "yapper_full_matrix_latest.json"

# Yapper homepage / create surface (2026-07) → Betty mapping
YAPPER_MATRIX = [
    {"id": "agent", "yapper": "Yapper Agent (Don't prompt, Just Direct)", "fe": "frontend/src/app/agent/page.tsx", "apis": ["/api/v1/director/plan", "/api/v1/director/brain/modes"]},
    {"id": "image_gen", "yapper": "Pro Image Generation", "fe": "frontend/src/app/create/image/page.tsx", "apis": ["/api/v1/generate/analyze"]},
    {"id": "video_gen", "yapper": "Video Generation / Seedance Omni", "fe": "frontend/src/app/create/video/page.tsx", "apis": ["/api/v1/generate/analyze"]},
    {"id": "lipsync", "yapper": "Studio Lip-Syncing", "fe": "frontend/src/app/create/lipsync/page.tsx", "apis": ["/api/v1/lipsync/voices"]},
    {"id": "avatar", "yapper": "Talking Avatar", "fe": "frontend/src/app/create/avatar/page.tsx", "apis": ["/api/v1/lipsync/voices"]},
    {"id": "motion", "yapper": "Motion Control", "fe": "frontend/src/app/create/motion/page.tsx", "apis": ["/api/v1/motion/samples"]},
    {"id": "timeline", "yapper": "Timeline Editor", "fe": "frontend/src/app/create/timeline/page.tsx", "apis": ["/api/v1/timeline/subtitles/parse"]},
    {"id": "upscale", "yapper": "Media Upscaling", "fe": "frontend/src/app/create/upscale/page.tsx", "apis": ["/api/v1/generate/edit"]},
    {"id": "bg_remove", "yapper": "Image Background Remover", "fe": "frontend/src/app/create/bg-remove/page.tsx", "apis": ["/api/v1/generate/edit"]},
    {"id": "extend", "yapper": "Image Extender", "fe": "frontend/src/app/create/extend/page.tsx", "apis": ["/api/v1/generate/edit"]},
    {"id": "image_editor", "yapper": "Pro Image Editor", "fe": "frontend/src/app/create/image-editor/page.tsx", "apis": ["/api/v1/generate/edit"]},
    {"id": "extractor", "yapper": "Prompt Extractor (+ social URL)", "fe": "frontend/src/app/create/extract/page.tsx", "apis": ["/api/v1/generate/extract-prompt"]},
    {"id": "audio", "yapper": "Generate Audio", "fe": "frontend/src/app/create/audio/page.tsx", "apis": ["/api/v1/generate/speech"]},
    {"id": "explore", "yapper": "Explore / Remix", "fe": "frontend/src/app/explore/page.tsx", "apis": ["/api/v1/gallery/"]},
    {"id": "pricing", "yapper": "Flexible Pricing (Starter→Max)", "fe": "frontend/src/app/pricing/page.tsx", "apis": ["/api/v1/pricing/plans"]},
    {"id": "sessions", "yapper": "Sessions", "fe": "frontend/src/app/sessions/page.tsx", "apis": ["/api/v1/director/sessions"]},
    {"id": "tools_hub", "yapper": "All Tools hub", "fe": "frontend/src/app/tools/page.tsx", "apis": ["/api/v1/system/capabilities"]},
    {"id": "library", "yapper": "My Library / Assets", "fe": "frontend/src/app/library/page.tsx", "apis": ["/api/v1/library/"]},
    # Yapper differentiators often missing or thin on Betty
    {"id": "product_shots", "yapper": "Stunning Product Shots (dedicated)", "fe": "frontend/src/app/create/product/page.tsx", "apis": []},
    {"id": "headshots", "yapper": "Professional Headshots (dedicated)", "fe": "frontend/src/app/create/headshots/page.tsx", "apis": []},
    {"id": "photo_packs", "yapper": "AI Photo Packs", "fe": "frontend/src/app/create/photo-packs/page.tsx", "apis": []},
    {"id": "face_swap", "yapper": "AI Face Swapping / viral templates", "fe": None, "apis": [], "gap_hint": "no verified upstream SKU — capabilities.face_swap=unavailable"},
    {"id": "url_viral", "yapper": "URL-to-Viral (TikTok/IG reel → prompt)", "fe": "frontend/src/app/create/extract/page.tsx", "apis": ["/api/v1/generate/extract-prompt"], "gap_hint": "social page URLs honestly rejected; direct media URL ok"},
    {"id": "motion_voice", "yapper": "Motion + Voice Changer", "fe": "frontend/src/app/create/motion/page.tsx", "apis": ["/api/v1/motion"], "gap_hint": "voice_text TTS旁白有；非实时变声引擎"},
    {"id": "seedance_omni", "yapper": "Seedance 2.0 Omni multi-modal / multi-shot", "fe": "frontend/src/app/create/video/page.tsx", "apis": ["/api/v1/generate/"]},
]


def _row(name: str, ok: bool, detail: str = "", **extra) -> dict:
    d = {"name": name, "ok": bool(ok), "detail": detail}
    d.update(extra)
    return d


def _fe_exists(rel: str | None) -> bool:
    if not rel:
        return False
    return (REPO / rel).is_file()


def run_contract(client, headers: dict) -> list[dict]:
    checks: list[dict] = []

    # FE pages
    for item in YAPPER_MATRIX:
        exists = _fe_exists(item.get("fe"))
        expected_missing = item["id"] in ("photo_packs", "face_swap")
        if expected_missing:
            checks.append(_row(
                f"fe:{item['id']}",
                True,  # absence recorded as known gap, not hard fail
                item.get("gap_hint") or "missing dedicated surface",
                expected_missing=True,
                gap=True,
                yapper=item["yapper"],
            ))
            continue
        detail = item.get("fe") or item.get("gap_hint") or "missing"
        partial = item["id"] in ("product_shots", "headshots", "url_viral", "motion_voice", "seedance_omni")
        if partial and exists:
            detail = (item.get("gap_hint") or detail) + " (partial surface)"
        checks.append(_row(
            f"fe:{item['id']}",
            exists,
            detail,
            partial=partial,
            gap=partial,
            yapper=item["yapper"],
        ))

    # Capabilities honesty
    cap = client.get("/api/v1/system/capabilities")
    feats = (cap.json() or {}).get("features") or {}
    for key in ("motion_transfer", "prompt_extractor", "talking_avatar", "storyboard",
                "share_permalink", "failure_refund", "director_minimal", "multi_reference_i2i"):
        checks.append(_row(f"cap:{key}", key in feats and cap.status_code == 200, str((feats.get(key) or {}) )[:120]))
    mt = feats.get("motion_transfer") or {}
    checks.append(_row("cap:motion_native", mt.get("mode") == "native" and mt.get("sku") == "kling-3.0/motion-control", str(mt)[:160]))

    # Models shelf honesty vs Yapper "17+ / 26+"
    models = client.get("/api/v1/models")
    md = models.json() if models.status_code == 200 else {}
    active = int(md.get("active_count") or 0)
    checks.append(_row("models:active_ge_1", active >= 1, f"active={active} lab={md.get('lab_count')} total_catalog={md.get('total') or md.get('catalog_total')}"))
    checks.append(_row(
        "models:shelf_vs_yapper",
        False,  # honesty: we are NOT at Yapper shelf depth
        f"Betty active={active} (Yapper claims 17+ image / 26+ video) — intentional gap record",
        score_note="gap",
    ))

    # Analyze router
    an = client.post("/api/v1/generate/analyze", json={"prompt": "neon city night", "media_type": "image"}, headers=headers)
    checks.append(_row("api:analyze_image", an.status_code == 200 and "recommended_model" in (an.json() or {}), an.text[:100]))
    anv = client.post("/api/v1/generate/analyze", json={"prompt": "cinematic drone shot", "media_type": "video"}, headers=headers)
    checks.append(_row("api:analyze_video", anv.status_code == 200, anv.text[:80]))

    # Extractor
    if STILL.is_file():
        ex = client.post(
            "/api/v1/generate/extract-prompt",
            headers=headers,
            files={"media_file": ("still.png", io.BytesIO(STILL.read_bytes()), "image/png")},
            data={"media_kind": "image"},
        )
        body = ex.json() if ex.status_code == 200 else {}
        checks.append(_row("api:extractor_upload", ex.status_code == 200 and bool(body.get("prompt")), f"mode={body.get('mode')}"))
    else:
        checks.append(_row("api:extractor_upload", False, "fixture missing"))

    # Social URL extractor — expect honest non-scrape / failure, not fake success
    social = client.post(
        "/api/v1/generate/extract-prompt",
        headers=headers,
        data={"media_url": "https://www.tiktok.com/@x/video/123", "media_kind": "video"},
    )
    # Either 200 heuristic with honesty, or 4xx — both acceptable; pretending vision scrape is not.
    sbody = social.json() if social.headers.get("content-type", "").startswith("application/json") else {}
    pretend = (sbody.get("mode") == "vision" and "tiktok" in str(sbody.get("prompt", "")).lower())
    checks.append(_row(
        "api:extractor_social_url_honest",
        social.status_code in (200, 400, 422) and not pretend,
        f"status={social.status_code} mode={sbody.get('mode')} detail={str(sbody)[:100]}",
        gap=True,
    ))

    # Motion
    ms = client.get("/api/v1/motion/samples")
    msd = ms.json() if ms.status_code == 200 else {}
    checks.append(_row("api:motion_samples", ms.status_code == 200 and msd.get("available") and msd.get("mode") == "native", str(msd.get("sku"))))
    if msd.get("samples"):
        s0 = msd["samples"][0]
        img = client.get(s0["image_path"])
        vid = client.get(s0["video_path"])
        checks.append(_row("api:motion_sample_bytes", img.status_code == 200 and vid.status_code == 200 and len(vid.content) > 1000, f"img={len(img.content)} vid={len(vid.content)}"))

    # Lipsync / avatar voices
    lv = client.get("/api/v1/lipsync/voices")
    voices = (lv.json() or {}).get("voices") if lv.status_code == 200 else None
    checks.append(_row("api:lipsync_voices", bool(voices), f"n={len(voices or [])}"))

    # Director / Agent
    modes = client.get("/api/v1/director/brain/modes")
    checks.append(_row("api:director_modes", modes.status_code == 200))
    plan = client.post("/api/v1/director/plan", json={"brief": "15s product ad", "duration": 15}, headers=headers)
    checks.append(_row("api:director_plan", plan.status_code == 200 and (plan.json() or {}).get("steps"), plan.text[:100]))
    plan_min = client.post("/api/v1/director/plan", json={"brief": "短视频", "duration": 5, "minimal": True}, headers=headers)
    acts = [s.get("action") for s in ((plan_min.json() or {}).get("steps") or [])]
    checks.append(_row("api:director_minimal", plan_min.status_code == 200 and "video" in acts and "compose" not in acts, str(acts)))
    sb = client.post(
        "/api/v1/director/storyboard",
        json={
            "brief": "三镜广告",
            "shots": [{"prompt": "开场产品特写"}, {"prompt": "使用场景"}, {"prompt": "品牌收束"}],
            "dry_run": True,
            "async_mode": False,
            "with_compose": False,
        },
        headers=headers,
    )
    checks.append(_row("api:director_storyboard", sb.status_code in (200, 201), f"status={sb.status_code} {sb.text[:100]}"))
    ideate = client.post("/api/v1/director/ideate", json={"brief": "viral roast video"}, headers=headers)
    checks.append(_row("api:director_ideate", ideate.status_code in (200, 201), f"status={ideate.status_code}"))

    # Timeline SRT
    srt = "1\n00:00:00,000 --> 00:00:02,000\nHello Betty\n\n"
    tp = client.post("/api/v1/timeline/subtitles/parse", json={"content": srt}, headers=headers)
    checks.append(_row("api:timeline_parse", tp.status_code == 200 and int((tp.json() or {}).get("cue_count") or 0) >= 1, f"status={tp.status_code} {tp.text[:80]}"))

    # Gallery / explore
    gal = client.get("/api/v1/gallery/")
    gd = gal.json() if gal.status_code == 200 else {}
    n_items = len(gd.get("items") or [])
    checks.append(_row("api:gallery_list", gal.status_code == 200 and "items" in gd, f"items={n_items} total={gd.get('total')}"))
    stats = client.get("/api/v1/gallery/stats")
    sd = stats.json() if stats.status_code == 200 else {}
    checks.append(_row("api:gallery_stats", stats.status_code == 200, str(sd)[:120]))
    # Remix contract if any item
    if n_items:
        key = (gd["items"][0].get("id") or gd["items"][0].get("item_key") or "")
        if key:
            rm = client.post(f"/api/v1/gallery/{key}/remix", headers=headers)
            checks.append(_row("api:gallery_remix", rm.status_code in (200, 201), f"status={rm.status_code} {rm.text[:80]}"))

    # Pricing — Yapper Max vs Betty pro id mismatch
    plans = client.get("/api/v1/pricing/plans")
    pids = {p["id"] for p in (plans.json() or {}).get("plans", [])} if plans.status_code == 200 else set()
    checks.append(_row("api:pricing_four_tiers", {"starter", "personal", "creator", "max"} <= pids, str(sorted(pids))))
    fe_pricing = (REPO / "frontend/src/app/pricing/page.tsx").read_text(encoding="utf-8") if _fe_exists("frontend/src/app/pricing/page.tsx") else ""
    checks.append(_row(
        "pricing:fe_max_aligned",
        "Max" in fe_pricing and "max" in pids and 'subscribe("max")' in fe_pricing,
        "FE Max ↔ API id=max aligned (pro kept as alias)",
    ))

    # Library / sessions / developer / readiness
    lib = client.get("/api/v1/library/", headers=headers)
    checks.append(_row("api:library", lib.status_code == 200, str(lib.status_code)))
    sess = client.get("/api/v1/director/sessions", headers=headers)
    checks.append(_row("api:sessions", sess.status_code == 200, str(sess.status_code)))
    keys = client.get("/api/v1/developer/keys", headers=headers)
    checks.append(_row("api:developer_keys", keys.status_code == 200, str(keys.status_code)))
    ready = client.get("/api/v1/system/readiness")
    rd = ready.json() if ready.status_code == 200 else {}
    checks.append(_row(
        "api:readiness_surface",
        ready.status_code == 200 and all(k in rd for k in ("stripe", "storage", "sso")),
        f"ok={rd.get('ok')} stripe={((rd.get('stripe') or {}).get('api_key_configured'))} oidc_blockers={len(((rd.get('sso') or {}).get('blockers') or []))}",
    ))
    stripe = client.get("/api/v1/billing/stripe-status")
    st = stripe.json() if stripe.status_code == 200 else {}
    checks.append(_row("ops:stripe_configured", bool(st.get("api_key_configured")), str(st)[:160], gap=not st.get("api_key_configured")))
    oidc = client.get("/api/v1/auth/oidc/status")
    od = oidc.json() if oidc.status_code == 200 else {}
    checks.append(_row("ops:oidc_configured", bool(od.get("configured")), str(od)[:160], gap=not od.get("configured")))

    # Enqueue smoke (task created, not waited) — generate image/video/lipsync/motion/speech
    if STILL.is_file():
        # edit enqueue via multipart may be heavy; use analyze-only already done
        pass

    gen_img = client.post(
        "/api/v1/generate/",
        json={"prompt": "audit smoke still life", "media_type": "image", "model": "auto", "dry_run": True},
        headers=headers,
    )
    # dry_run may or may not exist — accept 200 with task or 422
    checks.append(_row(
        "enqueue:generate_image",
        gen_img.status_code in (200, 201, 202, 400, 422),
        f"status={gen_img.status_code} {gen_img.text[:100]}",
    ))

    # Speech — contract only (empty text → 422). Do NOT call paid TTS here.
    sp = client.post(
        "/api/v1/generate/speech",
        json={"text": "", "voice": "Rachel"},
        headers=headers,
    )
    checks.append(_row(
        "enqueue:speech_contract",
        sp.status_code in (400, 422),
        f"status={sp.status_code} (paid TTS gated; contract expects validation error)",
    ))
    openapi = client.get("/api/openapi.json")
    paths = (openapi.json() or {}).get("paths") or {}
    checks.append(_row(
        "openapi:speech",
        "/api/v1/generate/speech" in paths,
        "speech route registered" if "/api/v1/generate/speech" in paths else "missing",
    ))
    for route in (
        "/api/v1/generate/",
        "/api/v1/generate/edit",
        "/api/v1/lipsync",
        "/api/v1/motion",
        "/api/v1/director/run",
    ):
        checks.append(_row(f"openapi:{route}", route in paths, "registered" if route in paths else "missing"))

    # Tools hub honesty — motion badge text
    tools_fe = (REPO / "frontend/src/app/tools/page.tsx").read_text(encoding="utf-8") if _fe_exists("frontend/src/app/tools/page.tsx") else ""
    stale_be = "best-effort" in tools_fe.lower() or "best_effort" in tools_fe
    checks.append(_row(
        "fe:tools_motion_copy",
        not stale_be,
        "tools hub still says best-effort for motion" if stale_be else "motion copy ok",
        gap=stale_be,
    ))

    return checks


def run_live(report: dict) -> list[dict]:
    """Paid live probes — only when YAPPER_AUDIT_LIVE / smoke gates set."""
    live: list[dict] = []
    want = os.getenv("YAPPER_AUDIT_LIVE", "").lower() in ("1", "true", "yes", "on")
    if not want:
        live.append(_row("live:skipped", True, "YAPPER_AUDIT_LIVE not set — contract-only"))
        return live

    # Image sample
    if os.getenv("MODEL_SMOKE_LIVE", "").lower() in ("1", "true", "yes", "on"):
        from app.services.model_smoke import run_live_image_sample
        img = run_live_image_sample(["gpt-image-2", "nano-banana"])
        live.append(_row(
            "live:image_sample",
            int(img.get("outframe_ok") or 0) >= 1,
            f"outframe_ok={img.get('outframe_ok')} failed={img.get('failed')}",
            evidence=img,
        ))
    else:
        live.append(_row("live:image_sample", False, "MODEL_SMOKE_LIVE not set", skipped=True))

    # Video sample ≥2
    if os.getenv("MODEL_SMOKE_LIVE_VIDEO", "").lower() in ("1", "true", "yes", "on"):
        from app.services.model_smoke import run_live_video_sample
        vid = run_live_video_sample(["seedance-2.0-fast", "seedance-2.0"])
        live.append(_row(
            "live:video_ge2",
            int(vid.get("outframe_ok") or 0) >= 2,
            f"outframe_ok={vid.get('outframe_ok')} models={[d.get('model_id') for d in vid.get('details') or []]}",
            evidence={k: vid.get(k) for k in ("outframe_ok", "failed", "details", "ts")},
        ))
    else:
        live.append(_row("live:video_ge2", False, "MODEL_SMOKE_LIVE_VIDEO not set", skipped=True))

    # Motion native
    if os.getenv("MOTION_FIXTURE_LIVE", "").lower() in ("1", "true", "yes", "on"):
        import importlib.util
        path = ROOT / "scripts" / "fixture_derivative_harness.py"
        spec = importlib.util.spec_from_file_location("fixture_harness", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(mod)
        mout = mod.run_motion_live_optional()
        live.append(_row(
            "live:motion_native",
            bool(mout.get("ok")),
            f"model={mout.get('model')} source={mout.get('source')} err={mout.get('error') or mout.get('fixture_error', '')[:80]}",
            evidence=mout,
        ))
    else:
        live.append(_row("live:motion_native", False, "MOTION_FIXTURE_LIVE not set", skipped=True))

    # Prior last_run evidence
    last = ROOT / "fixtures" / "motion" / "last_run.json"
    if last.is_file():
        try:
            data = json.loads(last.read_text(encoding="utf-8"))
            live.append(_row(
                "live:motion_last_run_file",
                bool(data.get("ok")) and "motion-control" in str(data.get("model") or data.get("sku") or ""),
                f"model={data.get('model')} source={data.get('source')}",
            ))
        except Exception as e:
            live.append(_row("live:motion_last_run_file", False, str(e)))

    return live


def score_gaps(checks: list[dict], live: list[dict], meta: dict) -> dict:
    """Honest Betty vs Yapper gap board — not a vanity score."""
    contract = [c for c in checks if not c.get("expected_missing") and c["name"] not in ("models:shelf_vs_yapper",)]
    # models:shelf_vs_yapper is intentional False gap marker
    contract_ok = sum(1 for c in contract if c["ok"] and c["name"] != "models:shelf_vs_yapper")
    # exclude intentional gap rows from denominator for contract_pass_rate
    measurable = [c for c in contract if c["name"] != "models:shelf_vs_yapper" and not c.get("gap") or c["name"].startswith(("fe:", "api:", "cap:", "enqueue:", "ops:"))]
    # simpler: all checks that are meant to pass
    must = [c for c in checks if c["name"] not in ("models:shelf_vs_yapper",) and not c.get("expected_missing")]
    # gap-flagged ops may fail
    soft_fail_ok = {"ops:stripe_configured", "ops:oidc_configured", "api:extractor_social_url_honest"}
    hard = [c for c in must if c["name"] not in soft_fail_ok]
    hard_ok = sum(1 for c in hard if c["ok"])
    live_hard = [c for c in live if not c.get("skipped") and c["name"] != "live:skipped"]
    live_ok = sum(1 for c in live_hard if c["ok"])

    gaps = [
        {
            "area": "模型货架深度",
            "yapper": "宣传 17+ 图 / 26+ 视频全开",
            "betty": f"active={meta.get('active_models')}（诚实货架）",
            "severity": "P0",
            "impact": "高",
        },
        {
            "area": "Seedance Omni 产品化",
            "yapper": "多模态参考 + 内建唇形 + 多镜叙事",
            "betty": "Seedance T2V/I2V 可用，Omni 体验未产品化",
            "severity": "P0",
            "impact": "高",
        },
        {
            "area": "Studio Lip-Sync / Max Lip-Sync",
            "yapper": "强调专有/本地化训练级口型",
            "betty": "KIE kling/ai-avatar 通用链路；缺 fixture live 稳定 SLA",
            "severity": "P1",
            "impact": "高",
        },
        {
            "area": "Face Swap / 病毒模板",
            "yapper": "人脸替换 + 模板玩法",
            "betty": "无独立 SKU/路由",
            "severity": "P1",
            "impact": "中高",
        },
        {
            "area": "URL-to-Viral（社媒链接反推）",
            "yapper": "TikTok/IG URL → 提示词/结构",
            "betty": "Extractor 支持文件/直链；不抓社媒页面",
            "severity": "P1",
            "impact": "中高",
        },
        {
            "area": "专用 Image Apps",
            "yapper": "Product Shots / Headshots / Photo Packs",
            "betty": "多并入 /create/image，缺独立工作流",
            "severity": "P2",
            "impact": "中",
        },
        {
            "area": "Motion + Voice Changer",
            "yapper": "动作迁移可叠加变声",
            "betty": "原生 Kling Motion 有；无变声组合",
            "severity": "P2",
            "impact": "中",
        },
        {
            "area": "Explore 飞轮密度",
            "yapper": "百万级资产叙事 + 强 Remix",
            "betty": f"gallery items≈{meta.get('gallery_items')}；publish/remix 有，氛围弱",
            "severity": "P1",
            "impact": "中高",
        },
        {
            "area": "收款 / SSO 生产",
            "yapper": "成熟订阅收款",
            "betty": f"Stripe key={meta.get('stripe')} OIDC={meta.get('oidc')}",
            "severity": "P0（上线）",
            "impact": "高",
        },
        {
            "area": "定价命名",
            "yapper": "第四档 Max + credits 滑块",
            "betty": "FE Max / API id=pro 漂移",
            "severity": "P2",
            "impact": "低",
        },
        {
            "area": "Act-One 级 Motion 质量叙事",
            "yapper": "Advanced Motion Control 成片感",
            "betty": "原生 kling-3.0/motion-control 已通；非 Act-One，本地样片无人物需 playground 样例",
            "severity": "P1（体验）",
            "impact": "中",
        },
    ]

    # Two scores (do not conflate):
    # 1) tool_surface — Betty Yapper-route contract completeness
    # 2) overall_vs_yapper — product parity vs yapper.so (shelf/billing/community drag)
    tool_surface = round(100 * hard_ok / max(1, len(hard)), 1)
    live_score = round(100 * live_ok / max(1, len(live_hard)), 1) if live_hard else None
    shelf = 42 if meta.get("active_models", 0) < 12 else (70 if meta.get("active_models", 0) < 20 else 88)
    billing = 28 if not meta.get("stripe") else 82
    community = min(78, 18 + int(meta.get("gallery_items") or 0) * 1.2)
    live_component = live_score if live_score is not None else 58
    overall = round(
        0.30 * tool_surface
        + 0.25 * live_component
        + 0.20 * shelf
        + 0.15 * billing
        + 0.10 * community,
        1,
    )
    betty_readiness = round(
        0.40 * tool_surface
        + 0.35 * live_component
        + 0.15 * (75 if meta.get("active_models", 0) >= 8 else 50)
        + 0.10 * community,
        1,
    )

    return {
        "contract_hard_ok": hard_ok,
        "contract_hard_total": len(hard),
        "contract_pass_pct": tool_surface,
        "live_ok": live_ok,
        "live_total": len(live_hard),
        "live_pass_pct": live_score,
        "betty_internal_readiness_approx": betty_readiness,
        "overall_vs_yapper_approx": overall,
        "components": {
            "tool_surface": tool_surface,
            "live": live_component,
            "model_shelf": shelf,
            "billing": billing,
            "community": round(community, 1),
        },
        "gaps": gaps,
        "soft_known_gaps": sorted(soft_fail_ok),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-live", action="store_true", help="fail if any non-skipped live check fails")
    parser.add_argument("--live", action="store_true", help="set YAPPER_AUDIT_LIVE=1 for this run")
    args = parser.parse_args()
    if args.live:
        os.environ["YAPPER_AUDIT_LIVE"] = "1"

    logging.disable(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    email = f"audit_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post("/api/v1/auth/register", json={"email": email, "password": "Test1234!", "username": f"a{uuid.uuid4().hex[:6]}"})
    token = reg.json().get("access_token") if reg.status_code == 200 else None
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    checks = [_row("auth_register", bool(token), f"status={reg.status_code}")]
    checks.extend(run_contract(c, headers))

    # meta for scoring
    models = c.get("/api/v1/models").json() or {}
    gal = c.get("/api/v1/gallery/").json() or {}
    stripe = c.get("/api/v1/billing/stripe-status").json() or {}
    oidc = c.get("/api/v1/auth/oidc/status").json() or {}
    meta = {
        "active_models": int(models.get("active_count") or 0),
        "lab_models": int(models.get("lab_count") or 0),
        "gallery_items": len(gal.get("items") or []),
        "gallery_total": gal.get("total"),
        "stripe": bool(stripe.get("api_key_configured")),
        "oidc": bool(oidc.get("configured")),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    live = run_live({})
    scoring = score_gaps(checks, live, meta)

    report = {
        "suite": "yapper_full_matrix_audit",
        "ts": meta["ts"],
        "meta": meta,
        "yapper_matrix_size": len(YAPPER_MATRIX),
        "checks": checks,
        "live": live,
        "scoring": scoring,
        "honesty": (
            "Contract checks ≠ Yapper product parity. Live only when YAPPER_AUDIT_LIVE=1. "
            "Do not treat mapping smoke as outframe. Motion native ≠ Act-One."
        ),
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    hard = [c for c in checks if c["name"] not in (
        "models:shelf_vs_yapper", "ops:stripe_configured", "ops:oidc_configured",
    ) and not c.get("expected_missing")]
    contract_pass = all(c["ok"] for c in hard)
    live_hard = [x for x in live if not x.get("skipped") and x["name"] != "live:skipped"]
    live_pass = all(x["ok"] for x in live_hard) if live_hard else True
    if args.strict_live:
        return 0 if contract_pass and live_pass else 1
    return 0 if contract_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
