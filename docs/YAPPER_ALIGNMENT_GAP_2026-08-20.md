# Betty × Yapper 对齐差距评估（2026-08-20 下午）

**抓取：** [yapper.so](https://www.yapper.so/) 首页 · [定价](https://www.yapper.so/pricing) · [Agent](https://www.yapper.so/agent) · [Create Video](https://www.yapper.so/create/video) · Explore（SPA，公开 HTML 几乎无资产墙）  
**Betty 栈顶：** `cursor/p1-p2-professional-dev-d257` · 本环境 `GET /api/v1/system/commercial-open`  
**原则：** 学结构与气质，不抄货架话术、不假收款、不把 lab 算可售。页面有 ≠ 契约通 ≠ 真出片 ≠ 可对公众收费。

---

## 0. 一句话

相对 Yapper **今日公开面**，Betty 的工作室工具底盘和导演台结构已经能同台对照；  
**产品完成度仍被三件事钉死：货架广度、真实收款、社区密度。**  
Yapper 当天又把视频主推从品牌墙里的 2.0 抬到 **Seedance 2.5 Omni-Video**，定价对照表点名 Veo / Sora / Kling 3.0。Betty 不能、也不该用文案追这条线。

| 口径 | 值 |
|------|----|
| 工具面（路由真实可点） | **高** — 17+ create + Agent / Explore / Pricing / MCP |
| 工作室气质（Create / Agent） | **高** — studio 暗壳、空画布、导演竖轨 |
| 工程诚实 | **高于 Yapper 营销口径** |
| 对 Yapper 产品完成度（加权，见 §6） | **≈69 / 100** |
| **对公众收费开放** | **否** — `verdict=studio_ready_not_commercially_open` |

复现：

```bash
curl -s localhost:8000/api/v1/system/commercial-open | python3 -m json.tool
# open_to_public=false  verified_model_count=9
# vs_yapper.yapper_video_hero=seedance_2.5  betty_video_hero=seedance_2.0
```

---

## 1. Yapper 今日公开面（相对上午评估的增量）

上午文档已记 Explore **19+ 图 / 29+ 视**、品牌墙含 Veo 3.1 / Sora 2。下午再抓，目标线继续抬：

| 面 | 当日事实 | 相对 Betty |
|----|----------|------------|
| 首页心智 | Don't prompt, Just Direct；**Millions of assets** | Agent 有 Just Direct；**禁止 millions** |
| 视频主推卡 | **Seedance 2.5** Omni-Video（多模态 / 唇形 / 多镜头） | 工具卡写 **Seedance 2.0**；无 2.5 SKU |
| 品牌墙循环 | Veo 3.1 · Sora 2 · Kling · Grok · WAN · Hailuo · Seedance **2.0** · Nano Banana 2 · GPT Image 2 | 已验证 marquee **不并列** Veo/Sora |
| 定价卡 | Starter $9.99 可点 Get；卡面仍写 All **20+** 图 / **30+** 视 + Seedance **2.0** Omni（与首页 2.5 不完全一致） | 四档+Max 滑块**面有**；按钮 **disabled** |
| 定价对照表 | 点名 WAN 3.0 / FLUX.3 / MiniMax H3 / **Seedance 2.5 New** / Kling 3.0 / Veo3.1 / Sora 2 / LipDub v2 / OmniHuman 等积分单价 | Betty **不得**把该表抄进可售货架 |
| Agent 首屏 | 与首页同一套 Composer：Prompt mode · Sonnet 5 · Help Prompt · Create Content · Help Ideate · Generate Audio | **Dashboard 已有四 CTA**；营销首页仍是 Tab+发送；导演台是另一套 Composer |
| Agent Try Feature | Video：Ad / Anime / Microdrama / UGC / Product Commercial；**Utility：Prompt Helper**；**Agent：Earn with agent**；Image：Product Photoshoot | 视频/图片场景已分区；**无 Prompt Helper 卡、无 Earn 市场** |
| Create Video | 默认模型芯片 **Seedance 2.5**；16:9 · 720p · Std · 8s；Ref Images / Video / Audio；Prompt · Edit · Remix；Video Apps 含 Extractor | Composer 有参考图/视/音与参数条；默认必须停在已验证模型，**不能默认 2.5** |
| Explore | 登录墙/SPA，公开 HTML 几乎无瀑布流 | `gallery/stats` 本环境 **total=19**（seed 13 / community 6 / videos 0） |
| `/tools` | 公开 404（工具在首页分区 + Show More） | Betty `/tools` 是真实枢纽 |

Yapper 自己也有口径裂缝（首页 2.5 vs 定价卡仍写 2.0 Omni、Explore 19+ vs 卡面 20+/30+）。Betty 的正确反应是 **记下裂缝，不复制裂缝**。

---

## 2. 能力对齐（契约 vs 产品深）

图例：契约 = 有真实路由/API；产品深 = 相对 Yapper **今日**体验。

| # | Yapper | Betty | 契约 | 产品深 | 能否用代码追平 |
|---|--------|-------|------|--------|----------------|
| 1 | 统一 Composer（首页=Agent=Dashboard） | `/` 营销 Tab；`/dashboard` 四 CTA；`/agent` 导演 Composer | 分面都有 | 中 | **可**把首页做成 Dashboard 同构，但不该再堆徽章 |
| 2 | Agent 竖向工作流 | `DirectorTimeline` 01–08 竖轨 | ✅ | 中高 | 执行中点亮当前步、成片嵌右侧 |
| 3 | Try Feature Prompt Helper | 导演台已有润色按钮，**无独立场景卡** | 半 | 中 | **可**（`/generate/enhance` 已存在） |
| 4 | Earn with agent（付费 brief 市场） | 无 | 缺 | 缺 | **不可装**；没有品牌任务供给 |
| 5 | Seedance 2.5 Omni | Seedance **2.0** Omni 参考链 | 2.0 ✅ | 结构性落后 | **仅**周检 live 后升架 |
| 6 | Studio Lip-Sync / Avatar / Motion | 独立 SKU 页 | ✅ | 中 | ≠ 专有引擎 / ≠ Act-One |
| 7 | Timeline Editor「强大」 | `/create/timeline` ffmpeg 合成 | ✅ | 中偏弱 | 深剪是产品工期，不是换皮 |
| 8 | Video Apps + Extractor | VideoAppsRow + `/create/extract` | ✅ | 中 | IG/X 必须继续诚实禁用 |
| 9 | 19+/29+ 可售叙事 | **active=9** | 诚实 | 货架差一个数量级 | **禁止虚标** |
| 10 | Stripe 真订阅 + 积分包 | 面有、Key 无 | 面 | **缺** | 运营注入，不是前端假 countdown |
| 11 | MCP 账号 OAuth · 宣称 55+ | API Key · 货架=active | 中 | 中偏弱 | 鉴权模型不同，不能写成 Yapper 登录 |
| 12 | Millions 资产墙 + 社交证明 | Explore seed-heavy | ✅ 筛选有 | **弱** | 要真实社区，不要文案 |

**本环境商业门（P0，代码改不掉）：** Stripe / demo_mode / Redis / Celery workers。P1：OIDC、货架。

---

## 3. 体验对齐（已追上 vs 仍像两套产品）

### 已接近（不要再在这些面上堆营销）

- Create Video / Image：单框 Composer + 底部 chips + StudioStage 空画布  
- `/tools`：Video / Image / Utility 分区，入口指向独立 SKU  
- `/agent`：Just Direct、视频/图片场景分区、规划后竖轨时间线  
- 首页工具路由：放大/抠图/头像/产品不再误进 `/create/image`  
- 商业诚实条：首页 + Status 写明未对公众收费开放  

### 仍明显不像 Yapper（且多数不该抄）

1. **公开首屏不是同一块 Composer。** Yapper `/` 就是「What will you create?」+ 四动作。Betty `/` 仍是营销站 + 「生成视频」主按钮；四动作只在 `/dashboard`。  
2. **Agent 缺 Utility / Earn 两行。** Prompt Helper 可补；Earn 是市场，补了就是假功能。  
3. **Create Video 默认芯片写 2.5。** Betty 默认必须是已验证模型。  
4. **Explore 密度差数量级**（19 vs millions）。来源筛选已诚实，墙本身没有。  
5. **转化层。** Yapper 有可关闭的付费弹层 + countdown。无 Stripe 时做同款是欺诈，不做。  
6. **死代码口径。** `frontend/src/components/Navigation.tsx` 的 Tools 下拉仍指向 `/create/image?tool=*`，当前 AppShell **未挂载**该组件；真正侧栏 `AppSidebar` 已走独立 SKU。不要让死文件回流。

---

## 4. 专业性（对公众开放的标准，不是「像不像」）

已具备：条款 / 隐私 / 内容政策 / Cookie / Status / 分层诚实 API。  
开放前仍缺（非本环境能代码虚构）：Stripe Price+Webhook、Redis+Worker、非 demo Key、live 升架、MCP OAuth（若要卖「登录即连」）。

分层答案不变：

| 问题 | 答案 |
|------|------|
| 内部/设计伙伴演示工作室？ | **能** |
| 对标 Yapper 产品完成度 100%？ | **不能** |
| 对公众开放注册并收费？ | **不能** |

---

## 5. 禁止改口（复述）

1. active **9**，不是 18+ / 19+ / 29+ / 55+  
2. Seedance **2.0**，不是 2.5；无 Veo / Sora 可售  
3. MCP = **API Key**，不是 Yapper 账号 OAuth  
4. Motion / Performance ≠ Act-One；Face Swap ≠ InsightFace  
5. `readiness.ok(dev)` ≠ 可收款 ≠ `open_to_public`  
6. Explore ≠ Millions of assets  

---

## 6. 九维（Yapper 今日公开面 = 100）

权重与上午商业评估相同。货架因目标线抬高（2.5 主推 + 对照表点名）从 40 降到 **38**；Agent / 体验因导演竖轨、影院壳各 +2 / +3。加权算术 = **69.0**。上午文中「≈74」是粗入；本表按同一权重量化，**不把分数抬高装进步**。

| 维度 | 权 | Betty | 说明 |
|------|----|-------|------|
| 模型货架 | 20 | **38** | 9 vs 19+/29+；主推还落后一代 |
| 核心生成 | 18 | **90** | Omni / Lipsync / Motion 有折叠 live |
| Agent | 12 | **90** | 竖轨已落地；缺 Prompt Helper 卡与 Earn |
| 投放完成度 | 15 | **88** | 时间线有；深剪弱 |
| 增长飞轮 | 12 | **66** | Remix/Extract 有；密度差数量级 |
| 商业化 | 13 | **36** | 不能收款 |
| 体验/前端 | 5 | **93** | 工作室路径高；营销首页仍分叉 |
| 专业合规 | 3 | **85** | 法律页 + 商业裁决 |
| 分发 MCP | 2 | **70** | Key 模式；≠ OAuth 55+ |

审计脚本 `overall_vs_yapper` 是另一套（工具合同高），**禁止与本表混谈**。

---

## 7. 下一刀（只排能诚实落地的）

**代码可做、且不虚标：**

1. ~~首页 Hero 与 `/dashboard` 四 CTA 同构~~ **已落地**（Help Prompt 就地润色 / Create Content / Help Ideate / Generate Audio）  
2. ~~Agent Try Feature 增加提示词助手~~ **已落地**（`/generate/enhance`，cat=工具；**没有** Earn with agent）  
3. ~~导演执行中点亮当前步；成片预览进时间线右侧~~ **已落地**（`agent-timeline-current` + `agent-monitor`）  

**代码做了也追不上、不要假装：**

4. Stripe / Redis / Worker / 非 demo Key  
5. Seedance 2.5 / Veo / Sora 升架  
6. Millions Explore、假 countdown 弹层  

下一刀不要再给首页加徽章或品牌墙。
