# Yapper 深度对标：出片 / Motion / Lipsync / Explore / Agent

**日期：** 2026-07-16  
**覆盖项：** 用户指定 1 · 2 · 5 · 6 · 7 · 10  
**原则：** 真实现、真测试；付费 live 成败如实记账，不把 mapping 冒充出片。

---

## 1. 视频真出片（#1）

| 改动 | 说明 |
|------|------|
| `run_live_video_sample()` 抽公共 | 脚本与 Beat 共用，避免双份逻辑 |
| `MODEL_HEALTH_ALERT` | `outframe_ok=0` 且 probed>0 时打 error |
| Beat 周检 | 仍由 `MODEL_SMOKE_LIVE_VIDEO_WEEKLY=1` 门控 |

```bash
MODEL_SMOKE_LIVE_VIDEO=1 python scripts/smoke_live_video_sample.py --models seedance-2.0-fast
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

## 5. Motion（#5）

| 改动 | 说明 |
|------|------|
| `motion-control` / `motion-control-studio` 映射 | → Seedance（诚实 best-effort） |
| `motion_tasks` 使用请求 model | Studio 可走更高分辨率 |
| fixtures + `MOTION_FIXTURE_LIVE` | 既有；last_run.json 可落盘 |

**诚实：** 仍非 Kling Motion / Act-One 原生 SKU。

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
.venv/bin/python scripts/generate_lipsync_fixtures.py
.venv/bin/python -m pytest tests/test_yapper_live_parity.py tests/test_yapper_core_parity.py -q
.venv/bin/python scripts/fixture_derivative_harness.py
# 付费（可选）:
# MODEL_SMOKE_LIVE=1 .venv/bin/python scripts/smoke_live_image_sample.py --models gpt-image-2
# MODEL_SMOKE_LIVE_VIDEO=1 .venv/bin/python scripts/smoke_live_video_sample.py --models seedance-2.0-fast
```

## 本环境 live 实测（2026-07-16）

| 探针 | 结果 |
|------|------|
| `smoke_live_image_sample` gpt-image-2 + nano-banana | **2/2 outframe_ok** |
| `smoke_live_video_sample` seedance-2.0-fast | **1/1 outframe_ok**（修复 duration≥5 后） |
| pytest live parity + core | **23 passed** |
| fixture harness | motion + lipsync libraries **passed** |

> 注：曾用 duration=2 触发 KIE `422 Invalid duration`，已改为 5s/720p。

## 分数影响（诚实）

| 维 | 前 | 后 |
|----|----|----|
| 工具/Agent 工程 | 高 | **更高**（minimal + remix） |
| 真出片 | 弱（视频 0） | **显著↑**：图 2/2 + 视频 1 SKU 真出片 |
| 综合就绪 | ~78 | **~82** |
