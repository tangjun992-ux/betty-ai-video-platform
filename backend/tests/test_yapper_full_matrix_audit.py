"""Smoke: full-matrix audit script exits 0 in contract-only mode."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_yapper_full_matrix_audit_contract():
    script = ROOT / "scripts" / "yapper_full_matrix_audit.py"
    assert script.is_file()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:] + proc.stdout[-2000:]
    report = json.loads(proc.stdout)
    assert report["suite"] == "yapper_full_matrix_audit"
    assert report["scoring"]["contract_hard_ok"] == report["scoring"]["contract_hard_total"]
    assert report["scoring"]["contract_pass_pct"] == 100.0
    out = ROOT / "fixtures" / "audit" / "yapper_full_matrix_latest.json"
    assert out.is_file()
