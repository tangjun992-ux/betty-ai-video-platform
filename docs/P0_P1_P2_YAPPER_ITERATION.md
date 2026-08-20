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
| **Explore 搜索 / Remix 漏斗** | `GET /gallery/?q=`；`gallery_remixes`；popular=`likes*2+remixes` | `tests/test_p1_yapper_explore_library.py` |
| **My Library Today / Multi Select** | `period=today` · tool 筛 · batch-delete/publish · 显式 Multi Select | 同上 + FE vitest |
| **Folders 目录** | `POST/PATCH/DELETE /library/folders` + `batch-folder`；空文件夹可存在 | `tests/test_p15_gap_folders_honesty.py` |
| **Explore 诚实密度** | stats 拆 `seed_items` / `community_items`；禁 millions | 同上 |
| **Create Video Session** | `GenerateRequest.session_uid` + `SessionChip` | `test_p1_yapper_explore_library.py` |
| **Face Swap 模板漏斗** | 8 张玩法卡片 + `/face-swap/templates` + 内容库选图 | FE vitest + templates contract |
| **Stripe 诚实条** | `stripe-status.honesty` + Pricing 横幅 | 同上 |

## P2 已落地

| 项 | 实现 | 验证 |
|----|------|------|
| **Product / Headshots / Photo Packs** | 批量 SKU：`GET /generate/packs` + quote 整批预检 + `POST /generate/pack`；仅已验证模型 | `tests/test_p2_packs_voice_max.py` |
| **Motion + Voice** | Motion 页可选 TTS 旁白；caps `voice_changer.mode=tts_narration`；**非 RVC/实时变声** | 同上 + FE vitest |
| **Max 滑块 / 团队席** | `checkout.credits` 对齐 `max_tiers`；积分包可点；席位诚实条 | 同上 |
| **Tools hub** | Face Swap / Performance / Packs / TTS 诚实文案 | 代码审查 |

---

## P3 已落地

| 项 | 实现 | 验证 |
|----|------|------|
| **URL-to-Viral 结构** | TikTok **官方 oEmbed**（标题+封面）；`viral.beats` 钩子/展开/收束；`GET /generate/viral-spec`；一键成片带 `shot=` | `tests/test_p3_url_viral.py` |
| **诚实边界** | 结构=投放规格+元数据，**不是**原片下载 / 逐帧反推；IG 仍 best-effort | capabilities `url_to_viral` + FE 诚实条 |

## 本轮测试总账

```
yapper_full_matrix_audit (contract)   → 76/76 hard
folded live (motion/lipsync/faceswap/omni) → 4/4
overall_vs_yapper                     → ≈81
betty_internal_readiness              → ≈90
```

## 本轮继续交付（Omni / Explore / 诚实话术）

见 `docs/OMNI_EXPLORE_HONESTY_SHIP.md`：

1. Omni 一体：upload 视/音 + storyboard 共享 refs + generate_audio + 完成后唇形跳转  
2. 货架诚实：首页 active_count、Pricing/Dashboard 去虚标  
3. Explore：seed v2 识别 + 稳定 item_key + remix API  
4. Face Swap：5 风格 prompt pack（薄）

## 仍待（下一刀）

1. Stripe/OIDC **密钥注入**（代码已就绪；本轮只加诚实条，不假装可收款）  
2. 更多 KIE 模型 ID 校正后才能诚实扩 active（仍 9，不虚标）  
3. URL-to-Viral：**oEmbed + 投放规格分镜已落地**；IG 仍需上传/直链；禁止宣称逐帧反推  
4. Explore **真实社区规模**（搜索/remix/诚实密度已有；**分页 load-more 已落地**；禁止 millions 话术）  
5. Lipsync **周检 Beat**（`smoke_live_lipsync_weekly` + Studio 样片 + `/system/slo` 状态）  
6. Folders 仍是**标签目录**，不是嵌套文件系统 / 团队共享盘  
7. 真 Voice Changer / IP-Adapter 身份锁 / Max 滑块真实收款（需 Stripe Key）  

## P1/P2 本轮继续（2026-08-20）

| 项 | 实现 | 验证 |
|----|------|------|
| **Explore 分页** | `has_more` + FE load-more | `test_p1_p2_professional_dev.py` |
| **Remix 深链** | `create_query` + ref/prompt | gallery remix API |
| **URL 分镜 CTA** | extract 每 beat「生成此镜」 | FE `extract-beat-*` |
| **Motion 样片预设** | dance/product/anime-v1 | `/motion/samples` ≥4 |
| **Performance 样片** | `/performance/samples` | FE load demo |
| **Lipsync Studio** | `/lipsync/samples` + 周检 Celery beat | slo.lipsync_fixture |
| **Face Swap 视觉模板** | icon + color on templates | templates API |
| **Motion TTS 音色** | voice select from `/lipsync/voices` | motion page |
| **Pack 批次进度** | `GET /generate/pack/{batch_id}/status` | 404 contract |
| **团队席位账** | included/purchased/members_count | teams API |

## P1/P2 第三轮继续（2026-08-20）

| 项 | 实现 | 验证 |
|----|------|------|
| **Playwright 选择器对齐** | 首页 strict / VideoComposer 参数条 / 图片页 ImageComposer | `e2e/betty.spec.ts` |
| **Vitest CosmicParamPanel** | Info `aria-label` 替代过时 testid | vitest 21/21 |
| **Pack FE 聚合轮询** | `getPackBatchStatus` + BatchPackStudio 单请求轮询 | BatchPackStudio test |
| **任务页 Explore CTA** | 完成态 `publishShare` 按钮 | `task-publish-explore` |
| **Extract IG 诚实禁用** | Instagram/X 仅 URL 时禁用提交 + 提示条 | `extract-ig-honesty` |
| **Pricing 订阅禁用** | `subscription_ready` 绑定 disabled + toast | `pricing-stripe-honesty` |

## P1/P2 第四轮测试修复（2026-08-20）

| 项 | 实现 | 验证 |
|----|------|------|
| **Lipsync 测试漂移** | 断言 `gateway.generate_lipsync` / `kling-ai-avatar` | test_audio_prep_lipsync |
| **Director minimal 契约** | 无 scenario 静图 brief 跳过 compose；scenario 包装保留 | yapper_live + director_scenarios |
| **字幕 cue 时长** | 对齐默认 2.4s/cue | test_director_subtitle |
| **Task authz 签名** | 补 `Request` 参数 | test_tasks_authz |
| **Face/Performance 契约** | TestClient + stub Celery send_task | test_gap_faceswap |
| **Edit tool 测试** | mock gateway 替代 KieAdapter | test_p1_cost_storyboard_stripe |
| **Matrix audit stdout** | lifespan 日志重定向 stderr + JSON 解析 | test_yapper_full_matrix_audit |
| **Audit Redis 诚实** | 无 broker 时 enqueue 500 记 partial | yapper_full_matrix_audit.py |
| **Playwright 扩展** | Extract IG + Pricing disabled E2E | 12/12 betty.spec.ts |

## 商业开放裁决（2026-08-20）

| 项 | 实现 | 验证 |
|----|------|------|
| **commercial-open API** | `GET /system/commercial-open` 诚实 go/no-go | `test_commercial_open_honest_not_public` |
| **Status 商业门** | `/status` 展示 blockers | `status-commercial-open` |
| **首页去虚标** | 去掉 GPU 集群/已可商业授权；未开放诚实条 | `home-commercial-honesty` |
| **页脚专业入口** | Status / MCP / Developer | 首页 footer |
| **评估文档** | `docs/YAPPER_COMMERCIAL_OPEN_EVAL_2026-08-20.md` | 对标 yapper.so 当日 |

## 界面工作室化（2026-08-20）

| 项 | 实现 | 验证 |
|----|------|------|
| **光谱** | 点缀恢复电蓝/紫/品红；brand 阶 600>500 | globals.css / tailwind |
| **Tools 枢纽** | Video/Image/Utility 分区；去掉竞品名 | ToolsPage.test + e2e |
| **首页 SKU 路由** | 放大/抠图/头像/产品不再误进 image | `home-tool--create-*` |
| **已验证 marquee** | 首屏品牌墙节奏，不并列 Veo/Sora | `verified-model-marquee` |
| **演示条** | 细顶栏，不盖住工作室 | `demo-mode-banner` |

## 影院创作台（2026-08-20）

| 项 | 实现 | 验证 |
|----|------|------|
| **默认暗色** | Theme 默认 dark；Create 路径 `html.studio` | ThemeScript + studio-shell |
| **空画布** | StudioStage 代替帮助段落 | `studio-stage` |
| **Explore** | 左对齐编辑头 + 仅社区/示例筛选 | `explore-origin-community` |

勿做：把 lab mapping 标成 active；宣称 Act-One / InsightFace / 实时变声 / 18+ 全开而无周检；首页不写 Kling 3.0 全量上线（仅 motion SKU 映射，且 live 未折）。
