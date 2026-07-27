"""Billing: team subscription pool + seat SKU resolution."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.billing import _resolve_purchase, CheckoutRequest, TEAM_SEAT_SKUS
from app.services.credits import TEAM_SUBSCRIPTION_PLANS


def test_team_subscription_plans():
    assert "creator" in TEAM_SUBSCRIPTION_PLANS
    assert "pro" in TEAM_SUBSCRIPTION_PLANS


def test_resolve_team_seats_purchase():
    req = CheckoutRequest(kind="team_seats", id="seat_monthly", team_id="team-abc", quantity=2)
    credits, price, label, extra = _resolve_purchase(req)
    assert credits == 0
    assert price == round(TEAM_SEAT_SKUS["seat_monthly"]["price_usd"] * 2, 2)
    assert extra["team_id"] == "team-abc"
    assert extra["seats"] == 2


def test_resolve_team_seats_requires_team_id():
    req = CheckoutRequest(kind="team_seats", id="seat_monthly")
    with pytest.raises(Exception):
        _resolve_purchase(req)
