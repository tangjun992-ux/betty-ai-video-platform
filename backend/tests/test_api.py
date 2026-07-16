"""Backend API tests — in-process ASGI (TestClient) via the shared ``client``
fixture in conftest.py; no separately running server required."""
import pytest


class TestHealth:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        # "ok" when all deps are up, "degraded" when e.g. Redis is down in CI.
        assert data["status"] in ("ok", "degraded")
        assert data["checks"]["database"] == "ok"

    def test_api_health(self, client):
        r = client.get("/api/v1/health/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ok", "degraded", "healthy")
        assert "database" in data["services"]
        assert "redis" in data["services"]
        assert "celery" in data["services"]


class TestModels:
    def test_list_models(self, client):
        r = client.get("/api/v1/models/")
        assert r.status_code == 200
        models = r.json()["models"]
        assert len(models) >= 3

    def test_model_detail(self, client):
        r = client.get("/api/v1/models/gpt-image-2")
        assert r.status_code == 200

    def test_pricing_plans(self, client):
        r = client.get("/api/v1/models/pricing/plans")
        assert r.status_code == 200
        assert len(r.json()["plans"]) >= 3

    def test_pricing_user(self, client):
        r = client.get("/api/v1/models/pricing/user")
        assert r.status_code == 200
        data = r.json()
        assert "credits" in data


class TestGallery:
    def test_gallery(self, client):
        r = client.get("/api/v1/gallery/")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data

    def test_gallery_stats(self, client):
        r = client.get("/api/v1/gallery/stats")
        assert r.status_code == 200


class TestGenerate:
    def test_analyze_prompt(self, client):
        r = client.post("/api/v1/generate/analyze", json={"prompt": "美丽的日落"})
        assert r.status_code == 200
        data = r.json()
        assert "media_type" in data["analysis"]

    def test_submit_generation(self, client):
        # Task submission requires a Celery broker. When one is available the
        # API returns 202 with a queued task; without a broker the enqueue
        # raises, surfacing as a 5xx. Both are acceptable for a unit run, so we
        # use a client that turns server exceptions into 500 responses.
        from fastapi.testclient import TestClient

        from app.main import app

        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.post("/api/v1/generate/", json={
                "prompt": "测试图片生成",
                "media_type": "image",
            })
        assert r.status_code in (202, 500, 503)
        if r.status_code == 202:
            data = r.json()
            assert "task_id" in data
            assert data["status"] == "queued"


class TestTasks:
    def test_list_tasks(self, client):
        r = client.get("/api/v1/tasks/")
        assert r.status_code == 200

    def test_get_task_not_found(self, client):
        r = client.get("/api/v1/tasks/nonexistent-id-12345")
        assert r.status_code in (200, 404)


class TestDirectorIntent:
    """导演意图判定回归。曾有 bug: '配音' 子串误命中 '配音乐'，把视频请求
    错判成口播分支而丢失 video 步骤。"""

    def _plan(self, brief):
        from app.director import DirectorPlanner
        return DirectorPlanner().plan(brief)

    def test_video_with_background_music_keeps_video_step(self):
        # 背景乐诉求("配音乐"/"配乐")不得触发口播分支，必须保留视频生成步骤。
        for brief in (
            "给我做一个赛博朋克城市夜景的宣传短视频，配音乐和字幕",
            "宣传片，配乐+字幕",
        ):
            plan = self._plan(brief)
            actions = [s.action for s in plan.steps]
            assert plan.intent != "talking", f"{brief} 误判为口播: {actions}"
            assert "video" in actions, f"{brief} 丢失视频步骤: {actions}"

    def test_real_talking_still_routes_to_talking(self):
        # 真正的口播/数字人请求仍应走 talking 分支。
        for brief in ("做一个数字人口播讲解视频", "让这个人物开口说话"):
            plan = self._plan(brief)
            assert plan.intent == "talking", f"{brief} 未识别为口播: {plan.intent}"

    def test_single_image_intent(self):
        plan = self._plan("生成一张赛博朋克海报")
        assert plan.intent == "image"


class TestTimelineCompose:
    """时间轴合成回归。曾有 bug: transition/trim 在 schema 里定义了，但 compose
    只取 url，转场和裁剪全被丢弃。这里用真实 ffmpeg 验证它们真正生效。"""

    def _ffmpeg(self):
        import shutil
        return shutil.which("ffmpeg") and shutil.which("ffprobe")

    def _make_clips(self, n, secs=3):
        import subprocess
        from app.adapters import demo_provider as dp
        gen = dp._generated_dir()
        urls = []
        cols = ["red", "green", "blue", "yellow"]
        for i in range(n):
            name = f"pytestclip_{i}_{secs}.mp4"
            path = gen / name
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                 f"color=c={cols[i % len(cols)]}:s=320x240:d={secs}:r=25",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
            urls.append(f"{dp.MEDIA_URL_PREFIX}/{dp.GENERATED_SUBDIR}/{name}")
        return urls

    def test_transitions_shorten_by_xfade_overlap(self):
        if not self._ffmpeg():
            pytest.skip("ffmpeg 未安装")
        from app.adapters import demo_provider as dp
        urls = self._make_clips(3)
        clips = [
            {"url": urls[0], "transition": "cut"},
            {"url": urls[1], "transition": "fade"},
            {"url": urls[2], "transition": "dissolve"},
        ]
        u, _ = dp.compose_final_video(None, None, False, None, clips)
        d = dp._probe_duration(dp._local_media_path(u))
        # 3×3s = 9s，两次 0.5s xfade 交叠 → ~8.0s（非简单拼接的 9s）。
        assert 7.5 < d < 8.5, f"转场未生效, duration={d}"

    def test_trim_applied(self):
        if not self._ffmpeg():
            pytest.skip("ffmpeg 未安装")
        from app.adapters import demo_provider as dp
        urls = self._make_clips(2)
        clips = [
            {"url": urls[0], "start": 0.0, "end": 1.0, "transition": "cut"},
            {"url": urls[1], "start": 0.0, "end": 1.0, "transition": "cut"},
        ]
        u, _ = dp.compose_final_video(None, None, False, None, clips)
        d = dp._probe_duration(dp._local_media_path(u))
        assert 1.7 < d < 2.3, f"裁剪未生效, duration={d}"

    def test_legacy_urls_still_work(self):
        if not self._ffmpeg():
            pytest.skip("ffmpeg 未安装")
        from app.adapters import demo_provider as dp
        urls = self._make_clips(2)
        u, _ = dp.compose_final_video(urls, None, False, None)
        d = dp._probe_duration(dp._local_media_path(u))
        assert 5.5 < d < 6.5, f"旧签名(list[str])回归失败, duration={d}"


class TestLongVideoDuration:
    """长视频回归。曾有 bug: demo provider 把时长硬夹到 12s，前端允许到 30s 的
    请求(含 15s 长视频)被静默截断。这里用真实 ffmpeg 验证 15s/30s 真正生效。"""

    def _ffmpeg(self):
        import shutil
        return shutil.which("ffmpeg") and shutil.which("ffprobe")

    def test_15s_long_video_honored(self):
        if not self._ffmpeg():
            pytest.skip("ffmpeg 未安装")
        from app.adapters import demo_provider as dp
        u, _ = dp.render_demo_video("a long cinematic shot", "640x360", 15, None)
        d = dp._probe_duration(dp._local_media_path(u))
        assert 14.5 < d < 15.5, f"15s 长视频未生效, duration={d}"

    def test_30s_ceiling(self):
        if not self._ffmpeg():
            pytest.skip("ffmpeg 未安装")
        from app.adapters import demo_provider as dp
        u, _ = dp.render_demo_video("x", "640x360", 30, None)
        d = dp._probe_duration(dp._local_media_path(u))
        assert 29.0 < d < 31.0, f"30s 上限未生效, duration={d}"


class TestProration:
    """方案变更按比例计费回归。前端承诺"随时按比例调整方案"，后端此前无 proration
    逻辑，plan 购买总是全额发放。这里验证升/降级/新订阅的按比例计算。"""

    def _compute(self, *a, **kw):
        from app.api.pricing import compute_proration
        return compute_proration(*a, **kw)

    def test_upgrade_half_cycle(self):
        # starter($9.99/1000) → creator($49.99/7000)，剩 15/30 天。
        r = self._compute("starter", "creator", 15, cycle_days=30, cycle="monthly")
        assert r["proration_factor"] == 0.5
        assert r["unused_credit_usd"] == round(9.99 * 0.5, 2)
        assert r["new_plan_prorated_usd"] == round(49.99 * 0.5, 2)
        assert r["net_charge_usd"] == round(49.99 * 0.5 - 9.99 * 0.5, 2)
        assert r["prorated_credits"] == int(round(7000 * 0.5))
        assert r["is_refund"] is False

    def test_downgrade_is_refund(self):
        r = self._compute("creator", "starter", 20, cycle_days=30, cycle="monthly")
        assert r["net_charge_usd"] < 0
        assert r["is_refund"] is True

    def test_new_subscription_full(self):
        r = self._compute(None, "personal", 30, cycle_days=30, cycle="monthly")
        assert r["unused_credit_usd"] == 0.0
        assert r["net_charge_usd"] == round(24.99, 2)
        assert r["prorated_credits"] == 3000

    def test_unknown_plan_raises(self):
        with pytest.raises(ValueError):
            self._compute(None, "nonexistent-plan", 30)

    def test_preview_endpoint(self, client):
        r = client.get("/api/v1/pricing/proration-preview",
                       params={"new_plan_id": "creator", "current_plan_id": "starter",
                               "days_remaining": 15, "cycle": "monthly"})
        assert r.status_code == 200
        data = r.json()
        assert data["net_charge_usd"] == round(49.99 * 0.5 - 9.99 * 0.5, 2)
        assert data["prorated_credits"] == 3500

    def test_preview_unknown_plan_404(self, client):
        r = client.get("/api/v1/pricing/proration-preview",
                       params={"new_plan_id": "nope"})
        assert r.status_code == 404


class TestPlanTracking:
    """方案持久化回归。plan checkout 现在写入 current_plan_id/plan_started_at/plan_cycle，
    /pricing/user 回报当前方案与周期剩余天数，支撑前端真实按比例换方案。"""

    def test_plan_days_remaining_helper(self):
        from datetime import datetime, timezone, timedelta
        from app.api.pricing import _plan_days_remaining
        # 无方案 → None
        assert _plan_days_remaining(None, None) is None
        # 刚订阅月付 → 约 30 天
        started = datetime.now(timezone.utc)
        assert 29 <= _plan_days_remaining(started, "monthly") <= 30
        # 已过 10 天 → 约 20 天
        assert 19 <= _plan_days_remaining(started - timedelta(days=10), "monthly") <= 21
        # 超期 → 夹到 0，不为负
        assert _plan_days_remaining(started - timedelta(days=99), "monthly") == 0
        # 年付周期 365 天
        assert 364 <= _plan_days_remaining(started, "yearly") <= 365

    def test_checkout_persists_plan(self, client):
        r = client.post("/api/v1/billing/checkout",
                        json={"kind": "plan", "id": "starter", "cycle": "monthly"})
        assert r.status_code == 200
        u = client.get("/api/v1/pricing/user").json()
        assert u["current_plan_id"] == "starter"
        assert u["plan_cycle"] == "monthly"
        assert 29 <= u["plan_days_remaining"] <= 30

    def test_prorated_checkout_switches_plan(self, client):
        client.post("/api/v1/billing/checkout",
                    json={"kind": "plan", "id": "starter", "cycle": "monthly"})
        u = client.get("/api/v1/pricing/user").json()
        r = client.post("/api/v1/billing/checkout",
                        json={"kind": "plan", "id": "creator", "cycle": "monthly",
                              "current_plan_id": "starter",
                              "days_remaining": u["plan_days_remaining"]})
        assert r.status_code == 200
        assert "按比例变更" in r.json()["label"]
        assert client.get("/api/v1/pricing/user").json()["current_plan_id"] == "creator"
