# Betty × Yapper 专业全方位对标评估

**日期：** 2026-07-16  
**对标站：** [yapper.so](https://yapper.so)（首页公开叙事 + 工具矩阵，非内部实现反编译）  
**分支证据：** `cursor/betty-yapper-parity-d257`  
**机器报告：** `backend/fixtures/audit/yapper_full_matrix_latest.json`  
**原则：** 页面有 ≠ 契约通 ≠ 真出片 ≠ 产品完成度；两套分数不可混谈。

---

## 0. 裁决（一句话）

Betty 在 **创作工具主路径的契约与 live 出片** 上已具备与 Yapper 同台竞争的「工作室底盘」；  
在 **模型货架广度、订阅收款、社媒病毒飞轮、专有口型/表演引擎叙事** 上仍明显落后。  
当前诚实分数：**工具面 100%（76/76）** · **折叠 live 证据 100%（4/4）** · **Betty 内部就绪 ≈90** · **对 Yapper 产品对标 ≈81**。

| 分数 | 值 | 含义 |
|------|----|------|
| 工具面契约 `tool_surface` | **100.0**（76/76） | FE/API/OpenAPI/capabilities 硬检查 |
| Live（折叠 last_run） | **100.0**（Motion/Lipsync/FaceSwap/Omni） | 有出片证据；非本轮重新付费刷量 |
| Betty 内部就绪 | **≈90** | 可演示、可开发、可出片 |
| **对 Yapper 产品对标** | **≈81** | 货架 42 + 收款 28 仍是主拖累 |

复现：

```bash
cd backend
python3 scripts/yapper_full_matrix_audit.py
# 可选付费重跑（勿默认）：
YAPPER_AUDIT_LIVE=1 MODEL_SMOKE_LIVE=1 MODEL_SMOKE_LIVE_VIDEO=1 \
  MOTION_FIXTURE_LIVE=1 python3 scripts/yapper_full_matrix_audit.py --live
```

---

## 1. 对标方法（专业口径）

### 1.1 四层证据

| 层 | 问什么 | Betty 证据 |
|----|--------|------------|
| L0 路由/UI | 有没有入口 | `frontend/src/app/**` 17 个 create 工具 + Agent/Explore/Pricing |
| L1 契约 | API/OpenAPI/caps 是否诚实 | `yapper_full_matrix_audit.py` 硬检查 |
| L2 入队 | 能否创建任务 | OpenAPI + dry/contract；付费入队门控 |
| L3 出片 | 是否真有 media URL | `fixtures/**/last_run.json`、`omni_live_latest.json` |

### 1.2 两套分数（禁止混谈）

1. **Betty 工具合同** — 自己声明的能力是否可测、是否诚实。  
2. **vs Yapper 产品对标** — 相对 yapper.so 公开产品深度（货架、账单、社区、病毒玩法）。

### 1.3 Yapper 公开产品画像（2026-07 首页）

- **定位：** AI Content Studio；「Don't prompt, Just Direct」Agent。  
- **模型话术：** Explore **18+** image / **26+** video；品牌条含 Veo 3.1、Sora 2、Kling、Grok、WAN、Hailuo、Seedance 2.0。  
- **视频主推：** Seedance 2.0 Omni（多模态 + lip sync + multi-shot）、Studio Lip-Syncing、Motion Control、Talking Avatar、Timeline、Upscale。  
- **图像主推：** Pro Image / Editor / Product Shots / Headshots / Photo Packs / Extender / BG Remover。  
- **商业：** Starter→Max 四档 + Max credits 滑块；「Millions of assets」探索飞轮；创作者社交证明（千万/亿级 views 话术）。  
- **未在首页明示但常见竞品能力：** Face Swap / URL-to-Viral 等，按行业惯例与 Betty 既有对标台账纳入矩阵。

---

## 2. 能力矩阵（Yapper → Betty）

图例：**契约** = L0+L1；**出片** = L3 本环境证据；**产品深** = 相对 Yapper 体验深度（高/中/弱/缺）。

| # | Yapper 能力 | Betty 入口 | 契约 | 出片 | 产品深 | 诚实备注 |
|---|-------------|------------|------|------|--------|----------|
| 1 | Agent（Just Direct） | `/agent` · director plan/ideate/minimal/storyboard | ✅ | 部分 | 中 | Help Ideate 有；成片依赖下游 SKU |
| 2 | Pro Image Generation | `/create/image` | ✅ | ✅ | 中 | active 图模型有限；≠18+ |
| 3 | Video Generation | `/create/video` | ✅ | ✅ | 中 | Seedance/Kling 真出片 |
| 4 | Seedance 2.0 Omni | `/create/video` + caps | ✅ 部分 | ✅ | **中偏弱** | reference_* + live omni；缺内建唇形一体流 |
| 5 | Studio Lip-Syncing | `/create/lipsync` | ✅ | ✅ | 中 | `kling/ai-avatar-pro`；非 Max 专有引擎 |
| 6 | Talking Avatar | `/create/avatar` | ✅ | 同 lipsync | 中 | 专用页走 lipsync 后端 |
| 7 | Motion Control | `/create/motion` | ✅ | ✅ native | 中高 | `kling-3.0/motion-control`；**≠ Act-One** |
| 8 | Performance / Advanced Motion | `/create/performance` | ✅ | 组合 | 中 | Motion+可选 Lipsync；诚实非 Act-One |
| 9 | Timeline Editor | `/create/timeline` | ✅ | 本地 ffmpeg | 中 | SRT parse ✅；深度剪辑弱 |
| 10 | Media Upscaling | `/create/upscale` | ✅ | 契约 | 中 | edit 路由 |
| 11 | BG Remover | `/create/bg-remove` | ✅ | 契约 | 中 | |
| 12 | Image Extender | `/create/extend` | ✅ | 契约 | 中 | |
| 13 | Pro Image Editor | `/create/image-editor` | ✅ | 契约 | 中 | |
| 14 | Prompt Extractor | `/create/extract` | ✅ | vision/heuristic | 中 | YouTube 封面可解析 |
| 15 | URL-to-Viral | 同上 | 部分 | YouTube ✅ | **弱** | TikTok/IG best-effort；非 reel→结构 |
| 16 | Generate Audio | `/create/audio` | ✅ OpenAPI | 门控 | 中 | 契约测验证；付费 TTS 另门控 |
| 17 | Explore / Remix | `/explore` | ✅ | n/a | **弱** | list≈32 / total≈72；非百万级 |
| 18 | Pricing Starter→Max | `/pricing` | ✅ | n/a | 中 | API `id=max` 已对齐；缺滑块/团队席 |
| 19 | Sessions | `/sessions` | ✅ | n/a | 中 | |
| 20 | Tools hub | `/tools` | ✅ | n/a | 高 | 全真链接；Motion native 文案 |
| 21 | Product Shots | `/create/product` | ✅ 薄 | — | **弱** | prompt-pack，非批量 SKU |
| 22 | Professional Headshots | `/create/headshots` | ✅ 薄 | — | **弱** | 同上 |
| 23 | AI Photo Packs | `/create/photo-packs` | ✅ 薄 | — | **弱** | hub 页，非批量管线 |
| 24 | Face Swap / 病毒模板 | `/create/face-swap` | ✅ | ✅ i2i | **中偏弱** | nano-banana-edit；≠ InsightFace；模板薄 |
| 25 | Motion + Voice Changer | Motion `voice_text` / Performance | 部分 | TTS 旁白 | **弱** | 非实时变声引擎 |
| 26 | 商业订阅收款 | Stripe / OIDC 面 | 面有 | ❌ | **缺** | 本环境 Key 未注入 |

**矩阵规模：** 审计脚本 `YAPPER_MATRIX` = **26** 行（含 performance_drive / seedance_omni 等分化项）。

---

## 3. 分维度专业评估

### 3.1 产品战略与定位

| 维度 | Yapper | Betty | 判断 |
|------|--------|-------|------|
| 心智 | 病毒创作者工作室 + Agent | AI 视频/多工具平台 + Director | Betty 更偏「工程诚实工作室」；Yapper 更偏「增长与病毒」 |
| 首屏叙事 | Agent + 百万资产 + 模型品牌墙 | 需看自有营销页 | 营销密度 Yapper 胜 |
| 诚实度 | 营销口径激进（18+/26+） | capabilities 分层诚实 | Betty 工程信誉优势；市场话术勿对冲 |

### 3.2 模型货架（最大结构性差距）

- Yapper：**18+ / 26+** 与 Veo/Sora/WAN 等品牌并列。  
- Betty：**active=9**，lab≈20；lab→active 必须 live 周检，**禁止虚增**。  
- **评分拖累：** `model_shelf=42`。  
- **建议：** 首页话术改为「已验证 N 模型」；扩货架只跟 createTask 周检绑定。

### 3.3 核心生成链路

| 链路 | Betty 状态 | vs Yapper |
|------|------------|-----------|
| 图 / 视 T2V·I2V | live 出片证据齐全 | 深度接近；广度落后 |
| Omni | `reference_*` + `omni_live_latest.json` ok | 产品化（内建唇形、多镜一键）仍弱 |
| Lipsync / Avatar | live `kling/ai-avatar-pro` | 缺「Max Lip-Sync」专有叙事与周检 Beat |
| Motion | native Kling Motion Control | 质量叙事接近 Advanced Motion；**≠ Act-One** |
| Performance Drive | Motion + optional Lipsync | 诚实替代方案；勿宣称 Act-One |

### 3.4 病毒与增长玩法

| 玩法 | Betty | 缺口 |
|------|-------|------|
| Face Swap | i2i_edit live | 模板库、一键病毒套件 |
| URL-to-Viral | YouTube ok；TikTok/IG best-effort | 完整结构反推、合规抓取 |
| Explore | remix/publish 有 | 密度与「millions」叙事差数量级 |
| Photo Packs / Product | 入口有 | 批量 SKU 管线 |

### 3.5 Agent / 导演系统

- Betty：`plan` / `minimal` / `storyboard` / `ideate` / sessions — 契约齐全，minimal 最短路径已修。  
- Yapper：Agent 是营销主锚点，端到端「描述→成片」体感更强。  
- **差距：** 不是缺 API，而是 **一键成片 UX + 下游质量一致性**。

### 3.6 商业化与运营

| 项 | Yapper | Betty |
|----|--------|-------|
| 四档定价 | Starter→Max + 滑块 | 四档 `max` 对齐；无滑块 |
| Stripe | 生产成熟 | **未配置 Key**（`billing=28`） |
| SSO/OIDC | 可用 | **未配置** |
| 团队席位 | 话术有 | 未产品化 |
| readiness | — | `ok`（dev）**≠** 可收款 |

### 3.7 体验与品牌（前端）

- Yapper：TikTok-adjacent 创作者审美、强社交证明、工具卡片矩阵。  
- Betty：工具面覆盖已齐；若做营销页，需独立品牌叙事，**勿抄紫色/奶油模板**，也勿虚标货架。

---

## 4. 评分拆解（本轮实测）

```
components:
  tool_surface: 100.0   # 76/76 hard
  live:         100.0   # 折叠 Motion/Lipsync/FaceSwap/Omni
  model_shelf:   42     # vs 18+/26+
  billing:       28     # Stripe/OIDC 未注入
  community:     56.4   # gallery list≈32
depth_bonus:     12     # FaceSwap/Lipsync/Omni/YT/Performance 闭环加分
→ overall_vs_yapper ≈ 81.1
→ betty_internal_readiness ≈ 89.9
```

相对旧审计（≈76）：分差主要来自 **Face Swap / YouTube 社媒 / Performance / Lipsync·Omni live 闭环** 的诚实加分，而非货架/收款突变。

---

## 5. 差距看板（P0 / P1 / P2）

### P0 — 决定「能否像 Yapper 一样卖」

| 差距 | 状态 | 下一刀 |
|------|------|--------|
| 模型货架深度 | open | lab ID 校正 + live 周检后扩 active；或改话术 |
| Omni 产品深度 | partial | 视频页：多 ref + shot list + 可选 lipsync 一体流 |
| Stripe / OIDC 注入 | open | 密钥与 Price/webhook；readiness 生产转绿 |

### P1 — 决定「创作者是否留下来」

| 差距 | 状态 | 下一刀 |
|------|------|--------|
| Lip-Sync 成片感 / 周检 | partial | Beat + studio/demo 分层话术 |
| Face Swap 模板库 | partial | 模板集 + 玩法漏斗；勿宣称 InsightFace |
| URL-to-Viral | partial | TikTok/IG 合规增强或产品诚实禁用 |
| Explore 飞轮 | open | 种子内容、排行、Remix 漏斗指标 |
| Performance 体验 | partial | 样片人物素材；勿 Act-One 话术 |

### P2 — 决定「边角完整度」

| 差距 | 状态 | 下一刀 |
|------|------|--------|
| Product/Headshots/Packs 批量 | partial | 批量 SKU 管线 |
| Voice Changer | partial | 真 VC 或保持 TTS 诚实文案 |
| Max 滑块 / 团队席 | partial | 商业档体验 |

---

## 6. 明确禁止的夸大

1. **Motion / Performance ≠ Runway Act-One**  
2. **Face Swap ≠ InsightFace / Roop 像素级换脸**（当前为 i2i_edit）  
3. **Lab 模型数 ≠ active 可售货架**  
4. **`readiness.ok`（development）≠ 生产可收款**  
5. **契约 100% ≠ 已对标 Yapper 产品完成度（≈81）**  
6. **折叠 last_run ≠ 本轮重新付费 live**（付费重跑需显式门控）

---

## 7. ROI 迭代顺序（建议）

1. **Stripe/OIDC 注入** — 否则永远差「可订阅创作」一截。  
2. **Omni 一体体验** — 多参考 + 分镜 + 可选口型接到 Create Video。  
3. **Active 货架扩展** — 仅 live 周检通过后升架；首页话术同步。  
4. **Explore 密度 + Remix 漏斗** — 增长侧最接近 Yapper 护城河。  
5. **Face Swap 模板 / URL-to-Viral 加深** — 选一个病毒入口做透。  
6. **Lipsync 周检 Beat** — 把「能 live」变成「稳 live」。

---

## 8. 文档关系

| 文档 | 用途 |
|------|------|
| **本文** `YAPPER_PROFESSIONAL_EVALUATION.md` | 专业全方位对标裁决与维度评估 |
| `YAPPER_FULL_MATRIX_AUDIT.md` | 矩阵审计摘要（随脚本刷新） |
| `GAP_CLOSURE_FACE_SOCIAL_PERF.md` | Face/社媒/Performance/Lipsync 闭环证据 |
| `P0_P1_P2_YAPPER_ITERATION.md` | 迭代台账 |
| `PLATFORM_FULL_TEST_PLAN.md` | L0–L5 全平台测试计划 |
| `YAPPER_CORE_PARITY.md` / `YAPPER_LIVE_PARITY.md` | 历史契约/live 台账 |

**结论复述：** Betty 工具面与关键 live 已就绪到可严肃对标；要追上 Yapper，下一刀是 **收款上线 + Omni/病毒飞轮产品化 + 诚实扩货架**，而不是再铺空壳页或虚标模型数。
