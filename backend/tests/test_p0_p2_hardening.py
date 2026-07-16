"""P0/P1/P2 production hardening tests."""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_model_smoke_mapping_demo_path():
    from app.services.model_smoke import probe_model, run_active_smoke

    with patch("app.adapters.demo_provider.demo_mode_active", return_value=True):
        r = probe_model("nano-banana", ["image"], mode="mapping")
        assert r["ok"] is True
        assert r["evidence"]["path"] == "demo_render"

    result = run_active_smoke(mode="mapping")
    assert result["probed"] >= 8
    assert result["ok"] == result["probed"] or result["mode"] == "mapping"


def test_model_smoke_live_mocked_image():
    from app.services.model_smoke import probe_model

    fake = MagicMock()
    fake.media_url = "https://cdn.example.com/x.png"
    fake.to_dict = lambda: {"media_url": fake.media_url}

    adapter = MagicMock()
    adapter.is_available.return_value = True
    adapter.generate_image = AsyncMock(return_value=fake)

    with patch("app.adapters.demo_provider.demo_mode_active", return_value=False), \
         patch("app.adapters.kie_adapter.KieAdapter", return_value=adapter):
        r = probe_model("nano-banana", ["image"], mode="live")
    assert r["ok"] is True
    assert r["evidence"]["path"] == "live_image"


def test_stripe_status_and_blockers(monkeypatch):
    from app.services import stripe_ready
    monkeypatch.setattr(stripe_ready.settings, "STRIPE_API_KEY", "")
    monkeypatch.setattr(stripe_ready.settings, "ENV", "production")
    st = stripe_ready.stripe_status()
    assert st.production_ok is False
    assert any("STRIPE_API_KEY" in b for b in st.blockers)

    monkeypatch.setattr(stripe_ready.settings, "STRIPE_API_KEY", "sk_test")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_x")
    monkeypatch.setattr(stripe_ready.settings, "STRIPE_PRICE_CREATOR_MONTHLY", "price_creator")
    st2 = stripe_ready.stripe_status()
    assert st2.subscription_ready is True


def test_storage_cdn_required_in_prod(monkeypatch):
    from app.services import storage_ready
    monkeypatch.setattr(storage_ready.settings, "ENV", "production")
    monkeypatch.setattr(storage_ready.settings, "STORAGE_TYPE", "s3")
    monkeypatch.setattr(storage_ready.settings, "MEDIA_CDN_BASE_URL", "")
    monkeypatch.setattr(storage_ready.settings, "S3_PUBLIC_BASE_URL", "")
    monkeypatch.setattr(storage_ready.settings, "AWS_ACCESS_KEY_ID", "x")
    monkeypatch.setattr(storage_ready.settings, "AWS_S3_BUCKET", "b")
    st = storage_ready.storage_status()
    assert st.production_ok is False
    assert any("CDN" in b or "S3_PUBLIC" in b for b in st.blockers)


def test_kie_generate_motion_payload():
    from app.adapters.kie_adapter import KieAdapter

    adapter = KieAdapter.__new__(KieAdapter)
    captured = {}

    async def fake_submit(payload, media_type="video", timeout=600):
        captured.update(payload)
        return {"resultJson": '{"resultUrls":["https://cdn.example.com/m.mp4"]}'}

    adapter._submit_and_poll = fake_submit  # type: ignore

    import asyncio
    res = asyncio.run(adapter.generate_motion(
        image_url="https://img/a.png",
        video_url="https://vid/b.mp4",
        prompt="walk",
        model_id="seedance-2.0-fast",
        duration=3,
    ))
    assert captured.get("videoUrl") == "https://vid/b.mp4"
    assert captured.get("imageUrl") == "https://img/a.png"
    assert res.media_url.endswith(".mp4")
    assert res.meta.get("op") == "motion"


def test_oidc_status_unconfigured():
    from app.api.oidc import oidc_status
    st = oidc_status()
    assert "configured" in st


def test_check_media_url_blocks_empty():
    from app.services.moderation import check_media_url
    r = check_media_url("", caption="ok")
    assert r.allowed is False


def test_audit_record_and_list(tmp_path, monkeypatch):
    """Async audit roundtrip against sqlite."""
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.models.base import Base
    from app.services.audit import AuditLog, record_audit, list_audit

    async def _run():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/audit.db")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as db:
            await record_audit(db, action="test.action", actor_user_id=1, target_type="x", target_id="1")
            await db.commit()
            rows = await list_audit(db, limit=10)
            assert rows and rows[0]["action"] == "test.action"
        await engine.dispose()

    asyncio.run(_run())
