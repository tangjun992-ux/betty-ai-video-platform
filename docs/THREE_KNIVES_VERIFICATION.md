# 三刀优化 · 真实验证与效果评估

**日期：** 2026-07-18  
**提交：** `ec83ea3`  
**门禁：** `backend/scripts/three_knives_verify.py` → **11/11 PASS**  
**产物：** `/opt/cursor/artifacts/three_knives_verify.zip`  
**单元：** `tests/test_three_knives.py` + gap closures → **13 passed**

---

## 1. 落地清单

### 刀 1 · 包装升级

| 项 | 实现 | 验证 |
|----|------|------|
| 授权 BGM URL | `BGM_URL_SOFT/UPBEAT/CINEMATIC/DRAMA` 或 `BGM_URLS` JSON；缓存后 loop | hook 可解析；未配置时 fallback fixtures（诚实） |
| 人声 ducking | narration+BGM → `sidechaincompress` + `asplit` | 5/5 样式 compose 均有音轨 |
| 字幕模板 8–12 | **12** 套：feed/talking/ad/drama/bold/neon/minimal/karaoke/top_banner/soft_shadow/impact/caption_box | count=12 PASS |
| 场景默认 | product_ad→`impact`，anime→`neon` | 单元覆盖 |

### 刀 2 · 变体工厂后半

| 项 | 实现 | 验证 |
|----|------|------|
| 并行出片 | `POST /director/variants/run` | dry-run batch 2 jobs PASS |
| 进度聚合 | `GET /director/variants/progress/{batch_id}` | done=True · finals=2 |
| FE 画廊选优 | 并排卡片 +「采用此变体」 | 代码已接入 Agent |

### 刀 3 · 身份产品化

| 项 | 实现 | 验证 |
|----|------|------|
| 锁强度 | `identity_lock=off\|hero\|edit`（计划+API+FE 开关） | 三模式断言 PASS |
| 身份对比条 | compose 后 `build_identity_strip` → `type=identity_strip` 资产 | dry-run 产出 strip 资产 PASS |
| FE | 成片上方展示对比条；身份锁按钮 | 已接入 |

---

## 2. 效果评估（相对优化前）

| 维度 | 优化前 | 优化后 | 提升判断 |
|------|--------|--------|----------|
| 字幕完成度 | 4 套底栏 | **12** 套场景化模板 | **明显**（CapCut 级仍缺动效花字） |
| BGM | fixtures/正弦 | URL 授权位 + fixtures + ducking | **工程闭环完成**；商用曲需注入 URL |
| 混音 | 固定 amix 比例 | 侧链 ducking（人声优先） | **可感知**（有旁白的广告片） |
| 变体工厂 | 仅计划扇出 | **并行出片 + 画廊选优** | **质变**（Advantage+ 半程补齐） |
| 身份 | 仅 edit 开关（隐式） | 三档锁 + 人眼对比条 | **产品化完成**；非角色库 |

**诚实边界（未宣称关闭）：**
- 未配置 `BGM_URL_*` 时仍用 fixtures（非商用曲库）
- 字幕无卡拉 OK 逐字高亮动效
- 变体真实 KIE 并行出片成本高；本门禁用 dry-run 验证编排，live 路径与单 job 相同
- 身份对比条辅助人眼，不替代 IP-Adapter/LoRA

---

## 3. 正式应用裁决

| 刀 | 评估目标 | 验证 | 可否应用 |
|----|----------|------|----------|
| 包装 | BGM URL + ducking + 8–12 字幕 | **PASS** | ✅ |
| 变体画廊 | 并行出片 + 选优 | **PASS**（dry-run 闭环） | ✅ |
| 身份 | 锁强度 + 对比条 | **PASS** | ✅ |

**结论：三刀均经真实验证，可正式合入应用。**  
下一刀建议：注入真实授权 BGM URL；变体画廊做一次 2 变体 live（控成本）；按用户差评再开。

---

## 4. 复现

```bash
cd /workspace/backend
PYTHONPATH=. .venv/bin/python -m pytest tests/test_three_knives.py tests/test_gap_closures.py -q
PYTHONPATH=. .venv/bin/python scripts/three_knives_verify.py
# 可选：配置授权床后复验
# export BGM_URL_UPBEAT=https://...
```
