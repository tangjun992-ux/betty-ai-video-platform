#!/usr/bin/env python3
"""Execute automatable staging runbook self-tests.

Usage:
  cd backend
  python scripts/staging_runbook_execute.py
  python scripts/staging_runbook_execute.py --json-only
  python scripts/staging_runbook_execute.py --strict
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def _run(strict: bool) -> dict:
    import logging
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    from app.db import async_session
    from app.services.staging_runbook_exec import execute_staging_runbook

    async with async_session() as db:
        report = await execute_staging_runbook(db, strict=strict)
        await db.commit()
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Betty staging runbook auto-execute")
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    report = asyncio.run(_run(args.strict))
    ok = bool(report.get("execute_ok"))

    if args.json_only:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"runbook execute: {'PASS' if ok else 'FAIL'}")
        print(f"  passed {report.get('steps_passed')}/{report.get('steps_executed')} executed")
        for r in report.get("results") or []:
            if not r.get("executed"):
                continue
            mark = "✓" if r.get("ok") else "✗"
            print(f"  [{mark}] {r.get('title')} ({r.get('duration_ms')}ms)")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
