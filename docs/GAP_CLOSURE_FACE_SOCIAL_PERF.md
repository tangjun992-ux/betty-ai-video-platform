# 缺口闭环：Face Swap / 社媒 Extract / Performance / Lipsync Live

**日期：** 2026-07-16  
**原则：** 只上线已 live 或可验证解析的能力；文案诚实。

## Face Swap

| 项 | 内容 |
|----|------|
| SKU | `google/nano-banana-edit` |
| 模式 | `i2i_edit`（双图指令合成） |
| Live | `fixtures/face_swap/last_run.json` — createTask → success 出图 |
| API | `POST /api/v1/face-swap`、`/face-swap/upload` |
| FE | `/create/face-swap` |
| 非宣称 | InsightFace / Roop 像素级身份换脸 |

## 社媒页 Extract

| 平台 | 状态 |
|------|------|
| YouTube | oEmbed / yt-dlp 封面 → Vision/heuristic |
| TikTok / IG / X | yt-dlp best-effort；IP 封锁 → 400 诚实 |
| 抖音 / 小红书 | 未接入 |

实现：`app/services/social_resolve.py`；依赖 `yt-dlp`。

## Performance Drive（≠ Act-One）

| 项 | 内容 |
|----|------|
| 组合 | 原生 Kling Motion Control + 可选 Lipsync 口播分轨 |
| API | `POST /api/v1/performance` |
| FE | `/create/performance` |
| 诚实 | 不是 Runway Act-One 表演编码器 |

## Lipsync Live

| 项 | 内容 |
|----|------|
| 门控 | `LIPSYNC_FIXTURE_LIVE=1` |
| 证据 | `fixtures/lipsync/last_run.json` |
| 模型 | `kling/ai-avatar-pro` |
| 结果 | `ok=true` + mp4 URL |

## 复验

```bash
cd backend
python3 -m pytest tests/test_gap_faceswap_social_performance.py tests/test_p0_omni_pricing_extract.py -q
LIPSYNC_FIXTURE_LIVE=1 python3 scripts/fixture_derivative_harness.py
python3 scripts/platform_full_e2e.py
```
