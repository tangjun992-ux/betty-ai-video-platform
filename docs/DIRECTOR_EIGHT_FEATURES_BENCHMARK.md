# 智能体导演 · 八功能对标验收

**日期：** 2026-07-17  
**目标：** 按 Agent 卡片顺序真实出片，对照全球顶级平台门槛验收，并交付每功能 ≥2 个样本。

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

| 功能 | 对标 | 平台必须交付 |
|------|------|--------------|
| 产品广告 | Meta Advantage+ / Pika ads | 钩子分镜 + 多镜合成一条成片 |
| UGC 种草 | Arcads / Creatify | 竖屏手持节拍，非影院建立镜头 |
| 动漫 | Runway / Luma stylized | 二次元光影，非写实串味 |
| AI 写真 | HeadshotPro / Aragon | 职业头肩套图，非产品三视图 |
| 产品商业片 | Runway / Kling Master | ≥4 镜叙事 + 合成 |
| 微短剧 | ShortMax 节奏 | 钩子/冲突多镜 + 竖屏合成 |
| 产品摄影 | Photoroom / Claid | 影棚多角度套图 |
| 数字人口播 | HeyGen / Hedra | 清晰驱动音 + 唇形视频（有模型天花板） |

## 本轮已落地优化

1. **稳定 `scenario` id**（FE 卡片 → API → Planner），不再仅靠关键词误路由  
2. **UGC / 广告 / 商业片分轨运镜词**  
3. **AI 写真改为职业头像四姿态**（修复产品角度误用）  
4. **多镜快速成片仍 compose**（可投放/可验收的一条成片）  
5. **微短剧 minimal 仍 ≥2 镜**  
6. **广告/商业片强制 Kling Master；UGC 强制 Kling Pro**

## 诚实天花板

- 视频运动/口型受 Kling、Seedance、Avatar 上游限制，无法宣称已全面追平 HeyGen/Runway 旗舰演示  
- 商业片 6 镜真实出片耗时长、成本高  
- ElevenLabs via KIE 仍可能抖动；口播优先 Edge TTS + loudnorm

## 样本产出

```
/opt/cursor/artifacts/director_eight_features/<scenario>/{A,B}_*
/workspace/artifacts/director_eight_features/
backend/fixtures/audit/director_eight_features_latest.json
```

脚本：`backend/scripts/director_eight_features_e2e.py`
