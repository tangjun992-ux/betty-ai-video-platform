# Betty 企业级大模型 API Gateway 方案

> 目标：消除「单一 KIE 提供商」单点风险，对标 Yapper/Dzine 的多模型策略，在任何情况下保证模型调用的稳定性、可切换性与可观测性。

---

## 1. 现状诊断

### 1.1 已有能力（可复用）

| 模块 | 位置 | 能力 |
|------|------|------|
| Adapter Registry | `app/adapters/registry.py` | 模型 ID → Adapter 查找 |
| PromptRouter | `app/router.py` | Auto 路由 + 风格评分 |
| Fallback Handler | `app/fallback_handler.py` | 同模型族 fallback（seedance ↔ fast） |
| Model Health | `app/services/model_health.py` | Redis 熔断 + 隔离 + 评分 |
| Model Catalog | `app/services/model_catalog.py` | verified / guess 治理 |
| Demo Provider | `app/adapters/demo_provider.py` | 无 Key 离线预览 |

### 1.2 核心风险

1. **90%+ 流量硬绑 KIE**：`KieAdapter._submit_and_poll()` 是唯一生产通道
2. **10+ 调用点绕过 Registry**：lipsync / motion / face_swap / performance / director 直接 `KieAdapter()`
3. **扩展能力不在 BaseAdapter 契约内**：TTS / lipsync / motion / edit 无法跨 Provider 切换
4. **Provider 级健康缺失**：熔断粒度是 `model_id`，不是 `provider + sku`
5. **LLM 与 Media 路由分裂**：director_brain 走 OpenAI/KIE `/v1`，与生成层无统一治理

---

## 2. Yapper 类平台的模型策略（推断 + 对标）

Yapper 对外展示 **37+ 模型货架**，用户只选「能力 + 质量档位」，不感知底层 Provider。

| 策略 | Yapper 做法 | Betty 应对 |
|------|------------|-----------|
| **统一 SKU** | 用户选 `Seedance 2.0`，不是选 KIE/Replicate | Betty `model_id` 已是统一 SKU，保留 |
| **Provider 抽象** | 后端多网关/多 Key 池 | Gateway `provider chain` |
| **质量档位** | Fast / Pro / Studio | 已有 seedance-fast、motion-control-studio |
| **Auto 路由** | 按 prompt 风格 + 健康分 | 已有 PromptRouter + model_health |
| **降级不中断** | 429/503 → 换 Provider 或换模型 | Gateway executor fallback chain |
| **诚实治理** | Beta/Lab 标签 | 已有 verified/guess 治理 |
| **成本透明** | 生成前显示 credits | 已有 estimate_cost |

---

## 3. 开源方案选型

### 3.1 按能力分层

```
┌─────────────────────────────────────────────────────────────┐
│                    Betty Application                         │
│  generate.py · director.py · Celery tasks · PromptRouter    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              Betty Model Gateway (自研 · 本方案)               │
│  统一 SKU · Provider Chain · 熔断 · 成本 · 审计日志          │
└──────┬──────────────┬──────────────┬────────────────────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐
│ KIE Backend │ │ Replicate │ │ Direct APIs │
│ (主通道)     │ │ (备通道)   │ │ Seedance/   │
│             │ │           │ │ Kling/OpenAI│
└─────────────┘ └───────────┘ └─────────────┘

┌─────────────────────────────────────────────────────────────┐
│         LiteLLM Proxy (可选 · LLM 专用)                      │
│  Director Brain · Prompt Extract · Chat 类能力               │
│  100+ LLM · Virtual Keys · Spend Limits · Fallback YAML     │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 方案对比

| 方案 | 适用 | 优势 | 局限 |
|------|------|------|------|
| **LiteLLM** | LLM（chat/completion/vision） | MIT、100+ Provider、YAML fallback、Virtual Keys | **不覆盖** KIE 异步 task 协议（createTask/poll） |
| **Portkey** | LLM + 部分 Agent | 托管 SLA、语义缓存、可观测 | 媒体生成非核心；托管有 vendor lock-in |
| **OpenRouter** | LLM 快速接入 | 400+ 模型 marketplace | 无 SLA；不适合视频/i2v 长任务 |
| **Betty Gateway（自研）** | Image/Video/Audio/Lipsync | 完全匹配 KIE task 协议 + 多 Provider | 需自行运维 |

**结论**：
- **媒体生成（image/video/lipsync/motion/TTS）** → Betty 自研 Gateway（本 PR 开始落地）
- **LLM（Director Brain / Prompt Extract）** → 推荐 LiteLLM Proxy 作为 Phase 2（OpenAI-compatible，零改代码）

---

## 4. 目标架构

### 4.1 核心概念

```
Capability（能力）     image.generate | video.generate | lipsync | motion | tts | llm.chat
       ↓
Model SKU（统一模型）   seedance-2.0 | gpt-image-2 | kling-2.5-turbo
       ↓
Route（路由表）         routes.yaml — 有序 Provider Chain
       ↓
Provider Target         { provider: kie, remote_model: "bytedance/seedance-2", priority: 1 }
       ↓
Backend Executor        提交 → 轮询 → 结果归一化 → 记录 health/cost
```

### 4.2 Provider Chain 示例

```yaml
# routes.yaml 片段
routes:
  - capability: image.generate
    model: gpt-image-2
    chain:
      - { provider: kie, remote_model: gpt-image-2-text-to-image, priority: 1 }
      - { provider: replicate, remote_model: black-forest-labs/flux-1.1-pro, priority: 2, fallback_only: true }

  - capability: video.generate
    model: seedance-2.0
    chain:
      - { provider: kie, remote_model: bytedance/seedance-2, priority: 1 }
      - { provider: replicate, remote_model: wan-video/wan-2.1-1.3b, priority: 2, fallback_only: true }

  - capability: lipsync
    model: kling-ai-avatar
    chain:
      - { provider: kie, remote_model: kling/ai-avatar-pro, priority: 1 }
      - { provider: kie, remote_model: infinitalk/from-audio, priority: 2, fallback_only: true }
```

### 4.4 切换策略矩阵

| 触发条件 | 动作 | 示例 |
|----------|------|------|
| HTTP 429 / 503 / 502 | 同 SKU 下一 Provider | KIE Seedance → Replicate Wan |
| Queue timeout (>240s) | 换 fallback 模型 | seedance-2.0 → seedance-2.0-fast |
| Provider circuit open | 跳过该 Provider 全部 target | KIE 熔断 → 仅 Replicate |
| Content policy | **不 fallback**，直接失败 | NSFW guardrail |
| API Key 缺失 | **不 fallback**，配置错误 | 运维告警 |
| Credits insufficient | **不 fallback**，用户侧错误 | 提示充值 |
| 连续 3 次 soft fail | Provider 级 5min 熔断 | model_health 已有 |

---

## 5. 模块设计

### 5.1 目录结构（已实现 Phase 1）

```
backend/app/gateway/
├── __init__.py          # 导出 gateway 单例
├── types.py             # Capability, RouteDefinition, ExecutionResult
├── config.py            # 加载 routes.yaml + env 覆盖
├── routes.yaml          # Provider Chain 配置（可热更新）
├── router.py            # SKU → 有序 target 列表（过滤熔断/Region/灰度）
├── executor.py          # 链式执行 + retry + 审计 + 预算
├── facade.py            # 对外统一 API（generate_image/video/...）
├── health.py            # Provider 级健康（extends model_health）
├── registry.py          # Redis 运行时禁用 / Kill Switch（Phase 3）
├── budget.py            # 用户/团队日额度（Phase 3）
├── metrics.py           # 请求 / fallback 计数（Phase 3）
├── assets.py            # 公开 URL 上传（Phase 2）
├── kie_keys.py          # KIE Key 池轮换（Phase 2）
└── providers/
    ├── base.py          # ProviderBackend Protocol
    ├── kie.py           # KIE createTask/poll 封装
    ├── replicate.py     # Replicate prediction 封装
    ├── seedance.py      # Seedance 直连（Phase 3）
    └── kling.py         # Kling 直连（Phase 3）
```

### 5.2 GatewayFacade 对外契约

```python
# 所有 Celery task / API / Director 应通过此入口，禁止直接 KieAdapter()
result = await gateway.generate_image(
    model="gpt-image-2",
    prompt="...",
    size="1024x1024",
    trace_id=task_id,  # 可观测性
)
# result.provider_used, result.model_used, result.fallback_used, result.cost
```

### 5.3 与现有模块集成

| 调用方 | 当前 | Phase 1 | Phase 2 |
|--------|------|---------|---------|
| `image_tasks.py` | registry → KIE | **gateway facade** | 全量 |
| `video_tasks.py` | registry → KIE | gateway facade | 全量 |
| `lipsync_tasks.py` | KieAdapter() | gateway facade | 全量 |
| `motion_tasks.py` | KieAdapter() | gateway facade | 全量 |
| `director.py` | 混合 | gateway facade | 全量 |
| `director_brain.py` | OpenAI/KIE LLM | LiteLLM proxy | LiteLLM |

---

## 6. 部署拓扑

### 6.1 推荐生产架构

```
                    ┌─────────────┐
                    │   CDN/S3    │
                    └──────▲──────┘
                           │
┌──────────┐    ┌──────────┴──────────┐    ┌─────────────┐
│ Frontend │───▶│  FastAPI (N replicas)│───▶│  Postgres   │
└──────────┘    └──────────┬──────────┘    └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌─────────┐  ┌──────────┐
        │ Redis   │  │ Celery  │  │ LiteLLM  │  ← 可选，LLM 专用
        │ health  │  │ workers │  │ :4000    │
        │ rate    │  │         │  └────┬─────┘
        └─────────┘  └────┬────┘       │
                          │            ▼
                          ▼      OpenAI / Anthropic / KIE /v1
                    Betty Gateway
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
           KIE.ai    Replicate    Direct APIs
         (主, 2 Key)  (备)      (Seedance/Kling)
```

### 6.2 环境变量

```bash
# Gateway 总开关
GATEWAY_ENABLED=true
GATEWAY_ROUTES_PATH=app/gateway/routes.yaml

# Provider Keys（至少配 2 个 Provider 才有意义）
KIE_API_KEY=...
KIE_API_KEY_BACKUP=...          # Key 池轮换
REPLICATE_API_KEY=...

# LiteLLM（Phase 2 — LLM）
LITELLM_PROXY_URL=http://litellm:4000
LITELLM_MASTER_KEY=...

# 熔断
GATEWAY_CIRCUIT_FAILURES=3
GATEWAY_CIRCUIT_TTL_SECONDS=300

# Phase 3 — Region / 预算 / 灰度
GATEWAY_REGION=cn              # cn | us | eu（空 = global）
GATEWAY_USER_DAILY_CREDIT_CAP=0   # 0 = 不限
GATEWAY_TEAM_DAILY_CREDIT_CAP=0

# Direct API backends（Phase 3）
SEEDANCE_API_KEY=...
KLING_ACCESS_KEY=...
KLING_SECRET_KEY=...
```

### 6.3 Docker Compose 增量（Phase 2）

```yaml
  litellm:
    image: ghcr.io/berriai/litellm:main-stable
    volumes:
      - ./infra/litellm/config.yaml:/app/config.yaml
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://redis:6379/3
    command: ["--config", "/app/config.yaml"]
    ports:
      - "4000:4000"
```

---

## 7. 可观测性

| 维度 | 实现 |
|------|------|
| **Trace ID** | 每个 generation 携带 `task_id` / `request_id` |
| **Structured Log** | `[gateway] capability=... model=... provider=... latency_ms=... fallback=...` |
| **Metrics** | Prometheus: `gateway_requests_total{provider,status}`, `gateway_fallback_total` |
| **Health API** | `GET /api/v1/gateway/health` — Provider 状态 + 熔断 + 路由表版本 |
| **Cost Ledger** | 写入 task.actual_cost + provider 维度 meta |
| **Sentry** | Provider 连续失败 → breadcrumb + alert |

---

## 8. 实施路线图

### Phase 1 — 本 PR（Foundation）

- [x] Gateway 核心模块 + routes.yaml
- [x] KIE / Replicate Provider Backend
- [x] Executor（链式 fallback + 熔断过滤）
- [x] GatewayFacade + image_tasks 接入
- [x] 单元测试
- [x] 本文档

### Phase 2 — Provider 全覆盖（本 PR）

- [x] video / lipsync / motion / face_swap / performance Celery tasks → gateway facade
- [x] generate.py `/speech` + `/edit` → gateway
- [x] director.py TTS / lipsync / edit / upload → gateway
- [x] KIE Key 池轮换（`KIE_API_KEY` + `KIE_API_KEY_BACKUP`）
- [x] Asset Gateway（`upload_public_url` / `publicize_url`）
- [x] `GET /api/v1/gateway/health` 公开健康端点
- [x] LiteLLM 配置模板 + director_brain 优先走 LiteLLM Proxy
- [x] Direct API backends（Seedance/Kling 直连 — Phase 3）
- [x] Docker Compose 内置 litellm 服务

### Phase 3 — 企业级（本 PR）

- [x] Admin UI：Gateway 控制台（`/admin/gateway`）— 健康、Kill Switch、Provider 下线
- [x] Admin API：`/api/v1/admin/gateway/*` — reload、disable/enable、reset-circuit、kill-switch
- [x] Redis Registry：运行时 Provider 禁用 + Kill Switch + 版本号
- [x] A/B 灰度：`canary_percent` + `trace_id` 稳定分桶（seedance-2.0 5% cn）
- [x] Region 路由：`GATEWAY_REGION` 过滤 chain 中的 `region` 字段
- [x] 预算上限：`GATEWAY_USER_DAILY_CREDIT_CAP` / `GATEWAY_TEAM_DAILY_CREDIT_CAP`
- [x] Gateway Metrics：Redis 请求 / fallback 计数
- [x] Webhook 增强：task 完成回调 payload 含 `gateway` 元数据
### Phase 4 — 生产硬化（本 PR）

- [x] Celery 任务传入 `user_id` / `team_id` / `estimated_cost`（预算真正生效）
- [x] 图像工具全路由：`face_swap` / `upscale` / `remove_bg` / `extend` → `execute_route`
- [x] Gateway Admin 操作接入 `record_audit()` 审计日志
- [x] Prometheus 指标：`betty_gateway_requests_total` / `betty_gateway_fallback_total`
- [x] 生成幂等：已完成任务跳过 + Redis 执行锁
- [x] `GATEWAY_ROUTES_PATH` 支持自定义路由文件
- [x] 生产公开 health 最小化（`GATEWAY_HEALTH_PUBLIC_MINIMAL`）
- [x] `model_smoke` live 探测走 Gateway
- [x] 生产 compose + `.env.example` 补全 Replicate / KIE backup / Gateway env

### Phase 5 — 生产抛光（本 PR）

- [x] 移除 motion_tasks legacy KieAdapter/registry fallback（Gateway 唯一路径）
- [x] Provider 级 RPM + 并发背压（`GATEWAY_PROVIDER_RPM` / `GATEWAY_PROVIDER_MAX_INFLIGHT`）
- [x] Gateway Admin HTTP 集成测试
- [x] Grafana Dashboard 模板（`infra/grafana/betty-gateway-dashboard.json`）
- [x] 前端 Admin 侧栏入口 + `is_admin` 暴露于 auth/settings API
- [x] lipsync publicize 统一走 Gateway assets

### Phase 6 — 收尾硬化（本 PR）

- [x] image/video Celery fallback 在 Gateway 模式下走 `gateway.generate_*`（不再旁路 registry adapter）
- [x] face_swap Gateway-only（移除 `gateway_enabled=false` 时直连 KieAdapter）
- [x] `validate_routes()` 启动校验 + Admin reload 前置校验
- [x] Prometheus `betty_gateway_provider_inflight` + Admin 预算/背压展示
- [x] Grafana 导入文档（`infra/grafana/README.md`）
- [x] Phase 6 单元测试

---

## 9. 风险与决策

| 风险 | 缓解 |
|------|------|
| Replicate 模型与 KIE SKU 输出质量不一致 | fallback 仅在同 capability 内；UI 标注「备用引擎」 |
| 双 Provider 成本不可控 | fallback_only 标记 + 成本上限 env |
| routes.yaml 配置错误 | 启动时 schema 校验 + CI 测试 |
| LiteLLM 与 Betty Gateway 职责重叠 | 严格分层：LLM→LiteLLM，Media→Betty Gateway |

---

## 10. 参考

- [LiteLLM Proxy Docs](https://docs.litellm.ai/docs/proxy/quick_start)
- [Portkey Routing & Fallbacks](https://portkey.ai/docs/product/ai-gateway/routing)
- Betty 内部：`app/adapters/kie_adapter.py`、`app/fallback_handler.py`、`app/services/model_health.py`
- Yapper 对标评估：`docs/YAPPER_PROFESSIONAL_EVALUATION.md`
