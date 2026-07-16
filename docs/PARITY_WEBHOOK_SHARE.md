# 顶级平台对标迭代（Webhook / Share / Notify / Redis）

## 本轮相对 Yapper / Runway / Kling / Luma

| 维度 | 对标能力 | Betty 状态 |
|------|----------|------------|
| API 回调 | Runway/Kling webhook | ✅ 终态 HMAC 投递 + 重试 |
| 限流一致性 | 多副本共享 Redis | ✅ `REDIS_URL` db=3 |
| 作品分享 | Yapper 公开 permalink | ✅ `/explore/{task_id}` + `GET /gallery/share/{id}` |
| 完成通知 | 邮件偏好实际投递 | ✅ 钩子 + `/settings/notifications/test` |
| Motion 诚实 | 不夸大 vs Act-One | ✅ capabilities.features.motion_transfer=best_effort |

## 验证

```bash
cd backend && pytest tests/test_parity_webhooks_share.py tests/ -q
```
