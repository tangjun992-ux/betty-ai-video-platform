"""Legacy guest pool migration — isolated per-browser guests."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.guest import migrate_legacy_guest_pool, LEGACY_POOL_USERNAME


@pytest.mark.asyncio
async def test_migrate_legacy_guest_pool_reassigns_zero_rows():
    mock_db = AsyncMock()
    update_result = MagicMock()
    update_result.rowcount = 2
    mock_db.execute = AsyncMock(return_value=update_result)
    mock_db.commit = AsyncMock()

    with patch("app.services.guest.get_or_create_legacy_pool_user", return_value=99):
        moved = await migrate_legacy_guest_pool(mock_db)

    assert moved == 12  # 6 tables × 2 rows each
    assert mock_db.execute.await_count == 6
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_migrate_legacy_guest_pool_skips_commit_when_nothing_moved():
    mock_db = AsyncMock()
    update_result = MagicMock()
    update_result.rowcount = 0
    mock_db.execute = AsyncMock(return_value=update_result)

    with patch("app.services.guest.get_or_create_legacy_pool_user", return_value=99):
        moved = await migrate_legacy_guest_pool(mock_db)

    assert moved == 0
    mock_db.commit.assert_not_awaited()


def test_legacy_pool_username_constant():
    assert LEGACY_POOL_USERNAME == "legacy_pool"
