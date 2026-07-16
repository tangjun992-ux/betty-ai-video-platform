# ROI 生产就绪迭代报告（2026-07-16）

基于评估 ROI 排序完成的一轮真实修复与验证。提交后生产就绪分预期从 ~55 → **~62–65**。

## 本轮已落地（按 ROI）

| ROI | 项 | 状态 | 真实验证 |
|-----|-----|------|----------|
| 1 | 模型验真 / active 扩容 | ✅ 5→**9** active | `GET /system/catalog` active_count=9 |
| 2 | WebSocket Redis pub/sub | ✅ | 频道 `betty:task-progress`，API 启动挂载 listener |
| 3 | CI 全量 pytest | ✅ | `.github/workflows/ci.yml` → `pytest tests/` |
| 4 | 生产默认 S3 | ✅ | `docker-compose.prod.yml` `STORAGE_TYPE=s3` |
| 5 | 营销文案对齐 | ✅ | 去掉 16+/23+；首页「已验证可用」 |
| 6 | 订阅 + 2× rollover | ✅ | `plan_credits` + Stripe `subscription` 模式；live checkout 验证 |
| 7 | lipsync/motion SLO 面 | ✅ | `GET /system/slo` |
| 8 | Director 吞吐 | ✅ | `DIRECTOR_VIDEO_CONCURRENCY` 默认 2 |
| 9 | 资产审核门禁 | ✅ | `check_media_url` |
| 10 | Explore remix | ✅ | `POST /gallery/{id}/remix` |

## 真实验证结果

```
pytest tests/          → 112 passed
npm run build          → OK
GET /system/catalog    → active_count=9
billing checkout plan  → plan_credits=3000 (personal)
3× starter renew       → plan_credits capped at 2000 (=2×1000)
```

## 仍未彻底关闭（下一轮计划）

| 优先级 | 项 | 说明 |
|--------|-----|------|
| P0 | 真网关出片回归 | 对 9 个 active 跑付费 KIE 冒烟（需生产 Key） |
| P0 | Stripe Price ID 配置 | 配齐后 checkout 自动走 `subscription` + `invoice.paid` |
| P1 | CI 加 Playwright E2E job | 当前仅全量 pytest + build |
| P1 | CDN 强制 | 生产需设置 `MEDIA_CDN_BASE_URL` / `S3_PUBLIC_BASE_URL` |
| P1 | Motion 专用 adapter | 仍复用 generate_video |
| P2 | SSO / 审计日志 | 企业 Teams |
| P2 | 视觉模型审核 | 现仅 caption + 可选 OpenAI text |

## 诚实口径

- Active=9 表示「网关映射已确认并纳入默认路由」，**不等于**本环境已对每个模型完成付费出片。
- Stripe Subscription **仅在配置了 Price ID 时**启用；否则仍为一次性 payment / dev-grant。
