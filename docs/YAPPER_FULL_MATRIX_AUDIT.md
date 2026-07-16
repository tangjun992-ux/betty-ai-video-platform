# Yapper 核心功能完整矩阵审计（真实测试）

**日期：** 2026-07-16（缺口闭环后刷新）  
**对标站：** [yapper.so](https://yapper.so)  
**分支证据：** `cursor/betty-yapper-parity-d257`  
**原则：** 页面有 ≠ 契约通 ≠ 真出片 ≠ 对标 Yapper 产品完成度。本报告基于本环境实测，不伪造 live。  
**专业长文：** 见 `docs/YAPPER_PROFESSIONAL_EVALUATION.md`。

---

## 0. 一句话结论

Betty **工作室工具面契约已对齐 Yapper 主路径**（硬契约 **76/76 = 100%**），且 Motion / Lipsync / Face Swap / Omni 均有出片证据；  
对 **Yapper 产品整体**仍落后在模型货架、收款 SSO、Explore 飞轮与病毒玩法深度。

| 分数（诚实） | 值 | 含义 |
|--------------|----|------|
| 工具面契约 | **100%**（76 hard） | FE/API/OpenAPI + FaceSwap/Performance/Omni/Max |
| Live（折叠证据） | **4/4** | Motion / Lipsync / FaceSwap / Omni last_run |
| Betty 内部就绪（约） | **~90** | 可演示可出片 |
| **对 Yapper 产品对标（约）** | **~81** | 货架/收款仍拖累；深度闭环 +12 |

机器可读报告：`backend/fixtures/audit/yapper_full_matrix_latest.json`  
复现：

```bash
cd backend
python3 scripts/yapper_full_matrix_audit.py
```

---

## 1. 本轮真实测试清单

| 套件 | 结果 |
|------|------|
| `yapper_full_matrix_audit.py`（契约） | **76/76 hard** |
| 折叠 live：Motion / Lipsync / FaceSwap / Omni | **4/4 ok** |
| Stripe / OIDC | **未配置**（诚实记入 ops gap） |
| 模型货架 | **active=9** / lab≈20（故意不虚增） |

---

## 2. Yapper 工具矩阵 ↔ Betty（摘要）

完整 26 行见 `YAPPER_PROFESSIONAL_EVALUATION.md` §2。本轮相对旧审计的关键变化：

| 能力 | 旧状态 | 现状态 |
|------|--------|--------|
| Face Swap | ❌ 无路由 | ✅ i2i_edit live（nano-banana-edit） |
| 社媒 Extract | 页面 URL 拒绝 | YouTube ✅；TikTok/IG best-effort |
| Performance Drive | 无 | ✅ Motion+可选 Lipsync（≠ Act-One） |
| Lipsync | 契约 | ✅ live `kling/ai-avatar-pro` |
| Omni | 部分 | ✅ live + caps |
| Pricing Max | FE/API 漂移 | ✅ API `id=max` 对齐 |
| Photo Packs / Product / Headshots | 缺或并入 | ✅ 独立路由（薄，prompt-pack） |

---

## 3. 硬差距看板（刷新）

| 优先级 | 差距 | 状态 |
|--------|------|------|
| **P0** | 模型货架 vs 18+/26+ | open（active=9） |
| **P0** | Omni 产品深度（内建唇形/多镜一键） | partial |
| **P0** | Stripe/OIDC 注入 | open |
| **P1** | Lip-Sync 周检 / 专有叙事 | partial |
| **P1** | Face Swap 模板库 | partial |
| **P1** | URL-to-Viral 完整结构 | partial |
| **P1** | Explore 飞轮密度 | open |
| **P2** | Packs 批量 / VC / Max 滑块 | partial |

---

## 4. 评分拆解

```
components:
  tool_surface: 100.0
  live:         100.0   # 折叠 last_run
  model_shelf:   42
  billing:       28
  community:     56.4
depth_bonus:     12
→ overall_vs_yapper ≈ 81
→ betty_internal_readiness ≈ 90
```

---

## 5. 不要再夸大的点

- Motion **原生 Kling** ≠ Act-One；Performance 亦然。  
- Face Swap = **i2i_edit** ≠ InsightFace。  
- 折叠 last_run ≠ 本轮重新付费 live。  
- `readiness.ok`（dev）≠ 生产可收款。  
- Lab ≠ active。

完整迭代见 `docs/P0_P1_P2_YAPPER_ITERATION.md`；专业评估见 `docs/YAPPER_PROFESSIONAL_EVALUATION.md`。
