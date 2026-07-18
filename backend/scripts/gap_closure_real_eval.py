#!/usr/bin/env python3
"""Real evaluation of gap closures — focused probes (2/3/5 + optional 1/4)."""
from __future__ import annotations

import asyncio
import json
import sqlite3
import subprocess
import time
import uuid
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

OUT = Path("/opt/cursor/artifacts/gap_closure_eval")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8000/api/v1"
report: dict = {"tests": [], "generated_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())}


def add(name: str, ok: bool, detail: str, **extra):
    row = {"name": name, "pass": bool(ok), "detail": detail, **extra}
    report["tests"].append(row)
    print(("PASS" if ok else "FAIL"), name, "::", detail, flush=True)


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=60)
    email = f"gap_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post(
        "/auth/register",
        json={"email": email, "password": "Test1234!", "username": f"g{uuid.uuid4().hex[:6]}"},
    )
    reg.raise_for_status()
    tok = reg.json()["access_token"]
    uid = reg.json()["user"]["id"]
    conn = sqlite3.connect("/workspace/backend/dev.db")
    conn.execute("UPDATE user_balance SET credits=3000 WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    h = {"Authorization": f"Bearer {tok}"}

    # Gap 5 — variants API
    vr = c.post(
        "/director/variants",
        headers=h,
        json={
            "brief": "Aurora降噪耳机15秒投放广告",
            "scenario": "product_ad",
            "n": 3,
            "minimal": True,
        },
    )
    print("variants", vr.status_code, flush=True)
    vr.raise_for_status()
    body = vr.json()
    add(
        "gap5_variants_api",
        body.get("count") == 3,
        f"count={body.get('count')}",
        axes=body["variants"][0]["axes_applied"],
    )

    # Gap 3 — packaging styles
    from app.adapters.demo_provider import (
        compose_final_video,
        render_demo_video,
        _local_media_path,
    )

    u1, _ = render_demo_video("gap3 a", "320x180", 2, "cinematic")
    u2, _ = render_demo_video("gap3 b", "320x180", 2, "sci-fi")
    for style in ("feed", "ad", "talking"):
        final, _ = compose_final_video(
            [u1, u2],
            None,
            True,
            None,
            subtitle_track=[{"text": f"字幕样式{style}", "start": 0, "end": 3}],
            export_preset="landscape_16_9",
            bgm=True,
            bgm_preset="upbeat" if style != "talking" else "soft",
            subtitle_style=style,
            cta_text="了解更多",
        )
        p = _local_media_path(final)
        dest = OUT / f"gap3_substyle_{style}.mp4"
        dest.write_bytes(Path(p).read_bytes())
        add(f"gap3_subtitle_style_{style}", dest.stat().st_size > 1000, f"saved {dest.name}")

    # Gap 2 — real image + i2v
    hero_url, dims = asyncio.run(gap2_native_vertical())
    if hero_url:
        asyncio.run(gap2_i2v(hero_url))

    # Gap 1 — talking plan + optional short live (skip InfiniTalk hang: just verify plan + one Kling lipsync if credits)
    from app.director import DirectorPlanner

    plan = DirectorPlanner().plan(
        "竖屏数字人口播：年轻女主播正面特写讲解智能手表",
        duration=10,
        minimal=True,
        scenario="talking_avatar",
    )
    lips = next(s for s in plan.steps if s.action == "lipsync")
    add(
        "gap1_talking_plan_studio",
        lips.params.get("prefer_infinitalk") is True
        and ("CLOSE-UP" in next(s.prompt for s in plan.steps if s.action == "image")),
        f"prefer_infinitalk={lips.params.get('prefer_infinitalk')}",
    )

    # Live talking via director async (real)
    try:
        asyncio.run(gap1_live_talking(c, h))
    except Exception as e:
        add("gap1_live_talking", False, f"error: {e}")

    (OUT / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    ok = sum(1 for t in report["tests"] if t["pass"])
    total = len(report["tests"])
    print(f"SUMMARY {ok}/{total}", flush=True)
    print("REPORT", OUT / "report.json", flush=True)
    return 0 if ok == total else 1


async def gap2_native_vertical():
    from app.adapters.kie_adapter import KieAdapter
    from app.director import _size_from_params

    k = KieAdapter()
    size = _size_from_params({"aspect_ratio": "9:16"}, "1024x1024")
    print("gap2 size", size, flush=True)
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
    path = OUT / f"gap2_ugc_hero_{w}x{h}.png"
    path.write_bytes(data)
    ok = h > w * 1.2
    add(
        "gap2_native_9_16_image",
        ok,
        f"{w}x{h} ratio={h / w:.3f}",
        path=str(path),
    )
    return (url if ok else url), (w, h)


async def gap2_i2v(hero: str):
    from app.adapters.kie_adapter import KieAdapter

    k = KieAdapter()
    res = await k.generate_video(
        prompt="handheld vertical selfie slight natural shake, product demo, UGC pacing",
        model_id="kling-2.1-pro",
        duration=5,
        image_url=hero,
        aspect_ratio="9:16",
        resolution="1080x1920",
    )
    url = res.media_url
    data = httpx.get(url, timeout=180, follow_redirects=True).content
    path = OUT / "gap2_ugc_i2v.mp4"
    path.write_bytes(data)
    meta = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "json",
                str(path),
            ]
        )
    )
    w = meta["streams"][0]["width"]
    h = meta["streams"][0]["height"]
    ok = h > w
    add("gap2_native_9_16_i2v", ok, f"{w}x{h}", path=str(path))


async def gap1_live_talking(c: httpx.Client, h: dict):
    """Run one real talking_avatar job and inspect final aspect + lipsync model."""
    brief = "竖屏数字人口播：年轻女主播正面特写，讲解智能手表续航，自然口型"
    plan_r = c.post(
        "/director/plan",
        headers=h,
        json={"brief": brief, "duration": 10, "minimal": True, "scenario": "talking_avatar"},
    )
    plan_r.raise_for_status()
    plan = plan_r.json()
    run = c.post(
        "/director/run/async",
        headers=h,
        json={
            "brief": brief,
            "duration": 10,
            "dry_run": False,
            "minimal": True,
            "scenario": "talking_avatar",
            "plan": plan,
        },
    )
    run.raise_for_status()
    job_id = run.json()["job_id"]
    t0 = time.time()
    last = None
    while time.time() - t0 < 900:
        st = c.get(f"/director/progress/{job_id}", headers=h)
        if st.status_code == 200:
            last = st.json()
            print(
                f"  talking [{int(time.time()-t0)}s] {last.get('status')} assets={last.get('asset_count')}",
                flush=True,
            )
            if last.get("done") or last.get("status") in ("completed", "failed", "error", "done"):
                break
        await asyncio.sleep(6)
    assert last is not None
    assets = last.get("assets") or []
    finals = [a for a in assets if a.get("final") or (a.get("type") == "video" and a.get("lipsync"))]
    # prefer final packaged
    pick = next((a for a in assets if a.get("final")), None) or next(
        (a for a in assets if a.get("type") == "video"), None
    )
    if not pick:
        add("gap1_live_talking", False, f"no video asset status={last.get('status')} err={last.get('error')}")
        return
    url = pick.get("media_url") or pick.get("url")
    if url.startswith("/"):
        url = "http://127.0.0.1:8000" + url
    data = httpx.get(url, timeout=180, follow_redirects=True).content
    path = OUT / "gap1_talking_final.mp4"
    path.write_bytes(data)
    meta = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ]
        )
    )
    w = meta["streams"][0]["width"]
    h = meta["streams"][0]["height"]
    dur = float(meta["format"]["duration"])
    model = pick.get("model") or ""
    ok = h >= w and dur > 3 and path.stat().st_size > 50_000
    add(
        "gap1_live_talking",
        ok,
        f"{w}x{h} {dur:.1f}s model={model} final={bool(pick.get('final'))}",
        path=str(path),
        model=model,
    )


if __name__ == "__main__":
    raise SystemExit(main())
