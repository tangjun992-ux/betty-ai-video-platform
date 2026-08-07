# Betty Gateway Grafana Dashboard

## 导入步骤

1. 在 Grafana 中选择 **Dashboards → New → Import**。
2. 上传 `betty-gateway-dashboard.json`，或粘贴其 JSON 内容。
3. 选择 Prometheus 数据源（需能 scrape Betty API 的 `/metrics`）。
4. 保存 Dashboard。

## 依赖指标

Dashboard 使用以下 Prometheus 指标（由 Betty backend `/metrics` 暴露）：

| 指标 | 说明 |
|------|------|
| `betty_gateway_requests_total` | 按 capability / provider / status 的请求计数 |
| `betty_gateway_fallback_total` | Provider chain fallback 次数 |
| `betty_gateway_provider_circuit_open` | Provider 熔断状态（1=打开） |
| `betty_gateway_provider_inflight` | 各 Provider 当前 in-flight 请求数 |

## Prometheus 配置示例

```yaml
scrape_configs:
  - job_name: betty-api
    metrics_path: /metrics
    static_configs:
      - targets: ["betty-api:8000"]
```

## 相关环境变量

- `GATEWAY_ENABLED=true` — 启用 Gateway 路由
- `GATEWAY_PROVIDER_RPM` — 默认 Provider RPM 上限
- `GATEWAY_PROVIDER_MAX_INFLIGHT` — Provider 最大并发
- `GATEWAY_USER_DAILY_CREDIT_CAP` / `GATEWAY_TEAM_DAILY_CREDIT_CAP` — 日预算上限

## Admin 控制台

运维人员也可通过 Web UI `/admin/gateway` 查看路由、Provider 健康、预算上限与 in-flight 背压状态。
