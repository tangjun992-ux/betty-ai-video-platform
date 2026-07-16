#!/usr/bin/env python3
"""Yapper core-feature parity harness — one JSON report for all studio tools.

Usage:
  cd backend && python scripts/yapper_core_parity_harness.py

Exit 0 when all contract checks pass. Does not run paid live generation.
"""
from __future__ import annotations

import io
import json
import logging
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]
STILL = ROOT / "fixtures" / "motion" / "still.png"


def _check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def main() -> int:
    # Keep stdout JSON-clean for CI parsers
    logging.disable(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    checks: list[dict] = []

    # Auth
    email = f"harness_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Test1234!", "username": f"h{uuid.uuid4().hex[:6]}"},
    )
    token = reg.json().get("access_token") if reg.status_code == 200 else None
    h = {"Authorization": f"Bearer {token}"} if token else {}
    checks.append(_check("auth_register", bool(token), f"status={reg.status_code}"))

    # Capabilities
    cap = c.get("/api/v1/system/capabilities")
    feats = (cap.json() or {}).get("features") or {}
    need = [
        "motion_transfer", "prompt_extractor", "talking_avatar",
        "storyboard", "share_permalink", "failure_refund",
    ]
    missing = [k for k in need if k not in feats]
    checks.append(_check("capabilities_yapper", not missing and cap.status_code == 200, str(missing)))

    # Models
    models = c.get("/api/v1/models")
    md = models.json() if models.status_code == 200 else {}
    checks.append(_check(
        "models_active",
        models.status_code == 200 and int(md.get("active_count") or 0) >= 1,
        f"active={md.get('active_count')}",
    ))

    # Analyze
    an = c.post("/api/v1/generate/analyze", json={"prompt": "neon city", "media_type": "image"}, headers=h)
    checks.append(_check("generate_analyze", an.status_code == 200, an.text[:80]))

    # Extractor
    if STILL.is_file():
        ex = c.post(
            "/api/v1/generate/extract-prompt",
            headers=h,
            files={"media_file": ("still.png", io.BytesIO(STILL.read_bytes()), "image/png")},
            data={"media_kind": "image"},
        )
        body = ex.json() if ex.status_code == 200 else {}
        checks.append(_check(
            "prompt_extractor",
            ex.status_code == 200 and bool(body.get("prompt")),
            f"mode={body.get('mode')}",
        ))
    else:
        checks.append(_check("prompt_extractor", False, "fixture missing"))

    # Motion samples
    ms = c.get("/api/v1/motion/samples")
    msd = ms.json() if ms.status_code == 200 else {}
    checks.append(_check("motion_samples", ms.status_code == 200 and msd.get("available"), msd.get("mode", "")))

    # Lipsync voices
    lv = c.get("/api/v1/lipsync/voices")
    checks.append(_check("lipsync_voices", lv.status_code == 200 and bool((lv.json() or {}).get("voices"))))

    # Director
    modes = c.get("/api/v1/director/brain/modes")
    checks.append(_check("director_brain_modes", modes.status_code == 200))
    plan = c.post(
        "/api/v1/director/plan",
        json={"brief": "product ad three shots", "duration": 15},
        headers=h,
    )
    checks.append(_check("director_plan", plan.status_code == 200, plan.text[:100]))

    # Gallery / pricing / library / readiness
    gal = c.get("/api/v1/gallery/")
    checks.append(_check("gallery_list", gal.status_code == 200 and "items" in (gal.json() or {})))
    plans = c.get("/api/v1/pricing/plans")
    pids = {p["id"] for p in (plans.json() or {}).get("plans", [])} if plans.status_code == 200 else set()
    checks.append(_check("pricing_four_tiers", {"starter", "personal", "creator", "pro"} <= pids, str(sorted(pids))))
    lib = c.get("/api/v1/library/", headers=h)
    checks.append(_check("library_list", lib.status_code == 200, str(lib.status_code)))
    ready = c.get("/api/v1/system/readiness")
    rd = ready.json() if ready.status_code == 200 else {}
    checks.append(_check(
        "readiness_surface",
        ready.status_code == 200 and all(k in rd for k in ("stripe", "storage", "sso")),
        "",
    ))
    oidc = c.get("/api/v1/auth/oidc/status")
    checks.append(_check("oidc_status", oidc.status_code == 200))

    # Dev keys
    keys = c.get("/api/v1/developer/keys", headers=h)
    checks.append(_check("developer_keys", keys.status_code == 200, str(keys.status_code)))

    report = {
        "suite": "yapper_core_parity",
        "passed": all(x["ok"] for x in checks),
        "ok": sum(1 for x in checks if x["ok"]),
        "total": len(checks),
        "checks": checks,
        "honesty": (
            "Contract/API surface only — does not assert live outframes. "
            "Motion remains best_effort. Stripe/OIDC/CDN may be unconfigured."
        ),
        "yapper_tool_routes": [
            "/agent", "/create/image", "/create/video", "/create/lipsync",
            "/create/avatar", "/create/motion", "/create/timeline",
            "/create/audio", "/create/extract", "/create/upscale",
            "/create/bg-remove", "/create/extend", "/create/image-editor",
            "/tools", "/explore", "/pricing", "/sessions",
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
