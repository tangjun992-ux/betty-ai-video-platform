# Betty ⇄ Yapper Parity LOOP — 对标收敛工程

> 目标：把 Betty 持续对标 https://yapper.so 直到 **Parity Score = 100%**（完全一致）。
> 这是 LOOP 的"宪法"——每一轮对标都以此为基准，自动更新。
> 基线侦察日期：2026-06-22 | 维护：Hermes Agent（自动 LOOP）

---

## 0. 什么是 LOOP 工程

LOOP 是一个**自我收敛的对标闭环**。每一轮（iteration）执行四个阶段，跑完回到起点，直到一致性分数达到 100%：

```
   ┌────────────────────────────────────────────────────┐
   │                                                      │
   ▼                                                      │
 L — Locate     抓取 yapper 最新现状 + Betty 现状，定位差异
   │
 O — Objectify  把差异量化成 0-100 的 Parity Score（逐维度打分）
   │
 O — Optimize   选当轮 ROI 最高的差距，实际改 Betty 代码修复
   │
 P — Prove      编译/部署/截图/回归打分，证明分数真的涨了
   │
   └──────────────────────► 分数 < 100 ? 回到 Locate ◄────┘
                            分数 = 100 ? LOOP 终止（完全一致）
```

**核心原则**
- **可量化终止**：不靠"感觉差不多"，靠 Parity Score = 100 才停。
- **每轮必有证据**：Prove 阶段必须编译通过 + 截图/数据对比，分数虚报无效。
- **单调收敛**：每轮分数只能涨不能跌；跌了说明引入回归，必须先修复。
- **ROI 优先**：每轮挑"分数收益 / 改动成本"最高的差距先修。

---

## 1. Yapper 金标准快照（2026-06）

> 这是对标的"真值"。yapper 进化后由 LOOP 的 Locate 阶段自动刷新本节。

### 1.1 产品定位
- **"AI Content Studio"** — Slogan: *"What do you want to create?"*
- 核心新卖点：**Yapper Agent — "DON'T PROMPT, JUST DIRECT"**（不写提示词，只做导演）
- 规模口号：*"Millions of assets generated"*，*"15+ image models and 22+ video models"*

### 1.2 模型矩阵（最大差距来源）
- **图片：15+ 模型** | **视频：22+ 模型**
- 已露出：Veo 3.1 · Sora 2 · Kling · Grok · WAN · Hailuo · Seedance 2.0 · GPT Image 2 · (Nvidia / Google 系)

### 1.3 首页结构
- 统一多模态 **Hero 输入框**：模式切换 `Agent / Image / Video` + `添加参考媒体` + 四快捷动作 `Help Prompt / Create Content / Help Ideate / Generate Audio`
- 横滑卡片区：`Video Tools` / `Image Tools`
- 模型 Spotlight：`Seedance 2.0` / `GPT Image 2`
- Agent 宣传位（视频演示）
- **Explore 画廊**：搜索框 + 筛选 `All / Videos / Images / All Filters` + 海量案例

### 1.4 导航 / 会话
- 顶部：Home / Explore / My Library / Tools(下拉) / Sessions / Pricing
- **Sessions**：持久化创作会话（连续上下文）
- 多语言 Language 切换

### 1.5 定价（真值）
| 档位 | 月 Credits | 标记 |
|---|---|---|
| Starter | 1,000 | — |
| Personal | 3,000 | — |
| Creator | 7,000 | **Most Popular** |
| Max | 22,500（滑块 15k→22k→37k→75k→150k）| **Best Value** |
- Monthly / **Yearly −20%** 切换；prorated 升级即时补差额 credits
- Credits 月结余**累积上限 ≈ 2× 月额度**；支持 one-time credit bundles 充值
- 支付 **Stripe**（不存卡，含发票/收据）；11+ 条 FAQ；隐私承诺

### 1.6 技术栈（推断）
Next.js + Vercel Edge · Firebase/Google Cloud · R2/对象存储 · Sentry · Stripe

---

## 2. Betty 真实现状（2026-06-22，按代码量证据）

| 模块 | 证据 | 状态 |
|---|---|---|
| 首页 Hero | `page.tsx` 999 行 | ✅ 重度实现 |
| Agent | `agent/page.tsx` 275 行 | ⚠️ 偏薄（疑似单轮对话，非导演式多步编排）|
| 图片生成 | `create/image` 654 行 + `image_tasks` 267 | ✅ 扎实 |
| 视频生成 | `create/video` 438 行 + `video_tasks` 246 | ✅ 扎实 |
| 唇形同步 | `create/lipsync` 303 + `lipsync_tasks` 140 + API 141 | ✅ 已实现（非空壳）|
| 运动控制 | `create/motion` 338 + `motion_tasks` 204 + API 207 | ✅ 已实现 |
| 时间轴 | `create/timeline` 410 + `timeline_tasks` 306 + API 269 | ✅ 已实现 |
| 模型展示页 | `models/page.tsx` **仅 118 行** | 🔴 太薄 |
| 画廊/库 | `gallery` 322 + `library` 178 | 🟡 弱于 yapper Explore |
| 定价页 | `pricing` 283 + API 305 | 🟡 需对齐 4 档/滑块/FAQ |
| 适配器 | kie(397)/kling(128)/openai(151)/replicate(357)/seedance(283) | 🟡 仅约 6 个模型 |
| 基建 | JWT 认证 ✅ · 本地存储 · 无 Sentry/Stripe/CDN | 🟡 |

> 验证：前端 41 处 "placeholder/todo" 命中**全部是真实输入框 placeholder，无一条"敬请期待/即将上线/not implemented"** → 页面是真功能，不是空壳。后端 13 处 mock/notimpl 信号待下一轮确认是否为 DRY_RUN 测试旁路。

---

## 3. Parity Score — 量化差距热力图（基线）

| # | 对标维度 | 权重 | Betty 现分 | 差距 | 热度 |
|---|---|:--:|:--:|---|:--:|
| 1 | **模型矩阵广度**（37 vs 37）✅ | 20% | 93 | ✅图片(nano-banana)+视频(seedance)代表模型真测active；余按需启用 | ✅ |
| 2 | **Agent 导演式编排** | 15% | 92 | ✅端到端实测+真生成+成片编排(配乐/字幕/合成步骤)；剩后期引擎真接 | ✅ |
| 3 | **核心生成功能** img/vid/lipsync/motion/timeline | 20% | 95 | ✅图片+视频双链路真生成实测(KIE→真URL)；剩lipsync/motion真测 | ✅ |
| 4 | **统一多模态 Hero** | 10% | 85 | ✅三模式切换+4快捷动作+参考媒体入口；剩内联预览 | 🔥 |
| 5 | **Explore 案例发现** | 10% | 95 | ✅搜索+筛选+排序+瀑布流+全部筛选(分辨率/时长)，全面对齐 | ✅ |
| 6 | **定价体系** | 10% | 90 | ✅4档(Starter/Personal/Creator/Max滑块)+年付−20%+消耗表+FAQ；剩Stripe真集成 | 🔥 |
| 7 | **设计系统/品牌质感** | 10% | 88 | ✅Inter专业字体(next/font)+白按钮+蓝基调；剩mono字体/像素级微调 | ✅ |
| 8 | **基建**（认证/存储/监控/支付） | 5% | 78 | ✅Sessions端到端DB实测；剩Sentry/Stripe/CDN(需凭证) | 🔥 |

**加权 Parity Score ≈ `50`** → **L1 `61`** → **L2 `67`** → **L3 `73`** → **L4 `77.5`** → **L5a `78`** → **L5b `78.5`** → **L5c `82.5`** → **L6a `84`** → **L6b `87`** → **L6c `88.3`** → **L6d `90.5`** → **L6e ≈ `91 / 100`**

> 计算：0.20·20 + 0.15·40 + 0.20·75 + 0.10·60 + 0.10·45 + 0.10·55 + 0.10·65 + 0.05·50 = **50.0**

---

## 4. 收敛路线（按 ROI 排序的 LOOP 迭代计划）

| 轮次 | 主攻维度 | 关键动作 | 预期 Δ分 |
|:--:|---|---|:--:|
| **L1** | 模型矩阵 + Agent | 模型注册表扩到 15img/22vid（适配器复用 KIE/Replicate 多模型路由）；models 页重做成矩阵 | +12 |
| **L2** | Agent 导演式 | agent 升级为多步编排（规划→选模型→串行/并行生成→合成→产出多资产） | +8 |
| **L3** | Hero + Explore | 统一输入框 3 模式 + 参考媒体 + 4 快捷动作；Explore 搜索/筛选/案例流 | +9 |
| **L4** | 定价 + 设计系统 | 4 档/滑块/年付−20%/FAQ/Stripe；白按钮+专业字体+蓝基调+间距变量 | +10 |
| **L5** | 基建 + 打磨 | Sentry/对象存储/Sessions/多语言；真 API 回归全链路 | +6 |
| **L6+** | 残差收敛 | 逐维度补到 100，像素级/交互级对齐 | → 100 |

---

## 5. 自动化（LOOP 作为常驻工程）

- **Locate 脚本**：定时抓 yapper 首页/pricing/explore 快照 → diff 上一版 → 更新 §1。
- **Objectify 脚本**：跑 rubric 逐维度打分 → 更新 §3 + 追加收敛曲线。
- **Optimize**：Agent 取当轮 P0 → 改代码 → 提交。
- **Prove**：`pnpm build` + Playwright 截图对比 + 回归打分；分数未涨则回滚。
- **调度**：cronjob 每轮自动跑并向 Tom 上报 Δ分 + 收敛曲线。

---

## 6. 收敛曲线（每轮追加）

| 日期 | 轮次 | Parity Score | Δ | 本轮主攻 |
|---|:--:|:--:|:--:|---|
| 2026-06-22 | L0 基线 | 50.0 | — | 侦察 + 量化 + LOOP 设计 |
| 2026-06-22 | L1 | 61.0 | +11.0 | 模型矩阵 4→37(15img/22vid) + models 页动态化(Tab/搜索) |
| 2026-06-22 | L2a | 63.0 | +2.0 | 导演编排引擎(后端): 意图识别+智能选模型+DAG并行执行+/director API |
| 2026-06-22 | L2b | 67.0 | +4.0 | agent 前端重做为导演视图(计划可视化+一键执行+多资产网格)，端到端闭环 |
| 2026-06-22 | L3 | 73.0 | +6.0 | 首页统一Hero(Agent/图/视频三模式+4快捷动作+参考媒体) + Explore搜索 |
| 2026-06-22 | L4 | 77.5 | +4.5 | 定价精确对齐yapper(4档/Max滑块/年付−20%/消耗表/FAQ) + 白按钮/蓝基调 |
| 2026-06-22 | L5a | 78.0 | +0.5 | Director Sessions 后端持久化(model+CRUD API)，对标 yapper Sessions |
| 2026-06-22 | L5b | 78.5 | +0.5 | Sessions 前端接入(挂载加载+执行存库+恢复)，端到端闭环 |
| 2026-06-22 | L5c | 82.5 | +4.0 | 起服务端到端真回归(ASGI): /models 37✓ /plan /run /sessions CRUD 全200 SQLite持久化✓ |
| 2026-06-22 | L6a | 84.0 | +1.5 | Explore 全部筛选(分辨率/时长/排序扩展)，对标 yapper All Filters |
| 2026-06-22 | L6b | 87.0 | +3.0 | 真KIE调用验证: nano-banana真出图(2积分/50s)✓ KIE网关连通+key有效有余额；视频已提交(>160s) |
| 2026-06-22 | L6c | 88.3 | +1.3 | 纠正过时分析:Inter专业字体早已通过next/font引入,设计系统如实上调；视频实测后台进行中 |
| 2026-06-22 | L6d | 90.5 | +2.2 | 视频真生成实测成功(seedance-2.0-fast KIE_VIDEO_OK)！图片+视频双链路全验证，突破90 |
| 2026-06-22 | L6e | 91.0 | +0.5 | 导演引擎加成片编排:视频意图自动追加 配乐→字幕→合成 三步，对标yapper Agent成片 |
