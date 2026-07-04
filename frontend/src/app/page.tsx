"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Sparkles,
  ImageIcon,
  Video,
  Bot,
  ArrowRight,
  Zap,
  Award,
  Timer,
  Star,
  TrendingUp,
  Users,
  ChevronRight,
  ExternalLink,
  Wand2,
  Scissors,
  Maximize2,
  Camera,
  Music,
  Layers,
  RefreshCw,
  User,
  Mic,
  Palette,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { BrandMark } from "@/components/BrandLogo";

// ─── Stagger animation preset ──────────────────────────

const staggerContainer = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
};

const fadeUpItem = {
  hidden: { opacity: 0, y: 20 },
  show: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const },
  },
};

const fadeScaleItem = {
  hidden: { opacity: 0, scale: 0.96 },
  show: {
    opacity: 1,
    scale: 1,
    transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] as const },
  },
};

// ─── Data ──────────────────────────────────────────────

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

const MODELS = [
  { name: "Kling 3.0", mono: "K", type: "视频", provider: "Kuaishou", badge: "Hot" },
  { name: "Seedance 2.0", mono: "S", type: "视频", provider: "ByteDance", badge: "Pro" },
  { name: "GPT Image 2", mono: "G", type: "图片", provider: "OpenAI", badge: "New" },
  { name: "Runway Gen-3", mono: "R", type: "视频", provider: "Runway" },
  { name: "Flux 1.1 Pro", mono: "F", type: "图片", provider: "Black Forest" },
  { name: "Pixverse V6", mono: "P", type: "视频", provider: "Pixverse" },
  { name: "Nano Banana", mono: "N", type: "图片", provider: "ByteDance" },
  { name: "Veo 3", mono: "V", type: "视频", provider: "Google" },
];

const STATS = [
  { value: "2.4M+", label: "素材已生成", icon: Sparkles },
  { value: "50K+", label: "活跃创作者", icon: Users },
  { value: "15+", label: "AI 模型", icon: TrendingUp },
  { value: "4.9", label: "用户评分", icon: Star },
];

const FEATURES = [
  {
    icon: Zap,
    title: "多模型路由",
    desc: "智能分发到最优 AI 模型，确保每次输出都是最佳质量，支持 15+ 主流模型一键切换",
    color: "from-amber-400 to-orange-500",
  },
  {
    icon: Award,
    title: "专业品质",
    desc: "4K 超高清输出，专业色彩管理，商业授权可用，满足从社交媒体到印刷品的全场景需求",
    color: "from-violet-400 to-purple-500",
  },
  {
    icon: Timer,
    title: "极速生成",
    desc: "分布式 GPU 集群加速，图片秒级生成，视频分钟级交付，创作流程零等待",
    color: "from-emerald-400 to-teal-500",
  },
];

const TRUSTED_BRANDS = [
  "OpenAI",
  "Stability AI",
  "Meta",
  "ByteDance",
  "Runway",
  "Midjourney",
];

const FOOTER_SECTIONS = [
  {
    title: "产品",
    links: [
      { label: "图片生成", href: "/create/image" },
      { label: "视频生成", href: "/create/video" },
      { label: "AI 放大", href: "/tools" },
      { label: "背景移除", href: "/tools" },
      { label: "AI 头像", href: "/tools" },
      { label: "所有工具", href: "/tools" },
    ],
  },
  {
    title: "资源",
    links: [
      { label: "灵感画廊", href: "/gallery" },
      { label: "使用案例", href: "/tools" },
      { label: "帮助中心", href: "/tools" },
      { label: "API 文档", href: "/models" },
    ],
  },
  {
    title: "公司",
    links: [
      { label: "关于我们", href: "/" },
      { label: "定价", href: "/pricing" },
      { label: "博客", href: "/gallery" },
      { label: "联系我们", href: "mailto:hello@betty.ai" },
    ],
  },
  {
    title: "法律",
    links: [
      { label: "服务条款", href: "#" },
      { label: "隐私政策", href: "#" },
      { label: "Cookie 政策", href: "#" },
    ],
  },
];

// ─── Badge style map ───────────────────────────────────

const badgeStyles: Record<string, string> = {
  New: "bg-blue-500/15 text-blue-400 border border-blue-500/20",
  Hot: "bg-red-500/15 text-red-400 border border-red-500/20",
  Pro: "bg-violet-500/15 text-violet-400 border border-violet-500/20",
};

// ─── Animated Grid Background ──────────────────────────

function GridBg() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Animated grid */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(hsl(var(--primary)/0.5) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--primary)/0.5) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          maskImage:
            "radial-gradient(ellipse 80% 50% at 50% 0%, black 30%, transparent 70%)",
        }}
      />
      {/* Blur orbs */}
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-blue-500/[0.06] rounded-full blur-[120px]" />
      <div className="absolute top-1/3 right-0 w-[500px] h-[500px] bg-violet-500/[0.05] rounded-full blur-[120px]" />
      <div className="absolute bottom-0 left-1/3 w-[400px] h-[400px] bg-accent-cyan/[0.04] rounded-full blur-[100px]" />
    </div>
  );
}

// ─── Brand Trust Bar ───────────────────────────────────

function BrandTrustBar() {
  return (
    <section className="relative px-4 py-12 border-y border-cosmic-border">
      <GridBg />
      <div className="relative max-w-6xl mx-auto text-center">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-text-secondary/40 mb-8">
          受全球创新者信赖
        </p>
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="flex flex-wrap items-center justify-center gap-x-10 gap-y-5"
        >
          {TRUSTED_BRANDS.map((brand) => (
            <motion.span
              key={brand}
              variants={fadeScaleItem}
              className="text-xl md:text-2xl font-bold text-text-tertiary/40 hover:text-text-tertiary/70 transition-colors duration-500 select-none"
            >
              {brand}
            </motion.span>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

// ─── Feature Highlights ────────────────────────────────

function FeatureHighlights() {
  return (
    <section className="relative px-4 py-20 md:py-24">
      <div className="max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-14"
        >
          <h2 className="text-3xl md:text-4xl font-bold text-text-primary mb-4">
            为什么选择我们
          </h2>
          <p className="text-text-secondary max-w-xl mx-auto text-lg">
            一个平台，聚合全球最先进的 AI 能力
          </p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-3 gap-5"
        >
          {FEATURES.map((feature) => (
            <motion.div key={feature.title} variants={fadeUpItem}>
              <div className="glass-card-hover p-8 h-full flex flex-col items-start gap-4 group">
                {/* Icon */}
                <div
                  className={cn(
                    "w-12 h-12 rounded-xl bg-gradient-to-br flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform duration-300",
                    feature.color
                  )}
                >
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                {/* Content */}
                <h3 className="text-lg font-semibold text-text-primary">
                  {feature.title}
                </h3>
                <p className="text-sm text-text-secondary leading-relaxed">
                  {feature.desc}
                </p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

// ─── Stats Section ─────────────────────────────────────

function StatsSection() {
  return (
    <section className="px-4 pb-20">
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        whileInView="show"
        viewport={{ once: true }}
        className="max-w-5xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        {STATS.map((stat, i) => (
          <motion.div
            key={stat.label}
            variants={fadeScaleItem}
            className="surface-interactive text-center p-6"
          >
            <stat.icon className="w-5 h-5 text-accent-cyan mx-auto mb-3" />
            <div className="text-3xl font-bold text-text-primary tracking-tight">
              {stat.value}
            </div>
            <div className="text-xs text-text-secondary mt-2">
              {stat.label}
            </div>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}

// ─── Tool Grid ─────────────────────────────────────────

function ToolGrid() {
  return (
    <section className="px-4 pb-20">
      <div className="max-w-6xl mx-auto">
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

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4"
        >
          {FEATURED_TOOLS.map((tool) => (
            <motion.div key={tool.label} variants={fadeScaleItem}>
              <Link
                href={tool.href}
                className="relative block p-5 rounded-xl border border-cosmic-border bg-cosmic-surface hover:border-cosmic-border-hover hover:shadow-card-hover transition-all duration-300 group h-full"
              >
                {/* Badge */}
                {tool.badge && (
                  <span
                    className={cn(
                      "absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-semibold",
                      badgeStyles[tool.badge] || badgeStyles.New
                    )}
                  >
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
        </motion.div>
      </div>
    </section>
  );
}

// ─── Models Section ────────────────────────────────────

function ModelsSection() {
  const spotlight = MODELS.filter(m => ["Seedance 2.0", "GPT Image 2", "Kling 3.0"].includes(m.name));
  const rest = MODELS.filter(m => !spotlight.includes(m));

  return (
    <section className="px-4 pb-24">
      <div className="max-w-5xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="mb-10"
        >
          <p className="text-overline text-text-tertiary/50 uppercase tracking-[0.2em] mb-3">
            Powered by
          </p>
          <h2 className="text-2xl font-bold text-text-primary mb-2">
            全球顶级 AI 模型矩阵
          </h2>
          <p className="text-body-sm text-text-tertiary">
            持续接入最新模型，创作永不过时
          </p>
        </motion.div>

        {/* ═══ Spotlight: 3 Featured Models ═══ */}
        <div className="grid md:grid-cols-3 gap-4 mb-5">
          {spotlight.map((m, i) => (
            <motion.div
              key={m.name}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="relative group flex flex-col items-start gap-3 p-5 rounded-2xl border border-cosmic-border bg-cosmic-surface overflow-hidden text-left"
            >
              {/* Subtle top gradient accent */}
              <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-brand via-accent-fuchsia to-brand opacity-60" />
              {/* Badge */}
              {m.badge && (
                <span className={cn(
                  "px-1.5 py-0.5 rounded-full text-[9px] font-bold",
                  m.badge === "Hot" && "bg-red-500/15 text-red-500 border border-red-500/20",
                  m.badge === "Pro" && "bg-brand/[0.12] text-brand border border-brand/20",
                  m.badge === "New" && "bg-accent-fuchsia/10 text-accent-fuchsia border border-accent-fuchsia/20",
                )}>
                  {m.badge}
                </span>
              )}
              {/* Monogram */}
              <div className="w-11 h-11 rounded-xl bg-brand/[0.06] border border-brand/10 flex items-center justify-center text-base font-bold text-brand">
                {m.mono}
              </div>
              {/* Name + provider */}
              <div>
                <div className="text-base font-semibold text-text-primary">{m.name}</div>
                <div className="flex items-center gap-1.5 mt-0.5 text-[11px] text-text-tertiary">
                  <span>{m.type}</span><span>·</span><span>{m.provider}</span>
                </div>
              </div>
              {/* CTA */}
              <Link
                href={m.type === "视频" ? "/create/video" : "/create/image"}
                className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-brand hover:text-brand-strong transition-colors"
              >
                开始创作 <span className="text-[10px]">→</span>
              </Link>
            </motion.div>
          ))}
        </div>

        {/* ═══ Remaining models grid ═══ */}
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2"
        >
          {rest.map((m) => (
            <motion.div
              key={m.name}
              variants={fadeScaleItem}
              className="relative group flex flex-col items-center gap-1.5 p-3 rounded-xl border border-cosmic-border/40 bg-cosmic-subtle/50 hover:bg-cosmic-surface hover:border-cosmic-border-hover transition-all duration-200 cursor-default"
            >
              <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-brand/[0.06] border border-brand/10 text-xs font-bold text-brand">{m.mono}</span>
              <span className="text-[11px] font-medium text-text-secondary">{m.name}</span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════
   Testimonials Section — 对标 yapper.so 创作者证言
   ═══════════════════════════════════════════════════════ */

const testimonials = [
  { name: "@创作达人小陈", role: "AI 视频创作者", views: "2700万", followers: "8.9万", quote: "用 betty 的导演 Agent，一句话生成完整视频方案——从构思到出片不到 5 分钟，画面质感电影级别。" },
  { name: "@品牌设计师Luna", role: "独立设计师", views: "1200万", followers: "5.2万", quote: "一站式切换 15+ 顶级模型，不用再在不同平台间导来导去。产品图渲染速度快到不敢信。" },
  { name: "@科技博主阿杰", role: "内容创作者", views: "3500万", followers: "15.6万", quote: "唇形同步和运动控制让我的 AI 数字人频道两周涨粉 6 万，每月收入破 2000 美元。" },
];

function TestimonialsSection() {
  return (
    <section className="px-4 pb-24">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <p className="text-overline text-text-tertiary uppercase tracking-[0.2em] mb-3">CREDIBILITY</p>
          <h2 className="text-2xl font-bold text-text-primary mb-2">创作者信赖</h2>
          <p className="text-text-secondary">全球数万创作者正在用 betty 做出爆款内容</p>
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          {testimonials.map((t, i) => (
            <motion.div
              key={t.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              className="relative flex flex-col gap-4 p-6 rounded-2xl border border-cosmic-border bg-cosmic-surface"
            >
              {/* Avatar + name */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-brand to-accent-fuchsia flex items-center justify-center text-white text-sm font-bold">
                  {t.name.slice(1, 2)}
                </div>
                <div>
                  <div className="text-sm font-semibold text-text-primary">{t.name}</div>
                  <div className="text-xs text-text-tertiary">{t.role}</div>
                </div>
              </div>
              {/* Stats */}
              <div className="flex items-center gap-4 text-xs">
                <span className="flex items-center gap-1 text-text-secondary">
                  <span className="w-2 h-2 rounded-full bg-accent-fuchsia" /> {t.views} 播放
                </span>
                <span className="flex items-center gap-1 text-text-secondary">
                  <span className="w-2 h-2 rounded-full bg-brand" /> {t.followers} 粉丝
                </span>
              </div>
              {/* Quote */}
              <p className="text-sm text-text-secondary leading-relaxed">&ldquo;{t.quote}&rdquo;</p>
              {/* Stars */}
              <div className="flex gap-0.5 text-brand text-sm">★★★★★</div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─── CTA Section ───────────────────────────────────────

function CtaSection() {
  return (
    <section className="px-4 pb-24">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="max-w-2xl mx-auto text-center p-10 md:p-14 rounded-2xl relative overflow-hidden"
        style={{
          background:
            "linear-gradient(135deg, hsl(var(--primary)/0.08), hsl(270 70% 50% / 0.06), hsl(var(--primary)/0.04))",
        }}
      >
        {/* Glow orbs */}
        <div className="absolute -top-20 -right-20 w-60 h-60 bg-accent-cyan/[0.08] rounded-full blur-[80px]" />
        <div className="absolute -bottom-20 -left-20 w-60 h-60 bg-violet-500/10 rounded-full blur-[80px]" />

        <div className="relative z-10">
          <Zap className="w-12 h-12 text-accent-cyan mx-auto mb-5" />
          <h2 className="text-3xl md:text-4xl font-bold mb-3 text-text-primary">
            准备好开始创作了吗？
          </h2>
          <p className="text-text-secondary mb-8 text-lg">
            无需信用卡，免费开始。升级解锁更多 Credits 和高阶功能。
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link href="/create/image" className="btn-primary px-7 py-3.5">
              免费开始
            </Link>
            <Link href="/pricing" className="btn-secondary px-7 py-3.5">
              查看定价
            </Link>
          </div>
        </div>
      </motion.div>
    </section>
  );
}

// ─── Footer ────────────────────────────────────────────

function Footer() {
  return (
    <footer className="border-t border-cosmic-border px-4 py-14">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
          {FOOTER_SECTIONS.map((section) => (
            <div key={section.title}>
              <h3 className="text-sm font-semibold text-text-primary mb-4">
                {section.title}
              </h3>
              <ul className="space-y-2.5">
                {section.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm text-text-secondary hover:text-text-primary transition-colors duration-200"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="flex flex-col md:flex-row items-center justify-between gap-4 pt-8 border-t border-cosmic-border">
          <div className="flex items-center gap-2.5">
            <BrandMark className="w-7 h-7" />
            <span className="font-semibold text-sm text-text-primary">betty</span>
            <span className="text-xs text-text-secondary/60 ml-1">
              AI 内容创作平台
            </span>
          </div>
          <p className="text-xs text-text-secondary/50">
            © 2026 betty. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}

// ═══════════════════════════════════════════════════════
//  HomePage
// ═══════════════════════════════════════════════════════

export default function HomePage() {
  const [heroInput, setHeroInput] = useState("");
  const [heroMode, setHeroMode] = useState<"agent" | "image" | "video">("agent");
  const [demoVideoIdx, setDemoVideoIdx] = useState(0);
  const heroGo = (override?: "agent" | "image" | "video") => {
    const m = override || heroMode;
    const path = m === "agent" ? "/agent" : m === "video" ? "/create/video" : "/create/image";
    const key = m === "agent" ? "brief" : "prompt";
    window.location.href = heroInput.trim() ? `${path}?${key}=${encodeURIComponent(heroInput)}` : path;
  };

  // Rotating demo cards with auto-advance
  const demoCards = [
    { prompt: "赛博朋克城市夜景", color: "from-accent-cyan to-accent-blue" },
    { prompt: "日式庭院·樱花飘落", color: "from-pink-500 to-rose-500" },
    { prompt: "电影级科幻飞船", color: "from-accent-violet to-accent-purple" },
    { prompt: "产品摄影·极简白", color: "from-amber-400 to-orange-500" },
  ];

  return (
    <div className="min-h-[calc(100vh-4rem)]">
      {/* ─── Announcement Banner ─── */}
      <div className="relative bg-gradient-to-r from-accent-cyan/15 via-accent-blue/10 to-accent-violet/15 py-2.5 border-b border-accent-cyan/10 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_hsl(189_94%_48%/0.08),transparent_70%)]" />
        <div className="relative max-w-7xl mx-auto px-4 flex items-center justify-center">
          <Link
            href="/create/video"
            className="flex items-center gap-2 text-body-sm text-text-secondary hover:text-text-primary transition-colors group"
          >
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-accent-cyan/15 border border-accent-cyan/20 text-caption font-semibold text-accent-cyan">
              <Sparkles className="w-3 h-3" /> NEW
            </span>
            <span>
              Seedance 2.0 &amp; Kling 3.0 现已上线！立即体验
              <ArrowRight className="w-3.5 h-3.5 inline ml-1 -mt-0.5 group-hover:translate-x-0.5 transition-transform" />
            </span>
          </Link>
        </div>
      </div>

      {/* ═══ HERO: Left-Right Split ═══ */}
      <section className="relative overflow-hidden">
        <GridBg />

        <div className="relative max-w-7xl mx-auto px-4 pt-20 pb-16 md:pt-28 md:pb-24">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">

            {/* ── LEFT: Text + Input + CTAs ── */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="flex flex-col"
            >
              {/* Badge */}
              <div className="inline-flex items-center gap-2 self-start px-3 py-1.5 rounded-full bg-accent-cyan/[0.06] border border-accent-cyan/15 text-caption text-accent-cyan mb-6">
                <Sparkles className="w-3 h-3" />
                <span className="font-medium tracking-wide">全球 15+ 顶级 AI 模型 · 一站式专业创作平台</span>
              </div>

              {/* Title */}
              <h1 className="text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-semibold tracking-[-0.035em] leading-[1.04] mb-5">
                Make something{" "}
                <br className="hidden sm:block" />
                <span className="text-gradient">special</span>
              </h1>

              {/* Subtitle */}
              <p className="text-lg md:text-xl text-text-secondary max-w-lg mb-8 leading-relaxed">
                对接 Veo 3.1 · Sora 2 · Kling · Seedance 等顶级模型；只做导演，不写提示词 — 一句话描述，AI 自动规划→生成→精修
              </p>

              {/* Mode tabs */}
              <div className="inline-flex items-center gap-1 p-1 rounded-xl bg-cosmic-surface/50 border border-cosmic-border/50 mb-3 self-start">
                {([
                  { key: "agent", label: "Agent", icon: Bot },
                  { key: "image", label: "图片", icon: ImageIcon },
                  { key: "video", label: "视频", icon: Video },
                ] as const).map((m) => {
                  const active = heroMode === m.key;
                  return (
                    <button
                      key={m.key}
                      onClick={() => setHeroMode(m.key)}
                      className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-body-sm font-medium transition-all ${
                        active ? "bg-accent-cyan/15 text-accent-cyan" : "text-text-tertiary hover:text-text-secondary"
                      }`}
                    >
                      <m.icon className="w-4 h-4" />{m.label}
                    </button>
                  );
                })}
              </div>

              {/* Unified multimodal input */}
              <div className="relative mb-4">
                <div className="relative rounded-2xl bg-cosmic-surface/50 backdrop-blur-xl border border-cosmic-border/50 shadow-elevation-sm transition-all duration-300 hover:border-accent-cyan/20 focus-within:border-accent-cyan/30 focus-within:shadow-glow-subtle">
                  <input
                    type="text"
                    value={heroInput}
                    onChange={(e) => setHeroInput(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") heroGo(); }}
                    placeholder={
                      heroMode === "agent"
                        ? "一句话说出想要的，Agent 自动规划并生成..."
                        : heroMode === "video"
                        ? "描述你想要的视频画面与运镜..."
                        : "描述你想要创作的图像..."
                    }
                    className="w-full h-14 pl-5 pr-28 bg-transparent text-body text-text-primary placeholder:text-text-tertiary focus:outline-none rounded-2xl"
                  />
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                    <Link href="/create/image" className="p-2 rounded-lg text-text-tertiary hover:text-accent-cyan hover:bg-cosmic-subtle transition-colors" title="添加参考媒体">
                      <ImageIcon className="w-5 h-5" />
                    </Link>
                    <button
                      onClick={() => heroGo()}
                      className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-r from-accent-cyan via-accent-blue to-accent-violet text-white shadow-button-glow hover:brightness-110 active:scale-[0.97] transition-all"
                    >
                      <Sparkles className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>

              {/* 4 Quick actions (对标 yapper) */}
              <div className="flex flex-wrap gap-2 mb-8">
                {[
                  { label: "帮我构思", icon: Bot, go: () => heroGo("agent") },
                  { label: "创作内容", icon: Sparkles, go: () => heroGo() },
                  { label: "优化提示词", icon: Wand2, go: () => heroGo("agent") },
                  { label: "生成视频", icon: Video, go: () => heroGo("video") },
                ].map((a) => (
                  <button
                    key={a.label}
                    onClick={a.go}
                    className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-cosmic-surface/40 border border-cosmic-border/40 text-body-sm text-text-secondary hover:text-accent-cyan hover:border-accent-cyan/30 transition-all"
                  >
                    <a.icon className="w-4 h-4" /><span>{a.label}</span>
                  </button>
                ))}
              </div>

              {/* Quick links */}
              <div className="flex flex-wrap gap-3">
                {[
                  { href: "/agent", icon: Bot, label: "AI Agent" },
                  { href: "/gallery", icon: Sparkles, label: "灵感画廊" },
                  { href: "/tools", icon: Wand2, label: "所有工具" },
                  { href: "/pricing", icon: Zap, label: "定价" },
                ].map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-caption text-text-tertiary hover:text-text-secondary hover:bg-cosmic-subtle transition-all duration-200"
                  >
                    <item.icon className="w-3.5 h-3.5" />
                    <span>{item.label}</span>
                  </Link>
                ))}
              </div>
            </motion.div>

            {/* ── RIGHT: Dynamic Demo Area ── */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
              className="relative hidden lg:block"
            >
              {/* Glow orbs behind the demo area */}
              <div className="absolute -inset-20 bg-glow-cyan opacity-40" />
              <div className="absolute top-1/2 -right-10 w-80 h-80 bg-accent-violet/5 rounded-full blur-[100px]" />

              {/* Main demo frame */}
              <div className="relative rounded-2xl overflow-hidden border border-cosmic-border/60 bg-cosmic-surface/40 backdrop-blur-2xl shadow-elevation-xl">
                {/* Fake browser chrome */}
                <div className="flex items-center gap-1.5 px-4 py-3 border-b border-cosmic-border/40 bg-cosmic-surface/60">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500/60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/60" />
                  <span className="ml-3 text-[10px] text-text-tertiary/50 font-mono">
                    betty.ai/create
                  </span>
                </div>

                {/* Demo content — rotating cards */}
                <div className="p-4 space-y-3 min-h-[320px] relative overflow-hidden">
                  {/* Generating indicator */}
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-accent-cyan/[0.06] border border-accent-cyan/10">
                    <div className="w-1.5 h-1.5 rounded-full bg-accent-cyan animate-glow-pulse" />
                    <span className="text-caption text-accent-cyan font-medium">
                      AI 生成中...
                    </span>
                  </div>

                  {/* Floating demo cards */}
                  {demoCards.map((card, i) => (
                    <motion.div
                      key={card.prompt}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{
                        opacity: demoVideoIdx === i ? 1 : 0.4,
                        y: 0,
                        scale: demoVideoIdx === i ? 1 : 0.97,
                      }}
                      transition={{ duration: 0.5 }}
                      onClick={() => setDemoVideoIdx(i)}
                      className={cn(
                        "relative rounded-xl overflow-hidden cursor-pointer transition-all duration-300",
                        "border",
                        demoVideoIdx === i
                          ? "border-accent-cyan/30 shadow-glow-subtle"
                          : "border-cosmic-border/40 hover:border-cosmic-border-hover"
                      )}
                    >
                      {/* Gradient placeholder image */}
                      <div
                        className={cn(
                          "h-20 bg-gradient-to-br flex items-end p-3",
                          card.color
                        )}
                      >
                        <div className="flex items-center gap-2">
                          {demoVideoIdx === i && (
                            <div className="flex items-center gap-1">
                              <div className="w-1 h-1 rounded-full bg-white animate-pulse" />
                              <div className="w-1 h-1 rounded-full bg-white animate-pulse" style={{ animationDelay: "0.2s" }} />
                              <div className="w-1 h-1 rounded-full bg-white animate-pulse" style={{ animationDelay: "0.4s" }} />
                            </div>
                          )}
                          <span className="text-caption font-medium text-white/90">
                            {card.prompt}
                          </span>
                        </div>
                      </div>
                    </motion.div>
                  ))}

                  {/* Auto-rotate */}
                  <motion.div
                    className="absolute bottom-4 right-4 flex gap-1"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 2 }}
                  >
                    {demoCards.map((_, i) => (
                      <button
                        key={i}
                        onClick={() => setDemoVideoIdx(i)}
                        className={cn(
                          "w-1.5 h-1.5 rounded-full transition-all duration-300",
                          demoVideoIdx === i
                            ? "bg-accent-cyan w-4"
                            : "bg-text-tertiary/30 hover:bg-text-tertiary/50"
                        )}
                      />
                    ))}
                  </motion.div>
                </div>
              </div>

              {/* Floating stat badges */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 }}
                className="absolute -bottom-3 -left-3 px-3 py-1.5 rounded-xl bg-cosmic-elevated/90 backdrop-blur-xl border border-cosmic-border/60 shadow-elevation-md flex items-center gap-2"
              >
                <div className="w-6 h-6 rounded-lg bg-accent-cyan/15 flex items-center justify-center">
                  <Sparkles className="w-3 h-3 text-accent-cyan" />
                </div>
                <div>
                  <div className="text-body-sm font-semibold text-text-primary">2.4M+</div>
                  <div className="text-[10px] text-text-tertiary">素材已生成</div>
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.0 }}
                className="absolute -top-3 -right-3 px-3 py-1.5 rounded-xl bg-cosmic-elevated/90 backdrop-blur-xl border border-cosmic-border/60 shadow-elevation-md flex items-center gap-2"
              >
                <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                <span className="text-body-sm font-semibold text-text-primary">4.9</span>
                <span className="text-[10px] text-text-tertiary">用户评分</span>
              </motion.div>
            </motion.div>
          </div>
        </div>

      </section>

      {/* ═══ HOT TEMPLATES: Horizontal Scroll Cards ═══ */}
      <section className="relative px-4 pb-16">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="flex items-center justify-between mb-6"
          >
            <div>
              <h2 className="text-2xl font-bold text-text-primary mb-1">
                热门创作模板
              </h2>
              <p className="text-body-sm text-text-tertiary">
                一键使用，即刻创作
              </p>
            </div>
            <Link
              href="/tools"
              className="flex items-center gap-1 text-body-sm text-accent-cyan hover:text-accent-blue transition-colors"
            >
              查看全部 <ChevronRight className="w-4 h-4" />
            </Link>
          </motion.div>

          <div className="flex gap-4 overflow-x-auto scrollbar-hide pb-2 -mx-4 px-4">
            {[
              { label: "电影级科幻", icon: "🎬", prompt: "电影级科幻城市，赛博朋克风格", type: "视频" },
              { label: "产品展示", icon: "📦", prompt: "产品360°旋转展示，极简背景", type: "视频" },
              { label: "AI 写真", icon: "📸", prompt: "专业商务头像，自然光线", type: "图片" },
              { label: "自然风光", icon: "🏔️", prompt: "4K 航拍自然风光延时", type: "视频" },
              { label: "动漫风格", icon: "🎨", prompt: "日式动漫风格角色创作", type: "图片" },
              { label: "电商摄影", icon: "🛍️", prompt: "电商产品白底摄影", type: "图片" },
              { label: "唇形同步", icon: "🎤", prompt: "虚拟主播说话视频", type: "视频" },
              { label: "延时摄影", icon: "⏱️", prompt: "城市天际线日出日落延时", type: "视频" },
            ].map((tpl, i) => (
              <motion.div
                key={tpl.label}
                initial={{ opacity: 0, x: 16 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
              >
                <Link
                  href={`/create/${tpl.type === "视频" ? "video" : "image"}?prompt=${encodeURIComponent(tpl.prompt)}`}
                  className="flex-shrink-0 w-[200px] rounded-2xl overflow-hidden border border-cosmic-border/40 bg-cosmic-surface/30 hover:border-accent-cyan/20 hover:shadow-glow-subtle transition-all duration-300 group block"
                >
                  {/* Thumbnail */}
                  <div className="h-28 bg-gradient-to-br from-cosmic-surface to-cosmic-elevated flex items-center justify-center relative overflow-hidden">
                    <span className="text-4xl group-hover:scale-110 transition-transform duration-300">
                      {tpl.icon}
                    </span>
                    <div className="absolute inset-0 bg-gradient-to-t from-cosmic-surface/80 to-transparent" />
                  </div>
                  {/* Info */}
                  <div className="p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-body-sm font-semibold text-text-primary">
                        {tpl.label}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-accent-cyan/10 text-accent-cyan font-medium">
                        {tpl.type}
                      </span>
                    </div>
                    <p className="text-caption text-text-tertiary line-clamp-2 leading-relaxed">
                      {tpl.prompt}
                    </p>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ Brand Trust Bar ═══ */}
      <BrandTrustBar />

      {/* ═══ Feature Highlights ═══ */}
      <FeatureHighlights />

      {/* ═══ Stats ═══ */}
      <StatsSection />

      {/* ═══ Agent Showcase — 对标 yapper "Don't Prompt, Just Direct" ═══ */}
      <section className="px-4 pb-16">
        <div className="max-w-4xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="relative overflow-hidden rounded-2xl border border-brand/20 bg-gradient-to-br from-brand/[0.06] via-cosmic-surface to-accent-fuchsia/[0.04] p-8 md:p-12"
          >
            <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-brand/[0.08] to-transparent rounded-full blur-3xl pointer-events-none" />
            <div className="relative flex flex-col md:flex-row items-start gap-8">
              <div className="flex-1">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-brand/[0.08] border border-brand/20 text-[11px] font-semibold text-brand mb-4">
                  <Sparkles className="w-3 h-3" /> AI Agent
                </span>
                <h3 className="text-2xl md:text-3xl font-bold text-text-primary mb-3">
                  Don&apos;t Prompt, <span className="text-brand">Just Direct</span>
                </h3>
                <p className="text-text-secondary max-w-md mb-5">
                  像导演一样工作。描述创意意图，AI Agent 自动规划全流程 — 从解析创意、智能选模型、生成视觉、动态视频、配乐到合成，一步到位。
                </p>
                <Link
                  href="/agent"
                  className="inline-flex items-center gap-2 h-10 px-5 rounded-xl bg-brand text-white text-sm font-semibold shadow-button-glow hover:bg-brand-strong hover:-translate-y-px transition-all"
                >
                  试试导演模式 <span>→</span>
                </Link>
              </div>
              {/* Visual flow — 6-step mini cards */}
              <div className="flex-shrink-0 grid grid-cols-3 gap-2">
                {["💡 描述", "🧠 规划", "🖼️ 生成", "🎥 动画", "🎵 配乐", "🎬 合成"].map((s) => (
                  <div key={s} className="flex items-center gap-1.5 px-2.5 py-2 rounded-lg bg-cosmic-surface border border-cosmic-border text-xs text-text-secondary">
                    {s}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ═══ Tool Grid ═══ */}
      <ToolGrid />

      {/* ═══ Models ═══ */}
      <ModelsSection />

      {/* ═══ Testimonials ═══ */}
      <TestimonialsSection />

      {/* ═══ CTA ═══ */}
      <CtaSection />

      {/* ═══ Footer ═══ */}
      <Footer />
    </div>
  );
}
