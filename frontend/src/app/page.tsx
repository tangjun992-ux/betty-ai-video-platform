"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
  Wand2,
  Scissors,
  Maximize2,
  Camera,
  Music,
  Layers,
  RefreshCw,
  User,
  Mic,
  Lightbulb,
  Brain,
  Film,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { BrandMark } from "@/components/BrandLogo";
import { API_BASE } from "@/lib/api";
import { useLocale } from "@/i18n/LocaleProvider";

// ─── Hero 演示轮播：由平台真实生成作品驱动（拉取 /gallery/，不用图库图）──
type HeroCard = { prompt: string; model: string; type: "图片" | "视频"; image: string; video?: string };

function resolveMedia(url: string): string {
  if (!url) return url;
  if (url.startsWith("http")) return url;
  const origin = API_BASE.replace(/\/api\/v1$/, "");
  return `${origin}${url}`;
}

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
    icon: Mic,
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

// 仅列平台实测可用（真实跑通）的模型，避免虚标点了就报错
const MODELS = [
  { name: "Seedance 2.0", mono: "S", type: "视频", provider: "ByteDance", badge: "Pro" },
  { name: "GPT Image 2", mono: "G", type: "图片", provider: "OpenAI", badge: "New" },
  { name: "Kling AI Avatar", mono: "K", type: "唇形", provider: "Kuaishou", badge: "Hot" },
  { name: "Nano Banana 2", mono: "N", type: "图片", provider: "Google" },
  { name: "Nano Banana Pro", mono: "P", type: "图片", provider: "Google" },
  { name: "ElevenLabs", mono: "E", type: "配音", provider: "ElevenLabs" },
  { name: "Topaz Upscale", mono: "T", type: "超分", provider: "Topaz" },
  { name: "Recraft", mono: "R", type: "抠图", provider: "Recraft" },
];

// 真实产品事实（非虚构增长数据）— 诚实且经得起推敲
const STATS = [
  { value: "15+", label: "顶级 AI 模型", icon: TrendingUp },
  { value: "4K", label: "超高清输出", icon: Award },
  { value: "秒级", label: "图片生成 · 分钟级出片", icon: Timer },
  { value: "一句话", label: "Agent 自动成片", icon: Bot },
];

const FEATURES = [
  {
    icon: Zap,
    title: "多模型路由",
    desc: "智能分发到最优 AI 模型，确保每次输出都是最佳质量，支持 15+ 主流模型一键切换",
    color: "from-brand to-accent-violet",
  },
  {
    icon: Award,
    title: "专业品质",
    desc: "4K 超高清输出，专业色彩管理，商业授权可用，满足从社交媒体到印刷品的全场景需求",
    color: "from-accent-violet to-accent-purple",
  },
  {
    icon: Timer,
    title: "极速生成",
    desc: "分布式 GPU 集群加速，图片秒级生成，视频分钟级交付，创作流程零等待",
    color: "from-brand-strong to-brand",
  },
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
      { label: "探索作品", href: "/explore" },
      { label: "模型库", href: "/models" },
      { label: "任务中心", href: "/tasks" },
    ],
  },
  {
    title: "公司",
    links: [
      { label: "定价", href: "/pricing" },
      { label: "联系我们", href: "mailto:hello@betty.ai" },
    ],
  },
  {
    title: "法律",
    links: [
      { label: "服务条款", href: "/terms" },
      { label: "隐私政策", href: "/privacy" },
      { label: "内容政策", href: "/content-policy" },
    ],
  },
];

// ─── Badge style map ───────────────────────────────────

const badgeStyles: Record<string, string> = {
  New: "bg-blue-500/10 text-blue-600 border border-blue-500/20",
  Hot: "bg-red-500/10 text-red-600 border border-red-500/20",
  Pro: "bg-violet-500/10 text-violet-600 border border-violet-500/20",
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
      {/* Blur orbs — 品牌紫同源，去蓝紫混色 */}
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-brand/[0.07] rounded-full blur-[120px]" />
      <div className="absolute top-1/3 right-0 w-[500px] h-[500px] bg-accent-violet/[0.05] rounded-full blur-[120px]" />
      <div className="absolute bottom-0 left-1/3 w-[400px] h-[400px] bg-accent-fuchsia/[0.03] rounded-full blur-[100px]" />
    </div>
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

                {/* Icon — 统一品牌单色（去彩虹，对齐 Linear/Vercel 克制美学） */}
                <div className={cn(
                  "w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 mb-4",
                  "bg-brand/[0.06] border border-brand/10 transition-all duration-300",
                  "group-hover:bg-brand/[0.12] group-hover:scale-105"
                )}>
                  <tool.icon className="w-6 h-6 text-brand" />
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
  const spotlight = MODELS.filter(m => ["Seedance 2.0", "GPT Image 2", "Kling AI Avatar"].includes(m.name));
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
          <p className="text-overline text-text-tertiary uppercase tracking-[0.2em] mb-3">
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
                href={
                  m.type === "视频" ? "/create/video"
                  : m.type === "唇形" ? "/create/lipsync"
                  : m.type === "配音" ? "/create/audio"
                  : m.type === "超分" ? "/create/upscale"
                  : m.type === "抠图" ? "/create/bg-remove"
                  : "/create/image"
                }
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
   Real Works Showcase — 平台真实产出瀑布流（替代虚构证言，诚实且更有说服力）
   ═══════════════════════════════════════════════════════ */

function RealWorksSection() {
  const [works, setWorks] = useState<HeroCard[]>([]);
  useEffect(() => {
    let active = true;
    fetch(`${API_BASE}/gallery/?sort=popular&limit=12`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!active || !d) return;
        const items = (Array.isArray(d) ? d : d.items || d.results || []) as any[];
        const cards: HeroCard[] = items.map((it) => ({
          prompt: it.prompt || "",
          model: it.model_used || it.model || "",
          type: it.media_type === "video" ? "视频" : "图片",
          image: resolveMedia(it.thumbnail || it.url),
          video: it.media_type === "video" ? resolveMedia(it.url) : undefined,
        }));
        if (cards.length) setWorks(cards);
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  if (works.length === 0) return null;

  return (
    <section className="px-4 pb-24">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-end justify-between mb-8">
          <div>
            <p className="text-overline text-text-tertiary uppercase tracking-[0.2em] mb-2">SHOWCASE</p>
            <h2 className="text-2xl font-bold text-text-primary mb-1">平台真实作品</h2>
            <p className="text-text-secondary text-sm">全部由 betty 用真实模型生成 · 悬停查看模型与提示词</p>
          </div>
          <Link href="/explore" className="hidden sm:flex items-center gap-1 text-sm text-brand hover:text-brand-strong transition-colors">
            探索全部 <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="columns-2 md:columns-3 lg:columns-4 gap-3 space-y-3">
          {works.map((w, i) => (
            <Link
              key={w.image + i}
              href="/explore"
              className="group relative block rounded-xl overflow-hidden break-inside-avoid ring-1 ring-cosmic-border hover:ring-brand/40 transition-all"
            >
              {w.video ? (
                <video src={w.video} poster={w.image} muted loop playsInline
                  className="w-full object-cover align-middle"
                  onMouseEnter={(e) => (e.currentTarget as HTMLVideoElement).play().catch(() => {})}
                  onMouseLeave={(e) => (e.currentTarget as HTMLVideoElement).pause()} />
              ) : (
                <img src={w.image} alt={w.prompt} loading="lazy"
                  className="w-full object-cover align-middle group-hover:scale-[1.03] transition-transform duration-500" />
              )}
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-t from-black/80 via-transparent to-transparent flex flex-col justify-end p-3">
                <p className="text-[11px] text-white/95 line-clamp-2 mb-1">{w.prompt}</p>
                {w.model && <span className="self-start text-[10px] text-white/80 px-1.5 py-0.5 rounded-full bg-white/15 backdrop-blur-sm">{w.model}</span>}
              </div>
            </Link>
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
  const router = useRouter();
  const { t } = useLocale();
  const [heroInput, setHeroInput] = useState("");
  const [heroMode, setHeroMode] = useState<"agent" | "image" | "video">("agent");
  const [demoVideoIdx, setDemoVideoIdx] = useState(0);
  const heroGo = (override?: "agent" | "image" | "video") => {
    const m = override || heroMode;
    const path = m === "agent" ? "/agent" : m === "video" ? "/create/video" : "/create/image";
    const key = m === "agent" ? "brief" : "prompt";
    router.push(heroInput.trim() ? `${path}?${key}=${encodeURIComponent(heroInput)}` : path);
  };

  // Real generated works power the hero showcase (fetched from the gallery).
  const [demoCards, setDemoCards] = useState<HeroCard[]>([]);
  useEffect(() => {
    let active = true;
    fetch(`${API_BASE}/gallery/?sort=popular&limit=5`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!active || !d) return;
        const items = (Array.isArray(d) ? d : d.items || d.results || []) as any[];
        const cards: HeroCard[] = items.slice(0, 5).map((it) => ({
          prompt: it.prompt || "AI 生成作品",
          model: it.model_used || it.model || "",
          type: it.media_type === "video" ? "视频" : "图片",
          image: resolveMedia(it.thumbnail || it.url),
          video: it.media_type === "video" ? resolveMedia(it.url) : undefined,
        }));
        if (cards.length) setDemoCards(cards);
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  // Auto-advance demo carousel
  useEffect(() => {
    if (demoCards.length < 2) return;
    const timer = setInterval(
      () => setDemoVideoIdx((i) => (i + 1) % demoCards.length),
      4000
    );
    return () => clearInterval(timer);
  }, [demoCards.length]);

  return (
    <div className="min-h-[calc(100vh-4rem)]">
      {/* ─── Announcement Banner ─── */}
      <div className="relative bg-gradient-to-r from-accent-cyan/15 via-accent-blue/10 to-accent-violet/15 py-2.5 border-b border-accent-cyan/10 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_hsl(var(--accent-cyan)/0.08),transparent_70%)]" />
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
                <span className="font-medium tracking-wide">{t("home.badge")}</span>
              </div>

              {/* Title */}
              <h1 className="text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-semibold tracking-[-0.035em] leading-[1.08] mb-5">
                {t("home.title1")}
                <br className="hidden sm:block" />
                <span className="text-gradient">{t("home.title2")}</span>
              </h1>

              {/* Subtitle */}
              <p className="text-lg md:text-xl text-text-secondary max-w-lg mb-8 leading-relaxed">
                {t("home.subtitle")}
              </p>

              {/* Mode tabs */}
              <div className="inline-flex items-center gap-1 p-1 rounded-xl bg-cosmic-surface/50 border border-cosmic-border/50 mb-3 self-start">
                {([
                  { key: "agent", label: t("home.agent"), icon: Bot },
                  { key: "image", label: t("home.image"), icon: ImageIcon },
                  { key: "video", label: t("home.video"), icon: Video },
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

              {/* Unified multimodal canvas input (multi-line, 旗舰级) */}
              <div className="input-canvas mb-4">
                <textarea
                  value={heroInput}
                  onChange={(e) => setHeroInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); heroGo(); }
                  }}
                  rows={3}
                  placeholder={
                    heroMode === "agent"
                      ? t("home.placeholderAgent")
                      : heroMode === "video"
                      ? t("home.placeholderVideo")
                      : t("home.placeholderImage")
                  }
                />
                <div className="flex items-center justify-between px-3 pb-3 pt-1">
                  <div className="flex items-center gap-1.5">
                    <Link href="/create/image" className="btn-icon" title="添加参考媒体">
                      <ImageIcon className="w-[18px] h-[18px]" />
                    </Link>
                    <span className="hidden sm:inline text-[11px] text-text-tertiary select-none">
                      <kbd className="font-sans">⏎</kbd> 发送 · <kbd className="font-sans">⇧⏎</kbd> 换行
                    </span>
                  </div>
                  <button onClick={() => heroGo()} className="btn-primary h-10 px-5">
                    <Sparkles className="w-4 h-4" />
                    {heroMode === "agent" ? t("home.startDirect") : t("home.startCreate")}
                  </button>
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
                  { href: "/explore", icon: Sparkles, label: "探索" },
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

                {/* Demo content — real-work carousel (platform-generated) */}
                <div className="p-4 space-y-3">
                  {demoCards.length === 0 ? (
                    <>
                      <div className="h-8 rounded-lg skeleton" />
                      <div className="aspect-[16/10] rounded-xl skeleton" />
                      <div className="flex gap-2">{[0,1,2,3,4].map((i) => <div key={i} className="flex-1 aspect-[4/3] rounded-lg skeleton" />)}</div>
                    </>
                  ) : (() => {
                    const active = demoCards[demoVideoIdx] || demoCards[0];
                    return (
                  <>
                  {/* Prompt bar (the active prompt being generated) */}
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-brand/[0.06] border border-brand/10">
                    <div className="w-1.5 h-1.5 rounded-full bg-brand animate-glow-pulse flex-shrink-0" />
                    <AnimatePresence mode="wait">
                      <motion.span
                        key={active.prompt}
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -4 }}
                        transition={{ duration: 0.3 }}
                        className="text-caption text-brand font-medium truncate"
                      >
                        {active.prompt}
                      </motion.span>
                    </AnimatePresence>
                  </div>

                  {/* Main preview — cross-fading real image / video */}
                  <div className="relative aspect-[16/10] rounded-xl overflow-hidden bg-cosmic-subtle/50 border border-cosmic-border/40">
                    <AnimatePresence mode="popLayout">
                      {active.video ? (
                        <motion.video
                          key={active.video}
                          src={active.video}
                          poster={active.image}
                          muted loop playsInline autoPlay
                          initial={{ opacity: 0, scale: 1.06 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 1.02 }}
                          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                          className="absolute inset-0 w-full h-full object-cover"
                        />
                      ) : (
                        <motion.img
                          key={active.image}
                          src={active.image}
                          alt={active.prompt}
                          loading="eager"
                          initial={{ opacity: 0, scale: 1.06 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 1.02 }}
                          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                          className="absolute inset-0 w-full h-full object-cover"
                        />
                      )}
                    </AnimatePresence>

                    {/* Bottom scrim + meta */}
                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 via-black/25 to-transparent p-3 flex items-end justify-between gap-2">
                      <div className="flex items-center gap-1.5 min-w-0">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                        <span className="text-[11px] font-medium text-white/90 truncate">
                          平台真实生成
                        </span>
                      </div>
                      {active.model && (
                        <span className="flex-shrink-0 text-[10px] font-semibold text-white/95 px-2 py-0.5 rounded-full bg-white/15 backdrop-blur-sm border border-white/20">
                          {active.model}
                        </span>
                      )}
                    </div>

                    {/* Type badge */}
                    <div className="absolute top-2.5 left-2.5 flex items-center gap-1 px-2 py-0.5 rounded-md bg-black/45 backdrop-blur-sm border border-white/10">
                      {active.type === "视频" ? (
                        <Video className="w-3 h-3 text-white/90" />
                      ) : (
                        <ImageIcon className="w-3 h-3 text-white/90" />
                      )}
                      <span className="text-[10px] font-medium text-white/90">
                        {active.type}
                      </span>
                    </div>
                  </div>

                  {/* Thumbnail strip */}
                  <div className="flex items-center gap-2">
                    {demoCards.map((card, i) => (
                      <button
                        key={card.image + i}
                        onClick={() => setDemoVideoIdx(i)}
                        aria-label={card.prompt}
                        className={cn(
                          "relative flex-1 aspect-[4/3] rounded-lg overflow-hidden transition-all duration-300",
                          demoVideoIdx === i
                            ? "ring-2 ring-brand ring-offset-1 ring-offset-cosmic-surface"
                            : "opacity-50 hover:opacity-90"
                        )}
                      >
                        <img
                          src={card.image}
                          alt=""
                          loading="lazy"
                          className="absolute inset-0 w-full h-full object-cover"
                        />
                      </button>
                    ))}
                  </div>
                  </>
                    );
                  })()}
                </div>
              </div>

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
                {[
                  { icon: Lightbulb, label: "描述" },
                  { icon: Brain, label: "规划" },
                  { icon: ImageIcon, label: "生成" },
                  { icon: Video, label: "动画" },
                  { icon: Music, label: "配乐" },
                  { icon: Film, label: "合成" },
                ].map((s) => (
                  <div key={s.label} className="flex items-center gap-1.5 px-2.5 py-2 rounded-lg bg-cosmic-surface border border-cosmic-border text-xs text-text-secondary">
                    <s.icon className="w-3.5 h-3.5 text-brand" />
                    {s.label}
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

      {/* ═══ Real Works Showcase ═══ */}
      <RealWorksSection />

      {/* ═══ CTA ═══ */}
      <CtaSection />

      {/* ═══ Footer ═══ */}
      <Footer />
    </div>
  );
}
