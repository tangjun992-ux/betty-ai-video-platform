#!/usr/bin/env python3
"""Staging go-live acceptance check — Stripe + CDN + OIDC + Live KPI.

Usage:
  cd backend
  python scripts/staging_go_live_check.py
  python scripts/staging_go_live_check.py --json-only
  python scripts/staging_go_live_check.py --soft   # dev: pass if only live KPI missing
  python scripts/staging_go_live_check.py --require-webhook  # fail if webhook misconfigured

Exit code 0 when go_live_ok (or --soft rules met), else 1.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Betty staging go-live acceptance")
    parser.add_argument("--json-only", action="store_true", help="Print JSON report only")
    parser.add_argument(
        "--soft",
        action="store_true",
        help="In non-production, pass when revenue+media ready (ignore live KPI)",
    )
    parser.add_argument(
        "--require-webhook",
        action="store_true",
        help="Fail when Stripe webhook config (whsec format + endpoint) is not setup_ok",
    )
    args = parser.parse_args()

    from app.services.go_live_ready import staging_go_live_report

    report = staging_go_live_report()
    ok = bool(report.get("go_live_ok"))

    if args.require_webhook:
        wh = (report.get("stripe") or {}).get("webhook_config") or {}
        sig = (report.get("stripe") or {}).get("webhook_signature_self_test") or {}
        if not wh.get("setup_ok") or not sig.get("self_test_ok"):
            ok = False

    if args.soft:
        from app.config import settings
        if not settings.is_production:
            ok = bool(report.get("revenue_ready")) and bool(report.get("media_ready"))

    if args.json_only:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report.get("summary") or {}
        print(f"staging go-live: {'PASS' if ok else 'FAIL'}")
        print(f"  env={report.get('env')} go_live_ok={report.get('go_live_ok')}")
        print(f"  revenue={report.get('revenue_ready')} media={report.get('media_ready')} sso={report.get('sso_ready')}")
        print(f"  live_kpi={report.get('live_kpi_ready')} blockers={summary.get('blocker_count', 0)}")
        for step in report.get("next_steps") or []:
            print(f"  → {step}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
