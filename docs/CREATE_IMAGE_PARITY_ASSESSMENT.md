# `/create/image` 对标评估：Betty 现状 vs「创视 Studio」专家规格

**日期：** 2026-07-29
**分支：** `cursor/betty-yapper-parity-d257`
**对标规格：** 专家给出的对标 Yapper `/create/image` 的「创视 Studio」完整开发提示词
**目的：** 评估 Betty 现有 image 能力，逐条找出可继续优化点。本文为**只读评估**，未改代码。

---

## 0. 架构前提（先讲清，避免南辕北辙）

专家规格的隐含技术路线是 **自建算力**：本地 Mac mini ComfyUI 集群 + FLUX + `workflow_templates`（ComfyUI JSON）+ 节点心跳/负载均衡/并发限流。

Betty 的实际路线是 **云 API 编排**：
- 适配器 `app/adapters/*`（KIE / Replicate / OpenAI / Kling / Seedance）→ 无自有 GPU。
- 任务队列 Celery + Redis（`app/tasks/image_tasks.py`），非 ComfyUI 节点调度。
- 「调度健康」由 `services/model_health.py`（熔断/隔离/quarantine）+ `fallback_handler.py` + `rate_limiter.py` 承担。

**裁决：** 专家方案里「ComfyUI 集群 / 节点心跳 / workflow JSON 模板 / 每台机并发 1–2」这一整块**不建议照搬**——它是另一条成本/运维路线。但其中两个**思想**值得吸收：①「模型 / 工作流配置化落库」提升扩展性；②「并发与节点健康可观测」。其余「用户可见的 image 页面功能」才是与 Yapper 对标、且 ROI 最高的优化区。

---

## 1. 八大功能模块对照（用户可见层）

图例：✅ 完整 · 🟡 部分 · ❌ 缺失。证据均来自只读代码审计。

| # | 专家规格 | Betty 现状 | 判定 | 关键证据 |
|---|----------|-----------|------|----------|
| 1 | Prompt 输入（文本 + 1–4 参考图 + 预览/删除/排序 + 历史一键再编辑） | 文本✅；拖拽/点击上传✅；预览+删除✅；**无排序**；remix 参考图**不进预览条**；结果区无「再次编辑」按钮 | 🟡 | `CosmicPromptCard.tsx` 上传/预览；`create/image/page.tsx` remix 仅提交时用 |
| 2 | 模型选择器（名称/标签/单张积分 + 切换实时更新预估） | 切换 UI✅；Fast/Pro 标签🟡；**模型旁无单张积分**；**切换不更新预估积分**（API 已返回 `estimated_cost_credits`，前端未用） | 🟡 | `ParameterPanel.tsx`；`api.ts GenerateResponse.estimated_cost_credits` 未消费 |
| 3 | 宽高比（1:1/16:9/9:16/4:3/3:4 + 自定义） | 有 1:1/16:9/9:16/4:3/**3:2**；**缺 3:4**（extend 页有）；**无自定义宽高** | 🟡 | `ParameterPanel.tsx ASPECT_RATIOS`；`page.tsx` 硬编码映射 |
| 4 | 生成数量 1/2/4 | 提供 1/2/4/**8**（后端 `count` ≤4，前端可选 8 与后端不一致） | 🟡 | `ParameterPanel.tsx COUNTS`；`generate.py count le=4` |
| 5 | 高级参数（Seed/Steps/CFG/Negative/高清修复） | Seed 后端✅但**无手输 UI**（仅 vary/reproduce）；Steps/CFG/Negative/高清修复**全缺** | 🟡→❌ | `generate.py seed`；前端无 steps/cfg/negative |
| 6 | 进度（Idle→Submitting→Queued→Generating→Success/Failed + 队列位/取消/重试） | 2s 轮询✅；进度条+阶段🟡；重试✅；**无队列位置**；**无取消按钮**；取消 API 为软置态（不 revoke celery）；WS 实现存在但**死代码未接入** | 🟡 | `page.tsx` 递归 poll；`tasks.py cancel` 仅置 `cancelled`；`SubmitResult.tsx` WS 未 import |
| 7 | 结果画廊（网格/放大/下载/复制 prompt/再编辑/加会话/批量下载/参数展示） | 网格✅；下载✅；model+seed🟡；**缺 lightbox / 复制 prompt / 再编辑 / 加会话 / 批量下载 / 耗时·积分** | 🟡 | `page.tsx` 结果网格；`ResultGrid.onEdit` 未使用 |
| 8 | Sessions（列表/新建/重命名/删除/切换加载/自动归属） | 独立 `/sessions` 存在但**仅 Director Agent**；create/image **未集成 sessions**；图片生成**不归属会话** | ❌ | `sessions/page.tsx` 拉 `/director/sessions`；`submitGeneration` 无 `session_uid` |
| 9 | Image Apps（editor/product/headshots/photo-packs/extend/upscale/bg-remove） | editor/extend/upscale/bg-remove **完整**（`ImageToolStudio`）；product/headshots **薄壳 redirect**；photo-packs 为目录页 | 🟡 | `image-editor/extend/upscale/bg-remove` 用 `ImageToolStudio`；`product/headshots` `router.replace` |

---

## 2. 数据库对照

| 专家实体 | Betty 表 | 判定 | 说明 |
|----------|----------|------|------|
| users（积分/套餐） | `users` + `user_balance` | ✅ | role/plan_credits/rollover 齐 |
| sessions | `director_sessions` | 🟡 | 仅 Director；无 image 会话归属 |
| generations | `tasks` | ✅ | status/params/results/cost/error 齐 |
| assets | `assets` | ✅ | 上传图；生成图在 `task.results` |
| models | — | ❌ | 无 models 表，模型在**代码** `adapters/registry.py`（76）+ `models_info.MODELS`（active 9） |
| workflow_templates | — | ❌ | 无模板表；「模板」是代码内 director scenarios / prompt packs，非配置化 |
| credit_transactions | `transactions` | ✅ | type/amount/balance/model 齐 |

**优化点：** `models` 与 `workflow_templates` 落库是专家 NFR「新增模型/模板只加配置不改核心」的核心，Betty 当前靠改代码升架。这是**扩展性**层面真实可优化项。

---

## 3. API 对照

| 专家 API | Betty | 判定 |
|----------|-------|------|
| POST /generate | `POST /api/v1/generate/` | ✅（含 reference_images≤4、seed、count） |
| GET /tasks/{id} | `GET /api/v1/tasks/{id}` | ✅ |
| POST /tasks/{id}/cancel | 有 | 🟡 软取消（置态，不中断 worker） |
| GET /models | `GET /api/v1/models` | ✅ |
| GET/POST /sessions | Director sessions | 🟡 非 image |
| 登录注册/积分 | auth + billing | ✅ |

---

## 4. 非功能性对照

| NFR | Betty | 判定 |
|-----|-------|------|
| 稳定性/重调度 | `fallback_handler` + `model_health` 熔断/隔离 | ✅（云 API 版） |
| 并发控制 | `rate_limiter`（RPM/RPH）；无「每节点 1–2」（无节点） | 🟡 不适用 |
| 安全（越权/文件限制） | task/asset 按 `user_id` 隔离；extract 限 25MB | ✅ |
| 可观测（日志/节点/耗时） | `/system/slo` + `catalog` + smoke | 🟡 无节点态（无节点） |
| 扩展性（配置化） | 模型/模板在代码 | 🟡 见 §2 |

---

## 5. 可继续优化点（按 ROI 排序）

### P0 · 低成本高感知（前端接线为主，后端已就绪）
1. **模型旁实时积分预估** — API 已返回 `estimated_cost_credits`，前端仅需消费并在模型/数量变更时刷新。改动小、体感强。
2. **结果画廊补齐** — lightbox 放大、复制 prompt、显示耗时/积分、批量下载。组件 `ResultGrid.onEdit` 已存在，接线即可。
3. **参考图体验** — remix 参考图进预览条、4 张 UI 上限提示、拖拽排序。
4. **宽高比对齐** — 补 `3:4`；把已有 720p–4K resolution UI 真正接进提交（当前被硬编码映射忽略）；数量 8 与后端 ≤4 对齐。

### P1 · 中成本（补齐创作闭环）
5. **高级参数 UI** — Seed 手输（后端已支持）+ Negative Prompt（需适配器透传，部分模型支持）。Steps/CFG 仅对开放这些参的模型暴露，云 API 多数不支持，宜按模型能力条件渲染，勿全量假装。
6. **进度升级** — 复活 `SubmitResult` 的 WebSocket 推送替代 2s 轮询；加真正「可取消」（celery revoke + worker 协作中断）；有队列信息时展示队列位。
7. **Sessions 嵌入创作页** — 让 image 生成可归属会话（新增 image 会话或复用 director_session），左栏会话列表 + 切换加载历史。这是与 Yapper 体验差最明显的一项，但需后端会话-任务关联建模。

### P2 · 高成本（场景化第二期）
8. **product / headshots 从薄壳升级为批量 SKU 管线** — 多角度/多风格批量出图 + 打包下载，替代当前 prompt-pack redirect。
9. **models / workflow_templates 落库** — 把模型与「模板」配置化，支撑 NFR 扩展性与后续教育模板。

### 架构路线（可选，非对标必需）
10. 若要**降本/自主可控**，可加一个 **ComfyUI/本地 provider 适配器** 作为云 API 的并列 provider（复用现有 `BaseModelAdapter` + `model_health` 调度），无需推翻现架构即可吸收专家方案的自建算力思想。

---

## 6. 诚实边界（勿夸大）

1. Betty 无 ComfyUI 集群 / 自有 GPU；「集群调度/节点心跳/负载均衡」在云 API 路线下由熔断+限流+fallback 等价承担，**不是**同一实现。
2. `cancel` 当前为软置态，**不保证**中断已在跑的上游任务与计费。
3. Steps/CFG/Negative 对多数云 API 模型不可透传；不应为对标而做「假参数」UI。
4. Sessions 现仅服务 Director；create/image 归属会话需要真实建模，非纯前端。
5. 本文为静态代码评估，未运行 live 出图复验；功能判定以代码路径为准。

---

## 7. 一句话结论

Betty 的 `/create/image` **后端契约与工具链已相当完整**（生成/编辑/超分/抠图/扩图/多参考 i2i/积分/退款全通），差距集中在**前端创作闭环的完成度**：实时积分、结果画廊操作、参考图体验、Sessions 归属、进度可取消。这些 **P0/P1 多为前端接线**（后端字段大多已具备），是继续优化 ROI 最高的区域；而专家规格的 ComfyUI 自建集群属于**另一条算力路线**，按需再议，不必照搬。
