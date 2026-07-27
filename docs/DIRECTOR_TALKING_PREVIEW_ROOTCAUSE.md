# 导演智能体 · 数字人口播「免费预览」根因

**日期：** 2026-07-17  
**复现 brief：** `一个竖屏数字人口播视频，自然口型同步，正面棚拍形象，讲解产品卖点`

---

## 用户看到的现象

1. 计划步骤写着：Director LLM → ElevenLabs TTS → **GPT Image 2** → **Kling AI Avatar**
2. 点「免费预览成片」→ ~2s 出片，标注「预览模式」
3. 缩略图是**地中海山城风景**，不是数字人

## 根因（已核实）

| 层级 | 实际行为 |
|------|----------|
| 按钮 | 「免费预览成片」= `dry_run: true` → **从不调用** KIE / GPT Image / ElevenLabs / Kling |
| 图片 | `render_demo_image` ← **picsum.photos/seed/{hash}**，与 prompt 语义无关 |
| 该 brief 的 seed | `79d97bd087fc` → picsum id/397 = 悬崖海景小镇（与截图一致） |
| 唇形 | Ken Burns 缩放同一张图，却仍把 `model` 显示为计划里的「Kling AI Avatar」 |
| 风格 | brief 含「产品」卖点 → style=`product`，未优先人像 |

**计划里的模型名是「将要调用的路由标签」；免费预览只跑本地占位。** 2.1s 完成是本地 Pillow/ffmpeg，不是真实生成。

要点「真实生成 · N 积分」且环境有 Key 时，才会走 GPT Image / TTS / `kling/ai-avatar-pro`。

---

## 已修复

1. 口播/数字人预览 → **人像占位图**（不再用随机风景）
2. 预览结果 `mode` / `honesty`；UI 显示「本地预览 · 非 GPT/Kling」
3. 资产区琥珀色说明条；风格对 talking brief 优先 `portrait`
4. 回归：`tests/test_director_talking_preview_honesty.py`

---

## 如何验收

1. 打开导演智能体 → 选「数字人口播」→「免费预览成片」  
   - 应看到棚拍人像占位 + Ken Burns，模型行写「本地预览」  
2. 「真实生成」→ 扣积分，才应出现真实人像与口型（需 Key + 积分）
