"""P2: Motion fixture library, OIDC/CDN readiness, Stripe bootstrap — verified."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "motion"


def test_motion_fixture_files_exist():
    assert (FIXTURE_DIR / "still.png").is_file()
    assert (FIXTURE_DIR / "ref.mp4").is_file()
    assert (FIXTURE_DIR / "still.png").stat().st_size > 100
    assert (FIXTURE_DIR / "ref.mp4").stat().st_size > 100


def test_motion_samples_api():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/motion/samples")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["available"] is True
    assert data["mode"] == "native"
    assert data.get("sku") == "kling-3.0/motion-control"
    assert len(data["samples"]) >= 1
    sample = data["samples"][0]
    img = c.get(sample["image_path"])
    assert img.status_code == 200
    assert img.headers["content-type"].startswith("image/")
    vid = c.get(sample["video_path"])
    assert vid.status_code == 200
    assert "video" in vid.headers.get("content-type", "") or len(vid.content) > 100


def test_fixture_harness_motion_library():
    from scripts.fixture_derivative_harness import check_motion_library, check_dry
    # Import via path
    import importlib.util
    path = Path(__file__).resolve().parents[1] / "scripts" / "fixture_derivative_harness.py"
    spec = importlib.util.spec_from_file_location("fixture_harness", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    lib = mod.check_motion_library()
    assert lib["passed"] is True
    dry = mod.check_dry()
    assert dry["passed"] is True


def test_oidc_ready_and_resolve_endpoints(monkeypatch):
    from app.services import oidc_ready

    monkeypatch.delenv("OIDC_ISSUER", raising=False)
    monkeypatch.delenv("OIDC_CLIENT_ID", raising=False)
    monkeypatch.delenv("OIDC_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("OIDC_REDIRECT_URI", raising=False)
    st = oidc_ready.oidc_status(discover=False)
    assert st.configured is False

    monkeypatch.setenv("OIDC_ISSUER", "https://idp.example.com")
    monkeypatch.setenv("OIDC_CLIENT_ID", "cid")
    monkeypatch.setenv("OIDC_CLIENT_SECRET", "sec")
    monkeypatch.setenv("OIDC_REDIRECT_URI", "https://api.example.com/cb")
    st2 = oidc_ready.oidc_status(discover=False)
    assert st2.configured is True
    assert st2.authorize_url.endswith("/authorize")

    with patch.object(oidc_ready, "_discover", return_value={
        "authorization_endpoint": "https://idp.example.com/oauth2/v1/authorize",
        "token_endpoint": "https://idp.example.com/oauth2/v1/token",
        "userinfo_endpoint": "https://idp.example.com/oauth2/v1/userinfo",
    }):
        eps = oidc_ready.resolve_endpoints("https://idp.example.com", discover=True)
    assert eps["discovery_ok"] is True
    assert "oauth2" in eps["authorize_url"]


def test_oidc_login_503_when_unconfigured():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/auth/oidc/login", follow_redirects=False)
    assert r.status_code == 503


def test_storage_public_media_base(monkeypatch):
    from app.services import storage_ready

    monkeypatch.setattr(storage_ready.settings, "MEDIA_CDN_BASE_URL", "https://cdn.betty.test/")
    monkeypatch.setattr(storage_ready.settings, "S3_PUBLIC_BASE_URL", "")
    monkeypatch.setattr(storage_ready.settings, "STORAGE_TYPE", "local")
    assert storage_ready.public_media_base() == "https://cdn.betty.test"

    monkeypatch.setattr(storage_ready.settings, "MEDIA_CDN_BASE_URL", "")
    monkeypatch.setattr(storage_ready.settings, "STORAGE_TYPE", "s3")
    monkeypatch.setattr(storage_ready.settings, "S3_PUBLIC_BASE_URL", "https://s3pub.test")
    assert storage_ready.public_media_base() == "https://s3pub.test"


def test_readiness_includes_sso_storage_stripe():
    from fastapi.testclient import TestClient
    from app.main import app

    c = TestClient(app)
    r = c.get("/api/v1/system/readiness")
    assert r.status_code == 200
    data = r.json()
    assert "stripe" in data and "storage" in data and "sso" in data
    assert "configured" in data["sso"]
    assert "cdn_configured" in data["storage"]


def test_bootstrap_stripe_dry_run():
    import subprocess
    script = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_stripe_prices.py"
    env = {**os.environ}
    env.pop("STRIPE_API_KEY", None)
    out = subprocess.check_output(
        [sys.executable, str(script), "--dry-run", "--json-only"],
        env=env,
        cwd=str(script.parent.parent),
    )
    report = json.loads(out.decode())
    assert report["mode"] == "dry-run"
    envs = {i["env"] for i in report["items"]}
    assert "STRIPE_PRICE_STARTER_MONTHLY" in envs
    assert "STRIPE_PRICE_PRO_YEARLY" in envs
    assert "STRIPE_PRICE_TEAM_SEAT_MONTHLY" in envs


def test_bootstrap_stripe_live_mocked(monkeypatch, tmp_path):
    """Simulate Stripe SDK create without network + write-env injection."""
    import importlib.util
    import types
    from types import SimpleNamespace

    path = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_stripe_prices.py"
    spec = importlib.util.spec_from_file_location("bootstrap_stripe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class FakeList:
        def __init__(self, items):
            self._items = items

        def auto_paging_iter(self):
            return iter(self._items)

    class FakeStripe:
        class Product:
            @staticmethod
            def list(**kw):
                return FakeList([])

            @staticmethod
            def create(**kw):
                return SimpleNamespace(id="prod_test_1", metadata=kw.get("metadata") or {})

        class Price:
            @staticmethod
            def list(**kw):
                return FakeList([])

            @staticmethod
            def create(**kw):
                return SimpleNamespace(
                    id=f"price_{kw['metadata']['betty_plan_id']}_{kw['metadata']['betty_cycle']}",
                    metadata=kw.get("metadata") or {},
                )

    monkeypatch.setenv("STRIPE_API_KEY", "sk_test_fake")
    fake_mod = types.ModuleType("stripe")
    fake_mod.api_key = None
    fake_mod.Product = FakeStripe.Product
    fake_mod.Price = FakeStripe.Price
    with patch.dict(sys.modules, {"stripe": fake_mod}):
        report = mod.create_prices()
    assert report["mode"] == "live"
    assert report["env"]["STRIPE_PRICE_STARTER_MONTHLY"].startswith("price_")
    assert "STRIPE_PRICE_TEAM_SEAT_MONTHLY" in report["env"]

    env_file = tmp_path / ".env"
    env_file.write_text("FOO=1\nSTRIPE_PRICE_STARTER_MONTHLY=old\n", encoding="utf-8")
    mod.write_env(str(env_file), report["env"])
    text = env_file.read_text(encoding="utf-8")
    assert "FOO=1" in text
    assert "STRIPE_PRICE_STARTER_MONTHLY=price_starter_monthly" in text
    assert text.count("STRIPE_PRICE_STARTER_MONTHLY=") == 1


def test_oidc_callback_state_mismatch():
    from fastapi.testclient import TestClient
    from app.main import app

    with patch("app.api.oidc.oidc_configured", return_value=True):
        c = TestClient(app)
        c.cookies.set("betty_oidc_state", "expected-state")
        r = c.get(
            "/api/v1/auth/oidc/callback",
            params={"code": "x", "state": "wrong"},
        )
        assert r.status_code == 400
        assert "state" in r.json()["detail"].lower()
