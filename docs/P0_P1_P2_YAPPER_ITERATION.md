# P0 / P1 / P2 对标迭代台账（真实验证）

**日期：** 2026-07-16（专业评估刷新）  
**依据：** `docs/YAPPER_PROFESSIONAL_EVALUATION.md` · `docs/YAPPER_FULL_MATRIX_AUDIT.md`  
**原则：** 能 live 的必须 live；不能扩货架绝不虚标；缺口诚实披露。

---

## P0 已落地

| 项 | 实现 | 验证 |
|----|------|------|
| **Seedance Omni** | `reference_*` → KIE；FE 多模态；auto→seedance | **live ok** `fixtures/audit/omni_live_latest.json` |
| **定价 Max** | API `id=max`，`pro` 别名；FE `subscribe("max")` | `/pricing/plans` + audit |
| **Stripe/OIDC 就绪面** | readiness / stripe-status 面 | 本环境仍无 Key（诚实） |
| **货架诚实** | 维持 9 active；lab 不虚增 | createTask 探针失败如实 |

## P1 已落地（本轮闭环）

| 项 | 实现 | 验证 |
|----|------|------|
| **Face Swap** | `i2i_edit` + `google/nano-banana-edit`；`/create/face-swap` | `fixtures/face_swap/last_run.json` |
| **社媒 Extract** | YouTube oEmbed/yt-dlp；TikTok/IG best-effort | caps + audit youtube resolve |
| **Performance Drive** | Motion + 可选 Lipsync；`/create/performance` | caps `motion_plus_optional_lipsync` |
| **Lipsync live** | `LIPSYNC_FIXTURE_LIVE` harness | `fixtures/lipsync/last_run.json` ok |
| **Explore 种子** | gallery seed（密度仍弱于 Yapper） | list≈32 / total≈72 |

## P2 已落地（薄）

| 项 | 实现 | 验证 |
|----|------|------|
| **Product / Headshots / Photo Packs** | 专用路由 → prompt-pack | FE 文件存在 |
| **Motion + Voice** | `voice_text` TTS 旁白（非变声引擎） | API 字段 |
| **Tools hub** | Face Swap / Performance 入口；Motion native 文案 | 代码审查 |

---

## 本轮测试总账

```
yapper_full_matrix_audit (contract)   → 76/76 hard
folded live (motion/lipsync/faceswap/omni) → 4/4
overall_vs_yapper                     → ≈81
betty_internal_readiness              → ≈90
```

## 仍待（下一刀）

1. Stripe/OIDC **密钥注入**（代码已就绪）  
2. Omni **一体 UX**（多镜 + 可选内建唇形）  
3. 更多 KIE 模型 ID 校正后才能诚实扩 active  
4. Face Swap **模板库** / URL-to-Viral 结构深化  
5. Explore 飞轮密度与 Remix 漏斗  
6. Lipsync **周检 Beat**  

勿做：把 lab mapping 标成 active；宣称 Act-One / InsightFace / 18+ 全开而无周检。
