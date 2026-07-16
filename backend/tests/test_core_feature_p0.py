"""P0 core-feature fixes: public API, timeline Task row, lipsync model_name, edit metering."""
import inspect
import os
import sys
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_execute_generation_exported_without_request():
    """Public API must call execute_generation — not FastAPI Depends-bound submit."""
    from app.api.generate import execute_generation
    from app.api import developer as developer_mod

    sig = inspect.signature(execute_generation)
    assert "request" not in sig.parameters
    assert "user_id" in sig.parameters
    assert "team_id" in sig.parameters

    assert developer_mod.execute_generation is execute_generation
    src = inspect.getsource(developer_mod.public_generate)
    assert "execute_generation" in src
    assert "submit_generation" not in src


def test_timeline_render_creates_task_row():
    """Async timeline render must persist a Task before Celery dispatch."""
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    headers = {"X-Guest-Id": "p0-timeline-render-guest"}

    save = c.post(
        "/api/v1/timeline/projects",
        headers=headers,
        json={
            "name": "p0-render",
            "clips": [{"url": "https://example.com/a.mp4", "start": 0, "end": 2}],
        },
    )
    assert save.status_code in (200, 201), save.text
    project_id = save.json()["id"]

    fake_celery = MagicMock(id="celery-fake-1")
    with patch("app.services.credits.deduct_credits", new_callable=AsyncMock) as mock_deduct, \
         patch("app.tasks.timeline_tasks.process_timeline_render") as mock_task:
        mock_deduct.return_value = True
        mock_task.delay = MagicMock(return_value=fake_celery)
        rend = c.post(
            "/api/v1/timeline/render",
            headers=headers,
            json={"project_id": project_id, "quality": "draft", "format": "mp4"},
        )

    assert rend.status_code in (200, 202), rend.text
    data = rend.json()
    task_id = data["task_id"]
    assert data.get("poll_url", "").endswith(task_id)

    poll = c.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert poll.status_code == 200, poll.text
    body = poll.json()
    assert body.get("task_id") == task_id or body.get("status") in (
        "queued", "generating", "completed", "failed",
    )


def test_lipsync_send_task_uses_model_name():
    """Studio tier must enqueue lipsync-studio, not Form default 'auto'."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "app" / "api" / "lipsync.py"
    text = src.read_text(encoding="utf-8")
    assert "voice_id, model_name]" in text
    send_chunk = text.split("send_task")[1][:500]
    assert "model_name" in send_chunk
    assert "voice_id, model]" not in send_chunk


def test_edit_tool_requires_metering_deps():
    """Image tools must resolve user_id and deduct credits."""
    from app.api.generate import edit_image_tool

    sig = inspect.signature(edit_image_tool)
    assert "user_id" in sig.parameters
    assert "db" in sig.parameters
    assert "request" in sig.parameters
