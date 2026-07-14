"""Trust & parity requirements — automated checks."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_prod_subscribe_blocked():
    from fastapi import HTTPException
    from app.api import pricing as pricing_mod
    from app.api import models_info as models_mod

    from app.config import settings

    with patch.object(settings, "ENV", "production"):
        with pytest.raises(HTTPException) as exc:
            await pricing_mod.subscribe("starter", user_id=1, db=AsyncMock())
        assert exc.value.status_code == 404

    with patch.object(settings, "ENV", "production"):
        with pytest.raises(HTTPException) as exc:
            await models_mod.subscribe("starter", user_id=1, db=AsyncMock())
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_progress_denied_without_owner_in_prod():
    from app.api.director import run_progress
    from fastapi import HTTPException
    from app.config import settings

    fake_state = {"job_id": "abc", "status": "running", "done": False}
    with patch("app.tasks.director_tasks.read_progress", return_value=fake_state):
        with patch.object(settings, "ENV", "production"):
            with pytest.raises(HTTPException) as exc:
                await run_progress("abc", user_id=42)
            assert exc.value.status_code == 403


def test_entitlements_studio_gate():
    from app.services.entitlements import has_studio, lipsync_cost, motion_cost
    assert not has_studio("guest")
    assert has_studio("personal")
    assert lipsync_cost("studio") > lipsync_cost("demo")
    assert motion_cost("studio") > motion_cost("demo")


def test_demo_tag_marks_results():
    from app.services.demo_tag import tag_result
    with patch("app.services.demo_tag.demo_mode_active", return_value=True):
        out = tag_result({"url": "/x", "type": "image"})
        assert out["demo"] is True
