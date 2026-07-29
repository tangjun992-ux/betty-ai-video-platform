# Betty × Yapper 全能力专业评估（2026-07-29 · 真实出片版）

**日期：** 2026-07-29
**分支：** `cursor/betty-yapper-parity-d257`
**对标：** [yapper.so](https://yapper.so)（/create/image、/create/video、/agent 公开产品面）
**关键状态：** `KIE_API_KEY` 已注入，**demo_mode=false，真实出片可用**（本评估基于真实端到端出片证据，非折叠/契约推断）。
**口径原则：** 页面有 ≠ 契约通 ≠ 真出片 ≠ 产品完成度。

---

## 0. 一句话裁决

自上次评估（07-29 多维 ≈84）以来最大变化：**Betty 已从"契约/演示就绪"跨越到"真实端到端出片"** —— 图像、视频(t2v/i2v)、导演一键成片、数字人口播(真实唇形) 均以真实 KIE 出片验证通过；三页 UI 已与 Yapper 输入/参数/布局对齐。
**对 Yapper 产品对标 ≈87（审计口径）**；**Betty 内部就绪 ≈94**；相对完成度（重货架+收款口径）≈77%。
仍存三处结构性天花板：**收款(Stripe/SSO) 未上线、模型货架广度(active 9 vs 18+/26+)、增长飞轮(Explore)**。

---

## 1. 能力矩阵（Yapper → Betty，真实出片核验）

图例：✅ 真实验证 · 🟡 部分/契约 · ❌ 缺。

| Yapper 能力 | Betty | 真实证据 |
|-------------|-------|----------|
| Agent「Just Direct」 | ✅ | 7 步计划 → 5 真实资产（图+2视频+身份条+字幕/CTA合成片），live 进度 |
| 文生图 T2I | ✅ | nano-banana 真实照片（~15–50s） |
| 图生图 / 指令编辑 | ✅ | nano-banana-edit i2i live |
| 视频生成 T2V | ✅ | seedance-2.0-fast 5s 真实 mp4（~80–166s） |
| 图生视频 I2V / Omni | ✅ | reference_* + seedance omni；多参考 |
| Studio Lip-Sync / 数字人 | ✅ | **Kling AI Avatar 真实唇形**（口型与中文语音同步，已修 TTS 超时缺陷） |
| Motion Control | 🟡 | 原生 Kling Motion；**≠ Act-One** |
| 多镜头分镜 Storyboard | ✅ | 2 镜真分镜 → 4 真实资产 |
| Timeline 编辑 | 🟡 | SRT 解析 + ffmpeg compose；深剪弱 |
| Upscale / BG Remove / Extend | ✅ | KIE edit 工具 live |
| Prompt Extractor | ✅ | vision/heuristic；YouTube 可解析 |
| Generate Audio (TTS) | ✅ | edge-tts（已加超时）+ KIE ElevenLabs 兜底 |
| Explore / Remix 飞轮 | 🟡→弱 | list≈32；远不及"millions" |
| Product Shots / Headshots / Photo Packs | 🟡 | prompt-pack + 场景卡；非批量 SKU 管线 |
| Face Swap / 病毒模板 | 🟡 | nano-banana-edit i2i；≠ InsightFace |
| 投放完成度（BGM/字幕/变体/导出规格） | ✅ | 8 BGM 床 + 12 字幕 + 6 导出规格 + 变体 live |
| 定价 Starter→Max | 🟡 | 四档对齐；无滑块/团队席 |
| 商业订阅收款 (Stripe/SSO) | ❌ | 未注入（KIE 解决出片≠解决收款） |

---

## 2. 分维评分（相对 Yapper=100）

| # | 维度 | 权重 | Yapper | Betty(07-29前) | **Betty(现)** | 变化说明 |
|---|------|------|--------|----------------|--------------|----------|
| 1 | 模型货架广度 | 20% | 100 | 42 | **45** | 9 active 均真实验证；广度仍窄 |
| 2 | 核心生成链路 | 18% | 92 | 82 | **90** | ★真实出片端到端打通（图/视/Omni/唇形/分镜） |
| 3 | Agent/导演 | 12% | 90 | 84 | **90** | ★真实执行 + live 进度 + 统一 composer |
| 4 | 投放完成度/成片感 | 15% | 85 | 90 | **90** | 真实合成片（字幕+CTA） |
| 5 | 病毒/增长飞轮 | 12% | 88 | 58 | **58** | 未动（Explore 弱） |
| 6 | 商业化/收款 | 13% | 90 | 28 | **32** | 出片真实（可售前提）；收款仍缺 |
| 7 | 体验/前端 | 5% | 88 | 80 | **88** | ★三页 Yapper 化统一 composer |
| 8 | 工程诚实/可验证 | 5% | 65 | 95 | **96** | 29/29 验证 + 真实证据 + 诚实修复 |
| 9 | 边角完整度 | 5% | 82 | 56 | **58** | 略升 |

**加权：** Yapper ≈ **94** · Betty ≈ **73**（相对完成度 ≈ **77%**，此口径放大货架+收款权重）。
**审计口径（tool_surface/live/shelf/billing/community + depth）：** 对 Yapper 对标 **≈87**（live 由"折叠证据"升级为"真实出片"）；内部就绪 **≈94**。

---

## 3. 相较上次评估的关键跃迁

1. **真实出片上线（最重要）**：`demo_mode=false`，图/视/导演/数字人全部真实 KIE 出片；这是此前所有评估里最大的 L3 缺口，现已闭合。
2. **数字人真实可用**：修复 TTS 无超时导致的连锁失败，Kling 唇形真实开口；字幕面部安全化。
3. **UI 全面对标**：image/video/agent 统一扁平 composer + 下拉参数 + 应用卡片，无双层框/聚焦圈。
4. **可验证性增强**：`agent_video_verify.py` 五维 29/29；发现并修复空 brief 校验、minimal 语义。

---

## 4. 仍存结构性天花板（决定"能否像 Yapper 一样卖/增长"）

| 天花板 | 现状 | 影响 | 下一刀 |
|--------|------|------|--------|
| 收款 Stripe/OIDC | 未注入 | 无法真正订阅/收款 | 注入 Key + Price/webhook + readiness 转绿 |
| 货架广度 | active 9 vs 18+/26+ | 心智/选择面 | live 周检后扩 active，或话术改"已验证 N" |
| 增长飞轮 | Explore≈32 | 无病毒护城河 | 种子内容 + 排行 + Remix 漏斗 |
| 内容质量细节 | 数字人念 brief 原文 | 成片专业度 | LLM 生成自然口播话术再驱动 TTS |

---

## 5. 诚实边界（禁止夸大）

1. Motion/Performance **≠ Runway Act-One**；Face Swap **≠ InsightFace**。
2. 真实出片依赖运行中注入的 `KIE_API_KEY`；**未持久化为 Cloud secret**（VM 重启/新 agent 需重注入）。平台内积分为 Betty 计费系统，与 KIE 额度独立。
3. `KIE 可出片` **≠ 可收款**；Stripe/SSO 仍未配置。
4. active=9 是真实可售货架；lab=20 **不得计入**。
5. 视频/唇形真实渲染慢（单条 1–5 分钟）；数字人当前"念"的是 brief 原文，尚需口播脚本生成。

---

## 6. ROI 路线（建议顺序）

1. **收款上线（Stripe/OIDC）** — 唯一阻断"像 Yapper 一样卖"的天花板。
2. **口播脚本生成 + 唇形真实进度** — 把已跑通的数字人做到"专业成片感"。
3. **诚实扩 active 货架**（仅 live 周检通过升架）。
4. **Explore 密度 + Remix 漏斗** — 最接近 Yapper 护城河的增长侧。
5. **批量 SKU（Product/Headshots/Packs）** — 边角完整度。

---

## 7. 结论

Betty 已经跨过"能不能真出片"这道最关键的坎——**图像/视频/导演成片/数字人口播均真实端到端可用**，UI 与工程可验证性已达严肃对标水准（对 Yapper ≈87，内部就绪 ≈94）。
要真正与 Yapper 同台"卖与增长"，剩下的是**商业化收款 + 货架广度 + 增长飞轮 + 内容质量细节**，而非再补生成能力本身。
