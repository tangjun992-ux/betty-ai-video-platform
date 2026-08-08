"""Phase 23 — staging report, CLI check, admin export."""
import json
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_staging_go_live_report_shape():
    from app.services.go_live_ready import staging_go_live_report

    r = staging_go_live_report(last_smoke=None)
    assert "generated_at" in r
    assert "summary" in r
    assert "next_steps" in r
    assert "commands" in r
    assert "dimensions" in r["summary"]


def test_staging_report_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/staging-report")
    assert r.status_code == 200
    assert "next_steps" in r.json()


def test_staging_go_live_check_script_runs():
    import subprocess
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "scripts" / "staging_go_live_check.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--json-only", "--soft"],
        capture_output=True,
        text=True,
        cwd=str(script.parents[1]),
    )
    assert proc.returncode in (0, 1)
    data = json.loads(proc.stdout)
    assert "go_live_ok" in data


def test_admin_go_live_export():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import require_admin

    c = TestClient(app)
    app.dependency_overrides[require_admin] = lambda: AsyncMock(id=1)
    try:
        r = c.get("/api/v1/admin/model-health/go-live-export")
        assert r.status_code == 200
        assert r.json().get("generated_at")
    finally:
        app.dependency_overrides.pop(require_admin, None)


def test_staging_go_live_check_soft_dev(monkeypatch):
    import importlib.util
    from pathlib import Path

    from app.config import settings

    monkeypatch.setattr(settings, "ENV", "development")

    script = Path(__file__).resolve().parents[1] / "scripts" / "staging_go_live_check.py"
    spec = importlib.util.spec_from_file_location("staging_go_live_check", script)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    with patch("app.services.go_live_ready.staging_go_live_report") as mock_report:
        mock_report.return_value = {
            "go_live_ok": False,
            "revenue_ready": True,
            "media_ready": True,
            "env": "development",
            "summary": {"blocker_count": 0},
            "next_steps": [],
        }
        spec.loader.exec_module(mod)
        monkeypatch.setattr(sys, "argv", ["staging_go_live_check.py", "--soft"])
        assert mod.main() == 0


def test_staging_go_live_e2e_spec_exists():
    from pathlib import Path
    assert (Path(__file__).resolve().parents[2] / "frontend" / "e2e" / "staging-go-live.spec.ts").is_file()
