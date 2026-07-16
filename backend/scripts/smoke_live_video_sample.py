#!/usr/bin/env python3
"""Paid live-video sample smoke for ops (P0).

Runs a small, explicit subset — default Seedance-fast + Kling turbo — so
weekly cost stays bounded while still proving out-frame video.

Usage:
  cd backend
  MODEL_SMOKE_LIVE_VIDEO=1 python scripts/smoke_live_video_sample.py
  python scripts/smoke_live_video_sample.py --models seedance-2.0-fast
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    from app.services.model_smoke import DEFAULT_LIVE_VIDEO_SAMPLE, run_live_video_sample

    parser = argparse.ArgumentParser(description="Sample live video smoke")
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_LIVE_VIDEO_SAMPLE),
        help="Active video model ids to probe (paid)",
    )
    args = parser.parse_args()

    os.environ.setdefault("MODEL_SMOKE_LIVE_VIDEO", "1")
    # Detect "defaults" vs explicit --models: argparse always fills default list.
    explicit = any(a == "--models" for a in sys.argv[1:])
    report = run_live_video_sample(args.models)
    # If primary set yields <2 outframes, try stable Seedance pair once (weekly SLO ≥2).
    if report.get("outframe_ok", 0) < 2 and not explicit:
        from app.services.model_smoke import STABLE_LIVE_VIDEO_FALLBACK
        fb = run_live_video_sample(list(STABLE_LIVE_VIDEO_FALLBACK))
        report["fallback"] = fb
        # Prefer unique model successes across primary + fallback
        ok_ids = {
            d.get("model_id")
            for d in (report.get("details") or [])
            if d.get("ok") and (d.get("evidence") or {}).get("path") == "live_video"
        }
        ok_ids |= {
            d.get("model_id")
            for d in (fb.get("details") or [])
            if d.get("ok") and (d.get("evidence") or {}).get("path") == "live_video"
        }
        report["outframe_ok_combined"] = len({x for x in ok_ids if x})
        report["outframe_models"] = sorted(ok_ids)
    else:
        report["outframe_ok_combined"] = int(report.get("outframe_ok") or 0)
        report["outframe_models"] = [
            d.get("model_id")
            for d in (report.get("details") or [])
            if d.get("ok") and (d.get("evidence") or {}).get("path") == "live_video"
        ]
    ok_n = int(report.get("outframe_ok_combined") or report.get("outframe_ok") or 0)
    report["slo_ge_2"] = ok_n >= 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok_n >= 1 or report.get("probed") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
