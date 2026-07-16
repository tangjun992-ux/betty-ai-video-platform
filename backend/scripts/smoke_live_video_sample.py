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
    report = run_live_video_sample(args.models)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["outframe_ok"] > 0 or report["probed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
