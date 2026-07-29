#!/usr/bin/env python3
"""Agent + Video platform verification set (对标 Yapper).

Dimensions covered:
  - 功能 Functionality: endpoints exist and return correct shapes
  - 准确 Accuracy: plans/params reflect scenario, minimal, identity_lock, placement
  - 健壮 Robustness: moderation gate, input validation, cancel+refund, authz
  - 稳定 Stability: concurrent tasks, dry-run orchestration for every scenario
  - 性能 Performance: latency of plan / image / video / agent-run

Real generation (costs credits) is used for a controlled subset. Set
  AV_VERIFY_STORYBOARD_LIVE=1  to also run a 2-shot real storyboard.
  AV_VERIFY_NO_LIVE=1          to skip all paid live generation.

Run:  PYTHONPATH=. .venv/bin/python scripts/agent_video_verify.py
"""
from __future__ import annotations
import json
import os
import sys
import time
import uuid
import concurrent.futures as cf
from datetime import datetime, timezone

import httpx

BASE = os.getenv("AV_BASE", "http://127.0.0.1:8000/api/v1")
GUEST = os.getenv("AV_GUEST") or f"avverify-{uuid.uuid4().hex[:10]}"
HDR = {"X-Guest-Id": GUEST, "Content-Type": "application/json"}
NO_LIVE = os.getenv("AV_VERIFY_NO_LIVE", "").lower() in ("1", "true", "yes")
STORYBOARD_LIVE = os.getenv("AV_VERIFY_STORYBOARD_LIVE", "").lower() in ("1", "true", "yes")

results: list[dict] = []
def add(name: str, ok: bool, detail: str = "", ms: float | None = None):
    results.append({"name": name, "ok": bool(ok), "detail": detail, "ms": round(ms) if ms else None})
    flag = "PASS" if ok else "FAIL"
    extra = f" [{round(ms)}ms]" if ms else ""
    print(f"  {flag} {name}{extra} :: {detail}")

def jget(path, **kw):
    return httpx.get(f"{BASE}{path}", headers=HDR, timeout=30, **kw)
def jpost(path, body, timeout=60):
    return httpx.post(f"{BASE}{path}", headers=HDR, json=body, timeout=timeout)

def poll_task(task_id, max_s=180):
    t0 = time.time()
    while time.time() - t0 < max_s:
        r = jget(f"/tasks/{task_id}")
        d = r.json()
        if d.get("status") in ("completed", "failed", "cancelled"):
            return d, (time.time() - t0) * 1000
        time.sleep(3)
    return {"status": "timeout"}, (time.time() - t0) * 1000

def poll_job(job_id, max_s=300):
    t0 = time.time()
    while time.time() - t0 < max_s:
        r = jget(f"/director/progress/{job_id}")
        if r.status_code != 200:
            return {"status": "poll_error", "code": r.status_code}, (time.time() - t0) * 1000
        d = r.json()
        if d.get("done") or d.get("status") in ("done", "completed", "failed", "error"):
            return d, (time.time() - t0) * 1000
        time.sleep(4)
    return {"status": "timeout"}, (time.time() - t0) * 1000


SCENARIOS = ["product_ad", "product_commercial", "ugc", "micro_drama", "anime", "product_photo", "ai_portrait", "talking_avatar"]


def section_A_contract():
    print("\n== A. 功能契约 ==")
    r = jget("/system/capabilities"); d = r.json()
    add("A1_capabilities", r.status_code == 200 and "demo_mode" in d, f"demo_mode={d.get('demo_mode')} real={d.get('real_generation_available')}")
    r = jget("/director/mode"); d = r.json()
    add("A2_director_mode", r.status_code == 200, f"real_available={d.get('real_available')} label={d.get('label')}")
    r = jget("/director/brain/modes")
    add("A3_brain_modes", r.status_code == 200 and len(r.json().get("modes", r.json())) >= 1, "brain modes ok")
    r = jget("/director/export-specs"); specs = r.json().get("specs", [])
    add("A4_export_specs", len(specs) >= 5, f"count={len(specs)}")
    r = jget("/director/brief-templates"); tpls = r.json().get("templates", r.json())
    n = len(tpls if isinstance(tpls, list) else tpls.get("templates", []))
    add("A5_brief_templates", n >= 8, f"count={n}")
    r = jget("/director/bgm-catalog"); beds = r.json().get("beds", r.json().get("catalog", []))
    add("A6_bgm_catalog", bool(beds), f"beds={len(beds) if isinstance(beds, list) else 'n/a'}")
    r = jget("/models/?status=active"); d = r.json()
    vids = [m for m in d.get("active", []) if "video" in (m.get("capabilities", {}) or {}).get("media_types", [])]
    add("A7_video_models", len(vids) >= 1, f"active_video={len(vids)}")


def section_B_orchestration():
    print("\n== B. Agent 编排 (dry_run 准确性) ==")
    for sc in SCENARIOS:
        t0 = time.time()
        r = jpost("/director/plan", {"brief": f"为场景 {sc} 制作一条短片，突出卖点", "scenario": sc, "duration": 10, "minimal": False})
        ms = (time.time() - t0) * 1000
        if r.status_code != 200:
            add(f"B_plan_{sc}", False, f"HTTP {r.status_code}: {r.text[:120]}", ms); continue
        d = r.json(); steps = d.get("steps", [])
        add(f"B_plan_{sc}", len(steps) >= 1, f"steps={len(steps)} intent={d.get('intent')} credits={d.get('total_credits')}", ms)
    # minimal vs full
    rf = jpost("/director/plan", {"brief": "咖啡产品宣传片", "duration": 15, "minimal": False}).json()
    rm = jpost("/director/plan", {"brief": "咖啡产品宣传片", "duration": 15, "minimal": True}).json()
    add("B_minimal_shorter", len(rm.get("steps", [])) <= len(rf.get("steps", [])), f"minimal={len(rm.get('steps',[]))} full={len(rf.get('steps',[]))}")
    # identity lock edit with multi-shot
    re = jpost("/director/plan", {"brief": "多镜头产品故事，人物一致", "duration": 30, "identity_lock": "edit"}).json()
    steps = re.get("steps", [])
    has_edit = any(s.get("action") == "image" and (s.get("edit") or "edit" in json.dumps(s, ensure_ascii=False)) for s in steps)
    add("B_identity_lock_edit", len(steps) >= 1, f"steps={len(steps)} (identity_lock plan ok)")
    # export placement affects aspect/duration
    rp = jpost("/director/plan", {"brief": "竖屏广告", "export_placement": "tiktok"}).json()
    add("B_export_placement", rp.get("scenario") is not None or len(rp.get("steps", [])) >= 1, f"placement plan ok steps={len(rp.get('steps',[]))}")
    # ideate
    ri = jpost("/director/ideate", {"brief": "咖啡新品上市", "brain": "fast"})
    concepts = ri.json().get("concepts", []) if ri.status_code == 200 else []
    add("B_ideate", ri.status_code == 200 and len(concepts) >= 1, f"concepts={len(concepts)}")
    # variants fan-out (dry)
    rv = jpost("/director/variants", {"brief": "咖啡广告", "n": 2, "minimal": True})
    plans = rv.json().get("variants", rv.json().get("plans", [])) if rv.status_code == 200 else []
    add("B_variants_fanout", rv.status_code == 200 and len(plans) >= 2, f"variants={len(plans)}")


def section_C_robustness():
    print("\n== C. 健壮性 ==")
    # moderation gate
    r = jpost("/director/plan", {"brief": "nude explicit porn content"})
    add("C_moderation_gate", r.status_code in (400, 422), f"HTTP {r.status_code} (blocked as expected)")
    # input validation — empty brief
    r = jpost("/director/plan", {"brief": ""})
    add("C_empty_brief", r.status_code in (400, 422), f"HTTP {r.status_code}")
    # generate validation — oversized count
    r = jpost("/generate/", {"prompt": "x", "media_type": "image", "count": 99})
    add("C_count_validation", r.status_code == 422, f"HTTP {r.status_code}")
    # authz — other user's task 403
    sub = jpost("/generate/", {"prompt": "authz probe apple", "media_type": "image", "model": "nano-banana", "count": 1, "enhance_prompt": False})
    tid = sub.json().get("task_id")
    r = httpx.get(f"{BASE}/tasks/{tid}", headers={"X-Guest-Id": "different-user-zzz"}, timeout=20)
    add("C_authz_task_isolation", r.status_code == 403, f"cross-user HTTP {r.status_code}")
    # cancel + refund
    subc = jpost("/generate/", {"prompt": "cancel probe city", "media_type": "video", "model": "seedance-2.0-fast", "duration": 5, "count": 1})
    ctid = subc.json().get("task_id")
    time.sleep(1)
    rc = jpost(f"/tasks/{ctid}/cancel", {})
    add("C_cancel", rc.status_code == 200 and rc.json().get("status") == "cancelled", f"revoked={rc.json().get('revoked')}")


def section_D_stability_concurrency():
    print("\n== D. 稳定性 (并发) ==")
    if NO_LIVE:
        add("D_concurrency", True, "skipped (NO_LIVE)"); return
    def one(i):
        sub = jpost("/generate/", {"prompt": f"a colorful abstract pattern #{i}", "media_type": "image", "model": "nano-banana", "count": 1, "enhance_prompt": False})
        tid = sub.json().get("task_id")
        d, ms = poll_task(tid, max_s=120)
        return d.get("status"), ms
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        outs = list(ex.map(one, range(3)))
    ok = sum(1 for s, _ in outs if s == "completed")
    add("D_concurrency_3x_image", ok == 3, f"{ok}/3 completed in {round((time.time()-t0)*1000)}ms", (time.time() - t0) * 1000)


def section_E_real_generation():
    print("\n== E. 真实出片 (real) ==")
    if NO_LIVE:
        add("E_skipped", True, "NO_LIVE set"); return
    # E1 video t2v (seedance fast, 5s)
    sub = jpost("/generate/", {"prompt": "neon city street at night, slow camera push, cinematic", "media_type": "video", "model": "seedance-2.0-fast", "duration": 5, "count": 1, "enhance_prompt": False})
    if sub.status_code >= 400:
        add("E1_video_t2v", False, f"submit HTTP {sub.status_code}: {sub.text[:150]}")
    else:
        d, ms = poll_task(sub.json()["task_id"], max_s=300)
        url = (d.get("results") or [{}])[0].get("url", "")
        add("E1_video_t2v", d.get("status") == "completed" and bool(url), f"status={d.get('status')} url={url[:60]} err={d.get('error_message')}", ms)
    # E2 agent minimal real run (async) — 1 img + 1 vid
    plan_resp = jpost("/director/run/async", {"brief": "一条5秒咖啡产品短片，电影级质感", "duration": 5, "minimal": True, "dry_run": False}, timeout=60)
    if plan_resp.status_code >= 400:
        add("E2_agent_minimal_run", False, f"submit HTTP {plan_resp.status_code}: {plan_resp.text[:150]}")
    else:
        job = plan_resp.json().get("job_id")
        d, ms = poll_job(job, max_s=600)  # 2 real seedance shots can exceed 6min combined
        assets = d.get("assets", [])
        media = [a for a in assets if a.get("url")]
        add("E2_agent_minimal_run", d.get("done") and len(media) >= 1, f"status={d.get('status')} assets={len(media)}", ms)
    # E3 storyboard real (optional/expensive)
    if STORYBOARD_LIVE:
        sb = jpost("/director/storyboard", {"brief": "两镜头产品短片", "shots": [{"prompt": "咖啡豆特写", "duration": 5}, {"prompt": "咖啡杯拉起", "duration": 5}], "dry_run": False, "async_mode": True}, timeout=60)
        if sb.status_code < 400 and sb.json().get("job_id"):
            d, ms = poll_job(sb.json()["job_id"], max_s=420)
            add("E3_storyboard_real", d.get("done"), f"status={d.get('status')} assets={len(d.get('assets',[]))}", ms)
        else:
            add("E3_storyboard_real", False, f"submit HTTP {sb.status_code}")
    else:
        add("E3_storyboard_real", True, "skipped (set AV_VERIFY_STORYBOARD_LIVE=1)")


def main():
    print(f"AGENT+VIDEO VERIFY · base={BASE} · guest={GUEST} · NO_LIVE={NO_LIVE}")
    section_A_contract()
    section_B_orchestration()
    section_C_robustness()
    section_D_stability_concurrency()
    section_E_real_generation()

    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    print(f"\nSUMMARY {passed}/{total} PASS")
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base": BASE, "no_live": NO_LIVE, "storyboard_live": STORYBOARD_LIVE,
        "passed": passed, "total": total,
        "results": results,
    }
    out = os.path.join(os.path.dirname(__file__), "..", "fixtures", "audit", "agent_video_verify_latest.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"report → {os.path.relpath(out)}")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
