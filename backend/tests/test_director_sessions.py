"""Director session ownership checks."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from app.api.director import _owned_session
from app.models.director_session import DirectorSession


@pytest.mark.asyncio
async def test_owned_session_rejects_other_user():
    db = AsyncMock()
    session = MagicMock(spec=DirectorSession)
    session.user_id = 5
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: session))
    with pytest.raises(HTTPException) as exc:
        await _owned_session(db, "abc123", user_id=9)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_owned_session_allows_owner():
    db = AsyncMock()
    session = MagicMock(spec=DirectorSession)
    session.user_id = 5
    db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: session))
    got = await _owned_session(db, "abc123", user_id=5)
    assert got is session
