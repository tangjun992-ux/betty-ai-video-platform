#!/usr/bin/env python3
"""Core Yapper full-dimension verify (L1/L6/L7/L8) — no live spend.

Usage:
  cd backend && DATABASE_URL=sqlite+aiosqlite:////tmp/betty-core-yapper-ux.db \\
    PYTHONPATH=. python3 scripts/core_yapper_full_verify.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/betty-core-yapper-ux.db")

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(os.environ.get("CORE_YAPPER_VERIFY_OUT", "/opt/cursor/artifacts"))
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "core_yapper_full_verify.json"

report: dict = {
    "generated_at": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()),
    "layer": ["L1", "L6", "L7", "L8"],
    "honesty": "进程内 TestClient 延迟 ≠ 生产 SLA；无 Stripe/KIE Key 不宣称可收款/可出片。",
    "tests": [],
    "latency_ms": {},
    "gaps": [],
}


def add(name: str, ok: bool, detail: str, **extra):
    row = {"name": name, "pass": bool(ok), "detail": detail, **extra}
    report["tests"].append(row)
    print(("PASS" if ok else "FAIL"), name, "::", detail, flush=True)


def main() -> int:
    sys.path.insert(0, str(ROOT / "backend"))
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.concurrency import PLAN_CONCURRENCY

    video_page = (ROOT / "frontend/src/app/create/video/page.tsx").read_text(encoding="utf-8")
    pricing_page = (ROOT / "frontend/src/app/pricing/page.tsx").read_text(encoding="utf-8")

    add(
        "L7.video_ideas_fill_composer",
        "setPrompt(idea.prompt)" in video_page and 'data-testid="video-ideas-row"' in video_page,
        "视频灵感芯片必须填 composer，而不是只跳 /agent",
    )
    add(
        "L7.video_ideas_not_agent_bounce",
        '{ label: en ? "Video ideas" : "视频灵感", href: "/agent" }' not in video_page,
        "旧「视频灵感 → /agent」跳走已移除",
    )
    add(
        "L6.pricing_limits_table",
        'data-testid="pricing-limits-table"' in pricing_page,
        "定价页有 Yapper 式 Limits 对照表",
    )

    with TestClient(app) as client:
        t0 = time.perf_counter()
        plans = client.get("/api/v1/pricing/plans")
        report["latency_ms"]["pricing_plans"] = round((time.perf_counter() - t0) * 1000, 2)
        ok = plans.status_code == 200
        body = plans.json() if ok else {}
        by_id = {p["id"]: p for p in body.get("plans", [])}
        expected = {"starter": (4, 0), "personal": (6, 0), "creator": (10, 2), "max": (40, 7)}
        limits_ok = ok and all(
            by_id.get(pid, {}).get("concurrent_generations") == conc
            and by_id.get(pid, {}).get("included_team_seats") == seats
            for pid, (conc, seats) in expected.items()
        )
        add(
            "L1.pricing_limits_contract",
            limits_ok,
            f"plans={list(by_id)} honesty={bool(body.get('limits_honesty'))}",
            expected=expected,
        )
        add(
            "L8.pricing_plans_budget",
            report["latency_ms"]["pricing_plans"] < 400,
            f"{report['latency_ms']['pricing_plans']}ms (in-process budget 400ms, not SLA)",
        )

        t0 = time.perf_counter()
        caps = client.get("/api/v1/system/capabilities")
        report["latency_ms"]["capabilities"] = round((time.perf_counter() - t0) * 1000, 2)
        add("L1.capabilities", caps.status_code == 200, f"status={caps.status_code}")
        add(
            "L8.capabilities_budget",
            report["latency_ms"]["capabilities"] < 800,
            f"{report['latency_ms']['capabilities']}ms (in-process budget 800ms, not SLA)",
        )

        models = client.get("/api/v1/models/?status=active")
        active = []
        if models.status_code == 200:
            payload = models.json()
            active = payload.get("active") or payload.get("models") or []
            if isinstance(active, dict):
                active = list(active.values())
        active_n = len(active) if isinstance(active, list) else 0
        report["active_count"] = active_n
        add(
            "L6.shelf_not_inflated",
            active_n <= 12,
            f"active={active_n}（禁止把 lab 算进可售；Yapper 公开 18+/29+ 是叙事差距）",
        )

        email = f"coreux_{uuid.uuid4().hex[:8]}@test.local"
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Test1234!", "username": f"c{uuid.uuid4().hex[:6]}"},
        )
        if reg.status_code == 200:
            token = reg.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            samples = []
            quote_ok = True
            for _ in range(3):
                t0 = time.perf_counter()
                q = client.post(
                    "/api/v1/generate/quote",
                    json={"prompt": "赛博朋克夜景", "media_type": "video", "duration": 5, "model": "seedance-2.0"},
                    headers=headers,
                )
                samples.append(round((time.perf_counter() - t0) * 1000, 2))
                quote_ok = quote_ok and q.status_code == 200 and q.json().get("estimated_cost_credits", 0) >= 1
            report["latency_ms"]["quote_samples"] = samples
            report["latency_ms"]["quote_min"] = min(samples)
            report["latency_ms"]["quote_median"] = round(statistics.median(samples), 2)
            add("L1.quote", quote_ok, f"samples_ms={samples}")
            add(
                "L8.quote_budget",
                min(samples) < 800,
                f"min={min(samples)}ms median={report['latency_ms']['quote_median']}ms (not SLA)",
            )
        else:
            add("L1.quote", False, f"register failed: {reg.status_code} {reg.text[:200]}")

        conc_ok = PLAN_CONCURRENCY.get("starter") == 4 and PLAN_CONCURRENCY.get("max") == 40
        add("L1.concurrency_source", conc_ok, f"PLAN_CONCURRENCY starter/max = {PLAN_CONCURRENCY.get('starter')}/{PLAN_CONCURRENCY.get('max')}")

    report["gaps"] = [
        {"id": "S1", "severity": "P2", "detail": "Yapper 货架话术 18+/29+；Betty active 以本机目录为准，禁止虚增"},
        {"id": "S2", "severity": "P2", "detail": "Yapper 主推 Seedance 2.5；Betty 仍为 Seedance 2.0"},
        {"id": "S3", "severity": "P2", "detail": "Yapper 卖 MCP/API 分发面；Betty 无对等产品页"},
        {"id": "P3", "severity": "P2", "detail": "本环境无 Stripe/OIDC Key，不能收款"},
        {"id": "L2", "severity": "env", "detail": "无 Redis/Celery 时入队失败记环境，不改产品分"},
    ]
    passed = sum(1 for t in report["tests"] if t["pass"])
    report["summary"] = {"passed": passed, "total": len(report["tests"]), "ok": passed == len(report["tests"])}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{passed}/{len(report['tests'])}  report={OUT}", flush=True)
    return 0 if report["summary"]["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
