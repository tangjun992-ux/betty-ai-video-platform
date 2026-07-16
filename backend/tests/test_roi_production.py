"""ROI iteration tests — catalog, rollover, websocket redis channel."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.models_info import MODELS, verified_model_ids
from app.services.model_catalog import catalog_integrity, GATEWAY_VERIFIED_IDS, should_be_active
from app.services.credits import apply_plan_credit_rollover
from app.models.billing import UserBalance
from app.api.websocket import PROGRESS_CHANNEL


def test_active_models_cover_gateway_verified_set():
    active = {m.id for m in MODELS if m.status == "active"}
    # Every gateway-verified catalog entry must be active
    in_catalog = {m.id for m in MODELS}
    expected = GATEWAY_VERIFIED_IDS & in_catalog
    missing = expected - active
    assert not missing, f"verified models not active: {missing}"
    assert len(active) >= 8


def test_catalog_integrity_report():
    report = catalog_integrity()
    assert report["active_count"] >= 8
    assert report["total"] == len(MODELS)
    assert should_be_active("nano-banana")
    assert not should_be_active("midjourney-v7")


def test_plan_credit_rollover_caps_at_2x():
    bal = UserBalance(user_id=1, credits=5000, daily_credits=0, plan_credits=0)
    # Month 1
    apply_plan_credit_rollover(bal, 1000)
    assert bal.plan_credits == 1000
    assert bal.credits == 5000  # purchased untouched
    # Month 2 with unused → 2000 (2×)
    apply_plan_credit_rollover(bal, 1000)
    assert bal.plan_credits == 2000
    # Month 3 still capped at 2×
    apply_plan_credit_rollover(bal, 1000)
    assert bal.plan_credits == 2000
    # Partial spend then renew
    bal.plan_credits = 400
    apply_plan_credit_rollover(bal, 1000)
    assert bal.plan_credits == 1400


def test_websocket_progress_channel_name():
    assert PROGRESS_CHANNEL == "betty:task-progress"


def test_pricing_features_no_longer_overclaim():
    from app.api.pricing import PLANS
    for plan in PLANS:
        names = " ".join(f.name for f in plan.features)
        assert "16+" not in names
        assert "23+" not in names
        assert "已验证" in names
