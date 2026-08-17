# Betty × Yapper 核心功能全维测试方案

**日期：** 2026-08-16  
**对标站：** [yapper.so](https://yapper.so)（公开页：首页 /create/video /pricing /explore，非内部反编译）  
**原则：** 页面能开 ≠ 契约通 ≠ 真出片 ≠ 产品完成度；**本机污染分 ≠ 产品分**；禁止虚标货架、收款、货架数量与模型代际。  
**叠在：** `docs/PLATFORM_FULL_TEST_PLAN.md`（L0–L5）之上，本文件补 **L6 界面专业性 / L7 UX 友好 / L8 性能**，并按核心面做 Yapper 对照检查表。

**可执行入口：**

```bash
# A. 本方案验证脚本（契约 + 源码 UX 门闩 + 延迟探针，不烧钱）
cd backend && PYTHONPATH=. python3 scripts/core_yapper_full_verify.py

# B. 本轮回归
PYTHONPATH=. python3 -m pytest tests/test_p4_core_yapper_ux.py -q
cd frontend && npm test -- --run src/app/create/video/__tests__/VideoPage.test.tsx src/app/pricing/__tests__/PricingPage.test.tsx

# C. 既有全量（L0–L5）
cd backend && python3 scripts/platform_full_e2e.py
python3 -m pytest tests/ -q
```

报告：`/opt/cursor/artifacts/core_yapper_full_verify.json`

---

## 0. 目标与诚实边界

### 要证明什么

一位持怀疑态度的工程师应能从本方案看出：

1. **可用性**：核心面（首页 / 图 / 视 / Agent / Explore / Pricing / Extract）能打开，主 CTA 有去处。
2. **完整性**：Yapper 公开卖的「工作室工具」Betty 是否有对等入口与契约；缺的必须点名。
3. **性能**：报价 / 能力探针 / 定价接口的**进程内延迟**有记录；**不把 demo 3 秒写成 SLA**。
4. **界面专业性**：定价对照、创作页灵感、诚实条是否像成熟 SaaS，而不是跳走或空卡片。
5. **UX 友好**：灵感芯片填词、限额一眼可比、失败路径诚实。

### 明确不做 / 不虚标

| 禁止 | 原因 |
|------|------|
| 把 lab SKU 算进 active | 本环境货架仍是 **active=9** |
| 宣称 Seedance 2.5 / Veo / Sora | Betty 主推仍是 **Seedance 2.0** |
| 宣称 Stripe/OIDC 可收款 | 本环境 **无 Key** |
| Explore「millions of assets」 | 本地 gallery 视种子，空库=0 |
| Voice = 实时变声 / RVC | 仅 TTS 旁白 |
| URL-to-Viral = 原片逐帧反推 | oEmbed + 投放规格分镜 |
| 把 TestClient 延迟写成生产 SLA | 无 Redis/Celery 的 VM 不能代表线上 |

---

## 1. 分层（L0–L8）

| 层 | 含义 | 通过标准 | 失败含义 |
|----|------|----------|----------|
| L0 可达 | FE 路由 / API 注册 | 200 + 无死链 | 空壳 |
| L1 契约 | 字段、鉴权、能力探针 | 正确状态码与诚实字段 | 协议漂移 |
| L2 入队 | Task + 扣积分 + 派发 | `task_id` | 调度/计费断 |
| L3 出片 | 上游可访问 media | live URL / 折叠证据 | 假成功 |
| L4 产品深 | 对标 Yapper 体验 | 见 §2 检查表 | 功能浅 |
| L5 生产 | Stripe/OIDC/CDN | 生产 env 下 ok | 不能上线收款 |
| **L6 界面专业性** | 对照表、货架诚实、视觉层级 | 定价 Limits 表 + 卡片限额 + 无虚标数字 | 像 demo 站 |
| **L7 UX 友好** | 灵感填词、少跳走、失败可读 | Video Ideas 填 composer；Agent 只作细化 | 用户被踢出创作流 |
| **L8 性能** | quote / capabilities / plans 延迟 | 记录 p50；进程内 < 800ms 为 UX 预算 | 输入卡顿（非 SLA） |

L0–L5 细则仍以 `PLATFORM_FULL_TEST_PLAN.md` 为准。本文件只把 L6–L8 写进门禁。

---

## 2. 核心面对标检查表

图例：✅ 本轮已对等或已补；◐ 契约在、体验仍浅；❌ 公开叙事 Betty 没有（诚实缺口）。

### 2.1 首页 / Dashboard

| ID | Yapper | Betty 期望 | 层 | 自动化 |
|----|--------|------------|----|--------|
| H1 | Don't prompt, Just Direct + 主输入 | 对话式首页 + 四 CTA | L4/L6 | Dashboard vitest |
| H2 | 一键进视频/Agent | Create Content → `/create/video?prompt=` | L7 | Dashboard vitest |
| H3 | 百万素材叙事 | **禁止**写 millions；有种子才有 Explore 数 | L6 | 文案审计 |

### 2.2 图片 `/create/image`

| ID | Yapper | Betty 期望 | 层 |
|----|--------|------------|----|
| I1 | 推荐词填入 composer | `SUGGESTIONS` 可点填词 | L7 |
| I2 | 参考图 1–N | `reference_images` 真传 | L2 |
| I3 | Remix 预填 | query `prompt` / `image_url` | L1 |

### 2.3 视频 `/create/video`（本轮重点）

| ID | Yapper | Betty 期望 | 层 | 自动化 |
|----|--------|------------|----|--------|
| V1 | Video Ideas **填入 composer** | 芯片 `data-testid=video-idea-*` 写 prompt + 比例 | L7 | VideoPage vitest + 源码门闩 |
| V2 | 不因灵感离开创作页 | **禁止**「视频灵感 → 只跳 /agent」 | L7 | 源码断言 |
| V3 | Agent 是细化，不是灵感本身 | 「在 Agent 细化」带 `brief=` | L7 | vitest |
| V4 | Omni / 口型 / 多镜 | VideoComposer 已有；出片走 L2–L3 | L4 | 既有 P0 测 |
| V5 | Seedance 2.5 主推 | **不宣称**；货架仍 2.0 | L6 | capabilities / models |

### 2.4 Agent / Director

| ID | Yapper | Betty 期望 | 层 |
|----|--------|------------|----|
| A1 | Help Ideate | concepts 返回 | L1 |
| A2 | 分镜真跑 | `/director/storyboard` | L2 |
| A3 | 不是灵感垃圾桶 | 视频页灵感不再只甩到 Agent | L7 |

### 2.5 Explore / Library

| ID | Yapper | Betty 期望 | 层 |
|----|--------|------------|----|
| E1 | 搜索 + Remix | 已有（P1） | L4 |
| E2 | 百万级社区 | **空库=0**；有种子才有 list | L6 |
| E3 | Folders | 标签目录，不是网盘 | L4 |

### 2.6 Pricing（本轮重点）

| ID | Yapper | Betty 期望 | 层 | 自动化 |
|----|--------|------------|----|--------|
| P1 | 四档 + Max 滑块 15k–150k | API `max_tiers` + FE 滑块 | L1/L6 | 既有 P2 |
| P2 | Limits 表：Credits / 并发 4/6/10/40 / 席位 —/—/2/7 | `GET /pricing/plans` 带 `concurrent_generations` + `included_team_seats`；FE 对照表 | L1/L6/L7 | test_p4 + Pricing vitest |
| P3 | 可 Stripe 收款 | 无 Key 必须诚实条 | L5 | stripe-honesty |
| P4 | 并发数字与后端一致 | 同源 `PLAN_CONCURRENCY` | L1 | test_p4 |

### 2.7 Extract / URL-to-Viral

| ID | Yapper | Betty 期望 | 层 |
|----|--------|------------|----|
| X1 | 链进口袋分镜 | oEmbed + `viral.beats`（P3） | L4 |
| X2 | 不是原片搬运 | 诚实文案 | L6 |

### 2.8 货架 / 分发（承认落后）

| ID | Yapper 2026-08-16 | Betty | 判定 |
|----|-------------------|-------|------|
| S1 | Explore 18+ / 29+；定价卡 19+ / 30+ | active=9 | ❌ 货架叙事 |
| S2 | Seedance 2.5 Omni-Video | Seedance 2.0 | ❌ 代际 |
| S3 | MCP + REST「54+ models」 | `/mcp` + JSON-RPC 连接器 + public REST；**active 货架 / API Key，非 OAuth / 非 54+** | ◐ 分发面已补协议，货架叙事仍落后 |

这些项 **本方案只记录，不靠文案补齐**。

---

## 3. 性能探针（L8）

| 探针 | 方法 | 预算（进程内） | 禁止写法 |
|------|------|----------------|----------|
| `POST /generate/quote` | 3 次取 min | < 800ms | 「生产报价 SLA」 |
| `GET /system/capabilities` | 1 次 | < 800ms | 「线上 P99」 |
| `GET /pricing/plans` | 1 次 | < 400ms | — |
| 视频页灵感点击 | vitest 同步填词 | 立即反映在 textarea | — |

Celery/Redis 缺失导致 `enqueue:generate_image` 失败 = **环境问题**，记入报告，不改产品分公式。

---

## 4. 界面专业性 / UX 评分尺（给复评用）

每项 0–2：0 缺失或误导；1 有但浅/跳走；2 对等且诚实。

| 维 | 2 分标准 | 本轮目标 |
|----|----------|----------|
| 定价对照 | 积分/并发/席位一表可读，数字同源 | 2（本轮补） |
| 创作灵感 | 芯片填词，不踢出页面 | 2（本轮补） |
| 诚实条 | Stripe / 货架 / Voice / Viral 不撒谎 | 2（已有，保持） |
| 货架墙 | 只列 active | 1（9 vs 29+，承认） |
| 社区密度 | 有搜索/Remix；不写 millions | 1 |
| 收款 | Key 在才能标 ready | 0（无 Key） |

---

## 5. 缺陷分级

| 级 | 定义 | 本方案处置 |
|----|------|------------|
| P0 | 主路径断、假出片、扣费不退、虚标收款 | 立即修；本轮未新开 |
| P1 | 核心 UX 跳走 / 限额不可比 | **本轮修**：Video Ideas、Limits 表 |
| P2 | 货架代际、MCP、百万社区 | 记录，不虚补 |
| P3 | 文案打磨 | 顺手 |

---

## 6. 本轮落地（2026-08-16）

| 项 | 行为 | 诚实约束 |
|----|------|----------|
| `GET /pricing/plans` | 每档返回 `concurrent_generations` + `included_team_seats`；顶层 `limits_honesty` | 席位是合同；无 Stripe 不能收款 |
| `/pricing` | Limits 对照表 + 卡片一行限额 | 数字与 `PLAN_CONCURRENCY` 同源 |
| `/create/video` | Video Ideas 填 prompt + 画幅；Agent 改为可选细化 | 不宣称 Act-One / 2.5 |

---

## 7. 本轮实测（2026-08-16，本 VM）

| 套件 | 结果 | 备注 |
|------|------|------|
| `pytest tests/test_p4_core_yapper_ux.py` | **4/4** | 限额契约 + quote 预算 + 视频页源码门闩 |
| Pricing vitest | **2/2** | 诚实条 + Limits 表 4/6/10/40 与 2/7 |
| Video vitest | **2/2** | 芯片填词、不跳 Agent；Agent 细化带 `brief=` |
| `core_yapper_full_verify.py` | **11/11** | `active=9`；quote min **8.64ms** / plans **34ms** / capabilities **4ms**（进程内，**不是 SLA**） |

原始 JSON：`/opt/cursor/artifacts/core_yapper_full_verify.json`

### 仍落后 Yapper（本轮不虚补）

- 货架叙事 18+/29+ vs Betty **active=9**
- Seedance **2.5** vs Betty **2.0**
- MCP/API 产品页：无
- Stripe/OIDC Key：无，不能收款
- Explore millions：无；空库=0

## 8. 验收清单

- [x] `pytest tests/test_p4_core_yapper_ux.py` 全绿
- [x] Pricing vitest 全绿
- [x] Video vitest 全绿
- [x] `core_yapper_full_verify.py` 契约段全绿
- [x] 视频灵感源码：`setPrompt(idea.prompt)`，旧 /agent 跳走已删
- [x] 定价表契约：4/6/10/40 与 0/0/2/7
- [x] 报告写明：active 仍为 9；Stripe 仍无 Key；未测付费出片
