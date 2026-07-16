# P0–P2 迭代实施（2026-07-16）

## P0
- Auto 路由 `MODEL_STYLE_PREFS` 覆盖全部 9 个 verified active；隔离模型跳过
- 软隔离 TTL：排队/5xx → 1h；硬失败 → 24h
- `scripts/smoke_live_video_sample.py`：Seedance-fast + Kling turbo 抽样出片
- 冒烟 KPI：`outframe_ok` / `outframe_skipped` 分列

## P1
- `scripts/fixture_derivative_harness.py`：lipsync/motion/tools/director dry 契约
- Motion 文案 + 定价改为「运动迁移（best-effort）」
- 工具链 golden：upscale / bg-remove / edit mock 契约测试

## P2
- Guess SKU → `status=lab`（默认列表隐藏，需 `include_lab=1`）
- 项目审片评论：`GET/POST /projects/{id}/reviews`

## 验证
`pytest tests/ -q` · `python scripts/fixture_derivative_harness.py`
