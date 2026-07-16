# Betty 核心能力验真评估（对标 Yapper / Runway / Kling / Luma）

**评估日：** 2026-07-16  
**环境：** Cloud Agent（有 `KIE_API_KEY`；无 Stripe / SMTP / OIDC）  
**原则：** 区分「页面有了」「链路通了」「真出片了」三层。

---

## 1. 总评（诚实分数）

| 维度 | 分数 | 含义 |
|------|------|------|
| 产品表面（创建页/Agent/Explore） | **88** | 与 Yapper 工具矩阵接近 |
| 工程链路（API→Celery→Adapter→落库） | **82** | 主路径齐全，钩子/限流/分享已补 |
| **真出片可信度（本环境实测）** | **58** | 仅 2/4 图片 live 成功；视频 live 未真正跑 |
| 衍生能力质量（唇形/Motion/Timeline） | **55–70** | Timeline 本地强；Motion best-effort；唇形依赖 KIE 排队 |
| 计费/企业生产门禁 | **45** | Stripe 未配；本地存储；SSO 骨架 |
| **综合生产就绪** | **~62** | 可内测/演示；不可宣称「全 SKU 对标 Runway」 |

> 对标定位：Betty = **多模型网关工作室（Yapper 类）**，不是 Runway/Kling/Luma 一等公民模型厂。

---

## 2. 本环境实测证据

### 2.1 映射冒烟（mapping）— 通过
- `probed=9 ok=9 failed=[]`
- 证据路径：全部 `mapping_only`（有 Key，**未计费生成**）
- 结论：9 个 active 的 KIE ID 映射完整

### 2.2 付费 live 冒烟（`MODEL_SMOKE_LIVE=1`）— 部分通过
| 模型 | 结果 | 证据路径 | 说明 |
|------|------|----------|------|
| gpt-image-2 | ✅ | `live_image` | **真出图** |
| nano-banana | ✅ | `live_image` | **真出图** |
| nano-banana-pro | ❌ 隔离 | — | KIE 排队 160s 超时 |
| imagen-4 | ❌ 隔离 | — | KIE Internal Error |
| seedance-2.0 / fast | ⚠️「ok」 | `live_skipped_video` | **未真正出视频**（live 模式跳过视频） |
| kling-2.5 / 2.1-* | ⚠️「ok」 | `live_skipped_video` | 同上 |

**硬结论：**
- 图片 active：**2/4 真出片**（50%）；2 个 upstream 失败已 quarantine  
- 视频 active：**0/5 真出片**（本轮未开 `MODEL_SMOKE_LIVE_VIDEO`）  
- 不可把 `ok=7/9` 解读为「7 个模型生产可用」

### 2.3 自动化测试
- 全量 pytest：**133 passed**
- 生成相关子集：**37 passed**（多为 mock / 映射 / 契约）
- 不能替代 live 出片

### 2.4 能力面探针
- `demo_mode=false`，`providers_configured=true`
- `motion_transfer.mode=best_effort`（诚实披露）
- Stripe `subscription_ready=false`；存储 `local`；SSO 未配置  
  （`ENV≠production` 时 readiness 仍可能 `ok=true`）

---

## 3. 核心生成流程评估

| 流程 | 链路完整度 | 真出片证据 | 对标差距 |
|------|------------|------------|----------|
| 文生图 / 图生图 | 高（generate→image_tasks→KIE） | 2 SKU live 成功 | 对标 Yapper 可用；深度不如 Midjourney 一等公民 |
| 文生视频 / 图生视频 | 高（video_tasks） | **本轮无 live_video** | 相对 Kling/Runway：**未在本环境验真** |
| Auto 路由 | 中 | 仅少量模型在 `MODEL_STYLE_PREFS` | 9 active 未全进自动池 |
| 公开 Developer API | 高 | 契约+webhook 已测 | 缺 live E2E 样例录像 |
| Demo 门控 | 高 | demo=false 时走真 Adapter | Motion 在 demo 下硬失败（正确） |

---

## 4. 衍生生成流程评估

| 流程 | 状态 | 验真 | 对标 |
|------|------|------|------|
| **Lipsync** | 真链路 + KIE avatar/infinitalk | 本轮未付费跑通 | 弱于专用唇形产品；依赖上游排队 |
| **Motion** | `generate_motion(image+video)` | 单测 payload；无 live | **≠** Kling Motion / Runway Act-One |
| **Timeline 合成** | 本地 ffmpeg | 可离线验 | 强于「假合成」；弱于生成式剪辑 |
| **Director/Agent** | plan/run + dry-run | 契约有 | 无 Key 时 dry-run；有 Key 仍依赖子任务 live |
| Upscale / BG / Edit / Extend / TTS | KIE tools + UI | 未 live | 「工具页在」≠「质量验过」 |
| Avatar | 重定向 lipsync | — | 无独立产品 |
| Remix / Share / Library / Projects | 产品面齐 | 分享/收藏/ACL 已测 | 接近 Yapper 工作室侧 |

---

## 5. 目录诚实度

- 目录 **37** = active **9** + beta **28**
- `GATEWAY_GUESS` 约 **20**（Sora / Runway Gen / Luma Ray / Pika…）— **不可对外当可用卖点**
- active 与 `GATEWAY_VERIFIED` 对齐良好（无串标）

---

## 6. 优化迭代方案（必须按序）

### P0 — 把「真出片」变成可运营真相（否则一切对标虚高）

1. **强制分层冒烟报告**  
   - UI/API 区分：`live_image` / `live_video` / `live_skipped_*` / `mapping_only`  
   - 禁止把 `live_skipped_video` 计入「出片成功」KPI  
2. **每周 live_video 抽样**（贵但必要）  
   - 至少 1× Seedance-fast + 1× Kling turbo，存 URL + latency + cost  
3. **隔离恢复策略**  
   - nano-banana-pro / imagen-4：退避重试 + 自动解隔离窗口；路由避开 quarantine  
4. **Auto 路由扩池**  
   - `MODEL_STYLE_PREFS` 覆盖全部 9 active（含 quarantine 权重）  
5. **生产门禁实装检查清单**  
   - Stripe Price + Webhook；`STORAGE_TYPE=s3` + CDN；禁止用本地盘上生产

### P1 — 衍生流程「可证明」

6. **Lipsync / Motion 专项 live harness**  
   - 固定 fixture（人像+短音频 / 人像+参考动作），产出前后对比页  
7. **Motion SKU 升级路径**  
   - 若 KIE 有真 Motion Control ID：映射并冒烟；否则保持 best_effort 文案，**前端禁止「动作控制专业级」话术**  
8. **Director 真跑回归**  
   - 关闭 dry-run 的最短脚本：1 图 + 1 镜视频，断言 media_url  
9. **工具链（upscale/bg/edit）抽检**  
   - 每个工具 1 条 golden case 进 CI（可 mock 上游，staging 每周 live）

### P2 — 体验与企业

10. Library 多级文件夹 / 团队审片评论  
11. OIDC 接真实 IdP；审计导出  
12. 下架或折叠长期 422 的 guess SKU，减少「看起来很全」的错觉  

---

## 7. 建议的下一迭代验收标准（DoD）

| 验收项 | 通过线 |
|--------|--------|
| mapping | 9/9 |
| live_image | ≥3/4 active 图片在 7 天内成功出 URL |
| live_video | ≥2/5 active 视频成功出 URL（显式 live_video） |
| lipsync | 1 条 fixture E2E 成功 |
| motion | 1 条 fixture E2E 或明确失败原因 |
| 状态页 | 展示分层冒烟，不把 skip 算成功 |
| 生产 | Stripe+CDN readiness 在 `ENV=production` 下为 true |

---

## 8. 一句话对标

- **vs Yapper：** 工作室表面已接近；**真模型深度与出片稳定是主差距**。  
- **vs Kling/Runway/Luma：** 借道 KIE，**没有原生模型护城河**；Motion/视频必须以 live 证据说话，不能用目录条目代替。
