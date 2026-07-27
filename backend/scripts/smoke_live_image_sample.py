#!/usr/bin/env python3
"""Paid live-image sample smoke for active image SKUs (Yapper parity P0).

Usage:
  cd backend
  MODEL_SMOKE_LIVE=1 python scripts/smoke_live_image_sample.py
  python scripts/smoke_live_image_sample.py --models gpt-image-2 nano-banana
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    from app.services.model_smoke import DEFAULT_LIVE_IMAGE_SAMPLE, run_live_image_sample

    parser = argparse.ArgumentParser(description="Sample live image smoke")
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_LIVE_IMAGE_SAMPLE),
        help="Active image model ids to probe (paid)",
    )
    args = parser.parse_args()

    os.environ.setdefault("MODEL_SMOKE_LIVE", "1")
    report = run_live_image_sample(args.models)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # Soft gate: pass if ≥50% outframe or zero probed
    ok = report["outframe_ok"]
    probed = report["probed"]
    return 0 if probed == 0 or ok * 2 >= probed else 1


if __name__ == "__main__":
    raise SystemExit(main())
