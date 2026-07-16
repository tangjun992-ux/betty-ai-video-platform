# Yapper 核心功能完整矩阵审计（真实测试）

**日期：** 2026-07-16  
**对标站：** [yapper.so](https://yapper.so)  
**分支证据：** `cursor/betty-yapper-parity-d257`  
**原则：** 页面有 ≠ 契约通 ≠ 真出片 ≠ 对标 Yapper 产品完成度。本报告基于本环境实测，不伪造 live。

---

## 0. 一句话结论

Betty **工作室工具面契约已对齐 Yapper 主路径**（硬契约 **62/62 = 100%**），且本轮 live 图/视/Motion 均有出片证据；  
但对 **Yapper 产品整体**仍明显落后：模型货架、Omni/病毒玩法、收款 SSO、社区飞轮。

| 分数（诚实） | 值 | 含义 |
|--------------|----|------|
| 工具面契约 | **100%**（64 hard） | FE/API/OpenAPI + Omni/Max/Packs |
| Live 探针 | **图/视/Motion/Omni** | 含 Omni live 出片 |
| Betty 内部就绪（约） | **~93** | Omni+定价+Explore 密度↑ |
| **对 Yapper 产品对标（约）** | **~76** | 货架/收款/FaceSwap 仍拖累 |

机器可读报告：`backend/fixtures/audit/yapper_full_matrix_latest.json`  
复现：

```bash
cd backend
python3 scripts/yapper_full_matrix_audit.py
YAPPER_AUDIT_LIVE=1 MODEL_SMOKE_LIVE=1 MODEL_SMOKE_LIVE_VIDEO=1 \
  MOTION_FIXTURE_LIVE=1 python3 scripts/yapper_full_matrix_audit.py --live --strict-live
python3 -m pytest tests/ -q   # 本轮 195 passed
```

---

## 1. 本轮真实测试清单

| 套件 | 结果 |
|------|------|
| `pytest tests/` | **195 passed** |
| `yapper_core_parity_harness.py` | **15/15 passed** |
| `yapper_full_matrix_audit.py`（契约） | **62/62 hard** |
| live 图片 `gpt-image-2` + `nano-banana` | **2/2 outframe_ok** |
| live 视频 `seedance-2.0-fast` + `seedance-2.0` | **2/2 outframe_ok** |
| live Motion `kling-3.0/motion-control` | **ok**（本地样片无人物 → 回退 KIE playground 样例出片） |
| Stripe / OIDC | **未配置**（诚实记入 ops gap） |

---

## 2. Yapper 工具矩阵 ↔ Betty 实测状态

图例：**契约** = API/FE 可测；**出片** = 本环境 live；**产品深** = 相对 Yapper 体验深度。

| Yapper 能力 | Betty 入口 | 契约 | 出片 | 产品深 | 备注 |
|-------------|------------|------|------|--------|------|
| Agent（Don't prompt, Just Direct） | `/agent` · director plan/ideate/minimal/storyboard | ✅ | 部分 | 中 | Help Ideate/Prompt 有；成片依赖下游 SKU |
| Image Generation | `/create/image` | ✅ | ✅ | 中 | active 图模型 4；非 17+ |
| Video Generation | `/create/video` | ✅ | ✅ | 中 | Seedance/Kling 真出片；非 Omni 叙事 |
| Seedance 2.0 Omni | 同上 | 部分 | 部分 | **弱** | 缺多模态/多镜/内建唇形产品化 |
| Studio Lip-Syncing | `/create/lipsync` | ✅ | 未本轮付费跑 | 中 | voices+任务链有；非 Max Lip-Sync 专有引擎 |
| Talking Avatar | `/create/avatar` | ✅ | 未本轮付费跑 | 中 | 专用页 + lipsync 后端 |
| Motion Control | `/create/motion` | ✅ | ✅ native | 中高 | `kling-3.0/motion-control`；**≠ Act-One** |
| Timeline Editor | `/create/timeline` | ✅ | 本地 ffmpeg | 中 | SRT parse ✅；深度剪辑弱于专业时间线 |
| Media Upscaling | `/create/upscale` | ✅ | 未本轮 | 中 | edit 路由 |
| BG Remover | `/create/bg-remove` | ✅ | 未本轮 | 中 | |
| Image Extender | `/create/extend` | ✅ | 未本轮 | 中 | |
| Pro Image Editor | `/create/image-editor` | ✅ | 未本轮 | 中 | |
| Prompt Extractor | `/create/extract` | ✅ | heuristic/vision | 中 | **无 TikTok/IG 页面抓取** |
| Generate Audio | `/create/audio` | ✅ OpenAPI | 未本轮 | 中 | 契约测验证错误；付费 TTS 另门控 |
| Explore / Remix | `/explore` | ✅ | n/a | **弱** | ~32 列表项级；非百万级飞轮 |
| Pricing Starter→Max | `/pricing` | ✅ | n/a | 中 | FE Max / API `pro` 命名漂移 |
| Sessions | `/sessions` | ✅ | n/a | 中 | |
| Tools hub | `/tools` | ✅ | n/a | 高 | 全真链接；Motion 文案已改 native |
| Product Shots（专用） | 并入 image | 部分 | — | **弱** | 无独立 App |
| Professional Headshots | 并入 image | 部分 | — | **弱** | 无独立 App |
| AI Photo Packs | ❌ | — | — | **缺** | |
| Face Swap / 病毒模板 | ❌ | — | — | **缺** | |
| URL-to-Viral | Extractor 直链 | 部分 | — | **弱** | 不抓社媒页 |
| Motion + Voice Changer | ❌ | — | — | **缺** | |

---

## 3. 分维度差距（相对 Yapper）

### 3.1 已对齐 / 本轮变强

1. **工具路由矩阵**：Agent / Image / Video / Lipsync / Avatar / Motion / Timeline / Upscale / BG / Extend / Editor / Extract / Audio / Tools / Explore / Pricing / Sessions — FE 文件与 API 契约齐全。  
2. **真出片**：图片 2 SKU、视频 2 SKU、原生 Motion Control 均有 live URL。  
3. **诚实能力探针**：`motion_transfer.mode=native` + `sku=kling-3.0/motion-control`；失败退款 / share publish / storyboard / multi-ref i2i 已声明。  
4. **Agent 最短路径**：`minimal` plan 跳过 compose/字幕，利于对标「just direct」。

### 3.2 硬差距（优先）

| 优先级 | 差距 | Yapper | Betty 现状 | 建议下一刀 |
|--------|------|--------|------------|------------|
| **P0** | 模型货架话术 vs 实际 | 17+ 图 / 26+ 视频 | **9 active**（4 图 + 5 视） | 扩 active 周检或改首页话术为「已验证 N」 |
| **P0** | Seedance Omni 产品化 | 多模态参考 + 多镜 + 内建唇形 | 普通 Seedance T2V/I2V | 视频页 Omni 模式：多 ref + shot list + 可选 lipsync 步 |
| **P0** | 收款上线 | Stripe 订阅成熟 | 本环境 Stripe **未注入** | 注入 Price + webhook，readiness 转绿 |
| **P1** | Lip-Sync 成片感 | Max Lip-Sync / 本地化训练叙事 | KIE 通用 avatar | lipsync fixture live SLO + studio/demo 模型分层话术 |
| **P1** | URL-to-Viral | TikTok/IG → 结构提示词 | 仅文件/直链 Extractor | 社媒 oEmbed/第三方抓取或明确「不支持页面 URL」 |
| **P1** | Explore 飞轮 | 海量资产 + Remix 习惯 | 小样本 gallery | 种子内容、排行、Remix 漏斗指标 |
| **P1** | Face Swap / 模板 | 病毒玩法入口 | 无 | 评估 KIE/上游 face-swap SKU 或模板库 |
| **P2** | Photo Packs / Headshots / Product | 独立 App | 并入 image | 专用向导页（prompt pack + 批量） |
| **P2** | Motion Voice Changer | 动作+变声 | 无 | Motion 后接 TTS/VC 一步 |
| **P2** | 定价命名 | Max + 滑块 | FE Max / API `pro` | 统一 id=`max` |
| **P2** | SSO | 企业登录 | OIDC 未配置 | 部署 IdP |

### 3.3 不要再夸大的点

- Motion **已是原生 Kling Motion Control**，但仍 **不是 Runway Act-One**。  
- 本地 synthetic fixture **过不了人物检测**；出片证据来自 KIE playground 样例（诚实写入 `last_run.json` / audit）。  
- `readiness.ok=true`（development）**≠** 生产可收款。  
- Lab 里 20+ 模型 **≠** active 可售货架。

---

## 4. 评分拆解（审计脚本）

```
components:
  tool_surface: 100.0   # 硬契约
  live:         100.0   # 本轮付费探针
  model_shelf:   42     # vs Yapper 17+/26+
  billing:       28     # Stripe 未配置
  community:     56.4   # gallery 密度有限
→ overall_vs_yapper ≈ 73
→ betty_internal_readiness ≈ 92
```

---

## 5. 建议迭代顺序（ROI）

1. **Omni 视频体验**：多参考 + 分镜 shots 真执行（已有 storyboard，接到 Create Video UI）。  
2. **Active 货架扩展**：Veo/Sora/WAN 等 lab→active 必须带 live 周检，禁止只改文案。  
3. **Stripe/OIDC 注入**：否则对标 Yapper「可订阅创作」永远差一截。  
4. **Lipsync live SLO** + Avatar 一键样片。  
5. **Extractor 社媒 URL** 或产品诚实禁用。  
6. **Face Swap / Photo Packs** 选一个病毒入口做深，避免再铺空壳页。

---

完整迭代细节见 `docs/P0_P1_P2_YAPPER_ITERATION.md`。

## 6. 与旧文档关系

| 文档 | 关系 |
|------|------|
| `YAPPER_CORE_PARITY.md` | 工具面契约台账；本审计覆盖并更新分数语境 |
| `YAPPER_LIVE_PARITY.md` | live 出片细节；本审计复验 ≥2 视频 SKU + Motion native |
| `WORLD_CLASS_BENCHMARK.md` | 多竞品；本审计专打 Yapper |
| `CORE_FEATURE_FINE_GRAINED_ASSESSMENT.md` | 历史细粒度；Motion/出片证据已过期部分以本审计为准 |

**勿重复：** 空壳 create 页、把 mapping 当出片、宣称 Act-One / 17+ 全开而无周检。
