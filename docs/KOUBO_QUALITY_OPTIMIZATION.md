# 口播质量优化空间与已落地改进

**用户反馈：** 声音太小；口型与播报「配音感」明显。  
**日期：** 2026-07-17

---

## 诊断（基于已交付两条约片）

| 问题 | 实测 | 根因 |
|------|------|------|
| 声音小 | A **-19.8 LUFS** / B **-24.5 LUFS**（广播目标约 -16） | 全链路无响度归一化 |
| 配音感 / 口型不贴 | Edge TTS 驱动 + Kling 口型 | ① 中文音色曾映射到 Rachel/Adam 听感错位；② 驱动音频偏弱时口型幅度变小；③ Kling 本身有口型天花板 |

Studio「720p」此前**并未**传给 `kling/ai-avatar-pro`（该 SKU 无 resolution 参数）。

---

## 已落地优化

1. **驱动音频 loudnorm → -16 LUFS**（唇形任务 + 导演口播）  
2. **成片二次响度均衡**（Kling 出片后再 loudnorm）  
3. **中文/列表 Neural 音色改走 Edge TTS**（与 UI「晓晓/云希」一致；语速 -5% 利口型）  
4. **Studio 优先 InfiniTalk 720p**，失败回退 Kling  
5. **唇形 prompt** 强化「口型精准匹配语音 / 保持身份」  
6. 货架文案与 quality tips 同步诚实披露  

代码：`app/services/audio_prep.py` · `lipsync_tasks.py` · `director.py`

---

## 仍属模型 / 产品天花板（需预期）

- Kling / InfiniTalk **无法做到影视级音素级口型**，手持产品时手部偶发形变  
- 「完全不像配音」需要更高阶数字人方案或真人拍摄  
- InfiniTalk 队列偶发变慢；Studio 溢价换的是尝试更高清路径，不是魔法  

---

## 使用建议（提升口型贴合）

1. 正面棚拍、嘴巴自然闭合或微张  
2. 台词 **8–20 秒**，避免一口气超长句  
3. 自备音频时保证响度与清晰吐字  
4. 要更稳口型可试 **Studio**（InfiniTalk 优先）  

---

## 已有成片「加大音量」版本（可直接听）

| 文件 | 响度 | 下载 |
|------|------|------|
| A 耳机女主播 | ≈ -16 LUFS | https://tempfile.redpandaai.co/kieai/161815/betty/uploads/A_earbuds_female_loud.mp4 |
| B 护肤男主播 | ≈ -16 LUFS | https://tempfile.redpandaai.co/kieai/161815/betty/uploads/B_skincare_male_loud.mp4 |
