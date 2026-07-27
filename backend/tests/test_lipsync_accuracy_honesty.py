"""Digital-human / lipsync honesty: mode tags + voice tier copy."""
from pathlib import Path

from fastapi.testclient import TestClient


def test_lipsync_voices_tiers_do_not_claim_generic_standard():
    from app.main import app

    r = TestClient(app).get("/api/v1/lipsync/voices")
    assert r.status_code == 200
    body = r.json()
    demo = (body.get("tiers") or {}).get("demo") or {}
    desc = (demo.get("description") or "")
    desc_l = desc.lower()
    assert "kling" in desc_l or "ken burns" in desc_l or "预览" in desc
    assert "标准唇形同步" not in desc
    assert body.get("voice_note")


def test_lipsync_task_source_tags_ken_burns_and_kling_modes():
    src = Path(__file__).resolve().parents[1] / "app" / "tasks" / "lipsync_tasks.py"
    text = src.read_text(encoding="utf-8")
    assert '"mode": "ken_burns"' in text
    assert '"mode": "kling_avatar"' in text
    assert "offline_preview_not_lipsync" in text


def test_accuracy_eval_script_and_report_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "scripts" / "lipsync_accuracy_eval.py").is_file()
    report = root / "fixtures" / "audit" / "lipsync_accuracy_latest.json"
    assert report.is_file(), "run scripts/lipsync_accuracy_eval.py before commit"
    data = __import__("json").loads(report.read_text(encoding="utf-8"))
    assert data.get("layers", {}).get("A_offline_demo", {}).get("ok") is True
    summary = data.get("professional_summary") or {}
    assert summary.get("offline_demo_is_digital_human") is False
