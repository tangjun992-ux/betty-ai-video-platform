# Yapper 核心功能对标 · 完整测试与优化台账

**日期：** 2026-07-16  
**目标：** 严格对标 [yapper.so](https://yapper.so) 工作室核心工具矩阵；契约/API 全测 + 缺口补齐。  
**原则：** 页面有 ≠ 链路通 ≠ 真出片；本轮验的是 **Yapper 工具面契约对齐**，不伪造 live 视频成功。

---

## 1. Yapper 工具矩阵 ↔ Betty

| Yapper 能力 | Betty 路由 / API | 本轮状态 |
|-------------|------------------|----------|
| Agent（Don't prompt, just direct） | `/agent` · `/director/*` | ✅ plan/storyboard/brain 契约通过 |
| Image generate | `/create/image` · `POST /generate/` | ✅ analyze + 目录 active |
| Video generate | `/create/video` · `POST /generate/` | ✅ UI 收起工具栏已修；live 出片另计 |
| Studio Lip-Syncing | `/create/lipsync` · `POST /lipsync` | ✅ voices + 链路 |
| Talking Avatar | `/create/avatar` · lipsync 后端 | ✅ **本轮新建专用页**（图+音频优先） |
| Motion Control | `/create/motion` · `/motion` | ✅ samples；原生 `kling-3.0/motion-control` |
| Timeline Editor | `/create/timeline` | ✅ SRT parse 契约 |
| Media Upscaling | `/create/upscale` · `/generate/edit` | ✅ 真路由（tools 页已修正） |
| Background remove | `/create/bg-remove` | ✅ |
| Extend / edit | `/create/extend` · `/create/image-editor` | ✅ |
| Prompt Extractor | `/create/extract` · `POST /generate/extract-prompt` | ✅ **本轮实现**（vision/heuristic） |
| Generate Audio | `/create/audio` · `/generate/speech` | ✅ tools 页链到真路由 |
| Explore | `/explore` · `/gallery/` | ✅ list 契约 |
| Pricing 4 档 | `/pricing` · `/pricing/plans` | ✅ starter/personal/creator/pro |
| Sessions | `/sessions` · director sessions | ✅ 既有 |
| Tools hub | `/tools` | ✅ **按 Yapper 矩阵重排，全真链接** |

---

## 2. 本轮优化（代码）

1. **Prompt Extractor**：`prompt_extract.py` + `POST /generate/extract-prompt` + FE `/create/extract`  
2. **Talking Avatar**：专用 `/create/avatar`（不再 redirect）  
3. **Tools hub**：对齐 Yapper 分组；修复放大/去背景/音频误链到错误页  
4. **Video 左侧栏收起**：实现 collapse（原 TODO）  
5. **capabilities**：声明 `prompt_extractor` / `talking_avatar`  
6. **assets.folder 迁移**：修复库表漂移导致上传/提取失败  
7. **测试矩阵**：`tests/test_yapper_core_parity.py` + `scripts/yapper_core_parity_harness.py`  
8. **pytest.ini**：仅收集 `tests/`（排除根目录 `test_kie_direct.py` 异步裸测）

---

## 3. 验证结果

```bash
cd backend
.venv/bin/python -m pytest tests/test_yapper_core_parity.py -q   # 16 passed
.venv/bin/python -m pytest tests/ -q                            # 185 passed
.venv/bin/python scripts/yapper_core_parity_harness.py          # passed=true
```

| 探针 | 结果 |
|------|------|
| Yapper core parity pytest | **16/16** |
| 全量 tests/ | **185 passed** |
| harness | 全契约项 ok（JSON report） |
| Motion 诚实 | `mode=native`（Kling Motion；非 Act-One） |
| Extractor | heuristic 或 vision（视 Key） |

---

## 4. 仍不对齐 / 勿夸大（诚实）

| 项 | 说明 |
|----|------|
| 完整矩阵审计 | 见 **`docs/YAPPER_FULL_MATRIX_AUDIT.md`**（2026-07-16 真测） |
| live 出片 | 图2 + 视2 + Motion native 已有证据；仍 ≠ Yapper 默认成片感/货架 |
| Motion | 原生 Kling Motion Control；**≠ Act-One** |
| 模型数量话术 | Yapper 宣传 17+ / 26+；Betty **9 active** 诚实货架 |
| Stripe / OIDC | 本环境未注入 |
| 社区飞轮 / Omni / FaceSwap / URL-to-Viral | 仍弱或缺失 |

**综合对 Yapper（完整审计）：** 工具面契约 **100%**；产品对标约 **~73**；Betty 内部就绪约 **~92**（live 拉高，货架/收款拉低对标分）。

---

## 5. 下一刀（ROI）

1. Seedance Omni 产品化（多 ref + 真分镜接到 Create Video）  
2. Active 货架扩展（必须带 live 周检）  
3. Stripe / OIDC 注入  
4. Explore 飞轮 + Extractor 社媒 URL（或诚实禁用）  
5. Face Swap / Photo Packs 选一个做深  

勿再重复：空壳 create 页、假「即将推出」、把 mapping 冒烟当出片、宣称 Act-One。
