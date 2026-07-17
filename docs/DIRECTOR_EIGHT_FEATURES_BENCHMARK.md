# 智能体导演 · 八功能对标验收

**日期：** 2026-07-17  
**目标：** 按 Agent 卡片顺序真实出片，对照全球顶级平台门槛验收，并交付每功能 ≥2 个样本。  
**样本状态：** **16/16 已齐**（详见下方「样本产出」）

## 验收顺序（与货架阅读序一致）

1. 产品广告 `product_ad`  
2. UGC 种草 `ugc`  
3. 动漫生成 `anime`  
4. AI 写真 `ai_portrait`  
5. 产品商业片 `product_commercial`  
6. 微短剧 `micro_drama`  
7. 产品摄影 `product_photo`  
8. 数字人口播 `talking_avatar`

## 对标参照与平台侧必须项

详见 `backend/app/director_scenarios.py` → `BENCHMARKS`。摘要：

| 功能 | 对标 | 平台必须交付 | 样本 |
|------|------|--------------|------|
| 产品广告 | Meta Advantage+ / Pika ads | 钩子分镜 + 多镜合成一条成片 | A/B `*_FINAL.mp4` |
| UGC 种草 | Arcads / Creatify | 竖屏手持节拍，非影院建立镜头 | A/B `*_FINAL.mp4` |
| 动漫 | Runway / Luma stylized | 二次元光影，非写实串味 | A/B 单镜 + 关键帧 |
| AI 写真 | HeadshotPro / Aragon | 职业头肩套图，非产品三视图 | A/B 各 4 张 |
| 产品商业片 | Runway / Kling Master | ≥4 镜叙事 + 合成 | A/B `*_FINAL.mp4`（样本 15s/4 镜；产品路径 30s/6 镜） |
| 微短剧 | ShortMax 节奏 | 钩子/冲突多镜 + 竖屏合成 | A/B `*_FINAL.mp4` |
| 产品摄影 | Photoroom / Claid | 影棚多角度套图 | A/B 各 4 张 |
| 数字人口播 | HeyGen / Hedra | 清晰驱动音 + 唇形视频 | A/B 唇形 mp4；响度 ≈ -16 LUFS |

## 本轮已落地优化

1. **稳定 `scenario` id**（FE 卡片 → API → Planner），不再仅靠关键词误路由  
2. **UGC / 广告 / 商业片分轨运镜词**  
3. **AI 写真改为职业头像四姿态**（修复产品角度误用）  
4. **多镜快速成片仍 compose**（可投放/可验收的一条成片）  
5. **微短剧 minimal 仍 ≥2 镜**  
6. **广告/商业片强制 Kling Master；UGC 强制 Kling Pro**  
7. **Kling Pro i2v** 公开 `image_url`/`source_url` + 本地上传兜底  
8. **口播** Edge Neural TTS + loudnorm（-16 LUFS）；InfiniTalk **不再静默回退**（仅 Studio 显式 `prefer_infinitalk`）

### 对标对齐 · 第二轮（画幅 / 包装 / 口播 / 身份 / 叙事）

1. **画幅硬化**：UGC / 微短剧 / 口播强制 `9:16`；产品广告 / 商业片 / 动漫强制 `16:9`（brief 写「竖屏」也不能撬开渠道锁；refine 同理）  
2. **成片包装层**：字幕烧录 + 软 BGM + 片尾 CTA（快速模式也保留字幕/BGM/CTA；完整模式另加 TTS）  
3. **口播强化**：男女声 Edge Neural 路由（Xiaoxiao / Yunxi）、更长旁白、统一 lipsync prompt、成片保留人声并包字幕+CTA  
4. **跨镜身份锁定**：hero/关键帧 `identity_from`，多镜 i2v 始终锚定同一主体图  
5. **动漫/短剧多镜叙事**：`ANIME_BEATS` 叙事弧；动漫 minimal 亦 ≥2 镜并合成

## 诚实天花板

- 视频运动/口型受 Kling、Seedance、Avatar 上游限制，无法宣称已全面追平 HeyGen/Runway 旗舰演示  
- 商业片完整 6 镜真实出片耗时长、成本高；本包 QA 样本为 15s/4 镜  
- ElevenLabs via KIE 仍可能抖动；口播优先 Edge TTS + loudnorm

## 样本产出

```
/opt/cursor/artifacts/director_eight_features/<scenario>/{A,B}_*
/workspace/artifacts/director_eight_features/
backend/fixtures/audit/director_eight_features_latest.json
```

脚本：`backend/scripts/director_eight_features_e2e.py`

### 口播响度（实测）

- A：Input Integrated **-15.9 LUFS**  
- B：Input Integrated **-16.3 LUFS**  
