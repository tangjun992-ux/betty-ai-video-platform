# P1 续：工具成本看板 · 真分镜/多参考图 · Stripe Price

**日期：** 2026-07-16  
**原则：** 只做台账未完成项；禁止重复已交付的 P0/P1；每项有自动化验证。

---

## 进度台账（累计）

| 项 | 状态 |
|----|------|
| P0 阻断五项 | ✅ |
| P1 退款 / Share 门闩 / live_video 周检 | ✅ |
| **工具成本 vs upstream `res.cost` 看板** | ✅ 本迭代 |
| **多参考图 + 真 i2i + 真分镜 API** | ✅ 本迭代 |
| **Stripe Starter/Personal/Creator/Pro Price 配置面** | ✅ 本迭代（代码+env 模板；生产填真实 Price ID） |

---

## 1. 工具成本看板（真实）

- `/generate/edit` 成功后写入 `Task(media_type=image_tool)`  
  - `estimated_cost` = 平台预扣 `cost_credits`  
  - `actual_cost` = 上游 `res.cost`  
  - `parameters.margin_credits` = charged − upstream  
- `GET /pricing/costs` 新增 `tools` + `charged_vs_upstream`  
- 验证：`test_edit_tool_persists_task_with_upstream_cost`、`test_pricing_costs_exposes_tools_slice`

## 2. 多参考图 / 真分镜（真实）

- `GenerateRequest.reference_images`（≤4）；Celery `image_tasks` 有 ref → `edit_image`（真 i2i）  
- KIE `generate_image` 收到 refs 时路由到 `edit_image`  
- `POST /director/storyboard`：每镜独立 video step + 依赖链 + compose（**非**提示词拼接）  
- FE：Image 上传全部参考图；Video 多镜头走 storyboard API  
- 验证：`test_image_task_routes_refs_to_edit_image`、`test_build_storyboard_plan_real_steps`、`test_storyboard_api_dry_run`

## 3. Stripe Price（真实配置面）

- 新增 env：`STRIPE_PRICE_STARTER_*`、`STRIPE_PRICE_PERSONAL_*`（含年付）  
- `_STRIPE_PLAN_PRICE` / `stripe_ready.PLAN_PRICE_ENVS` 覆盖四档套餐  
- `subscription_ready`：任一 `*_MONTHLY` Price ID + API Key  
- `.env.example` + `ops-beat.md` 文档  
- 验证：`test_stripe_line_item_uses_starter_personal_price_ids`、`test_stripe_status_subscription_ready_with_starter`  
- **生产仍需在 Stripe Dashboard 创建 Price 并写入密钥**（本仓库无法代填真实 Price ID）

---

## 验证命令

```bash
cd backend
python -m pytest tests/test_p1_cost_storyboard_stripe.py \
  tests/test_p0_p2_hardening.py tests/test_p1_refund_share_live_video.py \
  tests/test_core_feature_p0.py -q
```

---

## 分数校正

| 维度 | 前 | 后 |
|------|----|----|
| 计费/成本可观测 | 62 | **72** |
| 分镜/多镜叙事 | 66 | **78** |
| 计费订阅闭环 | 55 | **68**（配置面齐；密钥仍属环境） |
| **综合就绪** | ~70 | **~74** |
