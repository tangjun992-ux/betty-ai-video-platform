"""Model catalog governance: keep unverified (beta) models out of production."""
from unittest.mock import patch

import pytest


def test_verified_helpers():
    from app.api.models_info import verified_model_ids, is_verified, default_verified_model

    vids = verified_model_ids()
    assert vids, "expected at least one verified model"
    # Known verified anchors
    assert "gpt-image-2" in vids
    assert "seedance-2.0" in vids
    for vid in vids:
        assert is_verified(vid)
    assert not is_verified("definitely-not-a-real-model")

    assert is_verified(default_verified_model("image"))
    assert is_verified(default_verified_model("video"))


@pytest.mark.asyncio
async def test_list_models_default_is_verified_only():
    from app.api import models_info

    res = await models_info.list_models()
    assert res["models"], "default listing should not be empty"
    assert all(m["status"] == "active" for m in res["models"]), (
        "default listing must be verified-only"
    )
    assert all(m["verified"] is True for m in res["models"])
    assert res["beta_count"] >= 1  # beta still reported separately


@pytest.mark.asyncio
async def test_include_beta_blocked_in_production():
    from app.api import models_info
    from app.config import settings

    with patch.object(settings, "ENV", "production"):
        res = await models_info.list_models(include_beta=True)
    # Even with include_beta, production must not bundle beta into primary array
    assert all(m["status"] == "active" for m in res["models"])


@pytest.mark.asyncio
async def test_status_beta_returns_only_beta():
    from app.api import models_info

    res = await models_info.list_models(status="beta")
    assert res["models"]
    assert all(m["status"] != "active" for m in res["models"])


def test_router_downgrades_beta_model_in_production():
    from app.router import PromptRouter
    from app.config import settings

    router = PromptRouter()
    analysis = router.analyze("a cinematic product shot")

    # Pick a known beta model id from the catalog
    from app.api.models_info import MODELS
    beta_id = next(m.id for m in MODELS if m.status != "active")

    with patch.object(settings, "ENV", "production"):
        score = router.select_model(analysis, user_model=beta_id)
    from app.api.models_info import is_verified
    assert is_verified(score.model_id), (
        f"production must not select beta model {beta_id}, got {score.model_id}"
    )


def test_router_honours_verified_model_in_production():
    from app.router import PromptRouter
    from app.config import settings

    router = PromptRouter()
    analysis = router.analyze("a cinematic product shot")
    with patch.object(settings, "ENV", "production"):
        score = router.select_model(analysis, user_model="gpt-image-2")
    assert score.model_id == "gpt-image-2"


def test_router_honours_beta_in_dev():
    from app.router import PromptRouter

    router = PromptRouter()
    analysis = router.analyze("a cinematic product shot")
    from app.api.models_info import MODELS
    beta_id = next(m.id for m in MODELS if m.status != "active")
    score = router.select_model(analysis, user_model=beta_id)
    assert score.model_id == beta_id  # dev/demo honours the explicit pick
