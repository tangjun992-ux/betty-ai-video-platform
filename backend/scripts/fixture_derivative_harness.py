#!/usr/bin/env python3
"""Derivative fixture harness (P1) — lipsync / motion / director / tools.

Modes:
  dry   (default): validate adapter methods + payload contracts (no paid calls)
  live: optional paid probes when FIXTURE_LIVE=1 and KIE_API_KEY set

Exit 0 when dry checks pass. Live failures print but do not fail dry CI.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_dry() -> dict:
    from app.adapters.kie_adapter import KieAdapter
    from app.adapters.demo_provider import demo_mode_active, compose_final_video
    from app.api import director as director_api

    kie = KieAdapter()
    report = {
        "mode": "dry",
        "demo_mode": demo_mode_active(),
        "kie_available": kie.is_available(),
        "checks": [],
    }

    def ok(name: str, passed: bool, detail: str = ""):
        report["checks"].append({"name": name, "ok": passed, "detail": detail})

    ok("generate_motion", hasattr(kie, "generate_motion"))
    ok("generate_lipsync", hasattr(kie, "generate_lipsync"))
    ok("edit_image", hasattr(kie, "edit_image"))
    ok("upscale_image", hasattr(kie, "upscale_image"))
    ok("remove_background", hasattr(kie, "remove_background"))
    ok("compose_final_video", callable(compose_final_video))
    ok("director_dry_run_helper", hasattr(director_api, "_dry_run_default"))

    # Motion payload contract (mocked submit)
    async def _motion_payload():
        adapter = KieAdapter.__new__(KieAdapter)
        captured = {}

        async def fake_submit(payload, media_type="video", timeout=600):
            captured.update(payload)
            return {"resultJson": '{"resultUrls":["https://cdn.example.com/m.mp4"]}'}

        adapter._submit_and_poll = fake_submit  # type: ignore
        res = await adapter.generate_motion(
            image_url="https://img/a.png",
            video_url="https://vid/b.mp4",
            prompt="walk",
            model_id="seedance-2.0-fast",
            duration=3,
        )
        return captured, res

    captured, res = asyncio.run(_motion_payload())
    ok("motion_payload_imageUrl", captured.get("imageUrl") == "https://img/a.png")
    ok("motion_payload_videoUrl", captured.get("videoUrl") == "https://vid/b.mp4")
    ok("motion_result_url", bool(getattr(res, "media_url", "")))

    # Tools payload contracts
    async def _tools():
        adapter = KieAdapter.__new__(KieAdapter)
        calls = []

        async def fake_submit(payload, media_type="image", timeout=600):
            calls.append(payload)
            return {"resultJson": '{"resultUrls":["https://cdn.example.com/t.png"]}'}

        adapter._submit_and_poll = fake_submit  # type: ignore
        await adapter.upscale_image(image_url="https://img/a.png", factor="2")
        await adapter.remove_background(image_url="https://img/a.png")
        await adapter.edit_image(image_urls=["https://img/a.png"], prompt="make blue")
        return calls

    calls = asyncio.run(_tools())
    ok("tools_three_calls", len(calls) >= 3, f"n={len(calls)}")

    report["passed"] = all(c["ok"] for c in report["checks"])
    return report


def check_motion_library() -> dict:
    """Verify canonical Motion fixture files exist and are non-empty."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "fixtures" / "motion"
    still = root / "still.png"
    ref = root / "ref.mp4"
    report = {
        "mode": "motion_library",
        "fixture_dir": str(root),
        "still_ok": still.is_file() and still.stat().st_size > 100,
        "ref_ok": ref.is_file() and ref.stat().st_size > 100,
        "still_bytes": still.stat().st_size if still.is_file() else 0,
        "ref_bytes": ref.stat().st_size if ref.is_file() else 0,
        "honesty": "inputs only — not Act-One quality references",
    }
    report["passed"] = report["still_ok"] and report["ref_ok"]
    return report


def run_motion_live_optional() -> dict:
    """Optional paid motion probe using fixture files (MOTION_FIXTURE_LIVE=1)."""
    from pathlib import Path

    if os.getenv("MOTION_FIXTURE_LIVE", "").lower() not in ("1", "true", "yes", "on"):
        return {"skipped": True, "reason": "MOTION_FIXTURE_LIVE not enabled"}
    if not os.getenv("KIE_API_KEY", "").strip():
        return {"skipped": True, "reason": "KIE_API_KEY missing"}

    root = Path(__file__).resolve().parents[1] / "fixtures" / "motion"
    still = root / "still.png"
    ref = root / "ref.mp4"
    if not (still.is_file() and ref.is_file()):
        return {"ok": False, "error": "fixtures missing"}

    async def _run():
        from app.adapters.kie_adapter import KieAdapter
        from app.adapters.demo_provider import demo_mode_active

        if demo_mode_active():
            return {"ok": False, "error": "demo_mode active — refuse fake motion live"}
        adapter = KieAdapter()
        img_url = await adapter.upload_public_url(
            still.read_bytes(), filename="still.png", content_type="image/png",
        )
        vid_url = await adapter.upload_public_url(
            ref.read_bytes(), filename="ref.mp4", content_type="video/mp4",
        )
        res = await adapter.generate_motion(
            image_url=img_url,
            video_url=vid_url,
            prompt="natural body motion transfer",
            duration=2,
        )
        out = {
            "ok": bool(getattr(res, "media_url", "")),
            "media_url": getattr(res, "media_url", ""),
            "model": getattr(res, "model", ""),
            "cost": getattr(res, "cost", 0),
        }
        report_path = root / "last_run.json"
        report_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        out["report_path"] = str(report_path)
        return out

    return asyncio.run(_run())


def main() -> int:
    report = check_dry()
    lib = check_motion_library()
    report["motion_library"] = lib
    if not lib.get("passed"):
        report["passed"] = False
        report["checks"].append({
            "name": "motion_fixture_files", "ok": False,
            "detail": "run scripts/generate_motion_fixtures.py",
        })
    else:
        report["checks"].append({"name": "motion_fixture_files", "ok": True, "detail": "still+ref present"})

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if os.getenv("FIXTURE_LIVE", "").lower() in ("1", "true", "yes") or \
       os.getenv("MOTION_FIXTURE_LIVE", "").lower() in ("1", "true", "yes"):
        live = run_motion_live_optional()
        print(json.dumps({"motion_live": live}, ensure_ascii=False, indent=2))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
