#!/usr/bin/env python3
"""Staging go-live acceptance check — Stripe + CDN + OIDC + Live KPI.

Usage:
  cd backend
  python scripts/staging_go_live_check.py
  python scripts/staging_go_live_check.py --json-only
  python scripts/staging_go_live_check.py --soft   # dev: pass if only live KPI missing
  python scripts/staging_go_live_check.py --strict # require all required checks incl. live KPI when available
  python scripts/staging_go_live_check.py --require-webhook  # fail if webhook misconfigured
  python scripts/staging_go_live_check.py --live     # run live KPI smoke first (MODEL_SMOKE_LIVE*)

Exit code 0 when go_live_ok (or --soft rules met), else 1.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _live_smoke_enabled() -> bool:
    return os.getenv("MODEL_SMOKE_LIVE", "").lower() in ("1", "true", "yes") or os.getenv(
        "MODEL_SMOKE_LIVE_VIDEO", ""
    ).lower() in ("1", "true", "yes")


def main() -> int:
    parser = argparse.ArgumentParser(description="Betty staging go-live acceptance")
    parser.add_argument("--json-only", action="store_true", help="Print JSON report only")
    parser.add_argument(
        "--soft",
        action="store_true",
        help="In non-production, pass when revenue+media ready (ignore live KPI)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Use staging acceptance scorecard (all required checks + live KPI when available)",
    )
    parser.add_argument(
        "--require-webhook",
        action="store_true",
        help="Fail when Stripe webhook config (whsec format + signature self-test) is not ok",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live KPI smoke before check (requires MODEL_SMOKE_LIVE or MODEL_SMOKE_LIVE_VIDEO)",
    )
    args = parser.parse_args()

    last_smoke = None
    if args.live:
        if _live_smoke_enabled():
            from app.services.model_smoke import run_live_kpi_smoke

            last_smoke = run_live_kpi_smoke()
        else:
            print("warning: --live skipped (set MODEL_SMOKE_LIVE=1 or MODEL_SMOKE_LIVE_VIDEO=1)", file=sys.stderr)

    if args.strict:
        from app.services.go_live_ready import staging_acceptance_scorecard

        scorecard = staging_acceptance_scorecard(last_smoke=last_smoke, strict=True)
        report = scorecard
        ok = bool(scorecard.get("acceptance_ok"))
    else:
        from app.services.go_live_ready import staging_go_live_report

        report = staging_go_live_report(last_smoke=last_smoke)
        ok = bool(report.get("go_live_ok"))

    if args.require_webhook:
        stripe = report.get("stripe") or {}
        wh = stripe.get("webhook_config") or {}
        sig = stripe.get("webhook_signature_self_test") or {}
        if not wh.get("setup_ok") or not sig.get("self_test_ok"):
            ok = False

    if args.soft:
        from app.config import settings
        if not settings.is_production:
            ok = bool(report.get("revenue_ready")) and bool(report.get("media_ready"))

    if args.json_only:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if args.strict:
            print(f"staging acceptance: {'PASS' if ok else 'FAIL'}")
            print(f"  score={report.get('score_pct')}% required={report.get('required_pass')}/{report.get('required_total')}")
            for c in report.get("checks") or []:
                print(f"  [{c.get('status', '?'):4}] {c.get('label')}")
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
