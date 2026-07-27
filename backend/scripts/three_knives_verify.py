#!/usr/bin/env python3
"""Verify three-knife upgrades with real probes (local + API + dry-run variants).

Live KIE multi-variant real run is optional (costly); default verifies:
  1) packaging: 10+ subtitle styles + ducking compose + BGM URL hook
  2) variants: POST /variants + /variants/run (dry_run) + progress aggregation
  3) identity: lock modes + identity strip asset from dry-run multi-shot
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path

import httpx

OUT = Path("/opt/cursor/artifacts/three_knives_verify")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8000/api/v1"
report: dict = {"generated_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()), "tests": []}


def add(name: str, ok: bool, detail: str, **extra):
    report["tests"].append({"name": name, "pass": bool(ok), "detail": detail, **extra})
    print(("PASS" if ok else "FAIL"), name, "::", detail, flush=True)


def main() -> int:
    # ── Knife 1: packaging (local) ──
    from app.adapters.demo_provider import (
        SUBTITLE_STYLES, compose_final_video, render_demo_video,
        _local_media_path, _render_bgm_wav, _bgm_url_for_preset, build_identity_strip,
        _generated_dir, MEDIA_URL_PREFIX, GENERATED_SUBDIR,
    )
    import subprocess

    add("k1_subtitle_count", len(SUBTITLE_STYLES) >= 10, f"count={len(SUBTITLE_STYLES)} keys={sorted(SUBTITLE_STYLES)}")
    u1, _ = render_demo_video("k1a", "320x180", 2, "cinematic")
    u2, _ = render_demo_video("k1b", "320x180", 2, "sci-fi")
    narr = _generated_dir() / f"k1_narr_{uuid.uuid4().hex[:8]}.wav"
    _render_bgm_wav(3.0, narr, preset="soft")
    narr_url = f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{narr.name}"

    ducked_ok = 0
    for style in ("impact", "neon", "karaoke", "bold", "feed"):
        final, _ = compose_final_video(
            [u1, u2], None, True, narr_url,
            subtitle_track=[{"text": f"{style}字幕", "start": 0, "end": 3}],
            export_preset="landscape_16_9",
            bgm=True, bgm_preset="upbeat", subtitle_style=style,
            cta_text="了解更多", voice_duck=True,
        )
        p = Path(_local_media_path(final))
        dest = OUT / f"k1_{style}.mp4"
        dest.write_bytes(p.read_bytes())
        meta = json.loads(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(dest)],
        ))
        has_a = any(s.get("codec_type") == "audio" for s in meta.get("streams") or [])
        if has_a and dest.stat().st_size > 1000:
            ducked_ok += 1
    add("k1_duck_compose_styles", ducked_ok >= 5, f"ok_styles={ducked_ok}/5")
    # BGM URL hook resolvable (may be empty — still a pass if function works)
    try:
        url = _bgm_url_for_preset("upbeat")
        add("k1_bgm_url_hook", True, f"upbeat_url={'set' if url else 'empty(fallback fixtures)'}")
    except Exception as e:
        add("k1_bgm_url_hook", False, str(e))

    # ── Knife 3: identity strip local ──
    from app.adapters.demo_provider import render_demo_image
    h = render_demo_image("hero", "512x768", "portrait")
    s2 = render_demo_image("shot2", "512x768", "cinematic")
    strip, _ = build_identity_strip([h, s2], labels=["Hero", "Shot 1"])
    sp = Path(_local_media_path(strip))
    dest = OUT / "k3_identity_strip.jpg"
    dest.write_bytes(sp.read_bytes())
    add("k3_identity_strip", dest.stat().st_size > 500, f"bytes={dest.stat().st_size}", path=str(dest))

    from app.director import DirectorPlanner
    for mode, expect_variant in (("off", False), ("hero", False), ("edit", True)):
        plan = DirectorPlanner().plan(
            "UGC种草防晒霜", duration=15, minimal=True, scenario="ugc", identity_lock=mode,
        )
        vids = [s for s in plan.steps if s.action == "video"]
        ok = len(vids) >= 2 and (vids[1].params.get("identity_variant") is expect_variant)
        if mode == "off":
            ok = ok and not vids[0].params.get("identity_from")
        add(f"k3_identity_lock_{mode}", ok, f"shot2_variant={vids[1].params.get('identity_variant')}")

    # ── Knife 2: variants API dry-run parallel ──
    c = httpx.Client(base_url=BASE, timeout=60)
    email = f"knife_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post("/auth/register", json={
        "email": email, "password": "Test1234!", "username": f"k{uuid.uuid4().hex[:6]}",
    })
    reg.raise_for_status()
    tok = reg.json()["access_token"]
    uid = reg.json()["user"]["id"]
    conn = sqlite3.connect("/workspace/backend/dev.db")
    conn.execute("UPDATE user_balance SET credits=5000 WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    h = {"Authorization": f"Bearer {tok}"}

    vr = c.post("/director/variants", headers=h, json={
        "brief": "Aurora降噪耳机投放广告", "scenario": "product_ad",
        "n": 2, "minimal": True, "identity_lock": "edit",
    })
    add("k2_variants_plan", vr.status_code == 200 and vr.json().get("count") == 2,
        f"status={vr.status_code} count={vr.json().get('count') if vr.status_code==200 else None}")

    run = c.post("/director/variants/run", headers=h, json={
        "brief": "Aurora降噪耳机投放广告", "scenario": "product_ad",
        "n": 2, "minimal": True, "dry_run": True, "identity_lock": "hero",
        "variants": vr.json().get("variants") if vr.status_code == 200 else None,
    })
    if run.status_code != 200:
        add("k2_variants_run_dry", False, f"status={run.status_code} body={run.text[:200]}")
    else:
        batch_id = run.json()["batch_id"]
        add("k2_variants_run_dry", True, f"batch={batch_id} jobs={run.json().get('count')}")
        t0 = time.time()
        last = None
        while time.time() - t0 < 180:
            st = c.get(f"/director/variants/progress/{batch_id}", headers=h)
            if st.status_code == 200:
                last = st.json()
                print(f"  batch +{int(time.time()-t0)}s done={last.get('done')} status={last.get('status')}", flush=True)
                if last.get("done"):
                    break
            time.sleep(3)
        finals = [v for v in (last or {}).get("variants") or [] if v.get("final")]
        add(
            "k2_variants_gallery_dry",
            bool(last and last.get("done") and len(finals) >= 1),
            f"done={last.get('done') if last else None} finals={len(finals)}",
        )

    # Dry-run multi-shot for identity strip in progress assets
    plan_r = c.post("/director/plan", headers=h, json={
        "brief": "UGC种草竖屏", "duration": 15, "minimal": True,
        "scenario": "ugc", "identity_lock": "edit",
    })
    plan_r.raise_for_status()
    plan = plan_r.json()
    # keep 2 videos
    vids = [s for s in plan["steps"] if s["action"] == "video"][:2]
    keep = {s["id"] for s in vids}
    plan["steps"] = [s for s in plan["steps"] if s["action"] != "video" or s["id"] in keep]
    last_v = vids[-1]["id"]
    for s in plan["steps"]:
        if s["action"] in ("subtitle", "audio"):
            s["depends_on"] = [last_v]
        if s["action"] == "compose":
            s["depends_on"] = [x["id"] for x in plan["steps"] if x["action"] in ("video", "subtitle")]
    run2 = c.post("/director/run/async", headers=h, json={
        "brief": plan["brief"], "duration": 15, "dry_run": True, "minimal": True,
        "scenario": "ugc", "plan": plan, "identity_lock": "edit",
    })
    run2.raise_for_status()
    job = run2.json()["job_id"]
    t0 = time.time()
    snap = None
    while time.time() - t0 < 120:
        st = c.get(f"/director/progress/{job}", headers=h).json()
        snap = st
        if st.get("done"):
            break
        time.sleep(2)
    assets = (snap or {}).get("assets") or []
    strips = [a for a in assets if a.get("type") == "identity_strip" or a.get("identity_strip")]
    finals = [a for a in assets if a.get("final")]
    add(
        "k3_dryrun_strip_asset",
        bool(strips) or bool(finals and finals[0].get("identity_strip")),
        f"strip_assets={len(strips)} finals={len(finals)} asset_types={[a.get('type') for a in assets]}",
    )

    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for t in report["tests"] if t["pass"])
    total = len(report["tests"])
    print(f"SUMMARY {ok}/{total}", flush=True)
    print("REPORT", OUT / "report.json", flush=True)
    subprocess.run(["zip", "-qr", "/opt/cursor/artifacts/three_knives_verify.zip", "."], cwd=str(OUT), check=False)
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
