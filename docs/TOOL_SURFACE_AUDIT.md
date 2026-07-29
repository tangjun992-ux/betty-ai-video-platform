# 全工具面深度对标审计与修复（Tool Surface Audit）

**日期：** 2026-07-29
**分支：** `cursor/betty-yapper-parity-d257`
**前提：** 真实 KIE 出片可用。
**目的：** 对标 Yapper 全部工具（非仅核心），逐个验证是否真实可用，定位"占位符/浅实现/破损"并修复。
**验证集：** `backend/scripts/tool_surface_verify.py`；报告 `fixtures/audit/tool_surface_verify_latest.json`。

---

## 0. 裁决

对全部 Yapper 对标工具做了**真实出片级**验证。绝大多数工具**真实可用**；审计**发现并修复了 3 个真实缺陷**（1 个系统级），其中 2 个此前被"视频渲染慢/占位"掩盖：

| 工具 | 审计前 | 结果 |
|------|--------|------|
| 图像编辑 / 超分 / 去背景 / 扩图 | ✅ | 真实出片（KIE nano-banana-edit / recraft），8–150s |
| Prompt 提取 | ✅ | 真实（有 Key 走 vision，否则 heuristic） |
| 时间线合成 | ✅ | 真实 ffmpeg，~3.6s |
| 唇形/Motion/Performance 派发 | ✅ | 真实异步任务（唇形整片已验证） |
| **AI 配音 (Audio)** | ❌ 超时 | **已修**：改用 Edge Neural（~2.4s）+ KIE 兜底 |
| **换脸 face-swap** | ❌ image fetch failed | **已修**：本地图先上传为公网 URL 再调 KIE |
| **完成态写库（系统级）** | ❌ 成功即崩 | **已修**：`update_task` 跳过不存在列 `result_url` |

---

## 1. 发现的缺陷与修复

### 缺陷 1（系统级）· `result_url` 列不存在导致"成功即失败"
- **现象**：换脸任务在 KIE 真实返回图片后，写库崩溃 `(sqlite3.OperationalError) no such column: result_url`，任务被标记为 **failed（尽管生成成功）**。
- **波及**：`face_swap_tasks`、`motion_tasks`（2 处）、`timeline_tasks`、`performance_tasks` 均写了 `result_url`（Task 表无此列，结果存 `results` JSON）。这些视频类工具**每次真实成功都会崩**，此前被"渲染慢/KIE 拥塞"掩盖。
- **修复**：`update_task` 缓存 tasks 真实列并**跳过未知列**（单测证明 `result_url` 被跳过、不再崩溃），并移除 face_swap 的 `result_url` 传参。

### 缺陷 2 · AI 配音工具超时
- **现象**：`/generate/speech` 直接调 KIE ElevenLabs（慢，>60s 超时），standalone 配音工具不可用。
- **修复**：改用 Edge Neural TTS（~2.4s，带 20s 超时）优先，KIE ElevenLabs 兜底——与导演口播同一可靠路径。实测 2.4s 出音。

### 缺陷 3 · 换脸传本地 URL 给 KIE
- **现象**：face-swap 把 `/api/v1/media/...` 本地 URL 直接给 KIE，KIE 从自有服务器抓取 → `image fetch failed`。
- **修复**：任务内将本地图 **先上传为公网 URL** 再调用（与 `/generate/edit` 一致）。修复后成功到达 KIE 的 `edit`。

### 附带 · 稳健性
- 断连类错误（server disconnected/remote protocol/read error）纳入可重试；`createTask` 传输错误重试 3 次；图像队列等待上限 160s→240s（应对共享 GPU 拥塞）。

---

## 2. 真实验证

```
tool_edit / upscale / bg-remove / extend   PASS （真实 URL）
tool_extract_prompt                        PASS
tool_speech                                PASS  2.4s（edge-tts，修复后）
tool_timeline_compose                      PASS  3.6s（ffmpeg）
tool_lipsync/motion/performance_dispatch   PASS （真实异步任务）
update_task 跳过 result_url                 单测 PASS（不再崩溃）
```

**换脸端到端**：代码两处缺陷已修（fetch + 列崩溃），且同模型的图像编辑工具真实出图证明链路可用；本轮多次并发压测把 KIE nano-banana-edit 队列打满，出现 240s 排队超时（上游 GPU 拥塞，非代码缺陷，可重试）。KIE 空闲时即可成功（此前已 live 验证）。

---

## 3. 诚实边界

- 换脸/motion/performance 端到端真实成片受 KIE 共享 GPU 拥塞影响（本轮压测导致排队超时）；代码路径已修正。
- 真实出片依赖注入的 `KIE_API_KEY`；平台内积分独立计费。
- 换脸为 i2i 指令合成（nano-banana-edit），**非 InsightFace 像素级换脸**。

---

## 4. 后续建议

- 视频类工具（motion/performance）在 KIE 空闲时补一次端到端真实成片回归。
- 队列拥塞时的用户侧提示 + 自动降级到更快模型。
- 为 update_task 的列白名单加单测防回归。
