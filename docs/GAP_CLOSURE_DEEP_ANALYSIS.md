# 五大差距 · 细粒度分析 / 最优可行方案 / 真实评估

**日期：** 2026-07-18  
**提交基线：** gap-closure 实现轮  
**真实探针产物：** `/opt/cursor/artifacts/gap_closure_eval.zip`  
**探针报告：** `gap_closure_eval/report.json` → **8/8 PASS**

---

## 总览

| # | 差距 | 根因粒度 | 最优可行方案（当前栈） | 能否弥补 | 实测 |
|---|------|----------|------------------------|----------|------|
| 1 | 口型/微表情 | 上游模型天花板 + 构图/音频可优化 | 特写构图 + InfiniTalk→Kling 阶梯 + loudnorm | **部分（~15–25%）** | 成片可用；InfiniTalk 失败回退 Kling |
| 2 | 原生竖屏 i2v | `_SIZE_TO_RATIO` 缺 `720x1280`→误成 1:1 | 映射修复 + `1080x1920` + 显式 `aspect_ratio` | **基本弥补（~90%）** | 图 941×1672；i2v **1080×1916** |
| 3 | BGM/字幕样式 | 单一样式 + 双正弦床 | 场景字幕预设 + 多音色 BGM preset | **部分（~40%）** | 三套字幕成片可出；非商用曲库 |
| 4 | 跨镜身份 | 仅 hero i2v，无角度变体 | shot>1 `edit_image`→i2v | **部分（~35%）** | 管线已接入；成本换一致性 |
| 5 | 批量创意工厂 | 无扇出 API | `POST /director/variants` hook/cta/seed | **编排层弥补（~50%）** | API 返回 3 变体计划 |

---

## 差距 1 · 口型 / 微表情（对标 HeyGen）

### 细粒度拆解

| 子项 | HeyGen 旗舰 | 我们（修复前） | 可改空间 |
|------|-------------|----------------|----------|
| 音素级口型 | 专用驱动模型 | Kling Avatar / InfiniTalk | 换模才质变 |
| 微表情/眨眼 | 强 | 弱/偶发 | prompt 边际 |
| 人脸取景 | 紧特写优化 | 半身偏松 | **可改** |
| 驱动音频 | 工作室响度 | Edge+loudnorm 已有 | 微调 |
| 模型阶梯 | 自研 | 仅 Kling 默认 | **可改：InfiniTalk 优先** |

### 最优可行方案（已实现）

1. 数字人图改为 **CLOSE-UP 头肩特写**（嘴部清晰可见）  
2. lipsync prompt 强化 phoneme / blink / no warping  
3. **实测后策略修正：** InfiniTalk-first 会 internal error + 240s 空等再回退 Kling（总耗时翻倍）→ **默认 Kling**；Studio 可显式 `prefer_infinitalk=True`  
4. 特写构图 + 强化 phoneme prompt + loudnorm -16 LUFS  

### 真实评估

- 成片：`gap1_talking_final.mp4` → **1080×1920 · 10.4s · 包装完成**  
- Celery 日志：InfiniTalk attempt1 internal error → attempt2 **240s timeout** → **Kling Avatar Pro 成功**  
- **结论：** 构图/包装可提升观感；InfiniTalk 在当前 KIE 上 **不稳定、不适合默认**；画质仍是 **Kling 天花板**；相对 HeyGen **不能宣称追平**，约弥补 **15–25%**（构图+音频+包装），核心口型差距仍在 L1。

---

## 差距 2 · 原生竖屏 i2v（对标 Arcads/信息流）

### 细粒度拆解（根因）

```
Director: aspect_ratio="9:16"
  → _RATIO_TO_SIZE → "720x1280"   # 旧
  → KieAdapter._size_to_ratio("720x1280") → 默认 "1:1"  # BUG
  → 生成方图 → Kling i2v 跟方图 → 1440×1440
  → compose pad → 看似 9:16（黑边）
```

### 最优可行方案（已实现）

1. `_SIZE_TO_RATIO` 增加 `720x1280→9:16`、`1280x720→16:9`  
2. `_RATIO_TO_SIZE["9:16"]="1080x1920"`（与 KIE 映射一致）  
3. `generate_image` 支持显式 `aspect_ratio` kwargs  

### 真实评估

| 探针 | 结果 |
|------|------|
| UGC hero 图 | **941×1672**（ratio 1.777 ≈ 9:16）✅ |
| Kling Pro i2v | **1080×1916** ✅（非方屏） |

**结论：此差距已基本关闭（~90%）。** 剩余 10%：个别模型可能仍轻微裁切；compose 仍作安全垫。

---

## 差距 3 · 商用 BGM / 字幕样式（对标 Creatify/CapCut）

### 细粒度拆解

| 子项 | 顶级 | 修复前 | 修复后 |
|------|------|--------|--------|
| 字幕样式 | 多模板/花字 | 单一底栏 | feed/talking/ad/drama 预设 |
| BGM | 授权曲库 | 双正弦 | 场景 soft/upbeat/cinematic/drama |
| 人声 ducking | 侧链 | 简单 amix | 仍为固定比例 |
| 卡拉 OK 字 | 有 | 无 | 无（未做） |

### 最优可行方案（已实现）

- `SUBTITLE_STYLES` + compose `subtitle_style`  
- `BGM_PRESETS` 按 scenario 自动选择  
- **未做：** 商用曲库授权、花字动效（需素材与法务）  

### 真实评估

- `gap3_substyle_{feed,ad,talking}.mp4` 均生成成功  
- **结论：产品完成度提升约 40%。** 相对 Creatify 仍缺曲库与花字；对「可发成片」观感有实质改善。

---

## 差距 4 · 跨镜身份（对标角色库 / IP-Adapter）

### 细粒度拆解

| 层 | 修复前 | 修复后 |
|----|--------|--------|
| 计划 | `identity_from=hero` | 同左 + `identity_variant`（shot>1） |
| 执行 | 多镜共用同一 hero i2v | shot>1：`edit_image(hero, 新机位)`→i2v |
| 角色训练 | 无 | 仍无 |

### 最优可行方案（已实现）

在当前 KIE 能力内最优：**nano-banana-edit 变体机位 + 同 hero 锚定**，比纯 prompt 强，比训练 LoRA 现实。

### 真实评估

- 单元：UGC plan 验证 shot1 `identity_variant=False`、shot2 `True`  
- 完整多镜付费对比未在本探针重复（控成本）；机制已接通  
- **结论：约弥补 35%。** 身份稳定性会好于「同帧硬拉运镜」，但仍非 HeyGen/Midjourney 角色库级。

---

## 差距 5 · 批量创意工厂（对标 Advantage+/Creatify）

### 细粒度拆解

顶级 = 钩子×CTA×受众 矩阵 + 自动投放反馈。  
我们缺的是 **扇出编排**，不是新模型。

### 最优可行方案（已实现）

`POST /api/v1/director/variants`：

- 轴：`hook` / `cta` / `seed`  
- 返回 N 份可编辑 plan → 客户端并行 `/director/run/async`  

### 真实评估

```json
{"count": 3, "axes": ["seed=…", "痛点钩子", "cta=了解更多 · 立即选购"]}
```

**结论：编排层约弥补 50%。** 仍缺：FE 多成片画廊、投放数据回流、自动选优。

---

## 是否「弥补差距、优化平台」——诚实裁决

| 差距 | 是否值得做 | 平台是否明显更好 | 与顶级差距是否关闭 |
|------|------------|------------------|--------------------|
| 1 口型 | ✅ 值得（构图+阶梯） | 稳定性↑ | ❌ 未关闭 |
| 2 竖屏 | ✅✅ 必做 | **质变** | ✅ 基本关闭 |
| 3 包装 | ✅ 值得 | 观感↑ | ❌ 部分 |
| 4 身份 | ✅ 值得 | 多镜一致性↑ | ❌ 部分 |
| 5 变体 | ✅ 值得 | 投放产能↑ | ❌ 编排半程 |

**一句话：**  
本轮把 **可工程关闭的洞（竖屏 bug）彻底补上**，并在口型/包装/身份/变体上把 **产品层能做的都做了**；HeyGen 级口型与商用曲库仍依赖上游/商务，不能靠 prompt 硬吹。

---

## 建议下一刀（ROI）

1. **FE 接入 `/director/variants` 多成片对比 UI**（Gap5 后半）  
2. **口播：InfiniTalk 仅 Studio 手动触发**（避免默认 240s 空等；本次日志已证明易超时）  
3. **引入 1–2 条可商用 BGM URL 配置**（环境变量），替换程序化床  
4. **Gap4 A/B 真人眼对比**：同 brief 开关 `identity_variant` 各出一条  

---

## 产物下载

- 评估包：`/opt/cursor/artifacts/gap_closure_eval.zip`  
  - `gap2_ugc_hero_*.png` / `gap2_ugc_i2v.mp4`（原生竖屏铁证）  
  - `gap1_talking_final.mp4`  
  - `gap3_substyle_*.mp4`  
