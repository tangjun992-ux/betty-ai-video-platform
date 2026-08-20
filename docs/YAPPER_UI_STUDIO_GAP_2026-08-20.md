# Betty × Yapper 界面专业度评估（2026-08-20）

**抓取：** yapper.so 当日首屏（暗色转化弹层 + 电蓝 CTA + 模型品牌墙）  
**原则：** 学结构与气质，不抄 Veo/Sora/19+/Millions 话术。

## 一句话

Betty 的 Composer / Create 页已经接近工作室完成度；公开面曾像「银行后台 + 彩虹图标」，而不是媒体工作室。本轮修的是 **光谱、工具分区、错误路由、演示条噪音**。

## 差距（改前）

| 维 | Yapper | Betty 改前 | 本轮 |
|----|--------|------------|------|
| 配色 | 暗底、白字、电蓝主按钮、模型墙单色 | 全光谱被压成医院绿；`accent-violet` 实际是绿 | 品牌 CTA 仍 teal；点缀恢复电蓝/紫/品红 |
| Tools 枢纽 | Video Tools / Image Tools 大分区卡片 | 暗色残留 `bg-white/3`、竞品名「Yapper-style Agent」 | 真实分区 + Just Direct 自有话术 |
| 首页工具 | 每张卡进对应 App | 放大/抠图/头像/产品误进 `/create/image`；音频进 `/agent` | 全部指向独立 SKU 页 |
| 品牌墙 | Veo/Sora/Kling 循环（营销） | 仅下方模型栅格，首屏无节奏 | 已验证模型 marquee，明确不并列 Veo/Sora |
| 演示条 | 转化弹层（商业） | 厚卡片警告盖住工作室 | 顶栏细条，诚实但不抢主视觉 |
| 功能货架 | 19+/29+ 可售叙事 | active=9 | **不改口**；工具面齐、货架仍 9 |

## 仍落后（不能靠 CSS 补）

1. 没有 Yapper 级成片资产密度（Explore 仍偏 seed）
2. 没有可关闭的商业转化弹层（我们也不该在无 Stripe 时做假 countdown）
3. 默认仍是亮色壳；暗色主题可用，但公开首屏不是 Runway 级影院感
4. MCP / 收款 / Worker 仍是经营门，不是界面门

## 验证

- Playwright：`Studio 工具矩阵` + `首页工具路由`
- 视觉：`/tools` 出现 Video Tools / Image Tools；首页 marquee 仅已验证模型
