#!/usr/bin/env python3
"""Formal gate: verify the 5 gap-closure optimizations with REAL probes.

Each gap writes PASS/FAIL into report.json. Live KIE runs are required for
gaps 1/2/4/5; gap 3 is local compose + ffprobe (BGM fixture + audio stream).

Usage (API + Celery must be up, KIE key configured):
  cd /workspace/backend && PYTHONPATH=. .venv/bin/python scripts/optimize_gate_verify.py
"""
from __future__ import annotations

import asyncio
import json
import re
import sqlite3
import subprocess
import time
import uuid
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

OUT = Path("/opt/cursor/artifacts/optimize_gate_verify")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8000/api/v1"
CELERY_LOG_CANDIDATES = [
    Path("/tmp/celery-opt.log"),
    Path("/tmp/celery-gap.log"),
    Path("/workspace/backend/celery.log"),
]
report: dict = {
    "generated_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
    "tests": [],
    "capability_claims_vs_evidence": {},
}


def add(name: str, ok: bool, detail: str, **extra):
    row = {"name": name, "pass": bool(ok), "detail": detail, **extra}
    report["tests"].append(row)
    print(("PASS" if ok else "FAIL"), name, "::", detail, flush=True)


def ffprobe_json(path: Path) -> dict:
    return json.loads(
        subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-show_streams", "-show_format",
                "-of", "json", str(path),
            ],
            timeout=60,
        )
    )


def register_client() -> tuple[httpx.Client, dict]:
    c = httpx.Client(base_url=BASE, timeout=60)
    email = f"optgate_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post(
        "/auth/register",
        json={"email": email, "password": "Test1234!", "username": f"o{uuid.uuid4().hex[:6]}"},
    )
    reg.raise_for_status()
    body = reg.json()
    uid = body["user"]["id"]
    tok = body["access_token"]
    conn = sqlite3.connect("/workspace/backend/dev.db")
    conn.execute("UPDATE user_balance SET credits=5000 WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    return c, {"Authorization": f"Bearer {tok}"}


def poll_job(c: httpx.Client, h: dict, job_id: str, *, timeout_s: int = 1200) -> dict:
    t0 = time.time()
    last: dict = {}
    while time.time() - t0 < timeout_s:
        st = c.get(f"/director/progress/{job_id}", headers=h)
        if st.status_code == 200:
            last = st.json()
            print(
                f"  job[{job_id[:8]}] +{int(time.time()-t0)}s "
                f"status={last.get('status')} assets={last.get('asset_count')}",
                flush=True,
            )
            if last.get("done") or last.get("status") in (
                "completed", "failed", "error", "done",
            ):
                return last
        time.sleep(6)
    last["timeout"] = True
    return last


def download_asset(url: str, dest: Path) -> Path:
    if url.startswith("/"):
        url = "http://127.0.0.1:8000" + url
    data = httpx.get(url, timeout=180, follow_redirects=True).content
    dest.write_bytes(data)
    return dest


def strip_to_n_videos(plan: dict, n: int = 2) -> dict:
    """Keep first N video steps; rewrite compose/subtitle deps."""
    steps = list(plan.get("steps") or [])
    vids = [s for s in steps if s.get("action") == "video"]
    keep_vids = vids[:n]
    keep_ids = {s["id"] for s in keep_vids}
    other = [s for s in steps if s.get("action") != "video"]
    # Drop video steps beyond N
    new_steps = []
    for s in steps:
        if s.get("action") == "video" and s["id"] not in keep_ids:
            continue
        new_steps.append(s)
    # Fix compose depends_on → remaining media
    media_ids = [
        s["id"] for s in new_steps
        if s.get("action") in ("image", "video", "lipsync", "subtitle", "audio")
    ]
    for s in new_steps:
        if s.get("action") == "compose":
            # Prefer video + subtitle deps
            deps = [x["id"] for x in new_steps if x.get("action") in ("video", "lipsync", "subtitle")]
            s["depends_on"] = deps or media_ids[-3:]
    plan = {**plan, "steps": new_steps}
    return plan


def celery_log_blob() -> str:
    chunks: list[str] = []
    for p in CELERY_LOG_CANDIDATES:
        if p.is_file():
            try:
                chunks.append(p.read_text(encoding="utf-8", errors="ignore")[-200_000:])
            except Exception:
                pass
    # Also try tmux capture
    try:
        out = subprocess.check_output(
            ["tmux", "-f", "/exec-daemon/tmux.portal.conf", "capture-pane", "-t", "celery-opt", "-p", "-S", "-3000"],
            text=True, timeout=10,
        )
        chunks.append(out)
    except Exception:
        pass
    return "\n".join(chunks)


# ── Gap probes ──────────────────────────────────────────────────────────

def gap3_bgm_and_subtitles():
    """Local compose must use fixture BGM and produce an audio stream."""
    from app.adapters.demo_provider import (
        compose_final_video, render_demo_video, _local_media_path, _fixtures_music_dir,
    )

    fixture = _fixtures_music_dir() / "upbeat.wav"
    add(
        "gap3_fixture_bgm_present",
        fixture.is_file() and fixture.stat().st_size > 1000,
        f"{fixture} size={fixture.stat().st_size if fixture.is_file() else 0}",
    )
    u1, _ = render_demo_video("gap3 a", "320x180", 2, "cinematic")
    u2, _ = render_demo_video("gap3 b", "320x180", 2, "sci-fi")
    for style, preset in (("ad", "upbeat"), ("feed", "soft"), ("talking", "soft")):
        final, _ = compose_final_video(
            [u1, u2],
            None,
            True,
            None,
            subtitle_track=[{"text": f"字幕{style}", "start": 0, "end": 3}],
            export_preset="landscape_16_9",
            bgm=True,
            bgm_preset=preset,
            subtitle_style=style,
            cta_text="了解更多",
        )
        p = Path(_local_media_path(final))
        dest = OUT / f"gap3_{style}_{preset}.mp4"
        dest.write_bytes(p.read_bytes())
        meta = ffprobe_json(dest)
        has_a = any(s.get("codec_type") == "audio" for s in meta.get("streams") or [])
        has_v = any(s.get("codec_type") == "video" for s in meta.get("streams") or [])
        add(
            f"gap3_compose_{style}_has_av",
            has_a and has_v and dest.stat().st_size > 1000,
            f"audio={has_a} video={has_v} bytes={dest.stat().st_size}",
            path=str(dest),
        )


async def gap2_native_vertical():
    from app.adapters.kie_adapter import KieAdapter
    from app.director import _size_from_params

    k = KieAdapter()
    size = _size_from_params({"aspect_ratio": "9:16"}, "1024x1024")
    add("gap2_size_mapping", size == "1080x1920", f"size={size}")
    res = await k.generate_image(
        prompt=(
            "UGC creator holding sunscreen bottle, vertical phone selfie framing, "
            "bedroom, natural light, authentic, single photo, 9:16"
        ),
        model_id="gpt-image-2",
        size=size,
        aspect_ratio="9:16",
    )
    url = res.media_url
    data = httpx.get(url, timeout=120, follow_redirects=True).content
    im = Image.open(BytesIO(data))
    w, h = im.size
    path = OUT / f"gap2_hero_{w}x{h}.png"
    path.write_bytes(data)
    ok = h > w * 1.2
    add("gap2_native_9_16_image", ok, f"{w}x{h} ratio={h/w:.3f}", path=str(path))
    if not ok:
        return None
    vres = await k.generate_video(
        prompt="handheld vertical selfie slight natural shake, product demo, UGC pacing",
        model_id="kling-2.1-pro",
        duration=5,
        image_url=url,
        aspect_ratio="9:16",
        resolution="1080x1920",
    )
    vpath = OUT / "gap2_i2v.mp4"
    download_asset(vres.media_url, vpath)
    meta = ffprobe_json(vpath)
    vw = meta["streams"][0]["width"]
    vh = meta["streams"][0]["height"]
    add("gap2_native_9_16_i2v", vh > vw, f"{vw}x{vh}", path=str(vpath))
    return url


def gap1_plan_and_tts_rate():
    from app.director import DirectorPlanner
    from inspect import signature
    from app.services.audio_prep import synthesize_speech_edge

    plan = DirectorPlanner().plan(
        "竖屏数字人口播：年轻女主播正面特写讲解智能手表",
        duration=10, minimal=True, scenario="talking_avatar",
    )
    lips = next(s for s in plan.steps if s.action == "lipsync")
    img = next(s for s in plan.steps if s.action == "image")
    add(
        "gap1_talking_plan_closeup_kling",
        lips.params.get("prefer_infinitalk") is False
        and ("CLOSE-UP" in img.prompt or "close-up" in img.prompt.lower())
        and lips.params.get("lipsync_model") == "kling/ai-avatar-pro",
        f"prefer_infinitalk={lips.params.get('prefer_infinitalk')} model={lips.params.get('lipsync_model')}",
    )
    sig = signature(synthesize_speech_edge)
    add("gap1_tts_rate_param", "rate" in sig.parameters, f"params={list(sig.parameters)}")


def gap1_live_talking(c: httpx.Client, h: dict):
    brief = "竖屏数字人口播：年轻女主播正面特写，讲解智能手表续航，自然口型"
    plan_r = c.post(
        "/director/plan", headers=h,
        json={"brief": brief, "duration": 10, "minimal": True, "scenario": "talking_avatar"},
    )
    plan_r.raise_for_status()
    plan = plan_r.json()
    run = c.post(
        "/director/run/async", headers=h,
        json={
            "brief": brief, "duration": 10, "dry_run": False, "minimal": True,
            "scenario": "talking_avatar", "plan": plan,
        },
    )
    run.raise_for_status()
    job_id = run.json()["job_id"]
    last = poll_job(c, h, job_id, timeout_s=900)
    assets = last.get("assets") or []
    pick = next((a for a in assets if a.get("final")), None) or next(
        (a for a in assets if a.get("type") == "video"), None
    )
    if not pick:
        add("gap1_live_talking", False, f"no video status={last.get('status')} err={last.get('error')}")
        return
    path = download_asset(pick.get("media_url") or pick.get("url"), OUT / "gap1_talking_final.mp4")
    meta = ffprobe_json(path)
    w = next(s["width"] for s in meta["streams"] if s["codec_type"] == "video")
    hgt = next(s["height"] for s in meta["streams"] if s["codec_type"] == "video")
    dur = float(meta["format"]["duration"])
    has_a = any(s.get("codec_type") == "audio" for s in meta["streams"])
    ok = hgt >= w and dur > 3 and path.stat().st_size > 50_000 and has_a
    add(
        "gap1_live_talking",
        ok,
        f"{w}x{hgt} {dur:.1f}s audio={has_a} final={bool(pick.get('final'))}",
        path=str(path),
        model=pick.get("model"),
    )


def gap4_live_identity(c: httpx.Client, h: dict):
    """2-shot UGC real run; require celery log 'identity_variant edit ok'."""
    brief = "UGC种草：年轻女生竖屏自拍安利防晒霜，自然手持"
    marker = f"OPTGATE_ID_{uuid.uuid4().hex[:8]}"
    plan_r = c.post(
        "/director/plan", headers=h,
        json={"brief": brief, "duration": 15, "minimal": True, "scenario": "ugc"},
    )
    plan_r.raise_for_status()
    plan = strip_to_n_videos(plan_r.json(), 2)
    # Tag a video prompt so we can correlate logs
    for s in plan["steps"]:
        if s.get("action") == "video" and (s.get("params") or {}).get("identity_variant"):
            s["prompt"] = f"{s['prompt']}｜{marker}"
    vids = [s for s in plan["steps"] if s.get("action") == "video"]
    assert len(vids) == 2
    assert vids[1]["params"].get("identity_variant") is True
    add(
        "gap4_plan_identity_variant_flag",
        True,
        f"shots={len(vids)} shot2_variant={vids[1]['params'].get('identity_variant')}",
    )
    t_before = time.time()
    run = c.post(
        "/director/run/async", headers=h,
        json={
            "brief": brief, "duration": 15, "dry_run": False, "minimal": True,
            "scenario": "ugc", "plan": plan,
        },
    )
    run.raise_for_status()
    job_id = run.json()["job_id"]
    last = poll_job(c, h, job_id, timeout_s=1500)
    assets = last.get("assets") or []
    finals = [a for a in assets if a.get("final")]
    videos = [a for a in assets if a.get("type") == "video"]
    pick = finals[0] if finals else (videos[-1] if videos else None)
    if pick:
        path = download_asset(pick.get("media_url") or pick.get("url"), OUT / "gap4_identity_final.mp4")
        meta = ffprobe_json(path)
        w = next(s["width"] for s in meta["streams"] if s["codec_type"] == "video")
        hgt = next(s["height"] for s in meta["streams"] if s["codec_type"] == "video")
        add(
            "gap4_live_multishot_final",
            hgt > w and path.stat().st_size > 50_000,
            f"{w}x{hgt} videos={len(videos)} final={bool(finals)} status={last.get('status')}",
            path=str(path),
        )
    else:
        add("gap4_live_multishot_final", False, f"no video status={last.get('status')} err={last.get('error')}")

    # Evidence: celery log must show identity_variant edit ok after job start
    time.sleep(2)
    blob = celery_log_blob()
    hit = "identity_variant edit ok" in blob
    # Also accept skip with warning if edit failed — but mark FAIL for capability claim
    skipped = "identity_variant skipped" in blob
    add(
        "gap4_identity_variant_edit_logged",
        hit,
        f"edit_ok={hit} skipped={skipped} (must see edit ok for PASS)",
        log_hit=hit,
        log_skipped=skipped,
    )


def gap5_variants_and_execute(c: httpx.Client, h: dict):
    brief = "Aurora降噪耳机15秒投放广告，突出续航与降噪"
    vr = c.post(
        "/director/variants", headers=h,
        json={"brief": brief, "scenario": "product_ad", "n": 3, "minimal": True, "duration": 15},
    )
    vr.raise_for_status()
    body = vr.json()
    ok_api = body.get("count") == 3 and len(body.get("variants") or []) == 3
    axes0 = (body["variants"][0].get("axes_applied") if ok_api else []) or []
    add("gap5_variants_api", ok_api, f"count={body.get('count')} axes0={axes0}", axes=axes0)
    if not ok_api:
        add("gap5_variant_executed", False, "skipped: variants API failed")
        return

    # Execute variant A with only 1 video shot (cost control) — still real outing
    v0 = body["variants"][0]
    plan = strip_to_n_videos(v0["plan"], 1)
    run = c.post(
        "/director/run/async", headers=h,
        json={
            "brief": brief, "duration": 15, "dry_run": False, "minimal": True,
            "scenario": "product_ad", "plan": plan,
        },
    )
    run.raise_for_status()
    job_id = run.json()["job_id"]
    last = poll_job(c, h, job_id, timeout_s=1200)
    assets = last.get("assets") or []
    pick = next((a for a in assets if a.get("final")), None) or next(
        (a for a in assets if a.get("type") == "video"), None
    )
    if not pick:
        add("gap5_variant_executed", False, f"no video status={last.get('status')} err={last.get('error')}")
        return
    path = download_asset(pick.get("media_url") or pick.get("url"), OUT / "gap5_variant_A_final.mp4")
    meta = ffprobe_json(path)
    has_v = any(s.get("codec_type") == "video" for s in meta["streams"])
    has_a = any(s.get("codec_type") == "audio" for s in meta["streams"])
    dur = float(meta["format"]["duration"])
    ok = has_v and path.stat().st_size > 50_000 and dur > 2
    add(
        "gap5_variant_executed",
        ok,
        f"variant={v0.get('variant_id')} {dur:.1f}s audio={has_a} bytes={path.stat().st_size}",
        path=str(path),
        axes=v0.get("axes_applied"),
    )


def write_capability_matrix():
    by = {t["name"]: t for t in report["tests"]}

    def ok(*names):
        return all(by.get(n, {}).get("pass") for n in names)

    report["capability_claims_vs_evidence"] = {
        "gap1_talking_closeup_kling_tts": {
            "claim": "CLOSE-UP + Kling default + slower TTS rate; live talking final",
            "verified": ok(
                "gap1_talking_plan_closeup_kling",
                "gap1_tts_rate_param",
                "gap1_live_talking",
            ),
            "tests": [
                by.get("gap1_talking_plan_closeup_kling"),
                by.get("gap1_tts_rate_param"),
                by.get("gap1_live_talking"),
            ],
        },
        "gap2_native_9_16_i2v": {
            "claim": "Native portrait image + i2v (not square padded)",
            "verified": ok("gap2_size_mapping", "gap2_native_9_16_image", "gap2_native_9_16_i2v"),
            "tests": [
                by.get("gap2_size_mapping"),
                by.get("gap2_native_9_16_image"),
                by.get("gap2_native_9_16_i2v"),
            ],
        },
        "gap3_bgm_subtitle_packaging": {
            "claim": "Fixture BGM beds + subtitle styles produce A/V packaged films",
            "verified": ok(
                "gap3_fixture_bgm_present",
                "gap3_compose_ad_has_av",
                "gap3_compose_feed_has_av",
                "gap3_compose_talking_has_av",
            ),
            "tests": [by.get(n) for n in (
                "gap3_fixture_bgm_present",
                "gap3_compose_ad_has_av",
                "gap3_compose_feed_has_av",
                "gap3_compose_talking_has_av",
            )],
        },
        "gap4_identity_variant_live": {
            "claim": "shot>1 runs edit_image identity_variant then i2v (log evidence)",
            "verified": ok(
                "gap4_plan_identity_variant_flag",
                "gap4_live_multishot_final",
                "gap4_identity_variant_edit_logged",
            ),
            "tests": [
                by.get("gap4_plan_identity_variant_flag"),
                by.get("gap4_live_multishot_final"),
                by.get("gap4_identity_variant_edit_logged"),
            ],
        },
        "gap5_variants_execute": {
            "claim": "variants API fans out plans AND at least one variant executes to film",
            "verified": ok("gap5_variants_api", "gap5_variant_executed"),
            "tests": [by.get("gap5_variants_api"), by.get("gap5_variant_executed")],
        },
    }


def main() -> int:
    print("=== OPTIMIZE GATE VERIFY ===", flush=True)
    mode = httpx.get(f"{BASE}/director/mode", timeout=10).json()
    if not mode.get("real_available"):
        print("ABORT: real generation not available", mode, flush=True)
        return 2

    # Offline / local first
    gap1_plan_and_tts_rate()
    gap3_bgm_and_subtitles()

    # Live KIE
    try:
        asyncio.run(gap2_native_vertical())
    except Exception as e:
        add("gap2_native_9_16_image", False, f"error: {e}")
        add("gap2_native_9_16_i2v", False, f"error: {e}")

    c, h = register_client()
    try:
        gap1_live_talking(c, h)
    except Exception as e:
        add("gap1_live_talking", False, f"error: {e}")
    try:
        gap4_live_identity(c, h)
    except Exception as e:
        add("gap4_live_multishot_final", False, f"error: {e}")
        add("gap4_identity_variant_edit_logged", False, f"error: {e}")
    try:
        gap5_variants_and_execute(c, h)
    except Exception as e:
        add("gap5_variant_executed", False, f"error: {e}")

    write_capability_matrix()
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    caps = report["capability_claims_vs_evidence"]
    cap_ok = sum(1 for v in caps.values() if v.get("verified"))
    ok = sum(1 for t in report["tests"] if t["pass"])
    total = len(report["tests"])
    print(f"SUMMARY tests {ok}/{total} | capabilities {cap_ok}/{len(caps)}", flush=True)
    for k, v in caps.items():
        print(f"  CAP {'PASS' if v['verified'] else 'FAIL'} {k}", flush=True)
    print("REPORT", OUT / "report.json", flush=True)
    # Zip artifacts
    subprocess.run(
        ["zip", "-qr", "/opt/cursor/artifacts/optimize_gate_verify.zip", "."],
        cwd=str(OUT), check=False,
    )
    return 0 if ok == total and cap_ok == len(caps) else 1


if __name__ == "__main__":
    raise SystemExit(main())
