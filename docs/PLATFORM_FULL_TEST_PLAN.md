# Betty 平台完整真实测试方案

**版本：** 2026-07-16  
**原则：** 界面可打开 ≠ 链路通 ≠ 真出片 ≠ 生产可运营。每一层必须独立判定；付费 live 成败如实记账。  
**可执行入口：**

```bash
# A. 契约 + 界面可达 + API 深链路（默认，不烧钱）
cd backend && python3 scripts/platform_full_e2e.py

# B. 含付费 live（图/视；Motion/Omni 读既有证据或另开闸）
PLATFORM_E2E_LIVE=1 MODEL_SMOKE_LIVE=1 MODEL_SMOKE_LIVE_VIDEO=1 \
  python3 scripts/platform_full_e2e.py --live

# C. 单元/回归
python3 -m pytest tests/ -q

# D. 前端 E2E（Playwright）
cd frontend && npx playwright test e2e/betty.spec.ts e2e/capability.spec.ts
```

报告落盘：`backend/fixtures/audit/platform_full_e2e_latest.json`

---

## 1. 测试分层（必须分清）

| 层 | 含义 | 通过标准 | 失败含义 |
|----|------|----------|----------|
| L0 可达 | FE 路由 HTTP 200 / API OpenAPI 注册 | 页面能打开、接口存在 | 死链/空壳 |
| L1 契约 | 鉴权、入参校验、能力探针、目录 | 正确状态码与字段 | 协议漂移 |
| L2 入队 | 创建 Task、扣积分、Celery 派发 | `task_id` + queued/completed | 计费/调度断 |
| L3 出片 | 上游返回可访问 media URL | `outframe_ok` / live URL | 假成功/mapping 冒充 |
| L4 产品 | 对标 Yapper 体验深度 | 见矩阵审计 | 功能浅/缺口 |
| L5 生产 | Stripe/OIDC/CDN readiness | 生产 env 下 ok | 不能上线收款 |

**禁止：** 把 L0/L1 成功写成「平台已完全可用」；把 mapping smoke 写成 live 出片。

---

## 2. 界面操作矩阵（手动 + 自动化）

### 2.1 导航与 Tools Hub

| 步骤 | 操作 | 期望 | 自动化 |
|------|------|------|--------|
| N1 | 打开 `/` | 首屏品牌+主 CTA，无控制台致命错 | FE 200 + Playwright |
| N2 | 打开 `/tools` | 所有卡片可点，无「即将推出」死链 | `fe:tools_href_scan` |
| N3 | 逐一点：Agent/图/视/唇形/Avatar/Motion/时间轴/放大/抠图/扩图/编辑/音频/Extract/产品/头像/Packs | 进入对应 `/create/*` 或 `/agent` | FE 路由表 |
| N4 | `/create` 裸路径 | 重定向到 `/tools`（非 404） | FE 200 |
| N5 | Explore / Library / Gallery / Pricing / Sessions / Settings / Developer / Models / Billing / Tasks / Projects / Status | 页面可渲染 | FE 200 |

### 2.2 注册登录

| 步骤 | 操作 | 期望 | 自动化 |
|------|------|------|--------|
| A1 | `/auth/register` 注册 | 拿到 token / 进入可用态 | API register |
| A2 | `/auth/login` 登录 | 同账号可用 | API login |
| A3 | Settings 未登录 CTA | 指向 `/auth/login`（禁止 `/login` 死链） | `fe:settings_login_href` |
| A4 | OIDC 按钮 | 未配置时诚实提示，不白屏 | `oidc/status` |

### 2.3 图片创作 `/create/image`

| 步骤 | 操作 | 期望 | 层 |
|------|------|------|----|
| I1 | 输入提示词 → 生成 | Task 创建并可轮询 | L2 |
| I2 | 上传参考图（1–4） | `reference_images` 真传到后端 | L2 |
| I3 | Explore Remix 带 `image_url` | 预填参考图 | L1–L2 |
| I4 | 付费 live（gpt-image-2 / nano-banana） | 返回图片 URL | L3 |

### 2.4 视频创作 `/create/video`（含 Omni）

| 步骤 | 操作 | 期望 | 层 |
|------|------|------|----|
| V1 | 纯文生视频 | Task→视频 URL | L2–L3 |
| V2 | 加参考图 | i2v / Omni | L3 |
| V3 | 多图+参考视频/音频 | Seedance Omni `reference_*_urls` | L3 |
| V4 | 多镜头开关 | 走 `/director/storyboard` 真分镜 | L2 |
| V5 | 周检 ≥2 SKU | seedance-fast + seedance / Kling | L3 |

### 2.5 Lipsync / Avatar

| 步骤 | 操作 | 期望 | 层 |
|------|------|------|----|
| L1 | `/create/lipsync` 选音色+图+文/音频 | Task 入队 | L2 |
| L2 | `/create/avatar` 图+音频优先 | 同 lipsync 后端 | L2 |
| L3 | `LIPSYNC_FIXTURE_LIVE=1` | 可选付费出片 | L3 |

### 2.6 Motion

| 步骤 | 操作 | 期望 | 层 |
|------|------|------|----|
| M1 | 加载样片库 still+ref | 可下载 | L0–L1 |
| M2 | 提交 image+video | native `kling-3.0/motion-control` | L2–L3 |
| M3 | 可选 `voice_text` | 附带 TTS 音频（非变声） | L2 |
| M4 | 诚实文案 | 非 Act-One | L4 |

### 2.7 Agent / Director

| 步骤 | 操作 | 期望 | 层 |
|------|------|------|----|
| D1 | Help Ideate | 返回 concepts | L1 |
| D2 | Plan（普通） | 多步含 video | L1 |
| D3 | Plan minimal / 快速成片（中英 brief） | enhance→图→视，无 compose/字幕 | L1 |
| D4 | Storyboard 多镜 | 每镜独立 video step | L2 |
| D5 | Run（dry/真） | 进度可查 | L2–L3 |

### 2.8 Timeline / 图像工具 / Extract / Audio

| 步骤 | 操作 | 期望 |
|------|------|------|
| T1 | 解析 SRT | cue_count≥1 |
| T2 | compose（本地片段） | 合成视频或明确错误 |
| E1 | upscale/bg/extend/edit | 入队+扣费 |
| X1 | Extract 上传文件 | prompt 非空；标明 vision/heuristic |
| X2 | Extract TikTok 页 URL | **400 诚实拒绝** |
| X3 | Extract 直链 | 允许尝试 |
| S1 | TTS `/generate/speech` | 入队或校验错误（勿无门控乱烧钱） |

### 2.9 Explore / 分享 / 计费

| 步骤 | 操作 | 期望 |
|------|------|------|
| G1 | Explore 列表有内容 | items>0（seed 后） |
| G2 | Remix | 跳转 create 带 prompt/image_url |
| G3 | Publish 门闩 | 未 publish 不公开 |
| P1 | Pricing 四档含 Max | API `max`，FE 可点 |
| P2 | Checkout（无 Stripe） | dev 授信或 503 诚实 |
| B1 | 失败退款 | 幂等退还 |

### 2.10 专用工作流页

| 路径 | 期望 |
|------|------|
| `/create/product` | 跳转/预填图片工作流（电商提示词） |
| `/create/headshots` | 跳转职业头像提示词包 |
| `/create/photo-packs` | Packs 入口可点到真实 create |

---

## 3. API / 自动化矩阵（CI 必跑）

| 套件 | 命令 | 门禁 |
|------|------|------|
| 全量单测 | `pytest tests/ -q` | 必过 |
| Yapper 核心契约 | `scripts/yapper_core_parity_harness.py` | 必过 |
| 完整矩阵审计 | `scripts/yapper_full_matrix_audit.py` | 硬契约 100% |
| **平台全量 E2E** | `scripts/platform_full_e2e.py` | 本方案主入口 |
| 图片 live | `MODEL_SMOKE_LIVE=1 smoke_live_image_sample.py` | 周检 |
| 视频 live ≥2 | `MODEL_SMOKE_LIVE_VIDEO=1 smoke_live_video_sample.py` | 周检 |
| Motion live | `MOTION_FIXTURE_LIVE=1 fixture_derivative_harness.py` | 周检 |
| Omni live | 见 `fixtures/audit/omni_live_latest.json` | 发版前抽检 |
| Playwright UI | `npx playwright test e2e/betty.spec.ts` | 发版前 |

---

## 4. 付费 Live 预算与门控

| 探针 | 环境变量 | 建议频率 | 成本感 |
|------|----------|----------|--------|
| 图片 2 SKU | `MODEL_SMOKE_LIVE` | 每日/PR | 低 |
| 视频 2 SKU | `MODEL_SMOKE_LIVE_VIDEO` | 每周 | 中高 |
| Motion native | `MOTION_FIXTURE_LIVE` | 每周 | 高 |
| Omni | 脚本内 `--live` | 发版前 | 中 |
| Lipsync | `LIPSYNC_FIXTURE_LIVE` | 每周 | 高 |

未开闸时：**不得**宣称对应能力「已生产验证」。

---

## 5. 缺陷分级与迭代节奏

| 级 | 定义 | SLA |
|----|------|-----|
| P0 | 主路径断链、假出片、扣费不退、生产 readiness 撒谎 | 立即修 |
| P1 | 核心工具体验缺口（Omni/Lipsync/Explore/计费） | 本迭代 |
| P2 | 对标增强（Packs/FaceSwap/URL-to-Viral） | 排期 |
| P3 | 文案/命名/打磨 | 顺手 |

每轮迭代输出：测试报告 JSON + 缺陷列表 + 修复 commit + 复测勾选。

---

## 6. 本环境基线（2026-07-16 实测）

| 套件 | 结果 | 备注 |
|------|------|------|
| `pytest tests/ -q` | **203 passed** | 含 director 英文 ad 回归 |
| `platform_full_e2e.py`（含 FE） | **hard 69/69 = 100%** | L5 Stripe/OIDC 记为 known gap |
| `--live` 图+视 | **image outframe≥1；video≥2 SKU** | 真实 KIE 出片 |
| Motion / Omni 证据 | **ok** | `kling-3.0/motion-control`；Seedance Omni |
| Playwright `betty`+`capability` | **13/13 passed** | 清 `.next` 并重启 FE 后 |
| active 货架 | **9** | 未伪造 lab SKU |
| gallery seed | **32 items**（列表接口当时快照） | Explore 有内容 |

### 本轮真实发现并已修复

| ID | 问题 | 修复 |
|----|------|------|
| BUG-1 | Director `minimal` + 英文 brief「15s ad」只出图、不出视频 | 扩展 video 关键词 + word-boundary；`minimal` 默认视频最短路径 |
| BUG-2 | Settings 未登录 CTA 指向 `/login`（404） | 改为 `/auth/login` |
| BUG-3 | `/create` 裸路径 404 | 新增 `create/page.tsx` → `/tools` |
| BUG-4 | FE `.next` 损坏 → `_next/static/chunks/*.js` 404 → 页面积 `opacity:0`，能力提示永不出现 | 清缓存重启 `next dev`；`CapabilityNotice` 同域请求+超时+加载态始终挂 `data-testid` |
| BUG-5 | Motion 页重复 CapabilityNotice + 过时 best-effort 文案 | 合并为一处；文案改为原生 Kling Motion Control |

### 诚实缺口（未伪装）

- Stripe / OIDC 未注入 → **非生产收款就绪**
- Face Swap：`available=false`（无已验证 SKU）
- 社媒页面 URL Extract：诚实 400
- Motion ≠ Act-One（仅 Kling Motion Control）
- Lipsync 本轮未重新烧钱 live（有 fixture 门控）
- 浏览器直连 `localhost:8000` 个别 billing 接口偶发 CORS（布局积分徽标）；能力探针已改同域 `/api/v1`

---

## 7. 验收清单（发版前门禁）

- [x] `pytest` 全绿（本轮 203）
- [x] `platform_full_e2e.py` 契约段全绿
- [x] FE 核心路由 100% HTTP 200（含 `/create`、Tools href 扫描）
- [x] Playwright 核心 UI 冒烟 13/13
- [x] 图片 live ≥1 SKU outframe（本轮）
- [x] 视频 live ≥2 SKU outframe（本轮）
- [x] Motion native 证据或明确降级说明
- [ ] readiness：生产必须无 Stripe/CDN/SSO blocker（本环境开发黄灯）
- [x] 能力探针无夸大（face_swap / social URL / Act-One）

---

## 8. 持续迭代工作流

1. **改功能 → 写/改契约测 → 跑 e2e →（周检）开 live 闸**  
2. 失败项按 P0–P3 入缺陷表，修完必须复测勾选  
3. 更新本文件「§6 基线」与 `platform_full_e2e_latest.json`  
4. 对标深度另见 `docs/YAPPER_FULL_MATRIX_AUDIT.md` / `docs/P0_P1_P2_YAPPER_ITERATION.md`
