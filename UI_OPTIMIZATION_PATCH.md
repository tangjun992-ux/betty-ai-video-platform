# Betty 首页 UI 优化 - 手动应用补丁

## 📝 修改说明

需要修改 1 个文件: `frontend/src/app/page.tsx`

---

## 🔧 修改 1: 工具数据结构（第 66-140 行）

**找到这段代码（大约在第 66 行）:**

```typescript
const FEATURED_TOOLS = [
  {
    icon: Video,
    label: "视频生成",
    desc: "ByteDance Seedance 2.0 多模态输入，唇形同步，多镜头叙事",
    color: "from-blue-400 to-blue-500",
    href: "/create/video",
    badge: "New",
  },
  // ... 其他工具
];
```

**替换为:**

```typescript
const FEATURED_TOOLS = [
  {
    icon: Video,
    label: "视频生成",
    desc: "Seedance 2.0 多模态输入，唇形同步，多镜头叙事",
    iconColor: "text-blue-600",
    iconBg: "bg-blue-50",
    href: "/create/video",
    badge: "New",
  },
  {
    icon: ImageIcon,
    label: "图片生成",
    desc: "GPT Image 2.0 超高质量文本到图像，专业级输出",
    iconColor: "text-brand-600",
    iconBg: "bg-brand-50",
    href: "/create/image",
    badge: "Hot",
  },
  {
    icon: Maximize2,
    label: "AI 放大",
    desc: "2倍分辨率提升，保持画质不失真",
    iconColor: "text-cyan-600",
    iconBg: "bg-cyan-50",
    href: "/create/image",
  },
  {
    icon: Scissors,
    label: "背景移除",
    desc: "AI 智能去背景，透明输出",
    iconColor: "text-emerald-600",
    iconBg: "bg-emerald-50",
    href: "/create/image",
  },
  {
    icon: User,
    label: "AI 头像",
    desc: "专业商务头像，LinkedIn 简历照",
    iconColor: "text-pink-600",
    iconBg: "bg-pink-50",
    href: "/create/image",
  },
  {
    icon: Bot,
    label: "唇形同步",
    desc: "图片+音频生成说话视频，虚拟主播",
    iconColor: "text-amber-600",
    iconBg: "bg-amber-50",
    href: "/create/lipsync",
    badge: "Pro",
  },
  {
    icon: Camera,
    label: "产品摄影",
    desc: "AI 批量生成产品图，电商专用",
    iconColor: "text-indigo-600",
    iconBg: "bg-indigo-50",
    href: "/create/image",
  },
  {
    icon: RefreshCw,
    label: "运动控制",
    desc: "参考视频精准动作引导生成",
    iconColor: "text-red-600",
    iconBg: "bg-red-50",
    href: "/create/motion",
  },
  {
    icon: Layers,
    label: "时间轴编辑",
    desc: "强大的视频时间轴编辑器",
    iconColor: "text-sky-600",
    iconBg: "bg-sky-50",
    href: "/create/timeline",
  },
  {
    icon: Music,
    label: "音频生成",
    desc: "AI 配乐与音效",
    iconColor: "text-orange-600",
    iconBg: "bg-orange-50",
    href: "/agent",
  },
];
```

**关键变化:**
- 移除所有 `color: "from-xxx to-xxx"` 渐变色
- 添加 `iconColor: "text-xxx-600"` 深色图标
- 添加 `iconBg: "bg-xxx-50"` 浅色背景
- 缩短部分描述文字

---

## 🔧 修改 2: 标题样式（第 397-409 行）

**找到这段代码（在 ToolGrid 函数内）:**

```typescript
<motion.div
  initial={{ opacity: 0, y: 16 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true }}
  className="text-center mb-10"
>
  <h2 className="text-3xl md:text-4xl font-bold text-text-accent-cyan mb-4">
    探索所有工具
  </h2>
  <p className="text-text-secondary max-w-lg mx-auto text-lg">
    使用最先进的 AI 模型，在一个平台完成所有创作
  </p>
</motion.div>
```

**替换为:**

```typescript
<motion.div
  initial={{ opacity: 0, y: 16 }}
  whileInView={{ opacity: 1, y: 0 }}
  viewport={{ once: true }}
  className="text-center mb-12"
>
  <h2 className="text-h2 font-semibold text-text-primary mb-3">
    探索所有工具
  </h2>
  <p className="text-body text-text-secondary max-w-2xl mx-auto">
    使用最先进的 AI 模型，在一个平台完成所有创作
  </p>
</motion.div>
```

**关键变化:**
- `mb-10` → `mb-12` (增加底部间距)
- `text-3xl md:text-4xl font-bold text-text-accent-cyan` → `text-h2 font-semibold text-text-primary`
- `mb-4` → `mb-3`
- `text-lg` → `text-body`
- `max-w-lg` → `max-w-2xl`

---

## 🔧 修改 3: 卡片渲染（第 418-464 行）

**找到这段代码（工具卡片的 map 循环）:**

```typescript
{FEATURED_TOOLS.map((tool) => (
  <motion.div key={tool.label} variants={fadeScaleItem}>
    <Link
      href={tool.href}
      className="gradient-card bg-white/[0.02] flex flex-col gap-3 p-5 h-full group"
    >
      {/* Badge */}
      {tool.badge && (
        <span className={cn("absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-medium", badgeStyles[tool.badge] || badgeStyles.New)}>
          {tool.badge}
        </span>
      )}
      {/* Icon */}
      <div className={cn("w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform duration-300", tool.color)}>
        <tool.icon className="w-5 h-5 text-text-accent-cyan" />
      </div>
      {/* Text */}
      <div className="relative z-10">
        <h3 className="font-semibold text-sm text-text-accent-cyan mb-1">
          {tool.label}
        </h3>
        <p className="text-xs text-text-secondary leading-relaxed line-clamp-2">
          {tool.desc}
        </p>
      </div>
      {/* CTA */}
      <div className="mt-auto pt-2">
        <span className="text-xs text-accent-cyan group-hover:underline inline-flex items-center gap-1 relative z-10">
          开始使用 <ChevronRight className="w-3 h-3" />
        </span>
      </div>
    </Link>
  </motion.div>
))}
```

**替换为:**

```typescript
{FEATURED_TOOLS.map((tool) => (
  <motion.div key={tool.label} variants={fadeScaleItem}>
    <Link
      href={tool.href}
      className="relative block p-5 rounded-xl border border-cosmic-border bg-cosmic-surface hover:border-cosmic-border-hover hover:shadow-card-hover transition-all duration-300 group h-full"
    >
      {/* Badge */}
      {tool.badge && (
        <span className={cn("absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-semibold", badgeStyles[tool.badge] || badgeStyles.New)}>
          {tool.badge}
        </span>
      )}
      
      {/* Icon */}
      <div className={cn(
        "w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 mb-4",
        "border border-cosmic-border/50 transition-all duration-300",
        "group-hover:scale-105 group-hover:shadow-sm",
        tool.iconBg
      )}>
        <tool.icon className={cn("w-6 h-6", tool.iconColor)} />
      </div>
      
      {/* Text */}
      <div className="space-y-1.5 mb-3">
        <h3 className="font-semibold text-sm text-text-primary">
          {tool.label}
        </h3>
        <p className="text-xs text-text-secondary leading-relaxed line-clamp-2">
          {tool.desc}
        </p>
      </div>
      
      {/* CTA */}
      <div className="mt-auto pt-1">
        <span className="text-xs font-medium text-brand-600 group-hover:text-brand-700 inline-flex items-center gap-1 transition-colors">
          开始使用 <ChevronRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
        </span>
      </div>
    </Link>
  </motion.div>
))}
```

**关键变化:**
- 移除 `gradient-card` 类
- 添加 `border border-cosmic-border bg-cosmic-surface`
- 图标容器改用 `tool.iconBg` 浅色背景
- 图标颜色改用 `tool.iconColor`
- 标题颜色改为 `text-text-primary`
- CTA 改为 `text-brand-600`
- 优化 hover 动画

---

## ✅ 完成检查

修改完成后，保存文件并:

1. 启动开发服务器:
```bash
cd frontend
npm run dev
```

2. 访问 http://localhost:3000

3. 检查 "探索所有工具" 部分是否显示:
   - ✅ 白色卡片（非渐变）
   - ✅ 浅色图标背景
   - ✅ 深色图标
   - ✅ 悬停效果正常
