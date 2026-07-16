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
| live_video 出片 | 本环境仍无稳定成功记录；**不等于** Yapper 默认成片感 |
| Motion 质量 | 输入样片库 ≠ Kling Motion / Act-One |
| 模型数量话术 | Yapper 宣传 17+ / 24+；Betty **9 active** 诚实货架 |
| Stripe 真收款 | bootstrap 有；本环境无 Key |
| 社区飞轮 | Explore 有门闩，内容供给仍弱于 Yapper |

**综合对 Yapper：** 工具面契约约 **90–92%**；生产就绪仍受出片/密钥拖累 → 全局约 **~77–78**（相对此前 ~76 小幅↑）。

---

## 5. 下一刀（ROI）

1. 付费 live_video 周检 ≥2 SKU `outframe_ok`  
2. Extractor vision E2E（稳定 Key + 公开图 URL）  
3. Explore 内容供给 / Remix 转化漏斗  
4. Stripe Price 真注入  

勿再重复：空壳 create 页、假「即将推出」、把 mapping 冒烟当出片。
