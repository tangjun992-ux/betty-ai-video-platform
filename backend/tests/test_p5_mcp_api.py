"""P5 — Yapper-parity MCP / public REST distribution surface."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _client():
    from app.main import app
    return TestClient(app)


def _auth_and_key(c: TestClient) -> dict:
    email = f"mcp_{uuid.uuid4().hex[:8]}@test.local"
    username = f"mcp{uuid.uuid4().hex[:6]}"
    reg = c.post("/api/v1/auth/register", json={"email": email, "password": "Test1234!", "username": username})
    assert reg.status_code == 200, reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = c.post("/api/v1/developer/keys", json={"name": "mcp-test"}, headers=headers)
    assert created.status_code == 200, created.text
    secret = created.json()["secret"]
    assert secret.startswith("sk_betty_")
    return {"jwt": headers, "api": {"X-API-Key": secret}, "bearer": {"Authorization": f"Bearer {secret}"}}


def test_mcp_discover_and_initialize():
    with _client() as c:
        d = c.get("/api/v1/mcp/connector")
        assert d.status_code == 200, d.text
        body = d.json()
        assert body["transport"] == "streamable-http"
        assert body["auth"]["oauth"] is False
        assert "sk_betty_" in body["auth"]["note"] or "API Key" in body["auth"]["note"]
        assert "不宣称 54+" in (body.get("honesty") or "")
        assert "list_models" in body["tools"]
        assert "generate" in body["tools"]

        init = c.post("/api/v1/mcp/connector", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}},
        })
        assert init.status_code == 200, init.text
        result = init.json()["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert result["serverInfo"]["name"] == "betty"
        assert "OAuth" in result["instructions"]

        listed = c.post("/api/v1/mcp/connector", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in listed.json()["result"]["tools"]}
        assert {"list_models", "get_credits", "quote_generation", "generate", "get_task", "list_assets"} <= names


def test_mcp_list_models_unauth_and_generate_requires_key():
    with _client() as c:
        models = c.post("/api/v1/mcp/connector", json={
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "list_models", "arguments": {}},
        })
        assert models.status_code == 200, models.text
        text = models.json()["result"]["content"][0]["text"]
        assert "active_count" in text
        assert "仅已验证" in text or "active" in text

        denied = c.post("/api/v1/mcp/connector", json={
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "get_credits", "arguments": {}},
        })
        assert denied.status_code == 401


def test_public_rest_and_mcp_quote_with_key():
    with _client() as c:
        keys = _auth_and_key(c)
        pub = c.get("/api/v1/public/models")
        assert pub.status_code == 200
        assert pub.json()["active_count"] >= 1
        assert pub.json()["active_count"] <= 12

        credits = c.get("/api/v1/public/credits", headers=keys["api"])
        assert credits.status_code == 200
        assert "credits" in credits.json()

        quote = c.post(
            "/api/v1/public/quote",
            headers=keys["api"],
            json={"prompt": "赛博朋克夜景", "media_type": "image", "model": "auto"},
        )
        assert quote.status_code == 200, quote.text
        assert quote.json()["estimated_cost_credits"] >= 1
        assert quote.json()["eta_source"] == "catalog"

        rpc = c.post("/api/v1/mcp/connector", headers=keys["bearer"], json={
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "quote_generation", "arguments": {"prompt": "产品海报", "media_type": "image"}},
        })
        assert rpc.status_code == 200, rpc.text
        assert rpc.json()["result"]["isError"] is False
        assert "estimated_cost_credits" in rpc.json()["result"]["content"][0]["text"]

        assets = c.get("/api/v1/public/assets", headers=keys["api"])
        assert assets.status_code == 200
        assert "items" in assets.json()


def test_capabilities_advertise_mcp_honesty():
    with _client() as c:
        r = c.get("/api/v1/system/capabilities")
        assert r.status_code == 200
        feat = r.json()["features"]["mcp_api"]
        assert feat["available"] is True
        assert feat["oauth"] is False
        assert feat["auth"] == "api_key"
        assert "54+" in feat["note"]
