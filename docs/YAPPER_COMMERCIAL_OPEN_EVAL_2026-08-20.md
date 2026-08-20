# Betty × Yapper 商业开放就绪评估（2026-08-20）

**对标站：** [yapper.so](https://yapper.so) 当日首页 / 定价 / MCP 公开叙事（非内部反编译）  
**Betty 栈顶：** `cursor/p1-p2-professional-dev-d257`  
**原则：** 页面有 ≠ 契约通 ≠ 真出片 ≠ 可对公众收费开放。禁止虚标货架、收款与社区密度。

---

## 0. 一句话裁决

Betty **具备与 Yapper 同台竞争的工作室工具底盘**（创作路由、Composer UX、法律页、MCP/API Key 模式、诚实话术），  
**不具备作为对公众收费的商业平台立即开放。**

| 口径 | 值 | 含义 |
|------|----|------|
| 工具面 / 专业入口 | **高** | 17+ create 工具 + Agent / Explore / Pricing / MCP |
| 页面设计专业度 | **中高** | Composer 对齐 Yapper 单框；首页营销密度仍弱于 yapper.so |
| 工程诚实 / 专业性 | **高于 Yapper 营销口径** | 不虚标 19+/29+/55+、Veo、Sora、Millions |
| **对公众收费开放** | **否** | `open_to_public=false`：无 Stripe、无稳定队列/Worker、demo 模式 |

复现：

```bash
curl -s localhost:8000/api/v1/system/commercial-open
# verdict=studio_ready_not_commercially_open
```

---

## 1. Yapper 今日公开产品（2026-08-20 抓取）

相对 07-16 / 08-16 评估，目标线继续抬高：

| 项 | Yapper 公开 | Betty 事实 |
|----|-------------|------------|
| 心智 | Don't prompt, Just Direct + Millions of assets | Agent 默认 Tab + 已验证 N 模型；**不说 millions** |
| 货架话术 | Explore **19+ 图 / 29+ 视**；定价卡 **20+/30+** | **active=9**，lab 另计 |
| 视频主推 | **Seedance 2.5 Omni-Video** + 2.0 品牌墙 | Seedance **2.0** Omni 参考链；无 2.5 SKU |
| 品牌墙 | Veo 3.1 / Sora 2 / Kling / Grok / WAN / Hailuo / Seedance 2.0 / GPT Image 2 / Nano Banana 2 | 仅已验证：Seedance 2.0 / GPT Image 2 / Kling Avatar / Nano Banana 等；**不并列 Veo/Sora** |
| 商业 | Starter $9.99 → Max 滑块 15k–150k；可真实订阅 | 四档+滑块 **面有**；**Stripe Key 未注入** |
| MCP | 托管 connector + **账号 OAuth**；宣称 **55+ models** | 托管 MCP + REST；鉴权 **API Key 非 OAuth**；货架=active |
| 社交证明 | 千万/亿级 views 创作者证言 | 无对等社区密度；Explore 仍 seed-heavy |

---

## 2. 核心能力（Yapper → Betty）

图例：契约 = 路由/API；产品深 = 相对 Yapper **今日**体验。

| # | Yapper | Betty | 契约 | 产品深 | 商业可用？ |
|---|--------|-------|------|--------|------------|
| 1 | Agent Just Direct | `/agent` | ✅ | 中 | 演示可；成片依赖队列 |
| 2 | Pro Image | `/create/image` Composer | ✅ | 中 | 需 Key + Worker |
| 3 | Video / Omni | `/create/video` | ✅ | 中 | Seedance 2.0 ≠ 2.5 |
| 4 | Studio Lip-Sync | `/create/lipsync` | ✅ | 中 | Kling avatar；≠ 专有引擎 |
| 5 | Motion / Performance | motion + performance | ✅ | 中 | ≠ Act-One |
| 6 | Timeline / Upscale / BG / Extend | 各 create 页 | ✅ | 中 | 工具面齐 |
| 7 | Product / Headshots / Packs | 批量 SKU | ✅ | 中 | N 独立任务 |
| 8 | URL-to-Viral | extract + viral-spec | ✅ | 中偏弱 | IG/X 诚实禁用 |
| 9 | Explore Remix | `/explore` | ✅ | 弱 | 远非 millions |
| 10 | Pricing Max | `/pricing` | ✅ | 中 | **不能收款** |
| 11 | MCP / API | `/mcp` + public REST | ✅ | 中偏弱 | Key 模式；无 OAuth；≠55+ |
| 12 | 订阅收款 | Stripe | 面 | **缺** | P0 阻断开放 |

**结论：** 核心创作能力 **够用做工作室/内测**；货架广度与收款是相对 Yapper 的结构性落差，不是再铺空壳页能补上的。

---

## 3. 页面设计

| 面 | Yapper | Betty | 判断 |
|----|--------|-------|------|
| 首屏 | Agent 输入 + 百万资产叙事 + 模型品牌墙循环 | Agent/图/视 Tab + Composer 风格输入 + 画廊轮播 | Betty 更克制、更诚实；营销冲击弱 |
| Create Video/Image | 单框 + 底部参数 chips | `VideoComposer` / `ImageComposer` 同构 | **专业度接近** |
| Tools hub | 视频/图像分区卡片 | `/tools` 全真链接 | 齐 |
| Pricing | 四档 + Max 滑块 + 社交证明 | 四档 + 滑块 + 诚实条 + **按钮 disabled** | 专业；不能假装可买 |
| MCP | 分步 connector + OAuth | 产品页 + API Key 说明 | 功能有；转化漏斗弱 |
| 页脚 | 完整产品/法律 | 条款/隐私/内容政策 + 本轮补 Status/MCP | 法律底盘有 |

首页本轮去掉「自有 GPU 集群 / 商业授权已对公众可用」过虚句，改为 **已验证 active + 未收款不开放**。

---

## 4. 专业性（商业平台标准）

已具备：

- 服务条款 / 隐私 / 内容政策 / Cookie 同意
- 失败退款、任务鉴权、内容审核门
- `/status` 基础设施探针 + **商业开放裁决**
- capabilities / stripe-status / commercial-open **分层诚实**

仍缺（开放前必做，非本环境能代码虚构）：

1. **Stripe Price + Webhook 注入** → 真收款、发票、订阅生命周期  
2. **OIDC** → 企业登录  
3. **Redis + Celery Worker 常驻** → 公开流量可入队  
4. **KIE/供应商 Key + 周检出片** → 非 demo  
5. **货架 live 升架** → 才能诚实接近 19+/29+（禁止把 lab 算可售）  
6. MCP **账号 OAuth**（Yapper 卖点；Betty 目前 API Key）

---

## 5. 作为商业平台开放？——分层答案

| 问题 | 答案 |
|------|------|
| 能否给内部/设计伙伴演示工作室？ | **能**（工具面 + Composer + 法律页） |
| 能否宣称对标 Yapper 产品完成度 100%？ | **不能**（货架/收款/社区/2.5/55+） |
| 能否对公众开放注册并收费？ | **不能**。`GET /system/commercial-open` → `studio_ready_not_commercially_open` |
| 注入 Stripe + Redis/Worker + 非 demo 后能否卖？ | **可以开小流量商业内测**；仍不要用 19+/Millions 话术 |

---

## 6. 九维（相对 Yapper 今日=100，诚实）

| 维度 | 权 | Betty | 说明 |
|------|----|-------|------|
| 模型货架 | 20 | **40** | 9 vs 19+/29+/2.5 |
| 核心生成 | 18 | **90** | Omni/Lipsync/Motion 有折叠 live |
| Agent | 12 | **88** | 契约齐；一键成片体感弱于营销锚点 |
| 投放完成度 | 15 | **88** | 时间线/包装有；深剪弱 |
| 增长飞轮 | 12 | **66** | Remix/Pack/Extract 有；密度差数量级 |
| 商业化 | 13 | **36** | SKU 面有；**不能收款** |
| 体验/前端 | 5 | **90** | Composer 对齐；首页话术已去虚 |
| 专业合规 | 3 | **85** | 法律页+状态+商业裁决 |
| 分发 MCP | 2 | **70** | Key 模式；≠ OAuth 55+ |

加权约 **≈74 / 100 产品完成度**；审计公式 `overall_vs_yapper` 仍约 **81**（工具合同高、货架/收款拖累）。两套分不可混谈。

---

## 7. 禁止的夸大（复述）

1. Motion/Performance ≠ Act-One  
2. Face Swap ≠ InsightFace  
3. lab 数 ≠ active 可售  
4. readiness.ok(dev) ≠ 可收款 ≠ 可对公众开放  
5. MCP ≠ Yapper 55+ / 账号 OAuth  
6. Explore ≠ Millions of assets  

---

## 8. 下一刀（仅环境/运营能打开商业门）

1. 注入 Stripe Key + Price + Webhook，再把 Pricing 按钮从 disabled 打开  
2. 生产 Redis + Worker，商业开放裁决 P0 清零  
3. 非 demo Key + 周检出片  
4. 仅 live 通过后扩 active；首页继续动态 `active_count`  
5. Explore 真实社区，而不是种子密度话术
