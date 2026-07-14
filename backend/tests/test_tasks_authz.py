"""Task API must scope list/detail/cancel to the effective user."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.api.tasks import list_tasks, get_task_status, cancel_task
from app.models.task import Task


def _task(task_id: str, user_id: int) -> Task:
    t = MagicMock(spec=Task)
    t.task_id = task_id
    t.user_id = user_id
    t.status = "queued"
    t.prompt = "test"
    t.media_type = "image"
    t.selected_model = "gpt-image-2"
    t.progress = 0
    t.current_stage = None
    t.results = None
    t.created_at = None
    t.completed_at = None
    t.error_message = None
    t.parameters = {}
    t.started_at = None
    t.estimated_completion = None
    t.actual_cost = None
    return t


@pytest.mark.asyncio
async def test_list_tasks_filters_by_user_id():
    db = AsyncMock()
    owned = _task("t1", 42)
    # count query
    db.execute = AsyncMock(side_effect=[
        MagicMock(scalar=lambda: 1),
        MagicMock(scalars=lambda: MagicMock(all=lambda: [owned])),
    ])
    out = await list_tasks(user_id=42, limit=50, offset=0, db=db)
    assert out["total"] == 1
    assert out["tasks"][0]["task_id"] == "t1"


@pytest.mark.asyncio
async def test_get_task_status_forbidden_for_other_user():
    from fastapi import HTTPException

    db = AsyncMock()
    other = _task("t2", 99)
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: other))
    with pytest.raises(HTTPException) as exc:
        await get_task_status("t2", user_id=1, db=db)
    assert exc.value.status_code == 403
