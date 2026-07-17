#!/usr/bin/env python3
"""Real Director E2E for all 8 Agent scenario cards — 2 samples each.

Order matches the /agent UI visual reading order requested for QA:
  1 product_ad → 2 ugc → 3 anime → 4 ai_portrait →
  5 product_commercial → 6 micro_drama → 7 product_photo → 8 talking_avatar

Usage:
  cd backend && .venv/bin/python scripts/director_eight_features_e2e.py
  .venv/bin/python scripts/director_eight_features_e2e.py --only product_ad,ugc
  .venv/bin/python scripts/director_eight_features_e2e.py --only ai_portrait --samples 2
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import time
import uuid
import urllib.request
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
ROOT = Path(__file__).resolve().parents[1]
ART = Path("/opt/cursor/artifacts/director_eight_features")
WS_ART = ROOT.parent / "artifacts" / "director_eight_features"
REPORT = ROOT / "fixtures" / "audit" / "director_eight_features_latest.json"

# Visual order from Agent card grid (user QA sequence)
FEATURES = [
    {
        "id": "product_ad",
        "title": "产品广告",
        "duration": 15,
        "samples": [
            {
                "tag": "A",
                "brief": "为「Aurora 降噪耳机」制作15秒高转化投放广告：通勤地铁场景开场，突出主动降噪与30小时续航，电影级产品质感，适合信息流测试",
            },
            {
                "tag": "B",
                "brief": "为「Nimbus 便携咖啡机」制作15秒产品广告：清晨厨房钩子，30秒出杯与奶泡质感特写，转化收束适合社媒投放",
            },
        ],
    },
    {
        "id": "ugc",
        "title": "UGC 种草",
        "duration": 15,
        "samples": [
            {
                "tag": "A",
                "brief": "竖屏UGC种草：女生手持夏日防晒霜真实开箱试用，口语安利不闷痘、清爽，手机自拍感，生活卧室场景",
            },
            {
                "tag": "B",
                "brief": "竖屏UGC种草：男生宿舍测评磁吸充电宝，真实手持展示接口与容量，口语推荐通勤党，原生信息流节奏",
            },
        ],
    },
    {
        "id": "anime",
        "title": "动漫生成",
        "duration": 15,
        "samples": [
            {
                "tag": "A",
                "brief": "电影级动漫短片：少女站在雨后黄昏车站，新海诚式晚霞与积水倒影，发丝与云层细腻运动",
            },
            {
                "tag": "B",
                "brief": "电影级动漫短片：少年骑车穿过夏日乡间公路，强烈阳光丁达尔光柱，二次元角色与流动风景",
            },
        ],
    },
    {
        "id": "ai_portrait",
        "title": "AI 写真",
        "duration": 5,
        "samples": [
            {
                "tag": "A",
                "brief": "一组专业形象写真：25岁亚洲女性，深色西装外套，柔和棚拍布光，自然自信表情，领英/简历四张统一风格",
            },
            {
                "tag": "B",
                "brief": "一组专业形象写真：30岁亚洲男性，浅灰商务衬衫，柔光箱，沉稳微笑，名片与社媒头像四张统一身份",
            },
        ],
    },
    {
        "id": "product_commercial",
        "title": "产品商业片",
        # QA pack uses 15s (≈3 shots) under upstream credit budget; card/prod plan stays 30s/6.
        "duration": 15,
        "samples": [
            {
                "tag": "A",
                "brief": "30秒电影级商业片：高端护肤精华，玻璃瓶与晨光，精致布光多镜头叙事，奢侈品牌campaign质感",
            },
            {
                "tag": "B",
                "brief": "30秒电影级商业片：钛合金机械腕表，暗调金属反光与运镜，高级品牌发布大片",
            },
        ],
    },
    {
        "id": "micro_drama",
        "title": "微短剧",
        "duration": 30,
        "samples": [
            {
                "tag": "A",
                "brief": "竖屏微短剧：相亲局上发现对方竟是前同事，强钩子开场，情绪对峙与反转，人物张力，电影级竖屏叙事",
            },
            {
                "tag": "B",
                "brief": "竖屏微短剧：加班夜电梯里撞见老板拿着自己设计的原型，误会与澄清反转，人物情绪张力",
            },
        ],
    },
    {
        "id": "product_photo",
        "title": "产品摄影",
        "duration": 5,
        "samples": [
            {
                "tag": "A",
                "brief": "影棚级产品摄影：哑光黑陶瓷咖啡杯，柔光箱，纯净背景，反射高光，商业套图四张",
            },
            {
                "tag": "B",
                "brief": "影棚级产品摄影：极简白色无线耳机充电盒，柔光与材质特写，电商主图级四张套图",
            },
        ],
    },
    {
        "id": "talking_avatar",
        "title": "数字人口播",
        "duration": 15,
        "samples": [
            {
                "tag": "A",
                "brief": "竖屏数字人口播：年轻女主播正面棚拍，讲解智能手表续航与健康监测卖点，自然口型同步",
            },
            {
                "tag": "B",
                "brief": "竖屏数字人口播：专业男主播正面棚拍，讲解护肤精华成分与吸收感，自然口型同步",
            },
        ],
    },
]


def _safe_name(s: str, max_len: int = 60) -> str:
    """Filenames must not contain '/' (Chinese titles like '形象照 1/4' break paths)."""
    out = "".join(c if c.isalnum() or c in "-_." else "_" for c in (s or "x"))
    return (out.strip("_") or "x")[:max_len]


def _dl(url: str, dest: Path) -> bool:
    if not url:
        return False
    if url.startswith("/"):
        url = "http://127.0.0.1:8000" + url
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "BettyEightFeatures/1.0"})
        with urllib.request.urlopen(req, timeout=180) as r:
            dest.write_bytes(r.read())
        return dest.is_file() and dest.stat().st_size > 400
    except Exception as e:
        print("  dl fail", url[:120], e)
        return False


def _auth_client() -> tuple[httpx.Client, dict]:
    c = httpx.Client(base_url=BASE, timeout=60)
    email = f"dir8_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post(
        "/auth/register",
        json={"email": email, "password": "Test1234!", "username": f"d8{uuid.uuid4().hex[:6]}"},
    )
    reg.raise_for_status()
    body = reg.json() or {}
    token = body["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    uid = (body.get("user") or {}).get("id")
    db_path = ROOT / "dev.db"
    conn = sqlite3.connect(str(db_path))
    if not uid:
        row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if not row:
            conn.close()
            raise RuntimeError(f"registered user not found in {db_path}: {email}")
        uid = row[0]
    # Large pool: commercial ×2 alone can exceed 100 credits
    conn.execute(
        "UPDATE user_balance SET credits=5000, daily_credits=500, plan_credits=2000 WHERE user_id=?",
        (uid,),
    )
    conn.commit()
    conn.close()
    return c, headers


def run_one(c: httpx.Client, headers: dict, feature: dict, sample: dict, out_dir: Path) -> dict:
    scenario = feature["id"]
    brief = sample["brief"]
    duration = feature["duration"]
    tag = sample["tag"]
    print(f"\n=== {feature['title']} [{tag}] scenario={scenario} ===")
    plan_r = c.post(
        "/director/plan",
        headers=headers,
        json={"brief": brief, "duration": duration, "minimal": True, "scenario": scenario},
    )
    plan_r.raise_for_status()
    plan = plan_r.json()
    (out_dir / f"{tag}_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  intent={plan.get('intent')} credits={plan.get('total_credits')} steps={len(plan.get('steps') or [])}")

    run = c.post(
        "/director/run/async",
        headers=headers,
        json={
            "brief": brief,
            "duration": duration,
            "dry_run": False,
            "minimal": True,
            "scenario": scenario,
            "plan": plan,
        },
    )
    print(f"  run_async {run.status_code}")
    run.raise_for_status()
    job_id = run.json()["job_id"]

    t0 = time.time()
    last = None
    # Commercial 6×Kling can exceed 30 min
    timeout = 3600 if scenario == "product_commercial" else 2400
    while time.time() - t0 < timeout:
        st = c.get(f"/director/progress/{job_id}", headers=headers)
        if st.status_code != 200:
            time.sleep(4)
            continue
        last = st.json()
        step_sum = " | ".join(
            f"{(s.get('title') or '')[:12]}:{s.get('status')}" for s in (last.get("steps") or [])
        )
        print(
            f"  [{int(time.time()-t0):4d}s] {last.get('status')} assets={last.get('asset_count')} :: {step_sum}",
            flush=True,
        )
        if last.get("done") or last.get("status") in ("completed", "failed", "error", "done"):
            break
        time.sleep(6)

    assert last is not None
    (out_dir / f"{tag}_progress.json").write_text(
        json.dumps(last, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    saved = []
    for i, a in enumerate(last.get("assets") or []):
        url = a.get("media_url") or a.get("url")
        typ = a.get("type") or ""
        ext = ".mp4" if typ == "video" or (url or "").endswith(".mp4") else ".png"
        if a.get("final"):
            name = f"{tag}_FINAL{ext}"
        else:
            name = f"{tag}_asset{i}_{_safe_name(str(a.get('step', 'x')))}{ext}"
        dest = out_dir / name
        ok = _dl(url or "", dest)
        if ok:
            saved.append(str(dest))
            # also copy final-ish to workspace
            if a.get("final") or typ == "video" or (scenario in ("ai_portrait", "product_photo") and ext == ".png"):
                ws = WS_ART / feature["id"]
                ws.mkdir(parents=True, exist_ok=True)
                (ws / name).write_bytes(dest.read_bytes())

    return {
        "scenario": scenario,
        "title": feature["title"],
        "tag": tag,
        "brief": brief,
        "status": last.get("status"),
        "error": last.get("error"),
        "credits": plan.get("total_credits"),
        "intent": plan.get("intent"),
        "elapsed_s": int(time.time() - t0),
        "assets": saved,
        "asset_count": last.get("asset_count"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated scenario ids")
    ap.add_argument("--samples", type=int, default=2, help="1 or 2 samples per feature")
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    ART.mkdir(parents=True, exist_ok=True)
    WS_ART.mkdir(parents=True, exist_ok=True)

    c, headers = _auth_client()
    mode = c.get("/director/mode", headers=headers).json()
    print("mode", mode)
    if not mode.get("real_available"):
        print("ABORT: real generation not available")
        return 2

    results = []
    for feature in FEATURES:
        if only and feature["id"] not in only:
            continue
        out_dir = ART / feature["id"]
        out_dir.mkdir(parents=True, exist_ok=True)
        for sample in feature["samples"][: max(1, min(2, args.samples))]:
            try:
                results.append(run_one(c, headers, feature, sample, out_dir))
            except Exception as e:
                print(f"  FAILED {feature['id']} {sample['tag']}: {e}")
                results.append({
                    "scenario": feature["id"],
                    "title": feature["title"],
                    "tag": sample["tag"],
                    "status": "error",
                    "error": str(e),
                    "assets": [],
                })

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "artifact_dir": str(ART),
        "workspace_copy": str(WS_ART),
        "results": results,
        "ok": sum(1 for r in results if r.get("status") in ("completed", "done") and r.get("assets")),
        "total": len(results),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (ART / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n==== SUMMARY ====")
    print(json.dumps(report, ensure_ascii=False, indent=2)[:4000])
    return 0 if report["ok"] == report["total"] and report["total"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
