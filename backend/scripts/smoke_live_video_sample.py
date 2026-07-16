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

DEFAULT_MODELS = ("seedance-2.0-fast", "kling-2.5-turbo")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sample live video smoke")
    parser.add_argument(
        "--models",
        nargs="+",
        default=list(DEFAULT_MODELS),
        help="Active video model ids to probe (paid)",
    )
    args = parser.parse_args()

    os.environ.setdefault("MODEL_SMOKE_LIVE_VIDEO", "1")
    from app.services.model_smoke import probe_model, save_last_smoke
    from app.api.models_info import MODELS
    from app.services.model_health import model_health

    by_id = {m.id: m for m in MODELS}
    report = {
        "mode": "live_video_sample",
        "probed": 0,
        "ok": 0,
        "outframe_ok": 0,
        "outframe_skipped": 0,
        "failed": [],
        "quarantined": [],
        "skipped": [],
        "details": [],
    }
    for mid in args.models:
        m = by_id.get(mid)
        if not m:
            report["failed"].append(mid)
            report["details"].append({"model_id": mid, "ok": False, "error": "not in catalog"})
            continue
        report["probed"] += 1
        media = list(m.capabilities.media_types or ["video"])
        probe = probe_model(mid, media, mode="live_video")
        report["details"].append({"model_id": mid, **probe})
        path = (probe.get("evidence") or {}).get("path") or ""
        if probe["ok"] and path == "live_video":
            model_health.record_success(mid, probe.get("latency_ms") or 0)
            model_health.clear_quarantine(mid)
            report["ok"] += 1
            report["outframe_ok"] += 1
        elif probe["ok"]:
            report["skipped"].append(mid)
            report["outframe_skipped"] += 1
        else:
            from app.services.model_health import quarantine_ttl_for_reason
            model_health.record_failure(mid, probe.get("error") or "fail", retryable=True)
            model_health.set_quarantine(
                mid,
                reason=probe.get("error") or "live_video sample failed",
                ttl=quarantine_ttl_for_reason(probe.get("error") or ""),
            )
            report["failed"].append(mid)
            report["quarantined"].append(mid)

    import time
    report["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_last_smoke(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # Exit non-zero only when every sample failed outframe
    return 0 if report["outframe_ok"] > 0 or report["probed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
