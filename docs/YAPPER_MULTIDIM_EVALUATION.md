# Betty × Yapper 多维评估（含三刀 + 主线 B 增量）

**日期：** 2026-07-29
**分支：** `cursor/betty-yapper-parity-d257`
**对标站：** [yapper.so](https://yapper.so)（公开产品叙事 + 工具矩阵）
**口径原则：** 页面有 ≠ 契约通 ≠ 真出片 ≠ 产品完成度。两套分数不可混谈。
**证据基线：** 离线契约计数（本文表 1）+ 折叠 last_run live 证据 + 门禁脚本（`three_knives_verify.py` 11/11、`mainline_b_verify.py` 15/15、`optimize_gate_verify.py` 15/15）。本轮为评估，未重新付费刷 live。

---

## 0. 裁决（一句话）

自 07-16 专业评估以来，「三刀 + 主线 B」把 Betty 的 **投放完成度 / 成片感 / 变体产能** 从「能做」推到「默认就好看、可试投」，
使 **对 Yapper 产品对标从 ≈81 提升到 ≈84**，**Betty 内部就绪从 ≈90 提升到 ≈92**。
但两大结构性天花板 **未变**：**模型货架广度（active 9 vs 18+/26+）** 与 **收款/SSO 未注入**。
增量吃的是 L2/L3 完成度，不是 L0 货架与商业化。

---

## 1. 真实能力快照（可量化 · 2026-07-29）

| 维度计数 | 值 | 来源 |
|----------|----|------|
| 模型注册表 `MODEL_REGISTRY` | 76 | `app/adapters/registry.py` |
| 目录 active / total | **9 / 37** | `catalog_integrity()` |
| active 图模型 | 4（gpt-image-2 / nano-banana / nano-banana-pro / imagen-4） | `models_info.MODELS` |
| active 视频模型 | 5（seedance-2.0 / -fast / kling-2.5-turbo / kling-2.1-master / -pro） | 同上 |
| 导演场景 `SCENARIO_IDS` | 8 | `director_scenarios.py` |
| 包装场景 / 人像变体 / 产品变体 | 6 / 4 / 4 | 同上 |
| 字幕模板 | 12 | 三刀·刀 1 |
| Stock Beds（BGM 床） | 8 | 主线 B·B1 |
| 投放导出规格 | 6（meta_feed/stories · tiktok · reels · yt_shorts/landscape） | `export_specs.py` |
| brief 模板（广告/UGC/口播） | 9 | `director_brief_templates.py` |
| 变体工厂 live | finals=2（A/B 成片落盘） | `mainline_b_verify.py` |
| 身份锁 | off / hero / edit + 对比条 | 三刀·刀 3 |

诚实声明（`GET /system/capabilities`）：Motion = 原生 Kling Motion Control（**非 Act-One**）；Face Swap = i2i_edit（**非 InsightFace/Roop**）；Omni 口型仍走 `/lipsync`；`verified_model_count` 只报 active=9。

---

## 2. 多维评分（9 维加权）

打分口径：以「相对 Yapper 公开产品完成度」为 100 基准；Betty 为该维实测完成度。四层证据 L0 路由 / L1 契约 / L2 入队 / L3 出片。

| # | 维度 | 权重 | Yapper | Betty(0716) | Betty(0729) | 判断 |
|---|------|------|--------|-------------|-------------|------|
| 1 | 模型货架广度 | 20% | 100 | 42 | **42** | 硬天花板，未动 |
| 2 | 核心生成链路深度（图/视/Omni/Lipsync/Motion） | 18% | 92 | 82 | **82** | 深度接近，广度落后 |
| 3 | Agent / 导演系统 | 12% | 90 | 82 | **84** | +变体优先编排 |
| 4 | 投放完成度 / 成片感 | 15% | 85 | 70 | **90** | ★三刀+主线B 反超 |
| 5 | 病毒 / 增长飞轮 | 12% | 88 | 58 | **58** | Explore/URL-to-Viral 仍弱 |
| 6 | 商业化 / 收款 | 13% | 90 | 28 | **28** | Key 未注入，硬天花板 |
| 7 | 体验 / 品牌前端 | 5% | 88 | 78 | **80** | +投放位/模板芯片 UI |
| 8 | 工程诚实 / 可验证 | 5% | 65 | 95 | **95** | Betty 结构性优势 |
| 9 | 边角完整度（Product/Headshots/Packs/VC） | 5% | 82 | 55 | **56** | 仍薄 |

**加权总分（本口径）：** Yapper ≈ **90** · Betty ≈ **66 → 68**。相对完成度 ≈ **75%**。

> 说明：本表放大了「货架 + 收款」权重（33%），故绝对分低于 07-16 审计口径（tool_surface/live 权重更高，故 ≈81）。**两口径不冲突**：审计口径衡量「工具面 + live 是否诚实可测」，本表衡量「作为可售产品与 Yapper 的完成度差」。三刀+主线B 在两口径下都只显著抬升「投放完成度」这一维。

**沿用 07-16 审计口径的增量：**
```
components(0716):  tool_surface 100 · live 100 · model_shelf 42 · billing 28 · community 56.4 · depth_bonus 12  → vs_yapper ≈ 81.1 · readiness ≈ 89.9
components(0729):  同上，但 depth_bonus 12 → ~17（投放规格/brief/BGM 床/变体 live/身份锁闭环）→ vs_yapper ≈ 84 · readiness ≈ 92
```

---

## 3. 分维详评

### 维度 1 · 模型货架（最大结构性差距 · 未动）
- Yapper：18+ 图 / 26+ 视，Veo 3.1 / Sora 2 / Kling / WAN / Hailuo / Seedance 品牌墙。
- Betty：**active 9**（lab/beta 至 37），诚实周检升架，禁止虚增。
- 裁决：这是天花板 1。要么 live 周检后扩 active，要么首页话术改「已验证 N 模型」。三刀+主线B 不触碰此维。

### 维度 2 · 核心生成链路
- 图/视 T2V·I2V：live 出片证据齐（seedance/kling）。
- Omni：`reference_*` + `omni_live` ok；内建唇形一体流仍弱。
- Lipsync/Motion：`kling/ai-avatar-pro` + 原生 Motion Control；深度接近 Advanced Motion，**非 Act-One**。
- 裁决：深度可同台，广度随维度 1 受限。

### 维度 3 · Agent / 导演（+2）
- `plan / minimal / storyboard / ideate / sessions` 契约齐；主线 B 新增 **广告场景默认变体优先**（先扇出 n=2 再选优）。
- 差距：一键「描述→成片」体感与下游质量一致性仍略逊 Yapper Agent 营销锚点。

### 维度 4 · 投放完成度 / 成片感（★ +20 · 本轮主升维）
- **BGM**：8 条 Stock Beds + 公开 URL + `BGM_URL_*` 可换授权 + 侧链 ducking（人声优先）。
- **字幕**：12 套场景化模板（feed/talking/ad/drama/impact/caption_box…）。
- **投放规格**：6 档命名规格 + 画幅/时长校验 + `placement_warnings`（Meta/TikTok/Reels/Shorts）。
- **brief 模板**：9 套钩子/时长/CTA（广告/UGC/口播），替代抠 InfiniTalk。
- **变体**：`/variants/run` live finals=2，画廊选优。
- 裁决：此维 Betty **系统性反超**——Yapper 有 timeline/upscale，但「投放侧命名规格 + 默认成片 brief + 变体优先」Betty 更完备。仍缺卡拉 OK 逐字动效花字。

### 维度 5 · 病毒 / 增长（未动 · 差距最真）
- Face Swap i2i live；YouTube URL-to-Viral ok；TikTok/IG best-effort。
- Explore list≈32 / total≈72，距 Yapper「millions of assets」差数量级。
- 裁决：天花板 3（软），护城河维度，需选一个病毒入口做透 + Explore 种子/排行/Remix 漏斗。

### 维度 6 · 商业化 / 收款（天花板 2 · 未动）
- 四档定价 `id=max` 已对齐；Stripe / OIDC **Key 未注入**，团队席未产品化。
- `readiness.ok`（dev）**≠** 生产可收款。
- 裁决：决定「能否像 Yapper 一样卖」，是下一阶段最高 ROI。

### 维度 7 · 体验 / 前端（+2）
- 主线 B 加入投放位选择 + 成片模板芯片 + 广告场景变体优先 UI。
- 差距：营销密度与社交证明弱于 Yapper；勿抄紫/奶油模板，勿虚标货架。

### 维度 8 · 工程诚实 / 可验证（Betty 优势）
- 分层 capabilities + 门禁脚本 + 折叠 live 证据 + 目录诚信报告。
- 相对 Yapper 激进话术（18+/26+），Betty 工程信誉是差异化资产——市场话术不应对冲它。

### 维度 9 · 边角
- Product Shots / Headshots / Photo Packs 仍为 prompt-pack 薄入口，非批量 SKU 管线；Voice Changer 为 TTS 旁白（非实时变声）。

---

## 4. 天花板与 ROI 顺序

| 排名 | 动作 | 触及维度 | 为什么 |
|:--:|------|----------|--------|
| 🥇 | **Stripe / OIDC 注入 + readiness 转绿** | 6 | 否则永远差「可订阅创作」一截；天花板 2 |
| 🥈 | **Omni 一体体验**（多 ref + 分镜 + 可选口型接 Create Video） | 2/3 | 把「能 live」变「默认好用」 |
| 🥉 | **诚实扩 active 货架**（仅 live 周检通过升架 + 话术同步） | 1 | 天花板 1；禁止虚增 |
| 4 | **Explore 密度 + Remix 漏斗 / 选一病毒入口做透** | 5 | 最接近 Yapper 护城河 |
| 5 | **投放完成度收尾**（逐字花字 / 真授权曲注入 / 批量 SKU） | 4/9 | 把反超维度做到无短板 |

---

## 5. 明确禁止的夸大（复述）

1. Motion / Performance ≠ Runway Act-One
2. Face Swap ≠ InsightFace / Roop 像素级换脸（当前 i2i_edit）
3. Lab 模型数（37）≠ active 可售货架（9）
4. Stock Beds ≠ 商用曲库（平台自有 procedural；生产换 `BGM_URL_*`）
5. `readiness.ok`（dev）≠ 生产可收款
6. 契约 100% / 投放完成度反超 ≠ 已追平 Yapper 产品完成度（≈84，天花板在货架+收款）
7. 折叠 last_run ≠ 本轮重新付费 live

---

## 6. 文档关系

| 文档 | 用途 |
|------|------|
| **本文** `YAPPER_MULTIDIM_EVALUATION.md` | 含三刀+主线B 增量的多维评估裁决 |
| `YAPPER_PROFESSIONAL_EVALUATION.md` | 07-16 专业全方位对标基线 |
| `THREE_KNIVES_VERIFICATION.md` | 包装/变体/身份 三刀验证 11/11 |
| `MAINLINE_B_VERIFICATION.md` | 投放完成度 主线 B 验证 15/15 |
| `PIXEL_LEVEL_GENERATION_EVAL.md` | 像素级取舍（收敛 L2/L3） |

**结论复述：** 三刀 + 主线 B 让 Betty 在「投放完成度/成片感」这一维系统性反超 Yapper，对标分 ≈81→≈84。要继续追上，必须动天花板——**收款上线 + Omni/病毒飞轮产品化 + 诚实扩货架**，而非再铺空壳页或虚标模型数。
