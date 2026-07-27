# P1 迭代：失败退款 · 分享门闩 · live_video 周检

**日期：** 2026-07-16  
**原则：** 只做评估文档已列且未完成的项；每项有代码证据 + 自动化测试；不计假成功。

---

## 进度台账（防反复优化）

| 项 | 状态 | 证据 |
|----|------|------|
| P0 Public `execute_generation` | ✅ 已完成 | `developer.py` + `test_core_feature_p0` |
| P0 Timeline Task 行 | ✅ 已完成 | `timeline.py` + poll 测试 |
| P0 FE `image_url` i2i/i2v | ✅ 已完成 | image/video `page.tsx` |
| P0 Lipsync `model_name` | ✅ 已完成 | `lipsync.py` args |
| P0 Edit 鉴权计费 | ✅ 已完成 | `edit_image_tool` Depends |
| **P1 失败幂等退款** | ✅ 本迭代 | `refund_task_credits(_sync)` + `on_task_terminal` |
| **P1 Share publish 门闩** | ✅ 本迭代 | `share_public` + publish/unpublish API |
| **P1 live_video 周检** | ✅ 本迭代 | Beat `smoke_live_video_weekly` + env 门控 |
| P1 工具成本与上游对齐看板 | ⏳ 未做（下轮） | — |
| P2 多参考图 / 真分镜 | ⏳ 未做 | — |

---

## 本迭代实现摘要

### 1. 失败退款（真实）
- `credits.refund_task_credits_sync` / `refund_task_credits`：按 `task_id` 找回 CONSUMPTION，写 REFUND，恢复余额；二次调用返回 `already_refunded`
- Celery 终态 `failed|cancelled` → `on_task_terminal` 自动退款
- 生成调度失败、Timeline dispatch 失败、图像工具失败 → 异步退款

### 2. Share 门闩（真实）
- Explore 列表与 `/gallery/share/{id}`：**未** `share_public` → 404 / 不展示（seed 除外）
- `POST .../publish` / `unpublish`（所有者）
- FE：画廊「公开并复制 / 公开并打开」；能力探针 `requires_publish: true`

### 3. live_video 周检（真实且防误扣费）
- Beat 每 7 天注册 `smoke_live_video_weekly`
- **仅当** `MODEL_SMOKE_LIVE_VIDEO_WEEKLY=1`（或 `MODEL_SMOKE_LIVE_VIDEO=1`）才付费探测
- KPI：`outframe_ok` 仅计 `path==live_video`；skipped 不计成功

---

## 验证

```bash
cd backend
python -m pytest tests/test_p1_refund_share_live_video.py tests/test_core_feature_p0.py \
  tests/test_parity_webhooks_share.py tests/test_health_smoke.py -q
```

预期：上述子集全部通过。

---

## 分数校正（相对细粒度评估）

| 维度 | 修前 | 修后 | 说明 |
|------|------|------|------|
| 计费闭环 | 50 | **62** | 失败退款落地；Stripe 仍未配 |
| 分享隐私 | 60 | **78** | 显式 publish |
| 运维冒烟 | 78 | **82** | 周检注册+门控 |
| **综合就绪** | ~64–68 | **~70** | 仍为 Yapper 类网关工作室 |
