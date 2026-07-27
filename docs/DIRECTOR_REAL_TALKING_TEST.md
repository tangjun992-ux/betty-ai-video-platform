# 导演智能体 · 数字人口播「真实生成」实测

**日期：** 2026-07-17  
**Brief：** `一个竖屏数字人口播视频，自然口型同步，正面棚拍形象，讲解产品卖点`  
**证据目录：** `/opt/cursor/artifacts/director_real_talking/`  
**脚本：** `backend/scripts/director_real_talking_e2e.py`

---

## 结论（对用户问题：功能是否真的有效）

| 环节 | 结果 | 说明 |
|------|------|------|
| 真实模式可用 | ✅ | `real_available=true`，扣 13 积分入队 |
| Celery 执行 | ✅（修复后） | 旧 worker 签名不匹配曾卡 `queued` |
| GPT Image 2 人像 | ✅ | 棚拍东亚女性半身像 + 产品，符合口播意图 |
| ElevenLabs TTS | ❌ 上游 | KIE `internal error`（多次重试仍失败） |
| Kling 唇形 | ✅（补跑） | 用人像 + 真实语音驱动，口型 MAD≈6.6，身份保持 |

**总评：** 数字人链路**可以真实出片**（人像 + Kling 口型已验证）。当前完整导演一键真实生成会被 **KIE ElevenLabs TTS 不稳定**卡住；TTS 失败后已不再静默 Ken Burns，会明确失败。

---

## 第一轮真实跑（修复前）— 无效假成功

1. Celery 旧进程：`run_director() takes 3-4 args but 5 given` → 一直 queued  
2. 重启后：hex seed `79d97bd087fc` → `int(seed)` 崩掉 → 人像 5ms 失败  
3. TTS KIE internal error  
4. 唇形在缺图时**静默 Ken Burns**（标成完成）→ 看起来像「生成了但不是数字人」

## 已修 Bug

1. Celery include：`face_swap` / `performance`；重启 worker  
2. KIE seed：支持 hex digest  
3. 真实路径缺人像/音频 → **失败**，禁止回退 Ken Burns  
4. TTS 失败 → `failed`（非假 done）；缩短旁白 + Rachel/Adam 重试  

## 第二轮（seed 修复后）

- 人像：**成功**（`bbd8c98600a6.png`，约 1.7MB）  
- TTS：仍 KIE internal error → 唇形正确 **failed**  
- 补跑：`gpt-image` 人像 + espeak 语音 + `kling/ai-avatar-pro`  
  - 成片 9.7MB / 324s / cost 0.6  
  - `mouth_roi_mad_mean=6.619`，`identity_pixel_mad=4.79` → **通过说话数字人代理门槛**

---

## 验收建议

1. 点「真实生成」前确认 `导演模式 = 真实生成可用`  
2. 若卡在配音：看任务是否 `failed` 且文案含「配音失败」（不应再出 Ken Burns）  
3. TTS 恢复后应自动贯通；亦可在 `/create/lipsync` 用人像图 + 自备音频验证口型  
