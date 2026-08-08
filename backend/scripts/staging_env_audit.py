#!/usr/bin/env python3
"""Audit staging environment variables — show gaps before go-live.

Usage:
  cd backend
  python scripts/staging_env_audit.py
  python scripts/staging_env_audit.py --json-only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    parser = argparse.ArgumentParser(description="Betty staging env audit")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    from app.services.staging_env import staging_env_audit

    audit = staging_env_audit()
    ok = not audit.get("missing_required")

    if args.json_only:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    else:
        print(f"staging env audit: {'PASS' if ok else 'FAIL'} env={audit.get('env')}")
        if audit.get("missing_required"):
            print(f"  missing required: {', '.join(audit['missing_required'])}")
        for g, info in (audit.get("groups") or {}).items():
            print(f"  [{g}] {info.get('configured')}/{info.get('total')} configured")
        if not ok:
            print(f"\n  hint: {audit.get('env_file_hint')}")
            print(f"  demo: {audit.get('demo_export_snippet')}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
