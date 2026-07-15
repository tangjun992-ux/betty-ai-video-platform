"""Team shared credit pool unit tests."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.entitlements import pick_higher_role
from app.api.teams import _seat_limit_for_role, SEAT_LIMIT_BY_ROLE, DEFAULT_SEAT_LIMIT


def test_seat_limit_by_plan():
    assert _seat_limit_for_role("creator") == SEAT_LIMIT_BY_ROLE["creator"]
    assert _seat_limit_for_role("pro") == SEAT_LIMIT_BY_ROLE["pro"]
    assert _seat_limit_for_role("free") == DEFAULT_SEAT_LIMIT


def test_team_role_upgrade_still_monotonic():
    assert pick_higher_role("creator", "pro") == "pro"
