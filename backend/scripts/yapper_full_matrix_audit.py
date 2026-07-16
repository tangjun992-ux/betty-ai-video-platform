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
    {"id": "product_shots", "yapper": "Stunning Product Shots (dedicated)", "fe": "frontend/src/app/create/product/page.tsx", "apis": [], "gap_hint": "dedicated entry exists; thin prompt-pack redirect to image"},
    {"id": "headshots", "yapper": "Professional Headshots (dedicated)", "fe": "frontend/src/app/create/headshots/page.tsx", "apis": [], "gap_hint": "dedicated entry exists; thin prompt-pack redirect to image"},
    {"id": "photo_packs", "yapper": "AI Photo Packs", "fe": "frontend/src/app/create/photo-packs/page.tsx", "apis": [], "gap_hint": "hub page exists; not a batch SKU pipeline"},
    {"id": "face_swap", "yapper": "AI Face Swapping / viral templates", "fe": "frontend/src/app/create/face-swap/page.tsx", "apis": ["/api/v1/face-swap"], "gap_hint": "i2i_edit live (nano-banana-edit); not InsightFace; viral template library thin"},
    {"id": "url_viral", "yapper": "URL-to-Viral (TikTok/IG reel → prompt)", "fe": "frontend/src/app/create/extract/page.tsx", "apis": ["/api/v1/generate/extract-prompt"], "gap_hint": "YouTube cover resolve ok; TikTok/IG best-effort; not full reel→structure"},
    {"id": "motion_voice", "yapper": "Motion + Voice Changer", "fe": "frontend/src/app/create/motion/page.tsx", "apis": ["/api/v1/motion"], "gap_hint": "voice_text TTS旁白 + Performance Drive；非实时变声引擎"},
    {"id": "performance_drive", "yapper": "Advanced Motion / performance-like drive", "fe": "frontend/src/app/create/performance/page.tsx", "apis": ["/api/v1/performance"], "gap_hint": "Motion+optional Lipsync；≠ Runway Act-One"},
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
        detail = item.get("fe") or item.get("gap_hint") or "missing"
        # Surfaces that exist but are thinner than Yapper product depth
        partial = item["id"] in (
            "product_shots", "headshots", "photo_packs", "url_viral",
            "motion_voice", "seedance_omni", "face_swap", "performance_drive",
        )
        if partial and exists:
            detail = (item.get("gap_hint") or detail) + " (partial vs Yapper depth)"
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
    for key in (
        "motion_transfer", "prompt_extractor", "talking_avatar", "storyboard",
        "share_permalink", "failure_refund", "director_minimal", "multi_reference_i2i",
        "face_swap", "performance_drive", "seedance_omni",
    ):
        checks.append(_row(f"cap:{key}", key in feats and cap.status_code == 200, str((feats.get(key) or {}) )[:120]))
    mt = feats.get("motion_transfer") or {}
    checks.append(_row("cap:motion_native", mt.get("mode") == "native" and mt.get("sku") == "kling-3.0/motion-control", str(mt)[:160]))
    fs = feats.get("face_swap") or {}
    checks.append(_row("cap:face_swap_i2i", fs.get("mode") == "i2i_edit" and "nano-banana" in str(fs.get("sku") or ""), str(fs)[:160]))
    pd = feats.get("performance_drive") or {}
    checks.append(_row("cap:performance_drive", pd.get("mode") == "motion_plus_optional_lipsync", str(pd)[:160]))
    pe_social = (feats.get("prompt_extractor") or {}).get("social_page_urls") or {}
    checks.append(_row("cap:social_youtube", pe_social.get("youtube") is True, str(pe_social)[:120]))

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

    # Social URL extractor — TikTok best-effort honesty; YouTube must resolve cover
    social = client.post(
        "/api/v1/generate/extract-prompt",
        headers=headers,
        data={"media_url": "https://www.tiktok.com/@x/video/123", "media_kind": "video"},
    )
    sbody = social.json() if social.headers.get("content-type", "").startswith("application/json") else {}
    pretend = (sbody.get("mode") == "vision" and "tiktok" in str(sbody.get("prompt", "")).lower())
    checks.append(_row(
        "api:extractor_tiktok_honest",
        social.status_code in (200, 400, 422) and not pretend,
        f"status={social.status_code} mode={sbody.get('mode')} detail={str(sbody)[:100]}",
        gap=True,
    ))
    yt = client.post(
        "/api/v1/generate/extract-prompt",
        headers=headers,
        data={"media_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "media_kind": "auto"},
    )
    ytd = yt.json() if yt.status_code == 200 else {}
    checks.append(_row(
        "api:extractor_youtube_resolve",
        yt.status_code == 200 and (ytd.get("social") or {}).get("platform") == "youtube" and bool(ytd.get("prompt")),
        f"status={yt.status_code} source={(ytd.get('social') or {}).get('source')}",
    ))

    # Face swap + performance OpenAPI / enqueue contract
    oa = client.get("/api/openapi.json")
    paths = (oa.json() or {}).get("paths") or {}
    checks.append(_row("openapi:face_swap", "/api/v1/face-swap" in paths, "ok" if "/api/v1/face-swap" in paths else "missing"))
    checks.append(_row("openapi:performance", "/api/v1/performance" in paths, "ok" if "/api/v1/performance" in paths else "missing"))

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


def _evidence_file(rel: str, name: str, ok_fn) -> dict:
    path = ROOT / "fixtures" / rel
    if not path.is_file():
        return _row(name, False, f"missing fixtures/{rel}", skipped=True)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ok, detail = ok_fn(data)
        return _row(name, ok, detail, evidence={k: data.get(k) for k in list(data)[:8]})
    except Exception as e:
        return _row(name, False, str(e))


def run_live(report: dict) -> list[dict]:
    """Paid live probes and/or fold prior outframe evidence files.

    Default (no YAPPER_AUDIT_LIVE): fold last_run / omni evidence so scoring
    reflects proven outframes without re-spending quota.
    With YAPPER_AUDIT_LIVE=1: also run gated smoke harnesses when env set.
    """
    live: list[dict] = []
    want = os.getenv("YAPPER_AUDIT_LIVE", "").lower() in ("1", "true", "yes", "on")

    # Always fold prior evidence (honest: file ok ≠ re-run this session)
    live.append(_evidence_file(
        "motion/last_run.json",
        "live:motion_last_run_file",
        lambda d: (
            bool(d.get("ok")) and "motion-control" in str(d.get("model") or d.get("sku") or ""),
            f"model={d.get('model')} source={d.get('source')}",
        ),
    ))
    live.append(_evidence_file(
        "lipsync/last_run.json",
        "live:lipsync_last_run_file",
        lambda d: (bool(d.get("ok")) and bool(d.get("media_url")), f"model={d.get('model')}"),
    ))
    live.append(_evidence_file(
        "face_swap/last_run.json",
        "live:face_swap_last_run_file",
        lambda d: (
            bool(d.get("ok")) and "nano-banana" in str(d.get("model") or ""),
            f"model={d.get('model')} mode={d.get('mode')}",
        ),
    ))
    live.append(_evidence_file(
        "audit/omni_live_latest.json",
        "live:omni_last_run_file",
        lambda d: (
            bool(d.get("ok")) and bool((d.get("meta") or {}).get("omni") or d.get("url")),
            f"model={d.get('model')} omni={(d.get('meta') or {}).get('omni')}",
        ),
    ))

    if not want:
        live.append(_row(
            "live:paid_probe_skipped",
            True,
            "YAPPER_AUDIT_LIVE not set — using folded last_run evidence only",
            skipped=True,
        ))
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
    soft_fail_ok = {"ops:stripe_configured", "ops:oidc_configured", "api:extractor_tiktok_honest", "models:shelf_vs_yapper"}
    hard = [c for c in must if c["name"] not in soft_fail_ok]
    hard_ok = sum(1 for c in hard if c["ok"])
    live_hard = [c for c in live if not c.get("skipped") and c["name"] != "live:skipped"]
    live_ok = sum(1 for c in live_hard if c["ok"])

    gaps = [
        {
            "area": "模型货架深度",
            "yapper": "宣传 18+ 图 / 26+ 视频全开（Veo/Sora/WAN/Hailuo…）",
            "betty": f"active={meta.get('active_models')} / lab={meta.get('lab_models')}（诚实货架，不虚增）",
            "priority": "P0",
            "impact": "高",
            "status": "open",
        },
        {
            "area": "Seedance Omni 产品深度",
            "yapper": "多模态参考 + 内建唇形 + 多镜叙事（营销主推）",
            "betty": "reference_* 已接线 + Omni live 出片；缺内建唇形一体流与多镜一键成片 UX",
            "priority": "P0",
            "impact": "高",
            "status": "partial",
        },
        {
            "area": "收款 / SSO 生产",
            "yapper": "成熟订阅收款 + 企业登录",
            "betty": f"Stripe key={meta.get('stripe')} OIDC={meta.get('oidc')}（代码就绪，密钥未注入）",
            "priority": "P0（上线）",
            "impact": "高",
            "status": "open",
        },
        {
            "area": "Studio Lip-Sync 成片感",
            "yapper": "Advanced / Max Lip-Sync 病毒口型叙事",
            "betty": "kling/ai-avatar-pro live 已通；非专有训练引擎，缺周检 Beat",
            "priority": "P1",
            "impact": "高",
            "status": "partial",
        },
        {
            "area": "Face Swap / 病毒模板",
            "yapper": "人脸替换 + 模板库玩法",
            "betty": "i2i_edit live（nano-banana-edit）；非 InsightFace；病毒模板库薄",
            "priority": "P1",
            "impact": "中高",
            "status": "partial",
        },
        {
            "area": "URL-to-Viral（社媒链接反推）",
            "yapper": "TikTok/IG URL → 结构提示词/可复用工作流",
            "betty": "YouTube 封面解析 ok；TikTok/IG best-effort；非完整 reel→分镜结构",
            "priority": "P1",
            "impact": "中高",
            "status": "partial",
        },
        {
            "area": "Explore 飞轮密度",
            "yapper": "百万级资产叙事 + 强 Remix 习惯",
            "betty": f"gallery list≈{meta.get('gallery_items')} total≈{meta.get('gallery_total')}；publish/remix 有，氛围弱",
            "priority": "P1",
            "impact": "中高",
            "status": "open",
        },
        {
            "area": "Performance / Act-One 级叙事",
            "yapper": "Advanced Motion Control 成片感",
            "betty": "Performance Drive=Motion+可选 Lipsync；≠ Runway Act-One；样片常需 playground",
            "priority": "P1（体验）",
            "impact": "中",
            "status": "partial",
        },
        {
            "area": "专用 Image Apps 深度",
            "yapper": "Product / Headshots / Photo Packs 批量工作流",
            "betty": "独立路由存在；多为 prompt-pack 导向，非批量 SKU 管线",
            "priority": "P2",
            "impact": "中",
            "status": "partial",
        },
        {
            "area": "Motion + Voice Changer",
            "yapper": "动作迁移可叠加变声",
            "betty": "voice_text TTS 旁白 + Performance；非实时变声引擎",
            "priority": "P2",
            "impact": "中",
            "status": "partial",
        },
        {
            "area": "定价滑块 / 团队席位",
            "yapper": "Max credits 滑块 + Team members",
            "betty": "四档 id 含 max 已对齐；缺 credits 滑块与团队席位产品化",
            "priority": "P2",
            "impact": "低中",
            "status": "partial",
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
    # Depth bonus: closed/partial productization of former hard gaps (caps to 12 pts)
    depth = 0
    if meta.get("face_swap_live"):
        depth += 3
    if meta.get("lipsync_live"):
        depth += 2
    if meta.get("omni_live"):
        depth += 3
    if meta.get("youtube_social"):
        depth += 2
    if meta.get("performance_drive"):
        depth += 2
    depth = min(12, depth)
    live_component = live_score if live_score is not None else 58
    overall = round(
        min(
            96.0,
            0.28 * tool_surface
            + 0.24 * live_component
            + 0.18 * shelf
            + 0.14 * billing
            + 0.10 * community
            + depth,
        ),
        1,
    )
    betty_readiness = round(
        min(
            99.0,
            0.38 * tool_surface
            + 0.32 * live_component
            + 0.15 * (75 if meta.get("active_models", 0) >= 8 else 50)
            + 0.10 * community
            + 0.05 * (depth * 5),
        ),
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
        "depth_bonus": depth,
        "scoring_note": (
            "tool_surface=硬契约；overall_vs_yapper 含货架/收款/社区拖累 + 已闭环深度加分；"
            "勿把 readiness.ok(dev) 当生产可收款。"
        ),
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
    # Enrich meta from folded evidence + contract for depth scoring
    live_by = {x["name"]: x for x in live}
    meta["face_swap_live"] = bool((live_by.get("live:face_swap_last_run_file") or {}).get("ok"))
    meta["lipsync_live"] = bool((live_by.get("live:lipsync_last_run_file") or {}).get("ok"))
    meta["omni_live"] = bool((live_by.get("live:omni_last_run_file") or {}).get("ok"))
    meta["motion_live"] = bool((live_by.get("live:motion_last_run_file") or {}).get("ok"))
    meta["youtube_social"] = any(c["name"] == "api:extractor_youtube_resolve" and c["ok"] for c in checks)
    meta["performance_drive"] = any(c["name"] == "cap:performance_drive" and c["ok"] for c in checks)
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
            "Contract checks ≠ Yapper product parity. "
            "Folded last_run evidence counts for live_*_file (not a fresh paid re-run). "
            "Face Swap=i2i_edit≠InsightFace. Motion/Performance≠Act-One. "
            "Do not treat mapping smoke as outframe."
        ),
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # Intentional soft gaps may fail; everything else in checks must pass.
    hard = [
        c for c in checks
        if c["name"] not in (
            "models:shelf_vs_yapper", "ops:stripe_configured", "ops:oidc_configured",
        )
        and not c.get("expected_missing")
    ]
    contract_pass = all(c["ok"] for c in hard)
    live_hard = [
        x for x in live
        if not x.get("skipped") and x["name"] not in ("live:skipped", "live:paid_probe_skipped")
    ]
    live_pass = all(x["ok"] for x in live_hard) if live_hard else True
    if args.strict_live:
        return 0 if contract_pass and live_pass else 1
    return 0 if contract_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
