# 数字人 / 唇形同步 — 内容准确性专业评估

**日期：** 2026-07-17  
**范围：** 产品档 Demo（免费/4 积分）与离线 Ken Burns、以及 `kling/ai-avatar-pro` 真链路  
**证据：** `backend/fixtures/audit/lipsync_accuracy_latest.json` · `/opt/cursor/artifacts/lipsync_accuracy/`  
**复现：** `cd backend && python3 scripts/lipsync_accuracy_eval.py`（真人脸重跑加 `LIPSYNC_ACCURACY_LIVE=1`）

---

## 一句话结论

用户反馈「免费数字人生成了但不像」**成立且可复现**，根因通常不是「任务没完成」，而是路径/输入错配：

| 路径 | 数字人准确度 (0–5) | 是否算说话数字人 |
|------|-------------------|------------------|
| A 离线 Ken Burns（`DEMO_GENERATION` / 无 Key） | **0.3** | 否 |
| B 真链路 + 简笔画 + 正弦波（历史 fixture） | **2.15** | 否 |
| C 产品 `tier=demo` 契约（有 Key） | 入队成功 · 扣 4 积分 | — |
| D 真链路 + 真人脸 + 真实语音（Demo 同 SKU） | **5.0** | **是** |

**产品档 Demo ≠ 离线演示模式。** 有 KIE Key 时，Demo 与 Studio 都走 `kling/ai-avatar-pro`；无 Key / 强制 DEMO 时才是无声 Ken Burns。

---

## 双轨说明（易混淆）

```
产品 tier=demo|studio          运行时 demo_mode_active()
─────────────────────          ─────────────────────────
FE「Demo 4 积分」               DEMO_GENERATION=1 或无 Provider Key
有 Key → kling/ai-avatar-pro   → render_demo_video (Ken Burns)
Demo≈480p 意图 / Studio≈720p   → 无音轨 · DEMO 水印 · model=demo-lipsync
```

UI 曾写「标准唇形」——在离线路径上**完全失实**；在有 Key 时也不等于「已验证口型准确」，只表示走了 Avatar 模型。

---

## 细粒度指标（代理分，非 viseme 金标）

维度：音频存在 · 语音样态 · 嘴部 ROI 帧差 · 身份保持 · 模型诚实标签。

### A — 离线 Ken Burns

- 无音轨；嘴部 MAD **0.38**（近似静止缩放）
- `mode` 现标注为 `ken_burns` / `honesty=offline_preview_not_lipsync`
- **判定：不是数字人**，仅可作离线预览

### B — 历史 live（简笔画 + 正弦波）

- 有 A/V，模型 `kling/ai-avatar-pro`，1280×1600
- 音频 `energy_cv=0.135` → **tone_or_steady**（非语音）
- 嘴部 MAD **0.93**，口/眼运动比 **0.26**（嘴动弱于眼区噪声）
- 画面仍是简笔画，身份冻结
- **判定：任务成功 ≠ 内容准确**；输入不合格时真链路也会「不像数字人」

### D — 对照：真人脸 + 中文语音（espeak）· 同一 Demo SKU

- 耗时约 **212s**；音频 6.06s，`speechlike=5`，`energy_cv=0.736`
- 嘴部 MAD **15.3**，口/眼比 **1.09**，身份 hist_corr **0.95**
- 人工抽帧：张口/露齿随时间变化，发型与服饰一致
- **判定：通过说话数字人代理门槛**（音素级对齐未做 ASR/viseme 金标）

---

## 对用户场景的专业解读

1. **若当时环境无 Key / 演示模式**  
   免费档也会产出 Ken Burns → 无声缩放，**必然不像数字人**。CapabilityNotice 已提示，但档位文案曾仍写「标准唇形」。

2. **若当时有 Key 且选了 Demo**  
   上游已是真实 Avatar；不像时优先查输入：是否真人正面照、是否清晰语音（非静音/蜂鸣）、人脸是否过小或卡通。

3. **音色不一致**  
   UI 展示 `zh-CN-XiaoxiaoNeural` 等，任务层映射为 ElevenLabs Rachel/Adam → **音色名与听感可不一致**（非口型失败，但是体验缺口）。

4. **Studio vs Demo**  
   同模型不同积分/分辨率意图；**不是**另一套「更像真人」的独立数字人引擎。

---

## 已落地改进

- 结果 JSON：`mode=ken_burns|kling_avatar` + 诚实字段  
- `/lipsync` 与 Talking Avatar 档位文案随离线/在线切换  
- `/lipsync/voices` tier 描述与音色映射说明  
- 评估脚本 + 审计 JSON；fixture 增加 `photo_face.jpg` / `speech_zh.wav`

---

## 残余风险 / 未覆盖

- 未做音素级 lip-sync 金标（需标注数据或外部评测器）
- Studio 720p 意图对 Kling 是否生效取决于上游；未单独付费对比 Demo/Studio 画质差
- CDN tempfile URL 会过期；以本地 artifact + `last_run.json` 元数据为准
- 卡通/侧脸/口罩等困难输入仍可能「成功但不动嘴」

---

## 评级（相对「可用数字人」期望）

| 维度 | 分 | 说明 |
|------|----|------|
| 链路可达性（有 Key） | 5/5 | Demo 可入队并出片 |
| 离线诚实性（修复前） | 2/5 | 文案夸大；现已补 mode + UI |
| 内容准确（差输入） | 1/5 | 简笔画+音调失败属预期 |
| 内容准确（合格输入） | 5/5 | 代理指标满分 + 抽帧通过 |
| 与 Yapper Avatar 体感 | 4/5 | 同属 talking-avatar；音色/Studio 差异需诚实 |

**综合：** 免费 Demo 在**正确运行时 + 合格素材**下可以像数字人；用户遇到的「不像」高度符合 **离线预览** 或 **不合格输入** 两类失败模式，而非「生成按钮坏了」。
