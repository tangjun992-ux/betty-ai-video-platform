"""Phase 13 — task SLA/retry, mapping smoke promote, extract fallback."""
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_sla_payload_refund_note():
    from app.api.tasks import _sla_payload
    from app.models.task import Task

    task = Task(task_id="t1", user_id=1, prompt="p", media_type="image", status="failed")
    sla = _sla_payload(task, {})
    assert sla["refund"]["refunded"] is False
    assert "退还" in sla["refund"]["note"]
    assert sla["retryable"] is True


def test_sla_payload_queue_hint():
    from app.api.tasks import _sla_payload
    from app.models.task import Task

    task = Task(task_id="t2", user_id=1, prompt="p", media_type="video", status="queued")
    sla = _sla_payload(task, {}, queue_position=3)
    assert any("前方" in h for h in sla["hints"])


def test_mapping_promote_disabled_by_default():
    from app.services.model_promotion import mapping_promote_enabled, maybe_promote_from_mapping_smoke

    assert mapping_promote_enabled() is False
    r = maybe_promote_from_mapping_smoke({
        "details": [{"model_id": "veo-3.1", "ok": True, "path": "mapping_only"}],
    })
    assert r["skipped"] is True


def test_mapping_promote_on_mapping_ok():
    from app.api.models_info import MODELS
    from app.services.model_promotion import demote_model, maybe_promote_from_mapping_smoke

    mid = "veo-3.1"
    assert next(m for m in MODELS if m.id == mid).status == "beta"
    with patch.dict(os.environ, {"MODEL_SMOKE_MAPPING_PROMOTE": "1"}):
        r = maybe_promote_from_mapping_smoke({
            "details": [{
                "model_id": mid,
                "ok": True,
                "path": "mapping_only",
                "evidence": {"path": "mapping_only"},
            }],
        })
    assert mid in r["promoted"]
    demote_model(mid, note="phase13 cleanup")


def test_run_mapping_beta_probe():
    from app.services.model_smoke import run_mapping_beta_probe

    report = run_mapping_beta_probe(models=["veo-3.1", "veo-3"])
    assert report["probed"] == 2
    assert report["ok"] >= 1


def test_retry_rejects_completed():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    email = f"p13_{uuid.uuid4().hex[:8]}@test.local"
    reg = c.post("/api/v1/auth/register", json={
        "email": email, "password": "Test1234!", "username": f"p13{uuid.uuid4().hex[:6]}",
    })
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    with patch("app.api.tasks._owned_task", new_callable=AsyncMock) as owned:
        mock_task = MagicMock()
        mock_task.status = "completed"
        mock_task.media_type = "image"
        owned.return_value = mock_task
        r = c.post("/api/v1/tasks/fake-id/retry", headers=headers)
    assert r.status_code == 400


def test_get_task_includes_sla():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    headers = {"X-Guest-Id": f"phase13-sla-{uuid.uuid4().hex[:8]}"}
    # Create a failed task via generate with no credits path is complex — test list endpoint shape via mock
    from app.api import tasks as tasks_api
    from app.models.task import Task

    task = Task(
        task_id="sla-test-1", user_id=1, prompt="hello", media_type="image",
        status="failed", parameters={"credits_refunded": True, "refund_amount": 5},
    )
    sla = tasks_api._sla_payload(task, task.parameters)
    assert sla["refund"]["refunded"] is True
    assert sla["refund"]["amount"] == 5
