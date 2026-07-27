"""Moderation gates on speech / enhance / ideate return structured errors."""
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.services.moderation import moderation_reject, check_prompt


@pytest.fixture
def client():
    return TestClient(app)


def test_moderation_reject_payload():
    r = check_prompt("explicit nsfw nude content")
    exc = moderation_reject(r)
    detail = exc.detail
    assert detail["code"] == "CONTENT_MODERATION_BLOCKED"
    assert detail["moderation"]["allowed"] is False
    assert detail["moderation"]["category"] == "sexual"


def test_speech_blocked_with_structured_detail(client):
    res = client.post("/api/v1/generate/speech", json={"text": "nude explicit porn"})
    assert res.status_code == 400
    body = res.json()
    detail = body.get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "CONTENT_MODERATION_BLOCKED"
        assert detail.get("moderation", {}).get("allowed") is False


def test_enhance_blocked_with_structured_detail(client):
    res = client.post("/api/v1/generate/enhance", json={"prompt": "nude explicit nsfw"})
    assert res.status_code == 400
    detail = res.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "CONTENT_MODERATION_BLOCKED"


def test_ideate_blocked_with_structured_detail(client):
    res = client.post("/api/v1/director/ideate", json={"brief": "underage child inappropriate"})
    assert res.status_code == 400
    detail = res.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "CONTENT_MODERATION_BLOCKED"
