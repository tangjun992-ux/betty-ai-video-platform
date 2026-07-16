# P0 / P1 / P2 对标迭代台账（真实验证）

**日期：** 2026-07-16  
**依据：** `docs/YAPPER_FULL_MATRIX_AUDIT.md`  
**原则：** 能 live 的必须 live；不能扩货架绝不虚标；缺口诚实披露。

---

## P0 已落地

| 项 | 实现 | 验证 |
|----|------|------|
| **Seedance Omni** | `reference_images/videos/audios` → KIE `reference_*_urls`；FE 上传多模态；auto→seedance | **live ok** `fixtures/audit/omni_live_latest.json`（omni=true 出片） |
| **定价 Max** | API `id=max`，`pro` 别名；FE `subscribe("max")`；Stripe MAX/PRO 回退 | pytest + `/pricing/plans` |
| **Stripe/OIDC 就绪面** | MAX price env + readiness 文案；本环境仍无 Key（诚实） | `ops:stripe_configured=false` 仍记录 |
| **货架** | lab SKU 网关多不支持 → **不虚增 active**；维持 9 已验证 | createTask 探针失败如实 |

## P1 已落地

| 项 | 实现 | 验证 |
|----|------|------|
| **Extractor 社媒** | TikTok/IG/YT 页面 URL → 400 诚实拒绝；FE 直链输入 | pytest |
| **Explore 密度** | `seed_gallery` v2 → **40** 条带 likes/views | 脚本输出 |
| **Face Swap** | `capabilities.face_swap.available=false`（无已验证 SKU） | capabilities |
| **Lipsync SLO** | 既有 fixture harness；本轮未重复付费跑（避免刷配额） | 契约仍绿 |

## P2 已落地

| 项 | 实现 | 验证 |
|----|------|------|
| **Product / Headshots / Photo Packs** | 专用路由 → 真 generate 工作流 | FE 文件存在 |
| **Motion + Voice** | `voice_text` → TTS 旁白附件（非变声引擎） | API 字段 + task 分支 |
| **Tools hub** | 入口对齐到专用页；Motion native 文案 | 代码审查 |

---

## 本轮测试总账

```
pytest tests/                         → 202 passed
yapper_core_parity_harness            → 15/15
yapper_full_matrix_audit (contract)   → 64/64 hard
Omni live                             → ok (seedance-2-fast + reference_image)
Gallery seed                          → 40 items
```

## 仍待（下一刀）

1. Stripe/OIDC **密钥注入**（代码已就绪）  
2. 更多 KIE 模型 ID 校正后才能诚实扩 active  
3. Face Swap：找到可 live 的上游 SKU 再开入口  
4. URL-to-Viral：社媒 oEmbed/抓取（合规前提）  
5. Lipsync 付费周检纳入 Beat  

勿做：把 lab mapping 标成 active；假 Face Swap 页；宣称 Act-One / 17+ 全开。
