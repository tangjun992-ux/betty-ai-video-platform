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


def main() -> int:
    report = check_dry()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if os.getenv("FIXTURE_LIVE", "").lower() in ("1", "true", "yes"):
        print(json.dumps({"note": "FIXTURE_LIVE set — use smoke_live_video_sample / admin smoke for paid E2E"}, ensure_ascii=False))
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
