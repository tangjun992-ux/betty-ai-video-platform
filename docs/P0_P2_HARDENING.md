# P0–P2 生产加固迭代（2026-07-16）

## 已完成

### P0
- **KIE 冒烟管线** `app/services/model_smoke.py`：`mapping` / `live` / `live_video`
  - Celery `smoke_active_models` + `scripts/smoke_active_models.py`
  - Admin `POST /admin/model-health/smoke`
- **Stripe 就绪** `stripe_ready.py`：生产缺 Key/Webhook/Price ID 则启动失败；`GET /billing/stripe-status`

### P1
- **CI Playwright**：`capability` + `betty` specs
- **CDN/S3 强制**：生产 `storage_ready.assert_*`；缺 CDN/S3 公钥则启动失败
- **Motion 专用通道**：`KieAdapter.generate_motion` + motion task 优先调用

### P2
- **审计日志**：`audit_logs` + `GET /admin/model-health/audit`
- **OIDC SSO 骨架**：`/auth/oidc/login|callback|status`（未配置返回 503）
- **视觉审核**：`check_media_url` → omni-moderation（有 OPENAI_API_KEY 时）

## 验证

见仓库 pytest / scripts；无 Key 时 live 冒烟需运维配置后执行：

```bash
MODEL_SMOKE_LIVE=1 python backend/scripts/smoke_active_models.py live
```
