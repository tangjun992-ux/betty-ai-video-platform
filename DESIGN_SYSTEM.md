# betty 设计系统 v3 — NEBULA

> 深空黑 · 青蓝紫渐变 · 电影感 · Glassmorphism · 辉光微光

---

## 0. 设计哲学

**"深空中的光"** — 以宇宙深空（#05050A）为画布，以青→蓝→紫渐变流光为唯一的视觉焦点。所有 UI 元素退居幕后，让内容和技术感成为主角。

| 原则 | 实施 |
|------|------|
| **减法为王** | 减少装饰色、减少分割线、减少阴影层数 |
| **光即信息** | 颜色渐变仅用于引导操作、标记状态、突出品牌 |
| **玻璃即空间** | Glassmorphism 创造 Z 轴深度感，不是花哨装饰 |
| **静中有动** | 动画仅在 hover/focus/loading 时触发，不做无意义动效 |
| **触感真实** | 内阴影模拟物理凹陷、辉光模拟能量、微交互有重量感 |

---

## 1. 色彩系统

### 1.1 语义色板

```
┌─────────────────────────────────────────────────────────┐
│  DEEP SPACE 层级                    HSL               │
├─────────────────────────────────────────────────────────┤
│  cosmic-void      最深背景          240 20% 2%         │
│  cosmic-deep      默认背景          240 15% 4%         │
│  cosmic-surface   卡片/容器         240 12% 6.5%       │
│  cosmic-elevated  弹出层/浮层       240 10% 10%        │
│  cosmic-border    默认边框          240 5% 16%         │
│  cosmic-border-hv 悬停边框          240 5% 24%         │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  ACCENT 渐变光谱                     HEX               │
├─────────────────────────────────────────────────────────┤
│  accent-cyan      400              #22D3EE            │
│  accent-cyan      500              #06B6D4            │
│  accent-blue      500              #3B82F6            │
│  accent-violet    500              #8B5CF6            │
│  accent-purple    500              #A855F7            │
│  accent-fuchsia   500              #D946EF            │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  TEXT 层级                           HSL               │
├─────────────────────────────────────────────────────────┤
│  text-primary     标题/正文         0 0% 96%           │
│  text-secondary   辅助文字          0 0% 70%           │
│  text-tertiary    占位/禁用         0 0% 48%           │
│  text-disabled    不可用            0 0% 32%           │
└─────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  SEMANTIC                            HSL               │
├─────────────────────────────────────────────────────────┤
│  success          150 80% 48%       #1EA365            │
│  warning          36 95% 52%        #EAB308            │
│  destructive       0 80% 56%        #EF4444            │
│  info             210 100% 52%      #3B82F6            │
└─────────────────────────────────────────────────────────┘
```

### 1.2 渐变预设

```
gradient-primary:   cyan-400 → blue-500 → violet-500         (主按钮、CTA)
gradient-hero:      cyan-400 → blue-500 → violet-500 → purple-500  (Hero 标题)
gradient-subtle:    white/3% → white/0%                       (卡片底部微光)
gradient-glow:      primary/15% → transparent                 (辉光背景)
gradient-border:    cyan-400/40% → blue-500/40% → violet-500/40%  (渐变边框)
```

### 1.3 CSS 变量代码

```css
:root {
  /* === COSMIC DEPTH === */
  --cosmic-void: 240 20% 2%;
  --cosmic-deep: 240 15% 4%;
  --cosmic-surface: 240 12% 6.5%;
  --cosmic-elevated: 240 10% 10%;
  --cosmic-border: 240 5% 16%;
  --cosmic-border-hover: 240 5% 24%;

  /* === ACCENT HUES === */
  --accent-cyan: 189 94% 48%;
  --accent-blue: 217 91% 60%;
  --accent-violet: 255 92% 66%;
  --accent-purple: 271 91% 65%;
  --accent-fuchsia: 292 84% 61%;

  /* === TEXT === */
  --text-primary: 0 0% 96%;
  --text-secondary: 0 0% 70%;
  --text-tertiary: 0 0% 48%;
  --text-disabled: 0 0% 32%;

  /* === SEMANTIC === */
  --success: 150 80% 48%;
  --warning: 36 95% 52%;
  --destructive: 0 80% 56%;
  --info: 210 100% 52%;
}
```

---

## 2. 字体层级

| Token | Size | Weight | Line-height | Letter-spacing | 用途 |
|-------|------|--------|-------------|----------------|------|
| `--text-hero` | 3.5rem (56px) | 700 | 1.05 | -0.03em | 首页 Hero 标题 |
| `--text-h1` | 2.5rem (40px) | 700 | 1.1 | -0.02em | 页面主标题 |
| `--text-h2` | 1.75rem (28px) | 600 | 1.2 | -0.01em | 区块标题 |
| `--text-h3` | 1.25rem (20px) | 600 | 1.3 | 0 | 卡片标题 |
| `--text-h4` | 1.125rem (18px) | 500 | 1.4 | 0 | 小标题 |
| `--text-body` | 1rem (16px) | 400 | 1.6 | 0 | 正文 |
| `--text-body-sm` | 0.875rem (14px) | 400 | 1.5 | 0 | 辅助文字 |
| `--text-caption` | 0.75rem (12px) | 400 | 1.5 | 0 | 说明/元数据 |
| `--text-overline` | 0.6875rem (11px) | 600 | 1.4 | 0.08em | 标签/分类 |

**字族**: Inter (已配置) — 现代几何无衬线，x-height 高，适合屏幕阅读。

### Tailwind 扩展

```js
fontSize: {
  hero: ['3.5rem', { lineHeight: '1.05', letterSpacing: '-0.03em', fontWeight: '700' }],
  h1:   ['2.5rem', { lineHeight: '1.1',  letterSpacing: '-0.02em', fontWeight: '700' }],
  h2:   ['1.75rem',{ lineHeight: '1.2',  letterSpacing: '-0.01em', fontWeight: '600' }],
  h3:   ['1.25rem',{ lineHeight: '1.3',  fontWeight: '600' }],
  h4:   ['1.125rem',{lineHeight: '1.4',  fontWeight: '500' }],
  body: ['1rem',   { lineHeight: '1.6' }],
  'body-sm': ['0.875rem', { lineHeight: '1.5' }],
  caption: ['0.75rem', { lineHeight: '1.5' }],
  overline: ['0.6875rem', { lineHeight: '1.4', letterSpacing: '0.08em', fontWeight: '600' }],
}
```

---

## 3. 间距与栅格

### 3.1 间距标尺

使用 4px 基准 (0.25rem = 1 unit):

| Token | rem | px | 用途 |
|-------|-----|----|------|
| `space-0.5` | 0.125 | 2 | 图标间距 |
| `space-1` | 0.25 | 4 | 内边距最小 |
| `space-2` | 0.5 | 8 | 紧凑间距 |
| `space-3` | 0.75 | 12 | 常规内边距 |
| `space-4` | 1.0 | 16 | 标准间距 |
| `space-5` | 1.25 | 20 | 扩展间距 |
| `space-6` | 1.5 | 24 | 区块间距 |
| `space-8` | 2.0 | 32 | 大区块间距 |
| `space-10` | 2.5 | 40 | 区块分隔 |
| `space-12` | 3.0 | 48 | Section 间距 |
| `space-16` | 4.0 | 64 | 页面间距 |
| `space-20` | 5.0 | 80 | Hero 间距 |
| `space-24` | 6.0 | 96 | 超大间距 |

### 3.2 布局栅格

- **最大内容宽度**: `max-w-7xl` (1280px)
- **侧边栏宽度**: 240px (展开) / 64px (折叠)
- **内容区 padding**: `px-6 md:px-8 lg:px-12`
- **卡片网格**: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4`
- **表单双列**: `grid-cols-1 md:grid-cols-2 gap-4`

### 3.3 圆角系统

| Token | 值 | 用途 |
|-------|-----|------|
| `radius-xs` | 4px | 标签、小徽章 |
| `radius-sm` | 6px | 输入框、小按钮 |
| `radius-md` | 8px | 标准按钮 |
| `radius-lg` | 12px | 卡片、大按钮 |
| `radius-xl` | 16px | 模态框、大卡片 |
| `radius-2xl` | 20px | Hero 卡片、特色区块 |
| `radius-full` | 9999px | 药丸按钮、头像 |

---

## 4. 阴影与辉光系统

这是 betty 设计系统最核心的部分——通过阴影创造空间深度，通过辉光创造科技感。

### 4.1 阴影层级

```css
/* === ELEVATION SHADOWS === */
--shadow-xs:   0 1px 2px 0 rgb(0 0 0 / 0.4);
--shadow-sm:   0 1px 3px 0 rgb(0 0 0 / 0.5), 0 1px 2px -1px rgb(0 0 0 / 0.4);
--shadow-md:   0 4px 6px -1px rgb(0 0 0 / 0.5), 0 2px 4px -2px rgb(0 0 0 / 0.4);
--shadow-lg:   0 10px 15px -3px rgb(0 0 0 / 0.5), 0 4px 6px -4px rgb(0 0 0 / 0.4);
--shadow-xl:   0 20px 25px -5px rgb(0 0 0 / 0.5), 0 8px 10px -6px rgb(0 0 0 / 0.4);
--shadow-2xl:  0 25px 50px -12px rgb(0 0 0 / 0.6);

/* === GLOW SHADOWS === */
--glow-subtle:   0 0 15px -3px hsl(var(--accent-cyan) / 0.12);
--glow-medium:   0 0 25px -5px hsl(var(--accent-cyan) / 0.2);
--glow-strong:   0 0 40px -8px hsl(var(--accent-cyan) / 0.3);
--glow-cyan:     0 0 30px -6px hsl(189 94% 48% / 0.25);
--glow-blue:     0 0 30px -6px hsl(217 91% 60% / 0.25);
--glow-violet:   0 0 30px -6px hsl(255 92% 66% / 0.25);

/* === INNER SHADOWS (凹陷感) === */
--inner-glow-top:    inset 0 1px 0 0 rgb(255 255 255 / 0.06);
--inner-glow-bottom: inset 0 -1px 0 0 rgb(0 0 0 / 0.3);
--inner-shadow-sm:   inset 0 1px 3px 0 rgb(0 0 0 / 0.3);
--inner-shadow-md:   inset 0 2px 6px 0 rgb(0 0 0 / 0.4);
```

### 4.2 Tailwind Shadow 扩展

```js
boxShadow: {
  // Elevation
  'elevation-xs':  '0 1px 2px 0 rgb(0 0 0 / 0.4)',
  'elevation-sm':  '0 1px 3px 0 rgb(0 0 0 / 0.5), 0 1px 2px -1px rgb(0 0 0 / 0.4)',
  'elevation-md':  '0 4px 6px -1px rgb(0 0 0 / 0.5), 0 2px 4px -2px rgb(0 0 0 / 0.4)',
  'elevation-lg':  '0 10px 15px -3px rgb(0 0 0 / 0.5), 0 4px 6px -4px rgb(0 0 0 / 0.4)',
  'elevation-xl':  '0 20px 25px -5px rgb(0 0 0 / 0.5), 0 8px 10px -6px rgb(0 0 0 / 0.4)',
  'elevation-2xl': '0 25px 50px -12px rgb(0 0 0 / 0.6)',
  
  // Glow
  'glow-subtle':  '0 0 15px -3px hsl(189 94% 48% / 0.12)',
  'glow-medium':  '0 0 25px -5px hsl(189 94% 48% / 0.2)',
  'glow-strong':  '0 0 40px -8px hsl(189 94% 48% / 0.3)',
  'glow-cyan':    '0 0 30px -6px hsl(189 94% 48% / 0.25)',
  'glow-blue':    '0 0 30px -6px hsl(217 91% 60% / 0.25)',
  'glow-violet':  '0 0 30px -6px hsl(255 92% 66% / 0.25)',
  
  // Inner
  'inner-glow-t': 'inset 0 1px 0 0 rgb(255 255 255 / 0.06)',
  'inner-glow-b': 'inset 0 -1px 0 0 rgb(0 0 0 / 0.3)',
  'inner-depth':  'inset 0 2px 6px 0 rgb(0 0 0 / 0.4)',
  
  // Combined (elevation + glow)
  'card': '0 1px 3px 0 rgb(0 0 0 / 0.5), 0 1px 2px -1px rgb(0 0 0 / 0.4)',
  'card-hover': '0 4px 6px -1px rgb(0 0 0 / 0.5), 0 0 20px -5px hsl(189 94% 48% / 0.15)',
  'card-active': 'inset 0 2px 6px 0 rgb(0 0 0 / 0.4), 0 0 15px -3px hsl(189 94% 48% / 0.1)',
  'button-glow': '0 0 20px -5px hsl(189 94% 48% / 0.3)',
  'button-glow-lg': '0 0 30px -8px hsl(189 94% 48% / 0.4)',
}
```

---

## 5. 组件样式规范

### 5.1 卡片 (Card)

```
规范:
  background:     hsl(var(--cosmic-surface) / 0.7)
  backdrop-filter: blur(24px) saturate(180%)
  border:         1px solid hsl(var(--cosmic-border) / 0.6)
  border-radius:  16px (--radius-xl)
  box-shadow:     --shadow-card
  padding:        24px (p-6)

Hover:
  background:     hsl(var(--cosmic-surface) / 0.85)
  border-color:   hsl(var(--accent-cyan) / 0.15)
  box-shadow:     --shadow-card-hover
  transition:     300ms cubic-bezier(0.16, 1, 0.3, 1)

Active/Pressed:
  box-shadow:     --shadow-card-active
  transform:      scale(0.985)
  transition:     150ms

变体:
  .card-glass      毛玻璃卡片
  .card-glass-hover  毛玻璃 + hover 辉光
  .card-gradient   渐变边框卡片 (使用 ::before 伪元素 + masking)
  .card-interactive  可点击卡片 (cursor: pointer)
```

**Tailwind 类**:
```
card-glass:        bg-cosmic-surface/70 backdrop-blur-2xl backdrop-saturate-150 border border-cosmic-border/60 rounded-2xl
card-glass-hover:  card-glass hover:bg-cosmic-surface/85 hover:border-accent-cyan/15 hover:shadow-card-hover transition-all duration-300 ease-out-expo
```

### 5.2 按钮 (Button)

```
┌──────────────────────────────────────────────────────────────┐
│  VARIANT           BG                     TEXT        BORDER │
├──────────────────────────────────────────────────────────────┤
│  primary           gradient-primary       white       none   │
│  primary-glass     white/5% + blur        white       white/8│
│  secondary         white/5%               text-sec    white/8│
│  ghost             transparent            text-ter    none   │
│  destructive       destructive/15%        destructive destr/30│
│  icon              transparent            text-ter    none   │
└──────────────────────────────────────────────────────────────┘

尺寸:
  sm:  h-8 px-3 text-body-sm rounded-lg
  md:  h-10 px-5 text-body-sm rounded-xl   (默认)
  lg:  h-12 px-6 text-body rounded-xl
  xl:  h-14 px-8 text-body rounded-2xl

状态:
  default:  正常状态
  hover:    brightness(1.1) + shadow-glow-medium
  active:   scale(0.97) + brightness(0.95)
  focus:    ring-2 ring-accent-cyan/40 ring-offset-2 ring-offset-cosmic-deep
  disabled: opacity-40 cursor-not-allowed
  loading:  spinner 替换 icon

动画:
  transition: all 200ms cubic-bezier(0.16, 1, 0.3, 1)
  glow pulse: 辉光呼吸动画 (仅 primary 变体, 2s ease-in-out infinite)
```

**Tailwind 类组合**:
```
btn-primary:
  inline-flex items-center justify-center gap-2
  h-10 px-5 rounded-xl
  bg-gradient-to-r from-accent-cyan via-accent-blue to-accent-violet
  text-white font-semibold text-body-sm
  shadow-button-glow hover:shadow-button-glow-lg
  hover:brightness-110 active:scale-[0.97] active:brightness-95
  transition-all duration-200 ease-out-expo
  focus-visible:ring-2 focus-visible:ring-accent-cyan/40 focus-visible:ring-offset-2 focus-visible:ring-offset-cosmic-deep
  disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-button-glow
```

### 5.3 输入框 (Input)

```
规范:
  background:     hsl(var(--cosmic-surface) / 0.5)
  border:         1px solid hsl(var(--cosmic-border) / 0.6)
  border-radius:  12px (--radius-lg)
  height:         40px (sm) / 48px (md) / 56px (lg)
  padding-x:      16px
  font-size:      14px (--text-body-sm)
  color:          hsl(var(--text-primary))
  placeholder:    hsl(var(--text-tertiary) / 0.5)

Focus:
  background:     hsl(var(--cosmic-surface) / 0.8)
  border-color:   hsl(var(--accent-cyan) / 0.4)
  box-shadow:     0 0 0 3px hsl(var(--accent-cyan) / 0.1)
  outline:        none

Error:
  border-color:   hsl(var(--destructive) / 0.5)
  box-shadow:     0 0 0 3px hsl(var(--destructive) / 0.1)

Disabled:
  opacity:        0.4
  cursor:         not-allowed
```

**Tailwind 类**:
```
input-cosmic:
  w-full rounded-xl
  bg-cosmic-surface/50 border border-cosmic-border/60
  px-4 py-2.5
  text-body-sm text-text-primary placeholder:text-text-tertiary/50
  focus:bg-cosmic-surface/80 focus:border-accent-cyan/40 focus:ring-3 focus:ring-accent-cyan/10 focus:outline-none
  transition-all duration-200
  disabled:opacity-40 disabled:cursor-not-allowed

input-cosmic-lg:
  input-cosmic h-14 px-5 text-body rounded-2xl
```

### 5.4 导航栏 (Navbar)

```
规范:
  position:       fixed, top 0, z-30
  height:         64px (h-16)
  background:     滚动前 transparent, 滚动后 cosmic-deep/80 + backdrop-blur-xl
  border-bottom:  滚动后 cosmic-border/50
  padding-x:      24px (px-6)
  left offset:    var(--sidebar-width) (桌面端侧边栏宽度)

Logo 区域:
  betty logo (32x32) + "betty" 文字 (font-bold, text-lg)

链接:
  default:  text-secondary, text-sm
  hover:    text-primary
  active:   底部 2px primary 下划线 + text-primary

搜索框:
  居中, max-w-xl
  icon: Search (lucide), left-3
  kbd: ⌘K, right-3, 隐藏于 sm 以下

右侧操作:
  theme toggle (Sun/Moon)
  语言选择 (暂)
  升级按钮 (accent 浅底 + icon)
  头像 DropdownMenu / 登录按钮
```

---

## 6. 动画与微交互

### 6.1 缓动曲线

```css
--ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);    /* 主要出场动画 */
--ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1); /* 弹跳出场 */
--ease-in-out:   cubic-bezier(0.65, 0, 0.35, 1);    /* 平滑过渡 */
--ease-spring:   cubic-bezier(0.22, 1.2, 0.36, 1);  /* 弹簧感 */
```

### 6.2 动画时长

| 类型 | 时长 | 用途 |
|------|------|------|
| micro | 150ms | 按钮按下、图标 hover |
| quick | 200ms | hover 状态切换、focus ring |
| normal | 300ms | 卡片 hover、导航出现 |
| slow | 500ms | 页面入场、大区块动画 |
| dramatic | 800ms | Hero 动画、品牌展示 |

### 6.3 关键帧动画

```css
/* 辉光呼吸 (按钮/卡片) */
@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 20px -5px hsl(var(--accent-cyan) / 0.2); }
  50%      { box-shadow: 0 0 30px -8px hsl(var(--accent-cyan) / 0.35); }
}

/* 渐变流动 (Hero 标题、品牌元素) */
@keyframes gradient-flow {
  0%   { background-position: 0% 50%; }
  50%  { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* 卡片悬浮微光 (鼠标追踪) */
@keyframes card-shine {
  from { opacity: 0; }
  to   { opacity: 1; }
}

/* 打字机光标 */
@keyframes blink-caret {
  0%, 100% { border-color: transparent; }
  50%      { border-color: hsl(var(--accent-cyan)); }
}

/* 加载旋转 (带渐变轨道) */
@keyframes spin-gradient {
  to { transform: rotate(360deg); }
}

/* 淡入上移 (页面元素入场) */
@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* 缩放淡入 (模态框) */
@keyframes scale-in {
  from { opacity: 0; transform: scale(0.95); }
  to   { opacity: 1; transform: scale(1); }
}
```

---

## 7. 关键组件示例代码

### 7.1 Prompt 输入卡片 (CosmicPromptCard)

```tsx
"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Sparkles, ImageIcon, Send, Wand2, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface CosmicPromptCardProps {
  onSubmit: (prompt: string) => void;
  placeholder?: string;
  suggestions?: string[];
  className?: string;
}

export function CosmicPromptCard({
  onSubmit,
  placeholder = "描述你想要的画面...",
  suggestions = [],
  className,
}: CosmicPromptCardProps) {
  const [prompt, setPrompt] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }, [prompt]);

  const handleSubmit = () => {
    if (!prompt.trim()) return;
    onSubmit(prompt.trim());
    setPrompt("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        // Glass card base
        "relative w-full rounded-2xl",
        "bg-cosmic-surface/60 backdrop-blur-2xl backdrop-saturate-150",
        "border border-cosmic-border/60",
        "shadow-elevation-md",
        // Focus glow
        isFocused && "border-accent-cyan/30 shadow-glow-subtle",
        "transition-all duration-300",
        className
      )}
    >
      {/* Inner glow top edge */}
      <div className="absolute inset-x-4 top-0 h-px bg-gradient-to-r from-transparent via-white/6 to-transparent" />

      {/* Prompt input area */}
      <div className="relative p-5 pb-4">
        {/* Left accent bar */}
        <div 
          className={cn(
            "absolute left-0 top-1/3 bottom-1/3 w-0.5 rounded-r-full",
            "bg-gradient-to-b from-accent-cyan via-accent-blue to-accent-violet",
            "opacity-0 transition-opacity duration-300",
            isFocused && "opacity-100"
          )} 
        />

        <textarea
          ref={textareaRef}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={3}
          className={cn(
            "w-full resize-none bg-transparent",
            "text-body text-text-primary placeholder:text-text-tertiary/50",
            "focus:outline-none",
            "min-h-[80px]"
          )}
        />
      </div>

      {/* Bottom bar: suggestions + actions */}
      <div className="flex items-center justify-between px-5 pb-4 gap-3">
        {/* Suggestions */}
        <div className="flex items-center gap-2 overflow-x-auto flex-1 scrollbar-hide">
          {suggestions.slice(0, 3).map((s) => (
            <button
              key={s}
              onClick={() => setPrompt(s)}
              className={cn(
                "flex-shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-full",
                "bg-white/[0.04] border border-white/[0.06]",
                "text-caption text-text-tertiary",
                "hover:bg-white/[0.08] hover:text-text-secondary hover:border-white/[0.1]",
                "transition-all duration-200"
              )}
            >
              <Wand2 className="w-3 h-3" />
              <span className="truncate max-w-[100px]">{s}</span>
            </button>
          ))}
        </div>

        {/* Submit button */}
        <motion.button
          onClick={handleSubmit}
          disabled={!prompt.trim()}
          whileTap={{ scale: 0.95 }}
          className={cn(
            "flex-shrink-0 inline-flex items-center justify-center gap-2",
            "h-10 px-5 rounded-xl",
            "bg-gradient-to-r from-accent-cyan via-accent-blue to-accent-violet",
            "text-white font-semibold text-body-sm",
            "shadow-button-glow",
            "hover:shadow-button-glow-lg hover:brightness-110",
            "active:brightness-95",
            "transition-all duration-200",
            "disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:shadow-button-glow"
          )}
        >
          <Sparkles className="w-4 h-4" />
          <span>生成</span>
        </motion.button>
      </div>
    </motion.div>
  );
}
```

### 7.2 生成按钮 (CosmicGenerateButton)

```tsx
"use client";

import { motion } from "framer-motion";
import { Sparkles, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "primary-glass" | "secondary" | "ghost" | "destructive";
type ButtonSize = "sm" | "md" | "lg" | "xl";

interface CosmicGenerateButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  className?: string;
  type?: "button" | "submit";
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: cn(
    "bg-gradient-to-r from-accent-cyan via-accent-blue to-accent-violet",
    "text-white",
    "shadow-button-glow hover:shadow-button-glow-lg",
    "hover:brightness-110 active:brightness-95"
  ),
  "primary-glass": cn(
    "bg-white/[0.05] backdrop-blur-md",
    "border border-white/[0.08]",
    "text-white",
    "hover:bg-white/[0.1] hover:border-white/[0.15]",
    "hover:shadow-glow-subtle"
  ),
  secondary: cn(
    "bg-white/[0.04]",
    "border border-cosmic-border/60",
    "text-text-secondary",
    "hover:bg-white/[0.08] hover:text-text-primary hover:border-cosmic-border-hover"
  ),
  ghost: cn(
    "text-text-tertiary",
    "hover:text-text-primary hover:bg-white/[0.05]"
  ),
  destructive: cn(
    "bg-destructive/15",
    "border border-destructive/30",
    "text-destructive",
    "hover:bg-destructive/25 hover:border-destructive/50"
  ),
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-caption rounded-lg gap-1.5",
  md: "h-10 px-5 text-body-sm rounded-xl gap-2",
  lg: "h-12 px-6 text-body rounded-xl gap-2",
  xl: "h-14 px-8 text-body rounded-2xl gap-2.5",
};

export function CosmicGenerateButton({
  children,
  onClick,
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  icon,
  className,
  type = "button",
}: CosmicGenerateButtonProps) {
  return (
    <motion.button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      whileTap={{ scale: disabled || loading ? 1 : 0.97 }}
      whileHover={{ scale: disabled || loading ? 1 : 1.02 }}
      className={cn(
        // Base
        "relative inline-flex items-center justify-center font-semibold",
        "overflow-hidden",
        "focus-visible:ring-2 focus-visible:ring-accent-cyan/40 focus-visible:ring-offset-2 focus-visible:ring-offset-cosmic-deep focus-visible:outline-none",
        "transition-all duration-200 ease-out-expo",
        "disabled:opacity-40 disabled:cursor-not-allowed",
        // Variant
        variantStyles[variant],
        // Size
        sizeStyles[size],
        // Custom
        className
      )}
    >
      {/* Glow pulse overlay (primary variant only) */}
      {variant === "primary" && !disabled && !loading && (
        <div 
          className="absolute inset-0 rounded-xl opacity-0 hover:opacity-100 transition-opacity duration-500"
          style={{
            background: "radial-gradient(circle at 50% 0%, hsl(189 94% 48% / 0.15), transparent 70%)",
          }}
        />
      )}

      {/* Content */}
      <span className="relative z-10 flex items-center gap-2">
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : icon ? (
          icon
        ) : variant === "primary" ? (
          <Sparkles className="w-4 h-4" />
        ) : null}
        {children}
      </span>
    </motion.button>
  );
}
```

### 7.3 参数面板 (CosmicParamPanel)

```tsx
"use client";

import { motion } from "framer-motion";
import { SlidersHorizontal, ChevronDown, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { ReactNode, useState } from "react";

interface ParamGroup {
  id: string;
  label: string;
  tooltip?: string;
  children: ReactNode;
  collapsed?: boolean;
}

interface CosmicParamPanelProps {
  groups: ParamGroup[];
  className?: string;
}

export function CosmicParamPanel({ groups, className }: CosmicParamPanelProps) {
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
    new Set(groups.filter((g) => g.collapsed).map((g) => g.id))
  );

  const toggleGroup = (id: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "w-72 flex-shrink-0",
        // Glass panel
        "bg-cosmic-surface/50 backdrop-blur-2xl backdrop-saturate-150",
        "border border-cosmic-border/60",
        "rounded-2xl",
        "shadow-elevation-md",
        "overflow-hidden",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-5 py-4 border-b border-cosmic-border/40">
        <SlidersHorizontal className="w-4 h-4 text-accent-cyan" />
        <span className="text-body-sm font-semibold text-text-primary">参数设置</span>
      </div>

      {/* Param groups */}
      <div className="divide-y divide-cosmic-border/30">
        {groups.map((group) => {
          const isCollapsed = collapsedGroups.has(group.id);
          return (
            <div key={group.id} className="px-5 py-4">
              {/* Group header */}
              <button
                onClick={() => toggleGroup(group.id)}
                className="flex items-center justify-between w-full mb-3 group"
              >
                <div className="flex items-center gap-1.5">
                  <span className="text-caption font-medium text-text-secondary">
                    {group.label}
                  </span>
                  {group.tooltip && (
                    <div className="relative group/tip">
                      <Info className="w-3 h-3 text-text-tertiary" />
                      <div className="absolute left-0 bottom-full mb-1.5 w-48 px-2.5 py-1.5 rounded-lg bg-cosmic-elevated border border-cosmic-border text-caption text-text-secondary opacity-0 invisible group-hover/tip:opacity-100 group-hover/tip:visible transition-all duration-200 pointer-events-none z-50">
                        {group.tooltip}
                      </div>
                    </div>
                  )}
                </div>
                <ChevronDown 
                  className={cn(
                    "w-4 h-4 text-text-tertiary transition-transform duration-200",
                    isCollapsed && "-rotate-90"
                  )} 
                />
              </button>

              {/* Group content */}
              <motion.div
                initial={false}
                animate={{
                  height: isCollapsed ? 0 : "auto",
                  opacity: isCollapsed ? 0 : 1,
                }}
                transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                className="overflow-hidden"
              >
                {group.children}
              </motion.div>
            </div>
          );
        })}
      </div>

      {/* Footer glow */}
      <div className="absolute inset-x-4 bottom-0 h-px bg-gradient-to-r from-transparent via-accent-cyan/20 to-transparent" />
    </motion.div>
  );
}

// ─── Slider sub-component ────────────────────────────────

interface CosmicSliderProps {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  leftLabel?: string;
  rightLabel?: string;
}

export function CosmicSlider({
  label,
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  leftLabel = "精准",
  rightLabel = "狂野",
}: CosmicSliderProps) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-caption text-text-tertiary">{label}</span>
        <span className="text-caption font-mono font-medium text-accent-cyan">{value}</span>
      </div>
      
      <div className="relative">
        {/* Track */}
        <div className="h-1.5 rounded-full bg-cosmic-border/60">
          {/* Filled track with gradient */}
          <div
            className="h-full rounded-full bg-gradient-to-r from-accent-cyan via-accent-blue to-accent-violet transition-all duration-150"
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Thumb */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
        
        {/* Visible thumb */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-[18px] h-[18px] rounded-full bg-white shadow-glow-cyan border-2 border-accent-cyan transition-all duration-150 pointer-events-none"
          style={{ left: `calc(${pct}% - 9px)` }}
        />
      </div>

      <div className="flex justify-between text-[10px] text-text-tertiary">
        <span>{leftLabel}</span>
        <span>{rightLabel}</span>
      </div>
    </div>
  );
}
```

### 7.4 渐变边框卡片 (CosmicGradientCard)

```tsx
"use client";

import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface CosmicGradientCardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  hover?: boolean;
}

export function CosmicGradientCard({
  children,
  className,
  onClick,
  hover = true,
}: CosmicGradientCardProps) {
  return (
    <div
      onClick={onClick}
      className={cn(
        "relative rounded-2xl p-px",
        "bg-gradient-to-br from-accent-cyan/20 via-accent-blue/15 to-accent-violet/20",
        hover && "hover:from-accent-cyan/40 hover:via-accent-blue/30 hover:to-accent-violet/40 transition-all duration-500",
        onClick && "cursor-pointer",
        className
      )}
    >
      {/* Inner card */}
      <div className="relative rounded-[15px] bg-cosmic-surface/70 backdrop-blur-xl p-6 h-full overflow-hidden">
        {/* Inner glow at top */}
        <div className="absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-white/8 to-transparent" />
        
        {/* Children */}
        <div className="relative z-10">{children}</div>

        {/* Bottom subtle gradient */}
        <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-accent-cyan/[0.03] to-transparent pointer-events-none" />
      </div>
    </div>
  );
}
```

---

## 8. 实现清单

### Phase 1: Token 层 (globals.css)
- [ ] 替换所有 HSL 变量为 Cosmic 色板
- [ ] 添加渐变预设变量
- [ ] 添加辉光阴影变量
- [ ] 添加内阴影变量
- [ ] 更新 glass 工具类

### Phase 2: Config 层 (tailwind.config.js)
- [ ] 添加 cosmic 色阶
- [ ] 添加 accent 色阶
- [ ] 添加 elevation/glow/inner shadow 工具类
- [ ] 添加字体层级
- [ ] 添加新动画关键帧

### Phase 3: 组件层
- [ ] Prompt 输入卡 (CosmicPromptCard)
- [ ] 生成按钮 (CosmicGenerateButton)
- [ ] 参数面板 (CosmicParamPanel)
- [ ] 渐变边框卡片 (CosmicGradientCard)
- [ ] 导航栏升级

### Phase 4: 页面层
- [ ] 首页 Hero 重写
- [ ] 创作页输入区替换
- [ ] 画廊卡片升级

---

## 9. 设计检查清单

| 检查项 | 标准 |
|--------|------|
| 色彩对比度 | 正文/背景 ≥ 4.5:1 (WCAG AA) |
| 焦点可见 | 所有可交互元素有 focus-visible ring |
| reduced-motion | @media (prefers-reduced-motion) 禁用动画 |
| 深色主题 | 默认深色 → 此设计系统为深色专属 |
| 触控友好 | 可点击区域 ≥ 44x44px |
| 文字截断 | 长文本使用 truncate/line-clamp |
| 加载状态 | 所有异步操作有 loading 状态 |
