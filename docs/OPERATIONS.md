# Betty · 生产运营手册（Operations Runbook）

面向对外提供服务的生产运营：监控告警、备份、CDN、扩缩容、SLA。

## 1. 监控与告警

### 指标（Prometheus）
- 抓取端点：`GET /metrics`（应用进程，Prometheus 文本格式）。
- 关键指标：
  - `betty_http_requests_total{method,path,status}` — 请求量/错误率（按 5xx 占比告警）
  - `betty_http_request_duration_seconds` — 延迟直方图（P95/P99）
  - `betty_http_in_flight` — 在途请求（过高=过载）
  - `betty_http_exceptions_total` — 未处理异常（>0 告警）
  - `betty_celery_queue_depth{queue}` — 队列积压（持续增长=worker 不足）
  - `betty_tasks_total{status}` — 任务分布（failed 激增告警）
  - `betty_up{dependency}` — DB/Redis 依赖健康（=0 告警）

### 建议告警规则（Prometheus Alertmanager）
```
- alert: HighErrorRate       expr: sum(rate(betty_http_requests_total{status=~"5.."}[5m])) / sum(rate(betty_http_requests_total[5m])) > 0.05  for: 5m
- alert: QueueBacklog        expr: betty_celery_queue_depth > 100  for: 10m
- alert: DependencyDown      expr: betty_up == 0  for: 1m
- alert: HighP95Latency      expr: histogram_quantile(0.95, sum(rate(betty_http_request_duration_seconds_bucket[5m])) by (le)) > 3  for: 10m
```

### 健康探针
- `GET /health` — 存活 + DB/Redis 健康（`degraded` 时报警）。
- `GET /health/ready` — 就绪门禁：DB/Redis 硬依赖 + Celery worker 数 + 队列积压；硬依赖不可用返回 **503**（供负载均衡摘流）。
- 公开状态页：`/status`（前端，10s 自动刷新，展示各服务与队列积压）。

### 错误聚合
- 配置 `SENTRY_DSN` 即启用 Sentry；每个请求带 `X-Request-ID`，异常日志与响应体均含 request_id 便于追踪。

## 2. 备份与恢复
- 脚本：`python backend/scripts/backup.py --out /backups`
  - SQLite：在线一致快照并 gzip；Postgres：`pg_dump | gzip`。
  - 媒体：写清单（path/size/mtime）用于校验对象存储/rsync 同步。
  - 产物：`betty-backup-<ts>.tar.gz`（含 database + media-manifest + meta）。
- Cron 示例：`0 3 * * * cd /app && python scripts/backup.py >> /var/log/betty-backup.log 2>&1`
- 恢复：解包 → 还原 DB（`gunzip | psql` 或替换 sqlite 文件）→ 校验媒体清单。
- 对象存储（S3/R2）媒体依赖 bucket 版本化/跨区复制，无需脚本重复备份。

## 3. CDN / 媒体分发
- 生成媒体按 uuid 内容寻址、不可变；`/api/v1/media/*` 已返回 `Cache-Control: public, max-age=31536000, immutable`，可直接被 CDN/浏览器缓存。
- 本地存储 + CDN：设 `MEDIA_CDN_BASE_URL=https://cdn.example.com`，媒体 URL 自动变为 CDN 绝对地址（CDN 回源 `/api/v1/media`）。
- 对象存储：`STORAGE_TYPE=s3` + `AWS_*` + `S3_PUBLIC_BASE_URL`（CDN/公有桶域名），生成物直传对象存储并返回 CDN URL。切换无需改代码。

## 4. 扩缩容
- **API**：无状态（限流走 Redis、鉴权走 JWT），可水平扩展。Dockerfile 已 `uvicorn --workers 4`；compose `deploy.replicas`（`API_REPLICAS`，默认 2）或 `docker compose up --scale api=N`，前置负载均衡 + `/health/ready` 摘流。
- **Worker**：按生成吞吐扩展 `--scale worker=N`（`WORKER_REPLICAS`，默认 2）；队列 `celery,image_q,video_q,director_q,pipeline_q,collector_q`。视频/唇形为长任务，可拆独立队列与专用 worker。
- **Redis/DB**：Redis 建议持久化 + 主从；Postgres 建议托管实例 + 只读副本；连接池见 `DATABASE_POOL_SIZE`。
- **Flower**：`flower` 服务提供 Celery 任务/worker 可视化监控。

## 5. SLA 与发布门禁
- 目标（建议）：API 可用性 99.9%；图片 P95 < 60s、视频分钟级；错误率 < 1%。
- 发布门禁：CI（pytest + alembic upgrade + 前端 build）通过 + `/health/ready` 200 + 关键告警静默。
- 依赖降级：第三方模型网关（KIE）不稳定时，生成侧已有重试 + 跨模型回退；支付回调需公网 HTTPS + 验签。

## 6. 上线前检查（Go-Live Checklist）
- [ ] `ENV=production`（自动禁用 `/api/docs`、启用 HSTS）
- [ ] `JWT_SECRET`、`KIE_API_KEY` 等密钥经环境注入（非默认值）
- [ ] `CORS_ORIGINS` 设为真实域名
- [ ] `DATABASE_URL` 指向 Postgres；`alembic upgrade head` 已执行
- [ ] `STORAGE_TYPE=s3` + CDN 已配置（或 `MEDIA_CDN_BASE_URL`）
- [ ] `SENTRY_DSN` + Prometheus 抓取 `/metrics` + 告警规则就位
- [ ] 备份 cron 已配置并演练过一次恢复
- [ ] 支付：商户号/Stripe Key + `PUBLIC_BASE_URL`（公网 HTTPS）+ notify 验签
