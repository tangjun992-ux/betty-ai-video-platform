# Betty × Yapper 专业评估（2026-08-16 复评）

**日期：** 2026-08-16  
**对标站：** [yapper.so](https://yapper.so)（当日首页 /create/video /pricing /mcp 公开叙事，非内部反编译）  
**评估栈顶：** `cursor/p3-url-viral-structure-d257` @ `9270cdc`（P0→P3 叠在 `betty-yapper-parity` 之上）  
**原则：** 页面有 ≠ 契约通 ≠ 真出片 ≠ 产品完成度；**本机污染分 ≠ 产品分**；禁止虚标货架与收款。

---

## 0. 一句话裁决

Betty 在 P0–P3 把「工作室工具面」做成了更完整、更诚实的对标体：报价/并发、Explore 搜索与 Remix、Folders、批量 Packs、Max 滑块入账字段、TikTok 官方 oEmbed + 投放规格分镜都已落地。  
**但相对 Yapper 的总分几乎不动**——因为同期 Yapper 把货架话术从 26+ 推到 **29+/30+**，首页已挂 **Seedance 2.5 Omni-Video**，并卖 **MCP/API**；Betty 货架仍是 **active=9 / Seedance 2.0**，本环境 **Stripe/OIDC 仍无 Key**，Explore 仍不是百万级社区。

| 口径 | 07-16 | 07-29（有 KIE 的评估） | **2026-08-16（本复评）** |
|------|-------|------------------------|--------------------------|
| 工具面硬契约 | 76/76 | 宣称 29/29 验证 | **产品应 76/76**；本 VM 75/76（Celery/Redis 缺失，见 §1） |
| 折叠 live | 4/4 | 另有付费真出片 | **4/4 折叠**（Motion / Lipsync / FaceSwap / Omni）；**本 VM 未付费重跑** |
| 审计口径 vs Yapper | ≈81 | ≈87（含当时 live Key） | **≈81（归一化）** |
| 9 维产品完成度 | ≈68/90 | ≈73/94 | **≈74 / 95（相对 ≈78%）** |
| Betty 内部就绪 | ≈90 | ≈94 | **≈90（归一化）** |

**读法：** P0–P3 抬的是边角、病毒入口与诚实产品化；Yapper 抬的是货架叙事与分发面。两边相抵，总分持平是诚实结论，不是「没进步」。

---

## 1. 本轮取证（必须分开两套数）

### 1.1 本 VM 实测（2026-08-16，污染）

在 P3 工作树用 lifespan `TestClient` 跑 `yapper_full_matrix_audit` 逻辑：

| 项 | 值 | 含义 |
|----|----|------|
| `demo_mode` | **true** | 本 VM **未注入 KIE Key** |
| `active_count` | **9** | lab=20；禁止把 lab 算进可售 |
| `enqueue:generate_image` | **失败** | Celery 结果后端 Redis 重试耗尽 |
| 硬契约 | **75/76** | 唯一失败是入队环境，不是缺路由 |
| gallery list/total | **0 / 0** | 新 sqlite，**未灌种子** → 社区分被公式打到 18 |
| Stripe / OIDC | **false / false** | 与历史一致 |
| 折叠 live | **4/4** | 文件证据，非本轮付费 |
| 公式 raw `overall_vs_yapper` | **76.9** | **不可直接当产品分**（空库 + 无队列） |

原始 JSON：`/opt/cursor/artifacts/p3_yapper_eval_audit.json`

### 1.2 归一化产品分（与 07-16 同公式）

沿用脚本权重：`0.28 tool + 0.24 live + 0.18 shelf + 0.14 billing + 0.10 community + depth≤12`。

代入：**tool=100**（入队失败记环境）、**live=100**（折叠 4/4）、**shelf=42**（active&lt;12）、**billing=28**（无 Key）、**community=56.4**（历史种子 list≈32）、**depth=12**（FaceSwap/Lipsync/Omni/YouTube/Performance 均满足加分位）。

```
overall_vs_yapper ≈ 28+24+7.56+3.92+5.64+12 = 81.1
betty_internal_readiness ≈ 38+32+11.25+5.64+3.0 = 89.9
```

P0–P3 **没有改这条公式的权重**，所以审计口径仍停在 ≈81。进步应看 §3 矩阵「产品深」列，而不是指望总分跳到 90。

---

## 2. Yapper 2026-08-16 公开画像（相对 07 月已变）

当日首页仍是「Don't prompt, Just Direct」+「Millions of assets」。相对 07-16 评估，**目标线升高**：

| 项 | 07-16 记录 | **2026-08-16 首页** |
|----|------------|---------------------|
| 图/视货架话术 | 18+ / 26+ | Explore **18+ / 29+**；定价卡 **19+ / 30+** |
| 视频主推 | Seedance 2.0 Omni | **Seedance 2.5 Omni-Video**（多模态 + lip sync + 多镜）仍并列 2.0 品牌墙 |
| 品牌墙 | Veo 3.1 / Sora 2 / Kling / Grok / WAN / Hailuo / Seedance | 同上 + **Nano Banana 2 / GPT Image 2** |
| 商业 | Starter $9.99 → Max $149.99 + 滑块 | 滑块档位公开 **15k–150k** credits |
| 新分发面 | 未强调 | **MCP + REST API**（yapper.so/mcp），宣称 54+ models one connection |

Betty **没有** Seedance 2.5 SKU、没有 Veo/Sora 可售、没有 MCP 产品页。对标时必须把这条算进「货架/分发」落后，而不是假装 Yapper 停在 07 月。

---

## 3. 能力矩阵（Yapper → Betty P3）

图例：契约 = L0+L1；出片 = L3 折叠或历史 live；产品深 = 相对 Yapper **今日**体验。

| # | Yapper | Betty | 契约 | 出片 | 产品深 | 相对 07-16 | 诚实备注 |
|---|--------|-------|------|------|--------|------------|----------|
| 1 | Agent Just Direct | `/agent` director | ✅ | 历史 live | 中 | 持平 | 一键成片 UX 仍弱于营销锚点 |
| 2 | Pro Image | `/create/image` | ✅ | 折叠/历史 | 中 | 持平 | ≠19+ 图模型 |
| 3 | Video | `/create/video` | ✅ | 折叠 Omni | 中 | 持平 | Seedance **2.0**，不是 2.5 |
| 4 | Seedance Omni | video + `lipsync_text` | ✅ | ✅ 折叠 | **中** | 中偏弱→中 | P0 同任务口型链；仍非 Omni 内建唇形引擎 |
| 5 | Studio Lip-Sync | `/create/lipsync` | ✅ | ✅ 折叠 | 中 | 持平 | 缺周检 Beat；≠ Max 专有引擎 |
| 6 | Talking Avatar | `/create/avatar` | ✅ | 同 lipsync | 中 | 持平 | |
| 7 | Motion Control | `/create/motion` | ✅ | ✅ native 折叠 | 中高 | 持平 | **≠ Act-One** |
| 8 | Advanced Motion | `/create/performance` | ✅ | 组合 | 中 | 持平 | Motion+可选 Lipsync |
| 9 | Timeline | `/create/timeline` | ✅ | ffmpeg | 中 | 持平 | 深剪弱 |
| 10–13 | Upscale / BG / Extend / Editor | 各 create 页 | ✅ | 契约/历史 | 中 | 持平 | |
| 14 | Prompt Extractor | `/create/extract` | ✅ | heuristic/oEmbed | 中 | 持平 | |
| 15 | URL-to-Viral | 同上 + `viral-spec` | ✅ | YouTube + TikTok oEmbed | **中偏弱** | **弱→中偏弱** | P3：官方 oEmbed+投放分镜；**不是**逐帧反推；IG 仍要上传 |
| 16 | Generate Audio | `/create/audio` | ✅ | 门控 | 中 | 持平 | |
| 17 | Explore / Remix | `/explore` | ✅ | n/a | **中偏弱** | **弱→中偏弱** | P1 搜索/remix/popular；P1.5 诚实密度；**远非 millions** |
| 18 | Pricing Max 滑块 | `/pricing` | ✅ | n/a | **中** | 中（缺滑块）→中 | P2 `checkout.credits`；**无 Key 不能收款** |
| 19 | Sessions | `/sessions` + video `session_uid` | ✅ | n/a | 中 | 持平+ | P1 SessionChip |
| 20 | Tools hub | `/tools` | ✅ | n/a | 高 | 持平 | 文案已去虚标 |
| 21–23 | Product / Headshots / Packs | 批量 SKU API | ✅ | 契约测 | **中** | **弱→中** | P2 N 独立任务+整批预检；≠ IP-Adapter 身份锁 |
| 24 | Face Swap | `/create/face-swap` | ✅ | ✅ i2i | **中** | 中偏弱→中 | P1.5 八张模板；**≠ InsightFace** |
| 25 | Voice Changer | Motion TTS | ✅ 诚实 | TTS | **中偏弱** | 弱→中偏弱 | P2 明确 **tts_narration**；不是 RVC |
| 26 | 订阅收款 | Stripe/OIDC 面 | 面+诚实条 | ❌ | **缺** | 持平 | P1.5 诚实条；Key 仍无 |
| — | MCP / 开放 API | Betty developer 路由有，无对标 MCP 产品 | 部分 | — | **弱** | **新缺口** | Yapper 已当增长面卖 |

---

## 4. 九维评分（相对 Yapper 今日=100）

权重与 07-29 多维表相同，便于纵向比较。Yapper 列因 2.5 / 30+ / MCP 略上调。

| # | 维度 | 权 | Yapper | Betty 07-16 | Betty 07-29 | **Betty 08-16** | 判断 |
|---|------|----|--------|-------------|-------------|-----------------|------|
| 1 | 模型货架广度 | 20% | 100 | 42 | 45 | **40** | 我方仍 9；对方话术 19+/30+ 且 2.5。相对**退步** |
| 2 | 核心生成链路 | 18% | 94 | 82 | 90 | **91** | Omni 同任务 `lipsync_text`；深度近、广度差 |
| 3 | Agent / 导演 | 12% | 90 | 82 | 90 | **90** | 契约齐；一键成片体感仍弱 |
| 4 | 投放完成度 | 15% | 85 | 70 | 90 | **90** | 三刀/主线 B 仍在；未再加分 |
| 5 | 病毒 / 增长飞轮 | 12% | 90 | 58 | 58 | **66** | 搜索/remix/Folders/URL 结构；密度仍差数量级 |
| 6 | 商业化 / 收款 | 13% | 92 | 28 | 32 | **36** | 滑块/席位 SKU 已产品化；**仍不能收款** |
| 7 | 体验 / 前端 | 5% | 90 | 78 | 88 | **90** | P0 Dashboard 对话首页 |
| 8 | 工程诚实 | 5% | 62 | 95 | 96 | **96** | 分层 caps；禁 millions / 禁 lab 充 active |
| 9 | 边角完整度 | 5% | 84 | 55 | 58 | **72** | Packs 批量 + TTS 诚实 + Max 滑块字段 |

**加权：** Yapper ≈ **95** · Betty ≈ **74** · 相对完成度 ≈ **78%**。

与 07-29「审计口径 87」不矛盾：那次把当时注入的 KIE 真出片算进 live 溢价。本 VM **没有 Key**，本复评 **不沿用 87**。

---

## 5. P0–P3 实际改变了什么（相对「继续开发」前）

| 迭代 | 闭合的产品缺口 | 仍禁止宣称 |
|------|----------------|------------|
| P0 | Dashboard 对话首页；`/generate/quote`；套餐并发；Omni `lipsync_text` 一体流 | 3 秒 demo ≠ SLA |
| P1 | Explore `q` 搜索 + remix 计数；Library Today/多选/批量；Video Session | Explore ≠ 百万资产 |
| P1.5 | Folders CRUD（标签目录）；Explore 密度拆 seed/community；换脸 8 模板；Stripe 诚实条 | Folders ≠ 嵌套网盘 |
| P2 | Packs 整批报价预检；Motion TTS 旁白；Max `checkout.credits`；团队席 SKU | Voice ≠ 实时变声；无 Key ≠ 已收款 |
| P3 | TikTok 官方 oEmbed + 钩子/展开/收束；一键带 `shot=` 进视频页 | ≠ 原片搬运 / 逐帧反推 |

**审计脚本 `score_gaps()` 的 gap 文案部分已过时**（仍写 TikTok best-effort、Packs 为 prompt-pack）。以 capabilities 与本表为准，不要用旧 gap 字符串对外报价。

---

## 6. 结构性天花板（决定能不能「像 Yapper 一样卖」）

| 天花板 | 现状 | 对总分的影响 | 下一刀 |
|--------|------|--------------|--------|
| **收款 / SSO** | 代码+诚实条就绪；Key 未注入 | billing 锁在 28–36 | 注入 Stripe Price/webhook + OIDC；readiness 生产转绿 |
| **货架广度** | active=9 vs 宣传 19+/30+；无 2.5 / Veo / Sora | shelf 锁在 40–42 | **仅** createTask 周检通过后升架；首页写「已验证 9」 |
| **增长密度** | 机制有、规模无 | community 公式上限远低于「millions」 | 真实 UGC，禁止种子充百万 |
| **分发面 MCP** | Yapper 已卖；Betty 仅有内部 developer API | 新缺口 | 真要做再单独立项，勿先做营销页 |
| **Lip-Sync 周检** | 折叠 live 有；Beat 无 | 稳 live 未产品化 | `MODEL_SMOKE_LIVE_LIPSYNC_WEEKLY` 门控任务 |

---

## 7. 明确禁止的夸大（2026-08-16 仍有效）

1. Motion / Performance **≠ Runway Act-One**  
2. Face Swap **≠ InsightFace / Roop**  
3. Lab 20 **≠** active 9  
4. `readiness.ok`（development）**≠** 可收款  
5. 契约 76/76 **≠** 已追上 Yapper 产品完成度  
6. 折叠 `last_run` **≠** 本轮付费重跑  
7. URL-to-Viral **≠** 原片下载 / 逐帧分镜  
8. Voice **≠** RVC / 实时变声  
9. Folders **≠** 嵌套文件系统  
10. 本 VM `overall=76.9` **≠** 产品对标分（空库污染）  
11. Yapper「29+ / 30+ / Seedance 2.5」是**营销口径**；Betty 不得用同等话术回击  

---

## 8. ROI 顺序（复评后）

1. **Stripe/OIDC 密钥** — 唯一把「能做」变成「能卖」的开关。  
2. **诚实扩货架或改话术** — 否则对标分被 20% 货架维永久压住；Yapper 已加 2.5。  
3. **Explore 真实内容** — 机制已够用，缺的是规模，不是再做一个搜索框。  
4. **Lipsync 周检 Beat** — 把折叠 live 变成可运营的稳 live。  
5. **不要**再铺空壳工具页；**不要**做假文件系统 / 假变声 / 假百万社区。

---

## 9. 结论

Betty 现在是一台**工程诚实的 AI 内容工作室**：主路径契约齐、关键 SKU 有折叠出片证据、P0–P3 把 Yapper 边角玩法做成了可测产品而不是海报。  
Yapper 现在是一台**增长导向的内容工厂**：货架话术更宽、首页已指向 Seedance 2.5、MCP 把模型货架卖给 Agent 生态，收款与社交证明完整。

**对标分数停在 ≈81（审计）/ ≈78%（九维），不是迭代失败，而是天花板换边：**  
我方补的是可验证深度，对方拉的是货架与分发。下一刀若还不碰 **Key 与货架**，再做十个 P 也只会让边角更满、总分不动。
