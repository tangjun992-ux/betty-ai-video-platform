#!/usr/bin/env python3
"""Real (non-preview) Director talking-avatar E2E via live API.

Requires: uvicorn + celery workers with current code, KIE_API_KEY, Redis.
Spends ~13 platform credits + upstream KIE cost (TTS + image + lipsync).
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
import urllib.request
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
BRIEF = "一个竖屏数字人口播视频，自然口型同步，正面棚拍形象，讲解产品卖点"
ROOT = Path(__file__).resolve().parents[1]
ART = Path("/opt/cursor/artifacts/director_real_talking")
REPORT = ROOT / "fixtures" / "audit" / "director_real_talking_latest.json"


def _dl(url: str, dest: Path) -> bool:
    if not url:
        return False
    if url.startswith("/"):
        url = "http://127.0.0.1:8000" + url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BettyRealTest/1.0"})
        with urllib.request.urlopen(req, timeout=180) as r:
            dest.write_bytes(r.read())
        return dest.is_file() and dest.stat().st_size > 500
    except Exception as e:
        print("dl fail", url[:100], e)
        return False


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    c = httpx.Client(base_url=BASE, timeout=60)
    email = f"dir_real_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post(
        "/auth/register",
        json={"email": email, "password": "Test1234!", "username": f"dr{uuid.uuid4().hex[:6]}"},
    )
    print("register", reg.status_code)
    token = (reg.json() or {}).get("access_token")
    if not token:
        print(reg.text[:400])
        return 1
    headers = {"Authorization": f"Bearer {token}"}

    conn = sqlite3.connect(str(ROOT / "dev.db"))
    uid = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()[0]
    conn.execute(
        "UPDATE user_balance SET credits=500, daily_credits=50, plan_credits=200 WHERE user_id=?",
        (uid,),
    )
    conn.commit()
    print("topped up user", uid)
    conn.close()

    mode = c.get("/director/mode", headers=headers).json()
    print("mode", mode)
    if not mode.get("real_available"):
        print("ABORT: real generation not available")
        return 2

    plan_r = c.post("/director/plan", headers=headers, json={"brief": BRIEF, "duration": 15})
    plan_r.raise_for_status()
    plan = plan_r.json()
    print("intent", plan.get("intent"), "credits", plan.get("total_credits"))
    for s in plan.get("steps") or []:
        print(" ", s.get("action"), s.get("model_id"), "+", s.get("est_credits"))
    (ART / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    run = c.post(
        "/director/run/async",
        headers=headers,
        json={"brief": BRIEF, "duration": 15, "dry_run": False, "plan": plan},
    )
    print("run_async", run.status_code, run.text[:400])
    run.raise_for_status()
    job = run.json()
    job_id = job["job_id"]
    assert job.get("dry_run") is False, job
    print("job_id", job_id)

    t0 = time.time()
    last = None
    while time.time() - t0 < 1200:
        st = c.get(f"/director/progress/{job_id}", headers=headers)
        if st.status_code != 200:
            print("poll err", st.status_code, st.text[:200])
            time.sleep(3)
            continue
        last = st.json()
        steps = last.get("steps") or []
        step_sum = " | ".join(
            f"{(s.get('title') or '')[:10]}:{s.get('status')}" for s in steps
        )
        print(
            f"[{int(time.time()-t0):4d}s] status={last.get('status')} "
            f"done={last.get('done')} assets={last.get('asset_count')} :: {step_sum}"
        )
        if last.get("done") or last.get("status") in ("completed", "failed", "error", "done"):
            break
        time.sleep(5)

    assert last is not None
    (ART / "progress_final.json").write_text(
        json.dumps(last, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    saved = []
    for i, a in enumerate(last.get("assets") or []):
        url = a.get("media_url") or a.get("url")
        ext = ".mp4" if a.get("type") == "video" else (
            ".mp3" if a.get("type") == "audio" else ".jpg"
        )
        dest = ART / f"asset_{i}_{a.get('type', 'x')}{ext}"
        ok = _dl(url, dest)
        saved.append({
            "i": i, "ok": ok, "path": str(dest) if ok else None,
            "bytes": dest.stat().st_size if ok and dest.exists() else 0,
            "type": a.get("type"), "model": a.get("model"),
            "mode": a.get("mode"), "honesty": a.get("honesty"),
            "step": a.get("step"), "url": url,
        })
        print("saved", saved[-1])

    report = {
        "suite": "director_real_talking",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "brief": BRIEF,
        "job_id": job_id,
        "dry_run": False,
        "elapsed_s": round(time.time() - t0, 1),
        "status": last.get("status"),
        "done": last.get("done"),
        "total_ms": last.get("total_ms"),
        "error": last.get("error") or last.get("error_message"),
        "plan_intent": plan.get("intent"),
        "plan_credits": plan.get("total_credits"),
        "assets": saved,
        "steps": last.get("steps"),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (ART / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", REPORT)

    ok = bool(last.get("done")) and last.get("status") in ("done", "completed") and any(
        a.get("ok") and a.get("type") == "video" for a in saved
    )
    # Real path must NOT tag ken_burns honesty on video
    for a in saved:
        if a.get("type") == "video" and a.get("honesty"):
            ok = False
    print("PASS" if ok else "FAIL", "status=", last.get("status"), "error=", report.get("error"))
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
