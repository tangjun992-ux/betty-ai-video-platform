#!/usr/bin/env python3
"""Betty platform full E2E — FE reachability + API deep paths + optional live.

Implements docs/PLATFORM_FULL_TEST_PLAN.md (L0–L3 automated slice).

Usage:
  cd backend
  python3 scripts/platform_full_e2e.py
  PLATFORM_E2E_LIVE=1 MODEL_SMOKE_LIVE=1 MODEL_SMOKE_LIVE_VIDEO=1 \\
    MOTION_FIXTURE_LIVE=1 python3 scripts/platform_full_e2e.py --live
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
REPORT = ROOT / "fixtures" / "audit" / "platform_full_e2e_latest.json"
STILL = ROOT / "fixtures" / "motion" / "still.png"

FE_BASE = os.getenv("PLATFORM_FE_BASE", "http://127.0.0.1:3000").rstrip("/")
API_BASE = os.getenv("PLATFORM_API_BASE", "http://127.0.0.1:8000").rstrip("/")

FE_ROUTES = [
    "/",
    "/tools",
    "/agent",
    "/explore",
    "/library",
    "/gallery",
    "/pricing",
    "/sessions",
    "/settings",
    "/dashboard",
    "/create",
    "/create/image",
    "/create/video",
    "/create/lipsync",
    "/create/avatar",
    "/create/motion",
    "/create/timeline",
    "/create/audio",
    "/create/extract",
    "/create/upscale",
    "/create/bg-remove",
    "/create/extend",
    "/create/image-editor",
    "/create/product",
    "/create/headshots",
    "/create/photo-packs",
    "/auth/login",
    "/auth/register",
    "/developer",
    "/models",
    "/billing",
    "/tasks",
    "/projects",
    "/status",
]


def _row(name: str, ok: bool, detail: str = "", layer: str = "L1", **extra) -> dict:
    d = {"name": name, "ok": bool(ok), "detail": detail, "layer": layer}
    d.update(extra)
    return d


def check_fe_routes() -> list[dict]:
    import httpx
    import re

    checks = []
    with httpx.Client(timeout=30, follow_redirects=True) as c:
        for path in FE_ROUTES:
            try:
                r = c.get(f"{FE_BASE}{path}")
                ok = r.status_code == 200
                checks.append(_row(
                    f"fe:{path}",
                    ok,
                    f"status={r.status_code} bytes={len(r.content)}",
                    layer="L0",
                ))
            except Exception as e:
                checks.append(_row(f"fe:{path}", False, f"{type(e).__name__}: {e}", layer="L0"))

        # Tools hub: every /create/* and /agent link must resolve (no dead cards)
        try:
            tools = c.get(f"{FE_BASE}/tools")
            hrefs = sorted(set(re.findall(r'href="(/create/[^"?#]+|/agent|/explore|/library|/pricing)"', tools.text)))
            dead = []
            for href in hrefs:
                rr = c.get(f"{FE_BASE}{href}")
                if rr.status_code != 200:
                    dead.append(f"{href}:{rr.status_code}")
            checks.append(_row(
                "fe:tools_href_scan",
                tools.status_code == 200 and not dead and len(hrefs) >= 8,
                f"hrefs={len(hrefs)} dead={dead[:8]}",
                layer="L0",
            ))
        except Exception as e:
            checks.append(_row("fe:tools_href_scan", False, f"{type(e).__name__}: {e}", layer="L0"))

        # Auth login page must not 404; settings CTA must point to /auth/login in source
        try:
            settings_src = (REPO / "frontend" / "src" / "app" / "settings" / "page.tsx").read_text(encoding="utf-8")
            checks.append(_row(
                "fe:settings_login_href",
                'href="/auth/login"' in settings_src and 'href="/login"' not in settings_src,
                "settings CTA → /auth/login",
                layer="L0",
            ))
        except Exception as e:
            checks.append(_row("fe:settings_login_href", False, str(e), layer="L0"))
    return checks


def check_api_deep() -> tuple[list[dict], dict]:
    """In-process FastAPI TestClient — authoritative contract (not stale remote)."""
    logging.disable(logging.WARNING)
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    checks: list[dict] = []
    meta: dict = {}

    # Auth
    email = f"e2e_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post("/api/v1/auth/register", json={
        "email": email, "password": "Test1234!", "username": f"e{uuid.uuid4().hex[:6]}",
    })
    token = (reg.json() or {}).get("access_token") if reg.status_code == 200 else None
    h = {"Authorization": f"Bearer {token}"} if token else {}
    checks.append(_row("api:auth_register", bool(token), f"status={reg.status_code}", layer="L1"))

    # Health / readiness / capabilities
    for path, keys in (
        ("/health", None),
        ("/api/v1/system/readiness", ("stripe", "storage", "sso")),
        ("/api/v1/system/capabilities", ("features",)),
    ):
        r = c.get(path)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        ok = r.status_code == 200
        if keys:
            ok = ok and all(k in body for k in keys)
        checks.append(_row(f"api:{path}", ok, str(body)[:120] if isinstance(body, dict) else str(r.status_code), layer="L1"))
        if path.endswith("capabilities"):
            feats = body.get("features") or {}
            meta["features"] = list(feats.keys())
            checks.append(_row("api:cap_omni", "seedance_omni" in feats, "", layer="L1"))
            checks.append(_row("api:cap_motion_native", (feats.get("motion_transfer") or {}).get("mode") == "native", "", layer="L1"))
            checks.append(_row("api:cap_face_swap_honest", (feats.get("face_swap") or {}).get("available") is False, "", layer="L1"))

    # Models
    models = c.get("/api/v1/models")
    md = models.json() if models.status_code == 200 else {}
    active = int(md.get("active_count") or 0)
    meta["active_models"] = active
    checks.append(_row("api:models_active", active >= 1, f"active={active}", layer="L1"))

    # Analyze
    for mt in ("image", "video"):
        r = c.post("/api/v1/generate/analyze", json={"prompt": "neon city", "media_type": mt}, headers=h)
        checks.append(_row(f"api:analyze_{mt}", r.status_code == 200, r.text[:80], layer="L1"))

    # Extractor file + social reject
    if STILL.is_file():
        ex = c.post(
            "/api/v1/generate/extract-prompt",
            headers=h,
            files={"media_file": ("still.png", io.BytesIO(STILL.read_bytes()), "image/png")},
            data={"media_kind": "image"},
        )
        body = ex.json() if ex.status_code == 200 else {}
        checks.append(_row("api:extractor_file", ex.status_code == 200 and bool(body.get("prompt")), f"mode={body.get('mode')}", layer="L2"))
    social = c.post(
        "/api/v1/generate/extract-prompt",
        headers=h,
        data={"media_url": "https://www.tiktok.com/@x/video/1", "media_kind": "video"},
    )
    checks.append(_row("api:extractor_social_reject", social.status_code == 400, social.text[:120], layer="L1"))

    # Motion samples
    ms = c.get("/api/v1/motion/samples")
    msd = ms.json() if ms.status_code == 200 else {}
    checks.append(_row("api:motion_samples", ms.status_code == 200 and msd.get("available"), msd.get("mode", ""), layer="L1"))

    # Lipsync voices
    lv = c.get("/api/v1/lipsync/voices")
    checks.append(_row("api:lipsync_voices", lv.status_code == 200 and bool((lv.json() or {}).get("voices")), "", layer="L1"))

    # Director — English + Chinese minimal must both yield video without compose
    for brief_label, brief in (
        ("en", "15s ad"),
        ("zh", "做一条短视频广告"),
    ):
        plan = c.post(
            "/api/v1/director/plan",
            json={"brief": brief, "duration": 5, "minimal": True},
            headers=h,
        )
        acts = [s.get("action") for s in ((plan.json() or {}).get("steps") or [])]
        checks.append(_row(
            f"api:director_minimal_{brief_label}",
            plan.status_code == 200 and "video" in acts and "compose" not in acts,
            str(acts),
            layer="L1",
        ))
    ideate = c.post("/api/v1/director/ideate", json={"brief": "viral roast"}, headers=h)
    checks.append(_row("api:director_ideate", ideate.status_code == 200 and bool((ideate.json() or {}).get("concepts")), "", layer="L1"))

    # Timeline
    srt = "1\n00:00:00,000 --> 00:00:01,000\nHi\n\n"
    tp = c.post("/api/v1/timeline/subtitles/parse", json={"content": srt}, headers=h)
    checks.append(_row("api:timeline_srt", tp.status_code == 200 and int((tp.json() or {}).get("cue_count") or 0) >= 1, "", layer="L1"))

    # Gallery / pricing / library
    gal = c.get("/api/v1/gallery/")
    gd = gal.json() if gal.status_code == 200 else {}
    n = len(gd.get("items") or [])
    meta["gallery_items"] = n
    checks.append(_row("api:gallery", gal.status_code == 200 and "items" in gd, f"items={n} total={gd.get('total')}", layer="L1"))
    if n:
        key = gd["items"][0].get("id") or gd["items"][0].get("item_key")
        if key:
            rm = c.post(f"/api/v1/gallery/{key}/remix", headers=h)
            checks.append(_row("api:gallery_remix", rm.status_code in (200, 201), f"status={rm.status_code}", layer="L2"))

    plans = c.get("/api/v1/pricing/plans")
    pids = {p["id"] for p in (plans.json() or {}).get("plans", [])} if plans.status_code == 200 else set()
    checks.append(_row("api:pricing_max", {"starter", "personal", "creator", "max"} <= pids, str(sorted(pids)), layer="L1"))

    lib = c.get("/api/v1/library/", headers=h)
    checks.append(_row("api:library", lib.status_code == 200, str(lib.status_code), layer="L1"))

    # OpenAPI critical routes
    oa = c.get("/api/openapi.json")
    paths = (oa.json() or {}).get("paths") or {}
    for route in (
        "/api/v1/generate/",
        "/api/v1/generate/speech",
        "/api/v1/generate/edit",
        "/api/v1/generate/extract-prompt",
        "/api/v1/lipsync",
        "/api/v1/motion",
        "/api/v1/director/plan",
        "/api/v1/director/storyboard",
        "/api/v1/director/run",
    ):
        checks.append(_row(f"openapi:{route}", route in paths, "ok" if route in paths else "missing", layer="L0"))

    # Speech contract (no paid call)
    sp = c.post("/api/v1/generate/speech", json={"text": "", "voice": "Rachel"}, headers=h)
    checks.append(_row("api:speech_validation", sp.status_code in (400, 422), f"status={sp.status_code}", layer="L1"))

    # Generate dry-ish enqueue: may create real task — use unlikely short to still validate auth path
    # Prefer analyze-only already done; enqueue with enhance false and expect 200/402/422
    gen = c.post(
        "/api/v1/generate/",
        json={
            "prompt": "e2e contract still life product shot",
            "media_type": "image",
            "model": "gpt-image-2",
            "enhance_prompt": False,
            "count": 1,
        },
        headers=h,
    )
    # Accept queued/completed/failed-credits — must not 500/auth break
    checks.append(_row(
        "api:generate_image_enqueue",
        gen.status_code in (200, 201, 202, 402),
        f"status={gen.status_code} body={gen.text[:100]}",
        layer="L2",
        task_id=(gen.json() or {}).get("task_id") if gen.status_code < 300 else None,
    ))

    stripe = c.get("/api/v1/billing/stripe-status").json() or {}
    oidc = c.get("/api/v1/auth/oidc/status").json() or {}
    meta["stripe"] = bool(stripe.get("api_key_configured"))
    meta["oidc"] = bool(oidc.get("configured"))
    checks.append(_row("ops:stripe", meta["stripe"], str(stripe)[:100], layer="L5", gap=not meta["stripe"]))
    checks.append(_row("ops:oidc", meta["oidc"], str(oidc)[:100], layer="L5", gap=not meta["oidc"]))

    return checks, meta


def check_live() -> list[dict]:
    live = []
    if os.getenv("PLATFORM_E2E_LIVE", "").lower() not in ("1", "true", "yes", "on"):
        live.append(_row("live:skipped", True, "PLATFORM_E2E_LIVE not set", layer="L3", skipped=True))
        return live

    if os.getenv("MODEL_SMOKE_LIVE", "").lower() in ("1", "true", "yes", "on"):
        from app.services.model_smoke import run_live_image_sample
        img = run_live_image_sample(["gpt-image-2"])
        live.append(_row("live:image", int(img.get("outframe_ok") or 0) >= 1, f"outframe_ok={img.get('outframe_ok')}", layer="L3"))
    else:
        live.append(_row("live:image", False, "MODEL_SMOKE_LIVE off", layer="L3", skipped=True))

    if os.getenv("MODEL_SMOKE_LIVE_VIDEO", "").lower() in ("1", "true", "yes", "on"):
        from app.services.model_smoke import run_live_video_sample
        vid = run_live_video_sample(["seedance-2.0-fast", "seedance-2.0"])
        live.append(_row("live:video_ge2", int(vid.get("outframe_ok") or 0) >= 2, f"ok={vid.get('outframe_ok')}", layer="L3"))
    else:
        live.append(_row("live:video_ge2", False, "MODEL_SMOKE_LIVE_VIDEO off", layer="L3", skipped=True))

    last = ROOT / "fixtures" / "motion" / "last_run.json"
    omni = ROOT / "fixtures" / "audit" / "omni_live_latest.json"
    if last.is_file():
        data = json.loads(last.read_text(encoding="utf-8"))
        live.append(_row("live:motion_evidence", bool(data.get("ok")), f"model={data.get('model')}", layer="L3"))
    if omni.is_file():
        data = json.loads(omni.read_text(encoding="utf-8"))
        live.append(_row("live:omni_evidence", bool(data.get("ok")), f"model={data.get('model')}", layer="L3"))
    return live


def score(checks: list[dict], live: list[dict], meta: dict) -> dict:
    hard = [c for c in checks if not c.get("gap") and not c.get("skipped")]
    hard_ok = sum(1 for c in hard if c["ok"])
    live_hard = [c for c in live if not c.get("skipped")]
    live_ok = sum(1 for c in live_hard if c["ok"])
    by_layer: dict[str, dict] = {}
    for c in checks + live:
        layer = c.get("layer") or "?"
        by_layer.setdefault(layer, {"ok": 0, "total": 0})
        by_layer[layer]["total"] += 1
        if c["ok"]:
            by_layer[layer]["ok"] += 1
    return {
        "hard_ok": hard_ok,
        "hard_total": len(hard),
        "hard_pass_pct": round(100 * hard_ok / max(1, len(hard)), 1),
        "live_ok": live_ok,
        "live_total": len(live_hard),
        "by_layer": by_layer,
        "meta": meta,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--skip-fe", action="store_true", help="Skip remote FE HTTP checks")
    args = parser.parse_args()
    if args.live:
        os.environ["PLATFORM_E2E_LIVE"] = "1"

    checks: list[dict] = []
    if not args.skip_fe:
        checks.extend(check_fe_routes())
    api_checks, meta = check_api_deep()
    checks.extend(api_checks)
    live = check_live()
    scoring = score(checks, live, meta)

    report = {
        "suite": "platform_full_e2e",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fe_base": FE_BASE,
        "api_base": API_BASE,
        "plan": "docs/PLATFORM_FULL_TEST_PLAN.md",
        "checks": checks,
        "live": live,
        "scoring": scoring,
        "failures": [c for c in checks + live if not c["ok"] and not c.get("skipped") and not c.get("gap")],
        "known_gaps": [c for c in checks if c.get("gap")],
        "honesty": "L0/L1 pass ≠ L3 outframe. Stripe/OIDC may be unconfigured. Face swap unavailable by design until SKU verified.",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

    hard = [c for c in checks if not c.get("gap") and not c.get("skipped")]
    return 0 if all(c["ok"] for c in hard) else 1


if __name__ == "__main__":
    raise SystemExit(main())
