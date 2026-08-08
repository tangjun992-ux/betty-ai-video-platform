#!/usr/bin/env python3
"""Print staging go-live runbook — ordered steps with commands.

Usage:
  cd backend
  python scripts/staging_runbook.py
  python scripts/staging_runbook.py --json-only
  python scripts/staging_runbook.py --host staging.example.com --https
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Betty staging go-live runbook")
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument("--host", default="localhost:8000", help="API host for Stripe CLI forward URL")
    parser.add_argument("--https", action="store_true", help="Use https in forward URL")
    args = parser.parse_args()

    from app.services.go_live_ready import staging_runbook

    rb = staging_runbook(host=args.host)
    if args.https:
        from app.services.stripe_ready import stripe_cli_webhook_guide
        rb["stripe_cli"] = stripe_cli_webhook_guide(host=args.host, use_https=True)

    if args.json_only:
        print(json.dumps(rb, ensure_ascii=False, indent=2))
        return 0

    print(f"staging runbook · {rb.get('steps_done')}/{rb.get('steps_total')} done · score {rb.get('score_pct')}%")
    print(f"acceptance_ok={rb.get('acceptance_ok')} env={rb.get('env')}")
    for step in rb.get("steps") or []:
        mark = {"done": "✓", "pending": "○", "skipped": "—"}.get(step.get("status", "?"), "?")
        print(f"\n[{mark}] {step.get('title')} ({step.get('id')})")
        for cmd in step.get("commands") or []:
            print(f"    $ {cmd}")
    cli = rb.get("stripe_cli") or {}
    if cli.get("listen_command"):
        print(f"\nStripe CLI: {cli['listen_command']}")
    return 0 if rb.get("acceptance_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
