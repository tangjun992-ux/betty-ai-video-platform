# Betty × 世界顶级平台多维对标评估（完整版）

**评估日：** 2026-07-16（含 P0–P2 全套后）  
**评估原则：** 区分「产品表面 / 工程链路 / 真出片 / 商业闭环」四层；分数基于本仓库代码 + 本环境实测，**不采信营销口径**。  
**Betty 定位：** **多模型网关 AI 工作室（Yapper 类聚合器）**——不是 Runway / Kling / Luma / Midjourney / OpenAI 一等公民模型厂。

**本环境硬探针（评估锚点）：**

| 探针 | 结果 |
|------|------|
| 模型目录 | **9 active + 8 beta + 20 lab**（默认列表仅 active） |
| demo_mode | **false**（有 KIE Key，可走真 Adapter） |
| fixture harness | **12/12 passed**（含 Motion 样片库） |
| pytest | **171** 用例可收集 |
| Stripe / CDN / SSO | **均未配置密钥**（`subscription_ready=false`，存储 local） |
| live 图片（历史） | **2/4** active 真出图 |
| live 视频 | **0 次** 本环境成功出片记录 |

---

## 0. 一句话总判

| 对标对象 | 结论 |
|----------|------|
| **Yapper** | 最近竞品；工具契约约 **90–92%** 对齐，主差距在**出片稳定、默认成片感、社区飞轮** |
| **Kling / Runway / Luma** | 可借道网关调用部分 SKU，**无原生模型护城河**；Motion/视频质量**禁止宣称对等** |
| **Midjourney / OpenAI** | 审美社区与一等公民模型差距大；Betty 是工具聚合，不是审美飞轮 |
| **综合生产就绪** | **~78 / 100** — Yapper 核心全测 + Extractor/Avatar 后；**真出片 + 生产密钥**仍是天花板 |

---

## 1. 评估方法（必须先读）

### 1.1 四层评分，禁止混层

| 层 | 问什么 | Betty 现状 |
|----|--------|------------|
| L1 产品表面 | 有没有页面/按钮/文案 | **强**（12 create + Agent + Teams…） |
| L2 工程链路 | 鉴权→扣费→任务→轮询→失败退款→观测 | **中上**（P0–P2 大量补齐） |
| L3 真出片 | 付费 live 是否稳定产出可用帧 | **弱**（视频 0；图片 2/4） |
| L4 商业闭环 | Stripe 订阅真收款、CDN、SSO、SLA | **骨架就绪、密钥未注** |

> 只拿 L1 对标顶级平台 = **虚假 parity**。本评估以 L2–L4 加权为主。

### 1.2 加权模型（Betty 综合就绪）

| 维度簇 | 权重 | 代表维度 |
|--------|------|----------|
| 核心生成质量 | **30%** | 文生图 / 文生视频 / Motion / 唇形 |
| 工作室工作流 | **25%** | 工具矩阵 / 时间线 / Agent / 编辑工具 |
| 信任与目录 | **15%** | 目录诚实 / 可观测 / 分享门闩 |
| 商业与企业 | **20%** | 计费订阅 / SSO·协作 / Developer API |
| 社区与生态 | **10%** | 分享 Remix / 品牌飞轮 |

竞品分值为**行业经验定位分**（非第三方审计），用于相对坐标，不用于宣称「已超越」。

### 1.3 分档含义

| 分 | 含义 |
|----|------|
| 90–100 | 该维生产可运营，有 live/商业证据 |
| 70–89 | 内测可用，主路径通，缺稳定或密钥 |
| 50–69 | 演示可用，真实用户会踩坑 |
| 30–49 | 骨架 / best-effort |
| &lt;30 | 断链或不可对外 |

---

## 2. 多维雷达（0–100）

| 维度 | Betty | Yapper* | Kling* | Runway* | Luma* | Midjourney* | OpenAI* | 说明 |
|------|-------|---------|--------|---------|-------|-------------|---------|------|
| 产品工具矩阵 | **92** | 90 | 70 | 85 | 65 | 40 | 55 | Extractor/Avatar/Tools 真路由对齐 Yapper |
| 文生图稳定性 | **62** | 75 | 55 | 60 | 50 | **92** | **88** | Betty live 2/4；MJ/OpenAI 一等公民 |
| 文生视频稳定性 | **45** | 70 | **92** | **90** | **85** | 35 | **80** | Betty **0** live_video 成功记录 |
| Motion / 动作 | **52** | 55 | **88** | **90** | 50 | 20 | 40 | 样片库+best-effort；≠ Act-One |
| 唇形同步 | **60** | 65 | 75 | 55 | 40 | 15 | 45 | 链路有；fixture live 未做 |
| 时间线 / 合成 | **72** | 70 | 40 | **88** | 45 | 20 | 35 | ffmpeg 可靠；弱于生成式剪辑 |
| Agent / 多镜 | **78** | 75 | 40 | 70 | 35 | 25 | 55 | 真分镜 API；子任务 live 仍拖累 |
| Developer API | **75** | 70 | **85** | **88** | 70 | 30 | **95** | HMAC webhook + public generate |
| 社区 / Remix | **78** | **88** | 60 | 65 | 55 | **95** | 50 | publish 门闩有；氛围弱 |
| 计费订阅 | **72** | **85** | 80 | 85 | 75 | 80 | **90** | bootstrap 就绪；无真实 Price |
| 企业 SSO / 协作 | **58** | 55 | 45 | **75** | 40 | 30 | **70** | OIDC 代码齐；未接 IdP |
| 目录诚实 / 信任 | **80** | 70 | 75 | 80 | 70 | 60 | 75 | active/beta/lab；guess 折叠 |
| 可观测 / 运维 | **76** | 60 | 70 | 75 | 55 | 40 | **85** | 冒烟 KPI、隔离、readiness |
| **加权综合** | **~78** | **~74** | **~72** | **~78** | **~58** | **~55** | **~72** | Betty 工具契约≈Yapper；弱于 Runway 视频护城河 |

\*竞品分为相对定位估计。

### 2.1 象限定位（战略）

```
高模型护城河
      │  Kling · Runway · Luma · OpenAI(Sora)
      │
      │                    ★ Midjourney（审美社区）
      │
低工具面 ──────────────┼──────────────── 高工具面
      │
      │         ★ Betty ≈ Yapper
      │         （多模型网关工作室）
      │
低模型护城河
```

**Betty 正确战场：** 与 Yapper 抢「一站式多模型工作室」；  
**错误战场：** 宣称「全面对标 Kling/Runway Motion/视频质量」。

---

## 3. 分平台深度对标

### 3.1 vs Yapper（最近竞品 · 主战场）

| 能力 | Betty | Yapper（典型） | 差距性质 |
|------|-------|----------------|----------|
| 创建工具矩阵 | 12 create + Agent | 同类工作室面 | **表面接近** |
| 模型货架诚实 | 9 active + lab 折叠 | 往往包装更「成片」 | Betty **更诚实** |
| 出片稳定 | 图 2/4；视频 0 | 通常更高默认成功率 | **Betty 主短板** |
| Agent/分镜 | 真 storyboard steps | 多轮编排体验 | 体验 polish |
| 社区 Explore | share/publish/Remix | 内容供给更强 | 飞轮 |
| 订阅收款 | 代码+bootstrap | 真收款运营 | **密钥未注** |
| 工程可观测 | readiness/冒烟/隔离 | 参差 | Betty **偏强** |

**结论：** 对 Yapper 可打「功能对齐 + 目录更诚实 + 工程可观测」；不可打「出片已全面超越」。胜负手 = **live 稳定率 + 默认模型成片感**。

### 3.2 vs Kling（视频原生厂）

| 能力 | Betty | Kling | 差距 |
|------|-------|-------|------|
| 文生/图生视频 | 经 KIE 调 Kling 等 SKU | 原生训练+产品闭环 | 排队/失败/SLA 不可控 |
| Motion Control | best-effort + 输入样片 | 原生 Motion | **巨大** |
| 唇形 | 网关链路 | 专用路径更稳 | 中 |
| 工作室剪辑 | timeline ffmpeg | 偏生成侧 | Betty 工具面略宽 |
| API/生态 | webhook+public | 官方 API 成熟 | Kling 更强 |

**结论：** Betty 是 **Kling 能力的转售/编排层**，不是替代品。对外只能说「可调用 Kling 类 SKU（视上游可用性）」。

### 3.3 vs Runway（创意工作室 + 模型）

| 能力 | Betty | Runway | 差距 |
|------|-------|--------|------|
| Gen 系列 | lab/guess，默认隐藏 | Gen-3/4 一等公民 | **不可对标宣传** |
| Act-One / Motion | 无原生 | 标志能力 | **禁止对标** |
| 时间线 | 本地合成可靠 | 生成式剪辑工作台 | Runway 深 |
| API / 企业 | 有骨架 | 生态+SLA | Runway 强 |
| 多模型货架 | Betty 更广（聚合） | 自有为主 | Betty 宽度优势 |

**结论：** 工具矩阵可部分对谈；**模型与 Motion 不可对谈**。Runway 综合约 **~78**，Betty **~76**——数字接近来自 Betty 工具/工程分，**不代表视频质量接近**。

### 3.4 vs Luma / Pika

| 平台 | Betty 相对位置 |
|------|----------------|
| Luma Ray | 目录 **lab only**；无 verified 活跃出片路径 |
| Pika | 同上；社交/创意短视频体验 Betty 未建模 |

**结论：** 这两家不是功能矩阵对手，是**上游候选**；未 verified 前不得进默认卖点。

### 3.5 vs Midjourney

| 维 | Betty | Midjourney |
|----|-------|------------|
| 图片审美与社区 | 网关模型 | Discord/Web 审美飞轮 **断层领先** |
| 视频 | 有路径但不稳 | 非主战场（历史） |
| 工作室工具 | Betty 远宽 | MJ 偏生成社区 |
| 商业 | 订阅代码面 | 成熟订阅 |

**结论：** 不要用「AI 创作平台」笼统对标 MJ；Betty 赢在**工具链**，输在**审美与社区**。

### 3.6 vs OpenAI（GPT-Image / Sora 等）

| 维 | Betty | OpenAI |
|----|--------|--------|
| 图片 | 可调 GPT-Image 类 SKU | 一等公民 + ChatGPT 分发 |
| 视频 | 无 Sora 官方一等路径（lab/guess 折叠） | Sora 产品化 |
| API | 自有 Developer API | 行业标准 API |
| 企业 | OIDC 骨架 | SSO/合规成熟 |

**结论：** Betty 是 **OpenAI 能力的可选上游之一**，不是 ChatGPT/Sora 替代。

### 3.7 vs 剪映 / CapCut（大众创作工具，参照系）

| 维 | Betty | 剪映/CapCut |
|----|--------|-------------|
| 受众 | AI 生成工作室 / 创作者-开发者 | 大众剪辑 |
| AI 生成深度 | 多模型生成主路径 | 模板+轻量 AI |
| 时间线 | 基础合成 | **行业级剪辑** |
| 分发 | 弱 | 强（生态） |

**结论：** 时间线维度 Betty **不应宣称对标剪映**；定位不同。

---

## 4. 四层切片：Betty 真实水位

### 4.1 L1 产品表面 — **~88**

12 个 create 路由（image/video/lipsync/motion/timeline/audio/avatar/upscale/bg-remove/extend/extract/image-editor）+ Director Agent + Library/Projects/Teams/Gallery。  
**这是对标叙事最容易夸大的一层。**

### 4.2 L2 工程链路 — **~78**

已验证具备：积分预扣、失败幂等退款、分享 publish 门闩、Webhook HMAC、Developer `execute_generation`、真分镜、工具成本看板、OIDC/CDN/Stripe readiness 门禁、fixture harness。  
**相对 Yapper：工程诚实度与可观测是差异化资产。**

### 4.3 L3 真出片 — **~48**

| 证据 | 状态 |
|------|------|
| active 图片 live | 历史 **2/4** |
| active 视频 live | **0** 成功记录 |
| Motion/Lipsync fixture live | 未跑付费 |
| mapping 冒烟 9/9 | **≠ 出片** |

这是对标 Kling/Runway 时的**致命短板**；也是综合分无法诚实冲到 80+ 的主因。

### 4.4 L4 商业闭环 — **~55（本环境）/ 代码面 ~72**

| 项 | 代码 | 本环境 |
|----|------|--------|
| Stripe Price bootstrap | ✅ | 无 Key，无真实 `price_*` |
| Webhook secret | 门禁有 | 未配 |
| CDN / S3 | 门禁有 | `local` |
| OIDC | discovery+FE | 未配 IdP |

开发环境 `readiness.ok=true` **不等于** Production Ready。

---

## 5. 优势 / 短板 / 不可宣称清单

### 5.1 可对外诚实说的优势
1. **多模型工作室工具面完整**（接近 Yapper）  
2. **目录治理诚实**（active/beta/lab；禁止 guess 当卖点）  
3. **工程可观测与门禁**（readiness、隔离、冒烟 KPI、fixture）  
4. **Agent 真分镜 + 工具成本透明**（相对聚合器同行偏强）  
5. **失败退款 / 分享隐私门闩**（信任面）

### 5.2 决定「能不能叫顶级」的短板
1. **视频真出片未闭合**  
2. **上游单点依赖（KIE）** → 排队=产品故障  
3. **Motion = best-effort**，无 Act-One/Kling Motion 级质量  
4. **Stripe/CDN/SSO 密钥未注入** → 非生产级 SaaS  
5. **社区与品牌飞轮弱**

### 5.3 对外话术红线（合规/品牌）
| 禁止 | 建议替代 |
|------|----------|
| 「全面对标 Runway / Kling」 | 「多模型 AI 视频工作室，可调用多家上游」 |
| 「专业级动作控制 / Act-One」 | 「运动迁移（best-effort）」 |
| 「Production Ready」 | 「内测可用；订阅/CDN/SSO 配置后可上生产」 |
| 「Sora / Gen-4 已支持」 | lab 折叠，不进默认货架 |

---

## 6. 分数演进与冲刺条件

| 阶段 | 综合就绪 | 备注 |
|------|----------|------|
| 早期表面 parity | ~55 | 页面多、验真少 |
| ROI + 加固 | ~62 | 门禁、冒烟、CI |
| Webhook/分享/ACL | ~63 | 信任面 |
| 路由扩池 + lab 折叠 | ~65 | 工程分↑ |
| P1 退款/分镜/Price 面 | ~74 | 商业与 Agent |
| P2 样片库/OIDC/bootstrap | ~76 | 配置面↑ |
| **Yapper 核心全测 + Extractor/Avatar** | **~78** | 工具契约≈Yapper；出片/密钥仍缺 |

**冲到 80+ 的硬条件（缺一不可）：**
1. live_video 周检稳定 ≥ **2** 个 SKU 真出片  
2. 图片 live ≥ **3/4** active  
3. Stripe Price + Webhook **真实注入**且 staging 收款成功  
4. `STORAGE_TYPE=s3` + CDN 公共基址  
5. OIDC 接真实 IdP 端到端登录  
6. Lipsync / Motion 各至少 **1** 条 fixture live（成败如实记账）

**冲到 85+（对标「顶级工作室」叙事）：** 另需默认模型成片感显著提升，或拿到更稳上游/一等公民合作；纯堆页面无效。

---

## 7. 决策层建议（ROI 序）

1. **叙事定锚**：对外只打 Yapper 类「多模型工作室」；模型质量用 live KPI 说话。  
2. **对内 KPI**：只认 `outframe_ok`（真出帧），禁止把 skip/mapping 算进成功率。  
3. **投入优先级**：  
   `live_video 稳定` → `Stripe+CDN 真注入` → `默认模型成片感` → `OIDC 企业单` → `社区供给`  
   **不要**优先堆新 create 页或新 lab 目录条目。  
4. **商业化门槛**：未完成 Stripe Price + CDN 前，不签「生产 SLA」类客户承诺。  
5. **Motion 策略**：保持 best-effort 文案；若上游出现真 Motion Control SKU，再单独立项映射+live，再考虑升档话术。

---

## 8. 复现实验清单

```bash
cd backend
# 目录与 readiness
curl -s localhost:8000/api/v1/models | jq '{active_count,beta_count,lab_count}'
curl -s localhost:8000/api/v1/system/readiness | jq .
curl -s localhost:8000/api/v1/billing/stripe-status | jq .
curl -s localhost:8000/api/v1/auth/oidc/status | jq .

# 工程契约（非出片）
.venv/bin/python scripts/fixture_derivative_harness.py
.venv/bin/python -m pytest -q --collect-only | tail -1

# 真出片（付费，需显式开门）
MODEL_SMOKE_LIVE=1 .venv/bin/python scripts/smoke_active_models.py
MODEL_SMOKE_LIVE_VIDEO=1 .venv/bin/python scripts/smoke_live_video_sample.py
```

细粒度功能卡：`docs/CORE_FEATURE_FINE_GRAINED_ASSESSMENT.md`  
P1/P2 台账：`docs/P1_*.md`、`docs/P2_MOTION_OIDC_STRIPE.md`
