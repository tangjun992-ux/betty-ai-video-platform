#!/usr/bin/env python3
"""Main Line B verification — packaging BGM URLs, placements, templates, 2-variant LIVE.

Requires API + Celery + KIE. Live step runs 2 stripped product_ad variants (1 shot each).
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import time
import uuid
from pathlib import Path

import httpx

OUT = Path("/opt/cursor/artifacts/mainline_b_verify")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8000/api/v1"
report: dict = {"generated_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()), "tests": []}


def add(name: str, ok: bool, detail: str, **extra):
    report["tests"].append({"name": name, "pass": bool(ok), "detail": detail, **extra})
    print(("PASS" if ok else "FAIL"), name, "::", detail, flush=True)


def strip_to_one_video(plan: dict) -> dict:
    steps = list(plan.get("steps") or [])
    vids = [s for s in steps if s.get("action") == "video"]
    keep = vids[:1]
    keep_ids = {s["id"] for s in keep}
    new_steps = [s for s in steps if s.get("action") != "video" or s["id"] in keep_ids]
    last = keep[-1]["id"] if keep else None
    for s in new_steps:
        if s.get("action") in ("subtitle", "audio") and last:
            s["depends_on"] = [last]
        if s.get("action") == "compose":
            deps = [x["id"] for x in new_steps if x.get("action") in ("video", "subtitle", "audio")]
            s["depends_on"] = deps
    return {**plan, "steps": new_steps}


def main() -> int:
    # Offline
    from app.adapters.demo_provider import (
        ensure_bgm_stock_installed, _bgm_url_for_preset, BGM_PRESETS,
        compose_final_video, render_demo_video, _local_media_path,
        _generated_dir, MEDIA_URL_PREFIX, GENERATED_SUBDIR, _render_bgm_wav,
    )
    from app.export_specs import list_export_specs, resolve_placement
    from app.director_brief_templates import list_brief_templates
    from app.director import DirectorPlanner

    installed = ensure_bgm_stock_installed()
    add("b_bgm_stock_count", len(installed) >= 6, f"installed={installed}")
    urls_ok = 0
    for p in ("soft", "upbeat", "cinematic", "drama", "corporate", "energetic", "chill", "hype"):
        u = _bgm_url_for_preset(p)
        if u and "bgm/" in u:
            urls_ok += 1
    add("b_bgm_public_urls", urls_ok >= 6, f"url_presets={urls_ok}/8 presets={len(BGM_PRESETS)}")

    # Fetch one bed via HTTP (proves media mount)
    sample = _bgm_url_for_preset("upbeat")
    try:
        r = httpx.get(sample, timeout=30)
        add("b_bgm_http_fetch", r.status_code == 200 and len(r.content) > 1000,
            f"status={r.status_code} bytes={len(r.content)} url={sample}")
    except Exception as e:
        add("b_bgm_http_fetch", False, str(e))

    specs = list_export_specs()
    add("b_export_specs", len(specs) >= 5, f"count={len(specs)} ids={[s['id'] for s in specs]}")
    tpls = list_brief_templates()
    add("b_brief_templates", len(tpls) >= 8, f"count={len(tpls)}")

    plan = DirectorPlanner().plan(
        "Aurora耳机投放", duration=15, minimal=True, scenario="product_ad",
        export_placement="meta_feed",
    )
    comp = next(s for s in plan.steps if s.action == "compose")
    add(
        "b_plan_meta_feed",
        comp.params.get("export_placement") == "meta_feed"
        and comp.params.get("aspect_ratio") == "16:9"
        and comp.params.get("bgm_preset") in BGM_PRESETS,
        f"placement={comp.params.get('export_placement')} aspect={comp.params.get('aspect_ratio')} bgm={comp.params.get('bgm_preset')}",
    )

    # Local compose with hype stock URL path
    u1, _ = render_demo_video("mlb1", "320x180", 2, "cinematic")
    u2, _ = render_demo_video("mlb2", "320x180", 2, "sci-fi")
    narr = _generated_dir() / f"mlb_n_{uuid.uuid4().hex[:6]}.wav"
    _render_bgm_wav(3.0, narr, preset="soft")
    narr_url = f"{MEDIA_URL_PREFIX}/{GENERATED_SUBDIR}/{narr.name}"
    final, _ = compose_final_video(
        [u1, u2], None, True, narr_url,
        subtitle_track=[{"text": "Meta试投", "start": 0, "end": 3}],
        export_preset="landscape_16_9", bgm=True, bgm_preset="upbeat",
        subtitle_style="impact", cta_text="了解更多", voice_duck=True,
    )
    dest = OUT / "b_packaged_ad.mp4"
    dest.write_bytes(Path(_local_media_path(final)).read_bytes())
    meta = json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(dest)],
    ))
    has_a = any(s.get("codec_type") == "audio" for s in meta["streams"])
    add("b_compose_stock_bgm", has_a and dest.stat().st_size > 1000,
        f"audio={has_a} bytes={dest.stat().st_size}")

    # API + LIVE 2 variants
    mode = httpx.get(f"{BASE}/director/mode", timeout=10).json()
    if not mode.get("real_available"):
        add("b_live_variants", False, "real_available=false")
        _finish()
        return 1

    c = httpx.Client(base_url=BASE, timeout=60)
    email = f"mlb_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post("/auth/register", json={
        "email": email, "password": "Test1234!", "username": f"m{uuid.uuid4().hex[:6]}",
    })
    reg.raise_for_status()
    tok = reg.json()["access_token"]
    uid = reg.json()["user"]["id"]
    conn = sqlite3.connect("/workspace/backend/dev.db")
    conn.execute("UPDATE user_balance SET credits=8000 WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    h = {"Authorization": f"Bearer {tok}"}

    # Catalog APIs
    for path, key in (("/director/export-specs", "specs"), ("/director/brief-templates", "templates"), ("/director/bgm-catalog", "beds")):
        rr = c.get(path, headers=h)
        add(f"b_api_{path.split('/')[-1]}", rr.status_code == 200 and bool(rr.json().get(key)),
            f"status={rr.status_code}")

    vr = c.post("/director/variants", headers=h, json={
        "brief": "Aurora降噪耳机15秒Meta信息流广告，突出续航与降噪",
        "scenario": "product_ad", "n": 2, "minimal": True,
        "export_placement": "meta_feed", "identity_lock": "hero",
    })
    add("b_variants_plan_n2", vr.status_code == 200 and vr.json().get("count") == 2,
        f"status={vr.status_code} count={vr.json().get('count')}")
    variants = vr.json().get("variants") or []
    # Strip each to 1 video for live cost control
    for v in variants:
        v["plan"] = strip_to_one_video(v["plan"])

    run = c.post("/director/variants/run", headers=h, json={
        "brief": "Aurora降噪耳机15秒Meta信息流广告，突出续航与降噪",
        "scenario": "product_ad", "n": 2, "minimal": True,
        "dry_run": False, "export_placement": "meta_feed",
        "identity_lock": "hero", "variants": variants,
    })
    if run.status_code != 200:
        add("b_live_variants", False, f"run status={run.status_code} {run.text[:200]}")
        _finish()
        return 1
    batch_id = run.json()["batch_id"]
    add("b_live_variants_enqueued", True, f"batch={batch_id}")
    t0 = time.time()
    last = None
    while time.time() - t0 < 1500:
        st = c.get(f"/director/variants/progress/{batch_id}", headers=h)
        if st.status_code == 200:
            last = st.json()
            print(
                f"  live-batch +{int(time.time()-t0)}s done={last.get('done')} "
                f"finals={sum(1 for v in last.get('variants') or [] if v.get('final'))}",
                flush=True,
            )
            if last.get("done"):
                break
        time.sleep(8)
    finals = [v for v in (last or {}).get("variants") or [] if v.get("final")]
    ok_live = bool(last and last.get("done") and len(finals) >= 1)
    add("b_live_variants", ok_live, f"done={last.get('done') if last else None} finals={len(finals)}")
    for i, v in enumerate(finals[:2]):
        url = (v.get("final") or {}).get("media_url") or (v.get("final") or {}).get("url")
        if not url:
            continue
        if url.startswith("/"):
            url = "http://127.0.0.1:8000" + url
        data = httpx.get(url, timeout=180, follow_redirects=True).content
        path = OUT / f"b_variant_{v.get('variant_id')}.mp4"
        path.write_bytes(data)
        add(f"b_variant_{v.get('variant_id')}_file", path.stat().st_size > 50_000,
            f"bytes={path.stat().st_size}", path=str(path))

    _finish()
    ok = sum(1 for t in report["tests"] if t["pass"])
    total = len(report["tests"])
    print(f"SUMMARY {ok}/{total}", flush=True)
    return 0 if ok == total else 1


def _finish():
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    subprocess.run(["zip", "-qr", "/opt/cursor/artifacts/mainline_b_verify.zip", "."], cwd=str(OUT), check=False)
    print("REPORT", OUT / "report.json", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
