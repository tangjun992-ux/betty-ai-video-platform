# Yapper 深度对标：出片 / Motion / Lipsync / Explore / Agent

**日期：** 2026-07-16  
**覆盖项：** 用户指定 1 · 2 · 5 · 6 · 7 · 10 + 本轮视频 ≥2 SKU / 原生 Motion  
**原则：** 真实现、真测试；付费 live 成败如实记账，不把 mapping 冒充出片。

---

## 1. 视频真出片（#1）— 周检 ≥2 SKU

| 改动 | 说明 |
|------|------|
| `run_live_video_sample()` 抽公共 | 脚本与 Beat 共用 |
| Kling `duration` 字符串 | KIE `kling/*` 要求 `"5"`，int 会 500 |
| 默认样本 | `seedance-2.0-fast` + `kling-2.5-turbo` |
| 稳定回退 | 主集 <2 出片时再跑 `seedance-2.0-fast` + `seedance-2.0` |
| `MODEL_HEALTH_ALERT` | `outframe_ok=0` 且 probed>0 时打 error |
| Beat 周检 | `MODEL_SMOKE_LIVE_VIDEO_WEEKLY=1` |

```bash
MODEL_SMOKE_LIVE_VIDEO=1 python scripts/smoke_live_video_sample.py
# 或显式：
MODEL_SMOKE_LIVE_VIDEO=1 python scripts/smoke_live_video_sample.py --models seedance-2.0-fast seedance-2.0
```

## 2. 图片 live / Auto 成片感（#2）

| 改动 | 说明 |
|------|------|
| mapping **不再** `record_success` | Auto 路由成功率只吃 live outframe |
| 未验真模型 `success_rate=0.85` | 冷启动不再假装 100% |
| live 证据加分 | `successes≥1` 路由 +3~12 |
| `smoke_live_image_sample.py` + 周检 Beat | `MODEL_SMOKE_LIVE_IMAGE_WEEKLY=1` |

```bash
MODEL_SMOKE_LIVE=1 python scripts/smoke_live_image_sample.py
```

## 5. Motion（#5）— 原生 Kling Motion Control

| 改动 | 说明 |
|------|------|
| `motion-control*` → `kling-3.0/motion-control` | 原生 SKU（非 Seedance 伪装） |
| Payload | `input_urls` + `video_urls` + `character_orientation` + `mode` |
| Studio | 同 SKU，`mode=1080p` |
| Fixture `ref.mp4` | **4s / 512×768**（满足 3–30s） |
| capabilities / samples | `mode=native`，诚实声明非 Act-One |
| 失败回退 | `motion_tasks` 仍可落到 Seedance i2v |

**诚实：** 已接原生 Kling Motion Control；**不是** Runway Act-One。

## 6. Lipsync / Avatar（#6）

| 改动 | 说明 |
|------|------|
| `fixtures/lipsync/{portrait.png,line.wav}` | 生成脚本 |
| `LIPSYNC_FIXTURE_LIVE=1` harness | 付费探针 |
| TTS 传 `voice_id` | Azure id → Rachel/Adam 映射 |

## 7. Explore 飞轮（#7）

| 改动 | 说明 |
|------|------|
| seed 写 likes/views | Popular 排序有密度 |
| seed `share_public=True` | Explore 可展示 |
| Remix 带 `image_url` | 真 i2i / i2v |
| Library「发布到 Explore」 | 生产内容入口 |

## 10. Agent 最短真路径（#10）

| 改动 | 说明 |
|------|------|
| `PlanRequest.minimal` | 跳过配音/字幕/合成 |
| duration≤5 自动 minimal-ish | 视频意图默认短路径 |
| FE「快速成片」开关 | 默认开；plan/run 透传 |

最短步：`enhance_prompt → image → video`。

---

## 验证

```bash
cd backend
python3 scripts/generate_motion_fixtures.py
python3 -m pytest tests/test_yapper_live_parity.py tests/test_yapper_core_parity.py tests/test_p0_p2_hardening.py -q
python3 scripts/fixture_derivative_harness.py
# 付费（可选）:
# MODEL_SMOKE_LIVE=1 python3 scripts/smoke_live_image_sample.py --models gpt-image-2
# MODEL_SMOKE_LIVE_VIDEO=1 python3 scripts/smoke_live_video_sample.py
# MOTION_FIXTURE_LIVE=1 python3 scripts/fixture_derivative_harness.py
```

## 本环境 live 实测（2026-07-16）

| 探针 | 结果 |
|------|------|
| `smoke_live_image_sample` gpt-image-2 + nano-banana | **2/2 outframe_ok** |
| `seedance-2.0-fast` | **outframe_ok**（既有） |
| `seedance-2.0` | **outframe_ok**（本轮复验） |
| `kling-2.5-turbo` | duration 字符串修复后复验（见最新 run） |
| Motion native createTask | 见最新 `MOTION_FIXTURE_LIVE` / last_run.json |
| pytest live parity + core | 见本轮 pytest |

> 注：曾用 duration=2 触发 KIE `422 Invalid duration`；Kling int duration 触发 `duration must be a string`。

## 分数影响（诚实）

| 维 | 前 | 后 |
|----|----|----|
| 真出片（视频） | 1 SKU | **≥2 SKU 周检路径**（Seedance×2 或 Seedance+Kling） |
| Motion | best_effort Seedance | **原生 Kling Motion Control SKU** |
| 综合就绪 | ~82 | **~85**（仍非 Act-One；密钥/全量周检待部署） |
