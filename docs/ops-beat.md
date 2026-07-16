# Celery Beat 运维部署

生产环境需单独运行 **Celery Beat** 调度器，否则 `model-health-smoke-daily` 等定时任务不会触发。

## Docker Compose（推荐）

仓库根目录 `docker-compose.yml` 已包含 `celery-beat` 服务：

```bash
docker compose up -d celery-beat celery-worker api redis db
```

Beat 与 Worker 必须共用同一 `CELERY_BROKER_URL` / `DATABASE_URL`。

## 裸机部署

```bash
cd backend
celery -A celery_app beat --loglevel=info
```

另开终端运行 worker（含 `pipeline_q` 以执行健康冒烟）：

```bash
celery -A celery_app worker -Q video_q,image_q,pipeline_q,director_q,celery --concurrency=4
```

## 模型隔离告警与复核

- Beat 任务 `smoke_active_models` 失败会将模型写入 Redis 隔离区，并打 `MODEL_HEALTH_ALERT` 错误日志。
- 管理员复核：`GET /api/v1/admin/model-health/quarantined`
- 解除隔离：`POST /api/v1/admin/model-health/{model_id}/clear-quarantine`（需 admin 角色）

## 每周 live_video 抽样（付费，需显式开启）

Beat 已注册 `model-health-live-video-weekly`（每 7 天），任务名：
`app.tasks.health_tasks.smoke_live_video_weekly`。

| 变量 | 说明 |
|------|------|
| `MODEL_SMOKE_LIVE_VIDEO_WEEKLY=1` | 允许周检真正跑付费 video outframe |
| `MODEL_SMOKE_LIVE_VIDEO=1` | 兼容门控（与手动脚本一致） |

未开启时任务 **no-op 返回**（`skipped: true`），不会产生上游费用。  
KPI：仅 `evidence.path == live_video` 计入 `outframe_ok`；`live_skipped_video` 记入 `outframe_skipped`，**不计成功**。

手动等价：

```bash
cd backend
MODEL_SMOKE_LIVE_VIDEO=1 python scripts/smoke_live_video_sample.py
```

## Stripe 生产环境变量

| 变量 | 说明 |
|------|------|
| `STRIPE_API_KEY` | Stripe Secret Key |
| `STRIPE_WEBHOOK_SECRET` | Webhook 签名密钥 |
| `STRIPE_PRICE_CREATOR_MONTHLY` | Creator 月付 Price ID |
| `STRIPE_PRICE_PRO_MONTHLY` | Pro 月付 Price ID |
| `STRIPE_PRICE_TEAM_SEAT_MONTHLY` | 团队额外席位 Price ID |

未配置 Price ID 时 checkout 回退到 `price_data` 动态定价（适合开发环境）。
