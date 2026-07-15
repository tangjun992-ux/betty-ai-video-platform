"""Subscription plan → role mapping (P1 entitlements)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.entitlements import (
    plan_subscription_role,
    pick_higher_role,
    rank_role,
    has_studio,
)


def test_plan_subscription_role_mapping():
    assert plan_subscription_role("personal") == "personal"
    assert plan_subscription_role("creator") == "creator"
    assert plan_subscription_role("pro") == "pro"
    assert plan_subscription_role("starter") == "free"
    assert plan_subscription_role("unknown") is None


def test_pick_higher_role_only_upgrades():
    assert pick_higher_role("free", "personal") == "personal"
    assert pick_higher_role("personal", "creator") == "creator"
    assert pick_higher_role("pro", "personal") == "pro"
    assert pick_higher_role("creator", "personal") == "creator"


def test_studio_tier_after_personal():
    assert not has_studio("free")
    assert has_studio(pick_higher_role("free", "personal"))


def test_role_rank_order():
    assert rank_role("pro") > rank_role("creator") > rank_role("personal") > rank_role("free")
