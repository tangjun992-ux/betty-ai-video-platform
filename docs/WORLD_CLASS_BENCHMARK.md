# Betty × 世界顶级平台多维对标评估

**评估日：** 2026-07-16（含 P0–P2 迭代后）  
**评估原则：** 区分「产品表面 / 工程链路 / 真出片 / 商业闭环」四层；分数基于本仓库代码 + 本环境实测，不采信营销口径。  
**Betty 定位：** **多模型网关 AI 工作室（Yapper 类聚合器）**，不是 Runway / Kling / Luma / Midjourney 一等公民模型厂。

---

## 1. 综合结论（一句话）

| 对标对象 | 结论 |
|----------|------|
| **Yapper** | 最接近的竞品；工作室工具面约 **85–90%** 对齐，主差距在**出片稳定与模型深度** |
| **Kling / Runway / Luma** | 可借道网关调用部分能力，但**无原生模型护城河**；Motion/视频质量不可宣称对等 |
| **Midjourney / OpenAI 一等公民** | 图片体验与社区闭环差距大；Betty 是工具聚合，非审美社区 |
| **综合生产就绪** | **~65 / 100**（内测可用；不可对外宣称「全面对标顶级实验室」） |

---

## 2. 多维雷达（0–100）

| 维度 | Betty | Yapper* | Kling* | Runway* | Luma* | 说明 |
|------|-------|---------|--------|---------|-------|------|
| 产品工具矩阵 | **88** | 90 | 70 | 85 | 65 | Betty 创建页齐全（图/视/唇形/Motion/时间线/工具） |
| 文生图质量稳定性 | **62** | 75 | 55 | 60 | 50 | 实测 2/4 active 图片 live 成功；上游排队影响大 |
| 文生视频质量稳定性 | **45** | 70 | **92** | **90** | **85** | 本环境 **0 次** live_video 真出片验真 |
| Motion / 动作控制 | **48** | 55 | **88** | **90** | 50 | Betty = best-effort；≠ Act-One / Kling Motion |
| 唇形同步 | **60** | 65 | 75 | 55 | 40 | 有真链路；依赖 KIE 排队，未做 fixture live |
| 时间线 / 合成 | **72** | 70 | 40 | **88** | 45 | 本地 ffmpeg 可靠；弱于 Runway 生成式剪辑 |
| Agent / 多镜叙事 | **68** | 75 | 40 | 70 | 35 | Director 有 plan/run；深度依赖子任务 live |
| 开发者 API / Webhook | **75** | 70 | **85** | **88** | 70 | HMAC webhook + `execute_generation` 公开 API（细粒度评估见 CORE_FEATURE_FINE_GRAINED） |
| 社区 / 分享 / Remix | **74** | **88** | 60 | 65 | 55 | 有 explore 分享页；社区氛围弱于 Yapper/MJ |
| 计费订阅闭环 | **42** | **85** | 80 | 85 | 75 | Stripe Price/Webhook **未配置** |
| 企业协作 / SSO | **50** | 55 | 45 | **75** | 40 | 团队积分+ACL+审片骨架；OIDC 未接 IdP |
| 目录诚实 / 信任 | **80** | 70 | 75 | 80 | 70 | active/beta/lab 分层；guess 已折叠 |
| 可观测 / 运维 | **76** | 60 | 70 | 75 | 55 | 冒烟分层 KPI、隔离、状态页、CI |
| **加权综合** | **~65** | **~74** | **~72** | **~78** | **~58** | *竞品分为行业经验估计，非其内部数据 |

\*竞品分用于相对定位，非第三方审计。

---

## 3. 本环境实测基线（硬证据）

| 探针 | 结果 | 解读 |
|------|------|------|
| 目录 | 37 = **9 active** + 8 beta + **20 lab** | lab 默认不进列表 |
| Auto 路由池 | 图片 4 + 视频 5 = **9/9** | 已覆盖全部 verified |
| mapping 冒烟 | **9/9** | 仅证明映射，非出片 |
| live 图片（此前） | **2/4** 真出图 | gpt-image-2、nano-banana；pro/imagen 上游失败 |
| live 视频 | **未抽样成功记录** | 需 `smoke_live_video_sample.py` 周检 |
| pytest | **140** 用例收集 | 契约充分，**不能替代 live** |
| demo_mode | false（有 KIE Key） | 工程上可走真 Adapter |
| Stripe / CDN / SSO | 未配置 | 生产门禁代码在，配置未齐 |

---

## 4. 分平台对标详表

### 4.1 vs Yapper（最近竞品）
| 能力 | Betty | 差距 |
|------|-------|------|
| 创建工具矩阵 | 对齐度高 | 体验 polish / 转化漏斗 |
| 模型货架 | 9 真可用 + lab 折叠 | Yapper 出片稳定与默认模型体验通常更「成片感」 |
| Agent | 有 | 多轮编排与稳定性 |
| 社区 Explore | 有分享/Remix | 内容供给与社区活跃度 |
| 订阅 | 代码就绪 | **Price ID 未配 = 无真订阅** |

### 4.2 vs Kling
| 能力 | Betty | 差距 |
|------|-------|------|
| 视频生成 | 经 KIE 调用 Kling SKU | 非官方一等公民；排队/失败不可控 |
| Motion Control | best-effort | **原生 Motion 差距巨大** |
| 唇形 | 可用链路 | 质量与一致性弱于专用路径 |

### 4.3 vs Runway
| 能力 | Betty | 差距 |
|------|-------|------|
| Gen 系列 | lab/guess，默认隐藏 | 无 Gen-4 真路径 |
| Act-One / Motion | 无 | 不可对标宣传 |
| 时间线 | ffmpeg 合成 | 弱于生成式剪辑工作台 |
| API | webhook 已有 | 生态与 SLA 弱 |

### 4.4 vs Luma / Pika / Midjourney
| 平台 | Betty 相对位置 |
|------|----------------|
| Luma Ray | 目录 lab only；无 verified 活跃路径 |
| Pika | 同上 |
| Midjourney | 无 Discord 社区与审美飞轮；图片靠 GPT-Image/Imagen 网关 |

---

## 5. 优势与短板（执行视角）

### 优势（可对外诚实说的）
1. **工作室功能面完整**：12 个 create 能力 + Agent + Teams + Library + Projects  
2. **工程可信度提升快**：Webhook、限流 Redis、分享、收藏、ACL、审片、冒烟 KPI 分层  
3. **目录治理诚实**：active / beta / lab；禁止把 Sora/Runway/Luma guess 当默认卖点  
4. **可观测**：隔离、软 TTL、状态页、CI、fixture dry harness  

### 短板（决定「能不能叫顶级」）
1. **视频真出片未闭合** → 对标 Kling/Runway 的核心战场失分  
2. **上游依赖 KIE** → 排队/Internal Error 直接变成产品故障  
3. **Motion 诚实上限 = best-effort**  
4. **商业闭环未通**（Stripe/CDN）→ 不能算生产级 SaaS  
5. **社区与品牌飞轮弱** → 难打 Midjourney/Yapper 的内容网络效应  

---

## 6. 分数演进（诚实轨迹）

| 阶段 | 综合就绪 | 备注 |
|------|----------|------|
| 早期表面 parity | ~55 | 页面多、验真少 |
| ROI + P0–P2 加固 | ~62 | 门禁、冒烟、CI |
| Webhook/分享/收藏/ACL | ~63 | 信任面补齐 |
| **本轮（路由扩池+lab折叠+fixture）** | **~65** | 工程分↑；出片分仍受 live_video 拖累 |

要冲到 **75+**，必须同时完成：  
live_video 周检稳定 ≥2 SKU、图片 live ≥3/4、Stripe+CDN 生产配置、Lipsync/Motion 各 1 条 fixture live。

---

## 7. 专业建议（给决策层）

1. **对外叙事**：定位「多模型 AI 视频工作室 / Yapper 替代」，**禁止**「全面对标 Runway/Kling」话术。  
2. **对内 KPI**：只用 `outframe_ok`，禁用含 skip 的成功率。  
3. **投入优先级**：真出片稳定 > 新页面 > 新模型目录条目。  
4. **商业化门槛**：未配 Stripe Price + CDN 前，不宣称 Production Ready。  

---

*本评估可复现：`docs/CORE_CAPABILITY_ASSESSMENT.md`、`docs/P0_P1_P2_ITERATION.md`；探针 `scripts/smoke_active_models.py`、`scripts/smoke_live_video_sample.py`、`scripts/fixture_derivative_harness.py`。*
