# betty 设计系统 v5 — STUDIO

> 深色优先的专业创作台 · 中性 zinc 灰阶 · 单一 teal 强调色  
> 对标：`yapper.so/dashboard`、`dzine.ai/home` 的顶级创作工具气质。

---

## 0. 设计哲学

**"只做导演，不写提示词"** —— 界面不是主角，创意才是。v5 从 v3/v4 的“深空霓虹”收敛为克制、专业、可日用的 Studio 风格：

| 原则 | 设计决策 |
|------|----------|
| **深色优先** | 默认主题 `#0E0E11`，让视频/图片内容更突出 |
| **零彩虹渐变** | 全站仅使用单一 teal 品牌色；旧 accent-* 变量全部收敛到同族 |
| **Border-first** | 用 1px 边框和层级背景区分组件，而非重阴影或 glow |
| **克制留白** | 减少装饰性动效，hover/focus 才有反馈 |
| **CJK 优先** | 字族以系统黑体为主，英文保持高可读性几何无衬线 |

旧 v3/v4 的类名与 CSS 变量名被**保留**，存量组件不需要改动即可自动继承 v5 视觉。

---

## 1. 色彩系统

### 1.1 语义色板（Dark，默认）

```txt
┌─────────────────────────────────────────────────────────┐
│ SURFACE 层级                            HSL             │
├─────────────────────────────────────────────────────────┤
│ cosmic-void      最深背景          240 7% 4%  #09090B   │
│ cosmic-deep      页面默认底        240 6% 6%  #0E0E11   │
│ cosmic-surface   卡片/容器         240 6% 9%  #151518   │
│ cosmic-elevated  浮层/弹层         240 5% 12% #1C1C21   │
│ cosmic-subtle    hover/分组底      240 5% 14% #212127   │
│ cosmic-border    默认边框          240 5% 16% #26262C   │
│ cosmic-border-hv 悬停边框          240 6% 26% #3D3D46   │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ BRAND TEAL                              HEX             │
├─────────────────────────────────────────────────────────┤
│ brand            主色              #26C5AB  (172 66% 45%) │
│ brand-strong     hover/提亮        #2BDDBD  (172 72% 56%) │
│ brand-soft       浅色底（暗）      hsl(172 40% 12%)      │
│ brand-foreground 按钮文字（暗）    #04231E                │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ TEXT 层级                               HSL             │
├─────────────────────────────────────────────────────────┤
│ text-primary     标题/正文         240 6% 96%  #F4F4F6  │
│ text-secondary   辅助文字          240 5% 65%  #9C9CA6  │
│ text-tertiary    占位/禁用         240 4% 47%  #75757F  │
│ text-disabled    不可用            240 4% 32%  #4C4C54  │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│ SEMANTIC                                HSL             │
├─────────────────────────────────────────────────────────┤
│ success                                          #2DB87A │
│ warning          仅用于真实警示（如余额不足）    #F5A524 │
│ destructive                                      #E85C5C │
│ info                                             #26C5AB │
└─────────────────────────────────────────────────────────┘
```

### 1.2 CSS 变量代码

```css
:root {
  --cosmic-void: 240 7% 4%;
  --cosmic-deep: 240 6% 6%;
  --cosmic-surface: 240 6% 9%;
  --cosmic-elevated: 240 5% 12%;
  --cosmic-subtle: 240 5% 14%;
  --cosmic-border: 240 5% 16%;
  --cosmic-border-hover: 240 6% 26%;

  --brand: 172 66% 45%;
  --brand-strong: 172 72% 56%;
  --brand-soft: 172 40% 12%;
  --brand-foreground: 174 85% 8%;

  /* 兼容旧名：全部收敛到 teal 同族，消灭彩虹 */
  --accent-cyan: 172 66% 45%;
  --accent-blue: 186 58% 46%;
  --accent-violet: 160 52% 44%;
  --accent-purple: 160 52% 44%;
  --accent-fuchsia: 186 58% 46%;

  --text-primary: 240 6% 96%;
  --text-secondary: 240 5% 65%;
  --text-tertiary: 240 4% 47%;
  --text-disabled: 240 4% 32%;

  --success: 152 60% 44%;
  --warning: 38 90% 55%;
  --destructive: 0 72% 60%;
  --info: 172 66% 45%;
}
```

### 1.3 Light 主题变量

通过 `html.light` 切换：

```css
html.light {
  --cosmic-void: 240 20% 100%;
  --cosmic-deep: 240 30% 99%;
  --cosmic-surface: 0 0% 100%;
  --cosmic-elevated: 240 33% 98%;
  --cosmic-subtle: 240 24% 96%;
  --cosmic-border: 240 18% 91%;
  --cosmic-border-hover: 172 30% 68%;

  --brand: 175 77% 26%;        /* #0F766E */
  --brand-strong: 175 78% 20%;
  --brand-soft: 170 55% 96%;
  --brand-foreground: 0 0% 100%;
}
```

---

## 2. 字体层级

| Token | Size | Weight | Line-height | 用途 |
|-------|------|--------|-------------|------|
| `text-hero` | 4.25rem | 600 | 1.04 | 首页 Hero 标题 |
| `text-h1` | 2.75rem | 600 | 1.08 | 页面主标题 |
| `text-h2` | 1.875rem | 650 | 1.18 | 区块标题 |
| `text-h3` | 1.3125rem | 600 | 1.30 | 卡片标题 |
| `text-h4` | 1.125rem | 600 | 1.40 | 小标题 |
| `text-body` | 1rem | 400 | 1.65 | 正文 |
| `text-body-sm` | 0.875rem | 400 | 1.55 | 辅助文字 |
| `text-caption` | 0.75rem | 400 | 1.50 | 说明/元数据 |
| `text-overline` | 0.6875rem | 600 | 1.40 | 标签/分类 |

字族：`var(--font-sans)` → `"PingFang SC"`, `"Hiragino Sans GB"`, `"HarmonyOS Sans SC"`, `MiSans`, `"Microsoft YaHei"`, `"Noto Sans SC"`, system-ui, sans-serif。

---

## 3. 间距与圆角

### 3.1 间距

沿用 Tailwind 4px 基准：`space-1` = 4px，常用值：`2(8)`, `3(12)`, `4(16)`, `6(24)`, `8(32)`, `12(48)`。

### 3.2 圆角

| Token | 值 | 用途 |
|-------|-----|------|
| `radius-xs` | 4px | 标签 |
| `radius-sm` | 6px | 小按钮 |
| `radius-md` | 8px | 标准按钮/输入框 |
| `radius-lg` | 12px | 卡片 |
| `radius-xl` | 16px | 大卡片/模态 |
| `radius-2xl` | 20px | Hero 输入框 |
| `radius-full` | 9999px | 药丸按钮 |

---

## 4. 阴影与 Elevation

暗色主题下阴影**深而克制**，仅用于表达层级；亮色主题下阴影**淡而干净**。

```css
--shadow-xs: 0 1px 2px 0 rgb(0 0 0 / 0.35);
--shadow-sm: 0 1px 3px 0 rgb(0 0 0 / 0.45), 0 1px 2px -1px rgb(0 0 0 / 0.4);
--shadow-md: 0 4px 14px -2px rgb(0 0 0 / 0.5), 0 2px 6px -2px rgb(0 0 0 / 0.4);
--shadow-lg: 0 14px 34px -8px rgb(0 0 0 / 0.6), 0 6px 14px -6px rgb(0 0 0 / 0.45);
--shadow-brand: 0 6px 20px -8px hsl(var(--brand) / 0.45);
```

Tailwind 对应：`shadow-elevation-xs/sm/md/lg/xl/2xl`、`shadow-button-glow`、`shadow-card`、`shadow-card-hover`。

---

## 5. 组件样式规范

### 5.1 按钮

```txt
primary    : bg-brand text-brand-foreground hover:bg-brand-strong
secondary  : bg-cosmic-surface border border-cosmic-border text-text-primary
ghost      : transparent text-text-secondary
```

类名：`.btn-primary`、`.btn-secondary`、`.btn-ghost`、`.btn-icon`。

### 5.2 输入框

`.input-cosmic` / `.input-canvas` — 12px 圆角，1px 边框，focus 时品牌色光环。

### 5.3 卡片

优先使用 `surface-raised`、`glass-card` 或 `gradient-card`（已中性化为 border 卡）。Hover 仅改变边框色，不使用彩色 glow。

### 5.4 Icon Tile

`.icon-tile` — yapper 式哑光图标砖：灰底、灰边框、灰图标；hover 才出现品牌色。禁止彩虹渐变方块。

### 5.5 Chip / Badge

- `.chip`：轮廓药丸，hover 变亮。
- `.badge-cyan` / `.badge-blue` / `.badge-violet`：已统一为品牌浅底（teal），保留旧类名是为了向后兼容。
- `.badge-success` / `.badge-warning` / `.badge-destructive`：仅保留给真实语义状态。

### 5.6 导航

左侧 Sidebar 分组展示：导航 / 创作工具 / 底部升级；顶部 TopBar 仅保留 Logo、搜索、主题切换、登录/CTA。避免重复入口与“AI 味”渐变文字。

---

## 6. 动画与交互

### 6.1 缓动曲线

```css
--ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);   /* 主要入场 */
--ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1); /* 轻微弹性 */
--ease-spring: cubic-bezier(0.22, 1.2, 0.36, 1);   /* 交互反馈 */
```

### 6.2 时长

| 类型 | 时长 | 用途 |
|------|------|------|
| micro | 150ms | 按下 |
| quick | 200ms | hover/focus |
| normal | 300ms | 卡片/导航状态 |
| slow | 500ms | 页面区块入场 |

### 6.3 关键帧

- `fade-in-up`
- `fade-in-scale`
- `slide-in-left/right`
- `shimmer`（骨架屏）

所有动画均受 `prefers-reduced-motion` 保护。

---

## 7. 实现清单（v5 已完成）

- [x] `globals.css` 替换为 Studio v5 tokens
- [x] `tailwind.config.js` 收敛品牌色、 elevation、阴影、字体
- [x] 默认主题为 dark，亮色为显式 opt-in
- [x] 首页 `/`：yapper 式居中创作台
- [x] `/tools`：统一哑光图标卡片矩阵
- [x] `/agent`：分段控制器 + 场景卡片
- [x] `/create/video`：去彩虹左侧工具栏
- [x] `/pricing`：单一 teal 价格卡
- [x] `/explore`：统一统计点/类型标签
- [x] `CookieConsent` / `DemoModeBanner` 定位优化并修复 dismissed 逻辑
- [x] Playwright 截图脚本覆盖 dark / light / desktop / mobile

---

## 8. 设计检查清单

| 检查项 | 标准 |
|--------|------|
| 色彩对比度 | 正文/背景 ≥ 4.5:1 (WCAG AA) |
| 焦点可见 | 所有可交互元素有 `focus-visible` ring |
| 减少动效 | `@media (prefers-reduced-motion)` 禁用动画 |
| 触控友好 | 可点击区域 ≥ 44×44px |
| 文字截断 | 长文本使用 `truncate` / `line-clamp` |
| 加载状态 | 异步操作有 loading / skeleton |
| 单品牌色 | 除 semantic 警示外，不使用 amber/orange/violet/rose 作为装饰 |
