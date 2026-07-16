# Omni 一体 · Explore 飞轮 · 货架诚实（本轮交付）

**日期：** 2026-07-16  
**原则：** 真接线、真契约、不虚标货架；口型仍走 `/lipsync`，≠ Act-One。

## 1. Omni 一体体验

| 能力 | 实现 |
|------|------|
| 上传 | `/upload` 接受 image/video/audio（视 50MB / 音 20MB / 图 10MB） |
| 单镜 Omni | Create Video → `reference_*` + `generate_audio` + Omni 芯片 |
| 真分镜 × Omni | `StoryboardRequest` 携带 refs；每镜 params 含 omni；Executor 传给 adapter |
| 绑定元素 | UI 写入 `@ImageN/@VideoN/@AudioN` |
| 生成音轨 | Seedance `generate_audio` 开关 |
| 完成后唇形 | 成片后跳转 `/create/lipsync?image_url=`（Kling avatar） |

## 2. 货架诚实（改话术，不虚增 active）

- 首页模型数 ← `GET /models` `active_count`
- Pricing Credits 表去掉 Veo/Sora/Runway 虚标价
- Dashboard `AVAILABLE_MODELS` = 9 个 active
- Agent 占位符不再暗示 Veo 可切换

## 3. Explore 做深

- `demo_seed_v1|v2` 均识别为示例
- `item_key = {task_id}_{result_index}` 对齐 seed likes
- 网格/灯箱「做同款」走 `POST /gallery/{id}/remix`

## 4. Face Swap 模板（薄加深）

- 5 个风格 prompt pack（海报/职场/赛博/漫画/胶片）
- 诚实：仍需用户双图；非 InsightFace 模板库

## 验证

```bash
cd backend
python3 -m pytest tests/test_omni_explore_honesty.py -q
```
