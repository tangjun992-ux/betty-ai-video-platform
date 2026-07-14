"""Director async progress must be scoped to the job owner."""
import pytest
from unittest.mock import patch

from fastapi import HTTPException


@pytest.mark.asyncio
async def test_run_progress_forbidden_for_other_user():
    from app.api.director import run_progress

    fake_state = {"job_id": "abc", "user_id": 42, "status": "running", "done": False}
    with patch("app.tasks.director_tasks.read_progress", return_value=fake_state):
        with pytest.raises(HTTPException) as exc:
            await run_progress("abc", user_id=99)
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_run_progress_allowed_for_owner():
    from app.api.director import run_progress

    fake_state = {"job_id": "abc", "user_id": 42, "status": "running", "done": False}
    with patch("app.tasks.director_tasks.read_progress", return_value=fake_state):
        out = await run_progress("abc", user_id=42)
        assert out["user_id"] == 42
