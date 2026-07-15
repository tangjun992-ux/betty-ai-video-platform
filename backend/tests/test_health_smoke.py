"""Model health smoke + quarantine tests."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.model_health import model_health


def test_quarantine_blocks_routable():
    model_health.reset("smoke-test-model")
    assert model_health.is_routable("smoke-test-model")
    model_health.set_quarantine("smoke-test-model", reason="smoke failed", ttl=60)
    assert model_health.is_quarantined("smoke-test-model")
    assert not model_health.is_routable("smoke-test-model")
    model_health.clear_quarantine("smoke-test-model")
    assert model_health.is_routable("smoke-test-model")


def test_smoke_task_registered():
    from celery_app import app
    app.loader.import_default_modules()
    assert "app.tasks.health_tasks.smoke_active_models" in app.tasks
