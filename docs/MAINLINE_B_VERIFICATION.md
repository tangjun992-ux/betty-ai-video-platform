# 主线 B · 投放完成度 · 真实验证与效果评估

**日期：** 2026-07-18  
**提交：** `c8f9126` / `a58fd4c` / `315e4ff`  
**门禁：** `backend/scripts/mainline_b_verify.py` → **15/15 PASS**  
**产物：** `/opt/cursor/artifacts/mainline_b_verify.zip`  
**单元：** `tests/test_mainline_b.py` + 相关 → **20 passed**

---

## 1. 落地清单

### B1 · 可投放 BGM（8 条 Stock Beds）

| 项 | 实现 | 验证 |
|----|------|------|
| 8 presets | soft/upbeat/cinematic/drama/corporate/energetic/chill/hype | installed=8 |
| 公开 URL | `$STORAGE/bgm/` → `/api/v1/media/bgm/{preset}.wav` | HTTP 200 · 2.1MB |
| 环境覆盖 | `BGM_URL_*` / `BGM_URLS` JSON 仍优先 | hook 保留 |
| LICENSE | `fixtures/music/LICENSE.md`（平台自有 procedural beds） | 诚实：非 Epidemic 级曲库 |

### B2 · 广告变体优先 + 2 变体 LIVE

| 项 | 实现 | 验证 |
|----|------|------|
| 广告场景默认 | `product_ad`/`product_commercial` → 先 `/variants` n=2 | FE `startScenario` |
| 并行 live | `/variants/run` dry_run=false · 各 1 镜控成本 | **finals=2** · A/B 成片已落盘 |
| 画廊选优 | 既有 FE 并排采用 | 沿用三刀 UI |

### B3 · Meta/TikTok/Reels 导出规格

| 投放位 | 画幅 | 时长建议 | 默认 BGM/字幕 |
|--------|------|----------|---------------|
| meta_feed | 16:9 | 6–15s | upbeat / impact |
| meta_stories | 9:16 | 5–15s | hype / bold |
| tiktok | 9:16 | 8–30s | energetic / feed |
| reels | 9:16 | 7–30s | hype / neon |
| youtube_shorts | 9:16 | 8–60s | upbeat / caption_box |
| youtube_landscape | 16:9 | 10–60s | cinematic / ad |

API：`GET /director/export-specs`；计划带 `export_placement` + `placement_warnings`。

### B4 · 口播/UGC/广告 brief 模板库

| 场景 | 模板数 | 示例 |
|------|--------|------|
| product_ad | 3 | 痛点钩子 / 利益钩子 / Stories 竖版 |
| ugc | 3 | 自拍安利 / 前后对比 / Reels 种草 |
| talking_avatar | 3 | 卖点口播 / 问答 / 开箱 |

API：`GET /director/brief-templates`；FE「成片模板」芯片一键开拍。

---

## 2. 门禁结果（真实）

```
PASS b_bgm_stock_count / b_bgm_public_urls / b_bgm_http_fetch
PASS b_export_specs (6) / b_brief_templates (9)
PASS b_plan_meta_feed / b_compose_stock_bgm
PASS b_api_export-specs / brief-templates / bgm-catalog
PASS b_variants_plan_n2
PASS b_live_variants :: done=True finals=2
PASS b_variant_A_file · b_variant_B_file
SUMMARY 15/15
```

Live 成片：
- `b_variant_A.mp4` (~1.9MB)
- `b_variant_B.mp4` (~3.0MB)

---

## 3. 效果评估

| 维度 | 优化前 | 优化后 | 裁决 |
|------|--------|--------|------|
| BGM 可试投 | fixtures 本地路径 | **8 条公开 URL + 可换授权** | ✅ 工程闭环 |
| 广告产能 | 单计划 | **默认变体优先 + live 双成片** | ✅ 质变 |
| 投放位 | 仅 9:16/16:9 | **6 个命名投放规格 + 校验** | ✅ |
| 默认成片感 | 空白 brief | **9 套钩子/时长/CTA 模板** | ✅ |

**诚实边界：** Stock Beds 为平台自有 procedural（见 LICENSE），非商用曲库；生产可替换 `BGM_URL_*`。Live 变体为控成本裁为每变体 1 镜，路径与完整多镜相同。

---

## 4. 正式应用

主线 B 四项均经真实验证，**可正式合入应用**。  
下一阶段建议回到主线 A（能卖：收款/CDN/失败 UX）或按真实投放差评迭代。
