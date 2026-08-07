"""Phase 2 gateway tests — key pool, routes, LiteLLM credentials."""
from __future__ import annotations

import os
from unittest.mock import patch

from app.gateway.config import find_route, get_routes
from app.gateway.kie_keys import current_kie_api_key, kie_key_pool_status
from app.gateway.types import Capability
from app.services.director_brain import _llm_credentials


def test_lipsync_studio_route_exists():
    get_routes(reload=True)
    route = find_route(Capability.LIPSYNC, "lipsync-studio")
    assert route is not None
    assert route.chain[0].remote_model == "infinitalk/from-audio"


def test_motion_studio_route():
    route = find_route(Capability.MOTION, "motion-control-studio")
    assert route is not None


def test_kie_key_pool_single_key(monkeypatch):
    monkeypatch.setattr("app.gateway.kie_keys.settings.KIE_API_KEY", "key-primary")
    monkeypatch.setattr("app.gateway.kie_keys.settings.KIE_API_KEY_BACKUP", "")
    # Reset cycle
    import app.gateway.kie_keys as kk
    kk._cycle = None
    assert current_kie_api_key() == "key-primary"
    status = kie_key_pool_status()
    assert status["configured"] == 1
    assert status["pool_enabled"] is False


def test_kie_key_pool_round_robin(monkeypatch):
    monkeypatch.setattr("app.gateway.kie_keys.settings.KIE_API_KEY", "key-a")
    monkeypatch.setattr("app.gateway.kie_keys.settings.KIE_API_KEY_BACKUP", "key-b")
    import app.gateway.kie_keys as kk
    kk._cycle = None
    keys = [current_kie_api_key(), current_kie_api_key(), current_kie_api_key()]
    assert keys[0] != keys[1]
    assert set(keys) == {"key-a", "key-b"}
    assert kie_key_pool_status()["pool_enabled"] is True


def test_litellm_credentials_priority(monkeypatch):
    monkeypatch.setattr("app.services.director_brain.settings.LITELLM_PROXY_URL", "http://litellm:4000")
    monkeypatch.setattr("app.services.director_brain.settings.LITELLM_MASTER_KEY", "master-key")
    monkeypatch.setattr("app.services.director_brain.settings.OPENAI_API_KEY", "openai-key")
    creds = _llm_credentials()
    assert creds == ("master-key", "http://litellm:4000")
