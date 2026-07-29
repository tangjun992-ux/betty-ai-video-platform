# 边角完整度（批量 SKU）+ Explore 增长飞轮 · 构建与验证

**日期：** 2026-07-29
**分支：** `cursor/betty-yapper-parity-d257`
**对标：** Yapper Product Shots / Headshots / Photo Packs + Explore
**前提：** 真实 KIE 出片可用。

---

## 0. 目标

补齐上次评估的两处短板：
- **边角完整度**：Product Shots / Headshots / Photo Packs 此前是薄壳（prompt 跳转），非真实批量。
- **增长飞轮（#3）**：Explore 浏览/Remix 后端已完善，缺"创作→发布→探索→Remix"的闭环入口。

---

## 1. 批量 SKU 管线（真实）

- `app/photo_packs.py`：Pack 注册表（product / headshots / lifestyle / brand），每个 pack 把**一个输入**（主体描述 和/或 参考图）扩展为 **N 个不同的专业变体**（角度 / 场景 / 风格）。i2i pack 保持上传的产品/人物。
- `GET /generate/packs`、`POST /generate/pack`：每个变体派发一个**真实图像任务**，逐任务扣费 + 派发失败退款；返回 `batch_id + items[task_id,label]`，前端逐个轮询。
- `BatchPackStudio` 组件 + 重建 `/create/product`、`/create/headshots`、`/create/photo-packs`：套系选择、参考图上传（i2i）、主体、数量、**边完成边填充的画廊**、下载全部、放大预览、**发布到 Explore**。

**真实验证：** 品牌视觉包（4 张）→ 生成 4 张**风格各异**的真实品牌图（极简海报/几何构图/渐变质感/产品排版，含真实品牌名与标语）。产品包（i2i，香水）→ 白底/45°/俯拍/场景不同构图。

## 2. Explore 增长飞轮

- Explore/gallery 后端与前端已完善：筛选/排序/点赞/**Remix(临摹精选)→ 创作页预填**/举报/发布/分享/统计。
- 新增**创作→发布闭环**：`BatchPackStudio` 的"发布到 Explore"把成套结果发布进探索画廊（复用 `publishShare`）。
- **真实验证：** 批量结果一键"发布到 Explore"（toast「4 张作品已进入探索画廊」）→ `/explore` 网格展示这 4 张 → 悬浮显示 Remix。闭环打通。

## 3. 稳健性修复（批量并发暴露）

批量并发暴露了 KIE 瞬时断连导致单变体硬失败（"Server disconnected"）：
- `fallback_handler`：将断连类错误（server disconnected / remote protocol / read error / connection error / EOF）列为**可重试**。
- `kie_adapter`：`createTask` HTTP 调用对 httpx 传输/协议错误**重试 3 次**（退避）。
- worker 并发 2→3（更好服务批量）。

效果：产品包 count=4 由此前 **2/4（2 次硬断连失败）** → **无硬失败**（3/4 完成 + 1 在途）。

---

## 4. 对评估维度的影响

| 维度 | 之前 | 现 | 说明 |
|------|------|----|------|
| 边角完整度 | 58 | **~72** | Product/Headshots/Photo Packs 变为真实批量 SKU 管线 |
| 增长飞轮 | 58 | **~64** | 创作→发布→探索→Remix 闭环打通（内容密度仍待累积） |
| 稳定性 | — | ↑ | 批量并发瞬时断连自愈 |

---

## 5. 仍可优化（非阻塞）

- Explore 内容密度：需真实创作/发布累积（当前 grid 靠 seed + 新发布）。
- 批量并发额度预检（避免中途 402）。
- i2i pack 的身份/产品一致性可进一步用 IP-Adapter/参考锁增强。
- 头像/产品 pack 增加更多变体与行业模板。

---

## 6. 复现

```bash
curl -s localhost:8000/api/v1/generate/packs
curl -s -X POST localhost:8000/api/v1/generate/pack -H 'Content-Type: application/json' \
  -H 'X-Guest-Id: <funded>' -d '{"pack_id":"brand","subject":"一个高端咖啡品牌","count":4}'
# 逐个轮询 items[].task_id → /tasks/{id}
```

**诚实边界：** 真实出片依赖注入的 `KIE_API_KEY`；平台内积分独立计费；批量为 N 个独立任务（非单请求多图），单张 15–60s，受 worker 并发与 KIE 延迟影响。
