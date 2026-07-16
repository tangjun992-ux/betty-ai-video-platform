# P0 → P1 迭代（冒烟可观测 / Webhook 落库 / Library 收藏 / 项目 ACL）

## P0
1. **上次冒烟持久化**：`model_smoke.save_last_smoke` → Redis/`memory`；`GET /models/health.last_smoke`、`/system/slo`、Admin `/admin/model-health/last-smoke`；状态页展示
2. **Webhook 投递状态**：写入 `tasks.parameters.webhook`；`GET /tasks/{id}` 返回 `webhook`

## P1
3. **Library 收藏 + 文件夹**：`POST/DELETE /library/favorites/{id}`、`?favorite=1`；`Asset.folder` + `PATCH /library/{id}/folder`
4. **项目可见性 ACL**：`Project.visibility` / `team_id`；`GET /projects/{id}` 与 `GET /teams/{id}/projects` 强制过滤

## 验证
`pytest tests/ -q` · frontend build
