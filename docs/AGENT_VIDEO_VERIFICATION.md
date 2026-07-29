# Agent + Video 平台验证报告与修复计划（对标 Yapper）

**日期：** 2026-07-29
**分支：** `cursor/betty-yapper-parity-d257`
**前提：** 已配置有效 `KIE_API_KEY`（真实出片模式，`demo_mode=false`）。
**验证集：** `backend/scripts/agent_video_verify.py`
**机器报告：** `backend/fixtures/audit/agent_video_verify_latest.json`

---

## 0. 裁决

对 agent 与 video 两页做了**功能 / 准确 / 健壮 / 稳定 / 性能**五维验证，并跑通**真实出片**（图/视频/多镜头分镜/导演成片）。
快速套件 **27/27 PASS**；全量含真实出片 **29/29 PASS**（修复空 brief 校验、对齐 minimal 语义、修正测试超时后）。
发现并修复 1 个真实健壮性缺陷（空 brief 返回 200），1 个文档/标签不一致（minimal 语义），其余"失败"均为测试侧（额度/超时）非平台缺陷。

---

## 1. 验证集设计（五维）

| 维度 | 覆盖 |
|------|------|
| 功能 Functionality | `/system/capabilities`、`/director/mode`、brain modes、export-specs、brief-templates、bgm-catalog、active 视频模型 |
| 准确 Accuracy | 8 个场景 dry-run 计划（product_ad/commercial/ugc/micro_drama/anime/product_photo/ai_portrait/talking_avatar）步骤/意图/积分；minimal vs full；identity_lock；export_placement；ideate；variants 扇出 |
| 健壮 Robustness | 内容审核门禁、空 brief 校验、count 越界校验、跨用户任务隔离(403)、取消+退款 |
| 稳定 Stability | 3× 图像并发全部完成 |
| 性能 Performance | plan / image / video / agent-run / storyboard 时延 |
| 真实出片 Real | 视频 t2v、agent minimal 真实成片、2 镜真分镜 |

---

## 2. 结果（真实运行）

### 功能 + 准确（fast，无成本）
```
A1..A7 capabilities/mode/brain/export(6)/brief(9)/bgm(8)/video_models(5)  PASS
B_plan_* × 8 场景  PASS  （steps 5–9，intent 与积分正确）
B_minimal_shorter / B_identity_lock_edit / B_export_placement  PASS
B_ideate(5 concepts) / B_variants_fanout(2)  PASS
```

### 健壮性
```
C_moderation_gate     PASS (400)
C_empty_brief         PASS (422)   ← 修复后（此前 200）
C_count_validation    PASS (422)
C_authz_task_isolation PASS (跨用户 403)
C_cancel              PASS (revoked + 退款)
```

### 稳定性 + 真实出片
```
D_concurrency_3x_image   PASS  3/3 完成 · 51.8s
E1_video_t2v             PASS  seedance-2.0-fast 5s → 真实 mp4 · ~166s
E2_agent_minimal_run     PASS  真实成片 5 资产（hero 图 + 2 视频 + 身份对比条 + 字幕/CTA 合成成片 final_*_sub_cta.mp4）· ~472s
E3_storyboard_real       PASS  2 镜真分镜 → 4 资产 · ~358s
```

### 性能快照
| 操作 | 时延 |
|------|------|
| dry-run 计划 | ~17ms |
| 图像真实出片（nano-banana） | ~15–50s |
| 视频 t2v（seedance-fast 5s） | ~80–166s |
| 3× 图像并发 | 51.8s 全完成 |
| agent minimal 真实成片（1 图 + 2 视频 + 合成） | ~472s |
| 2 镜真分镜 | ~358s |

---

## 3. 发现的问题与修复

| # | 问题 | 严重度 | 处理 |
|---|------|--------|------|
| 1 | `/director/plan` 对空/空白 brief 返回 200（应拒绝） | 中（健壮性） | ✅ 已修：`PlanRequest.brief` 加 `min_length=1` + field_validator，空白→422 |
| 2 | `minimal` 文档/UI 标签称"跳过配音/字幕"，实际保留字幕+合成（只跳 TTS 配音） | 低（一致性） | ✅ 已修：对齐后端 docstring/字段描述 + agent UI 标签为"快速成片·跳过配音"/"完整成片·配音+字幕" |
| 3 | E2 首轮"超时"（360s） | 测试侧 | ✅ 已修：2 个真实 seedance 视频合计 >6min，测试 poll 上调至 600s；实测 472s 通过 |
| 4 | 首轮 E1/E2/并发"积分不足" | 测试侧 | 非缺陷：Betty 平台内积分门禁正确生效；测试访客充值后全通过 |

---

## 4. 稳健性/正确性结论（对标 Yapper）

- **功能齐全且准确**：8 大场景计划、ideate、variants、导出规格、brief 模板、身份锁、投放位均可用且返回正确结构。
- **健壮**：内容审核、输入校验、跨用户隔离、取消+退款、积分门禁均按预期工作。
- **稳定**：并发图像 3/3 完成；真实视频/分镜/导演成片均端到端成功。
- **真实出片**：图 / 视频 / 2 镜分镜 / 导演一键成片（含字幕+CTA 合成）全部产出真实 media。

---

## 5. 后续增强建议（非阻塞）

| 优先级 | 项 | 说明 |
|:--:|----|------|
| P1 | 执行期分步缩略图 | agent 执行时步骤完成即内联显示该步产物（图/视频），当前在整体完成后统一展示 |
| P1 | 视频真实进度百分比 | 视频 t2v 目前为时间估算进度条；可接 KIE 轮询 state 映射真实百分比 |
| P2 | minimal 单镜快选 | 对非广告类短 brief 提供"单镜快出"更贴近 Yapper quick-direct |
| P2 | 变体并行出片额度预检 | variants/run 前做额度预检，避免中途 402 |

---

## 6. 复现

```bash
cd /workspace/backend
# 快速（无成本）：契约 + 编排 + 健壮
AV_VERIFY_NO_LIVE=1 PYTHONPATH=. .venv/bin/python scripts/agent_video_verify.py
# 全量含真实出片（需有效 KIE_API_KEY + 访客有平台积分）
AV_GUEST=<funded-guest> AV_VERIFY_STORYBOARD_LIVE=1 PYTHONPATH=. .venv/bin/python scripts/agent_video_verify.py
```

**诚实边界：** 真实出片依赖 `KIE_API_KEY`（本机通过 secret 注入运行中的 API+Worker）；平台内积分为 Betty 计费系统，与 KIE 额度独立；视频/分镜真实渲染耗时较长（单镜 seedance ~1–4 分钟）。
