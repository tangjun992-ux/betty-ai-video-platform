# 五大差距优化 · 正式门禁验证报告

**日期：** 2026-07-18  
**提交：** `02726ee` + 门禁脚本修复  
**门禁脚本：** `backend/scripts/optimize_gate_verify.py`  
**产物：** `/opt/cursor/artifacts/optimize_gate_verify.zip`  
**裁决：`tests 15/15 PASS` · `capabilities 5/5 PASS`**

> 本报告只记录**真实验证结果**。评估能力见 `docs/GAP_CLOSURE_DEEP_ANALYSIS.md`；二者同时成立后，本轮优化才算正式应用。

---

## 本轮落地（相对评估方案）

| # | 评估能力 | 本轮代码迭代 | 验证方式 |
|---|----------|--------------|----------|
| 1 | CLOSE-UP + Kling 默认 + 驱动音频优化 | TTS `rate=-8%`（口播） | 计划断言 + 真实口播出片 |
| 2 | 原生 9:16 图 + i2v | 保持映射修复 | 真实生图 + Kling i2v |
| 3 | 字幕样式 + BGM | `fixtures/music/{preset}.wav` 优先 | 本地 compose + ffprobe 音视频轨 |
| 4 | shot>1 `identity_variant` | 已有 edit→i2v；补 live | 2 镜 UGC + celery 日志 |
| 5 | 变体扇出 + 执行 | FE「创意变体」+ 真实执行 1 变体 | API + async 出片 |

---

## 门禁结果（真实）

### Gap1 · 口型路径

| 探针 | 结果 |
|------|------|
| `gap1_talking_plan_closeup_kling` | PASS · `prefer_infinitalk=False` · Kling Avatar Pro · CLOSE-UP |
| `gap1_tts_rate_param` | PASS · `synthesize_speech_edge(..., rate=)` |
| `gap1_live_talking` | PASS · **1080×1920 · 10.7s · audio=True · final=True** |

**能力裁决：PASS（部分弥补，非 HeyGen 旗舰口型）。**

### Gap2 · 原生竖屏

| 探针 | 结果 |
|------|------|
| `gap2_size_mapping` | PASS · `1080x1920` |
| `gap2_native_9_16_image` | PASS · **941×1672**（ratio 1.777） |
| `gap2_native_9_16_i2v` | PASS · **1080×1916** |

**能力裁决：PASS（差距基本关闭）。**

### Gap3 · BGM / 字幕包装

| 探针 | 结果 |
|------|------|
| `gap3_fixture_bgm_present` | PASS · upbeat.wav ~1.7MB |
| `gap3_compose_{ad,feed,talking}_has_av` | PASS · 三套样式均有 **audio+video** |

**能力裁决：PASS（工程层包装；非商用曲库）。**

### Gap4 · 跨镜身份

| 探针 | 结果 |
|------|------|
| `gap4_plan_identity_variant_flag` | PASS · 2 镜 · shot2 `identity_variant=True` · compose 保留 |
| `gap4_identity_variant_edit_logged` | PASS · celery: `[director] identity_variant edit ok shot=2` |
| `gap4_live_multishot_final` | PASS · **1080×1920 · final=True · audio=True · videos=3** |

**首轮诚实问题：** 裁镜脚本未重写 subtitle 依赖 → compose 被「依赖未满足」跳过（`final=False`）。  
**已修复门禁 `strip_to_n_videos` 并复跑 → 包装成片 PASS。**  
产品路径本身在完整 UGC plan 下本来就有 compose；失败点在验证夹具，已如实记录并修正。

**能力裁决：PASS（edit 路径真实触发 + 包装成片）。**

### Gap5 · 变体工厂

| 探针 | 结果 |
|------|------|
| `gap5_variants_api` | PASS · count=3 · seed/钩子/CTA |
| `gap5_variant_executed` | PASS · 变体 A · **7.5s · audio=True · final=True** |
| FE | 「创意变体」按钮 → `/director/variants` → 采用计划 |

**能力裁决：PASS（编排 + 至少一条变体真实出片）。**

---

## 正式应用裁决

| 差距 | 评估可弥补度 | 本轮验证 | 可否正式应用 |
|------|--------------|----------|--------------|
| 1 口型 | ~15–25% | PASS | ✅ 应用（诚实：非旗舰口型） |
| 2 竖屏 | ~90% | PASS | ✅ 应用 |
| 3 包装 | ~40% | PASS | ✅ 应用（诚实：非曲库） |
| 4 身份 | ~35% | PASS（含日志+成片） | ✅ 应用 |
| 5 变体 | ~50% | PASS（含执行） | ✅ 应用 |

**结论：** 五项评估能力均经真实验证通过，本轮优化可正式合入应用。上游天花板（HeyGen 口型、商用曲库、角色库）未宣称关闭。

---

## 复现

```bash
# API + Celery 需已启动，KIE 已配置
cd /workspace/backend
PYTHONPATH=. .venv/bin/python -m pytest tests/test_gap_closures.py -q
PYTHONPATH=. .venv/bin/python scripts/optimize_gate_verify.py
# 部分重跑：
PYTHONPATH=. .venv/bin/python scripts/optimize_gate_verify.py --only=gap4,gap5
```
