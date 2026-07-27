#!/usr/bin/env python3
"""Ops: smoke active models (mapping|live|live_video).

Usage:
  cd backend && python scripts/smoke_active_models.py
  MODEL_SMOKE_LIVE=1 python scripts/smoke_active_models.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.model_smoke import run_active_smoke, smoke_mode


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else smoke_mode()
    result = run_active_smoke(mode=mode)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if not result.get("failed") else 1)


if __name__ == "__main__":
    main()
