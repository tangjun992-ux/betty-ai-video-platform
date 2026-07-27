"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Sparkles,
  ImageIcon,
  Video,
  Bot,
  ChevronRight,
  Wand2,
  Maximize2,
  Mic,
  Music,
  Clock,
  Scissors,
  Expand,
  AudioLines,
  Lightbulb,
  ArrowUp,
  ImagePlus,
  SlidersHorizontal,
  Check,
} from "lucide-react";
import { BrandMark } from "@/components/BrandLogo";
import { API_BASE } from "@/lib/api";
import { useLocale } from "@/i18n/LocaleProvider";

/* ═══════════════════════════════════════════════════════
   Home — STUDIO v6 (对标 yapper.so/dashboard + dzine.ai)
   单输入工作台: 大标题 → 模式切换 → 可配置画布输入 → 建议词
   → 验证模型墙 → 创作工具矩阵 → 真实作品 → 精简 Footer
   零营销版块堆砌, 零彩虹图标, 零渐变糖果, 哑光高质感
   ═══════════════════════════════════════════════════════ */

// ─── 数据 ──────────────────────────────────────────────

const TOOLS = [
  { icon: Bot, label: "AI Agent", desc: "一句话导演成片", href: "/agent", tag: "核心" },
  { icon: ImageIcon, label: "图片创作", desc: "文生图 / 多参考图", href: "/create/image" },
  { icon: Video, label: "视频创作", desc: "文生 / 图生视频", href: "/create/video" },
  { icon: Mic, label: "唇形同步", desc: "图片+音频说话视频", href: "/create/lipsync" },
  { icon: Music, label: "动作同步", desc: "参考视频动作迁移", href: "/create/motion" },
  { icon: Wand2, label: "图片编辑", desc: "AI 指令修图", href: "/create/image-editor" },
  { icon: Clock, label: "时间线", desc: "片段编排与合成", href: "/create/timeline" },
  { icon: Maximize2, label: "AI 放大", desc: "2x/4x 超分", href: "/create/upscale" },
  { icon: Scissors, label: "去背景", desc: "一键透明 PNG", href: "/create/bg-remove" },
  { icon: Expand, label: "AI 扩图", desc: "智能外扩构图", href: "/create/extend" },
  { icon: AudioLines, label: "AI 音频", desc: "配音与音效", href: "/create/audio" },
];

const MODELS = [
  "Seedance 2.0", "GPT Image 2", "Kling Avatar", "Nano Banana 2",
  "Nano Banana Pro", "ElevenLabs", "Topaz Upscale", "Recraft",
];

const SUGGESTIONS: Record<"agent" | "image" | "video", string[]> = {
  agent: [
    "为我的咖啡品牌拍一支 15 秒广告",
    "把产品图变成城市夜景海报",
    "做一条 30 秒人物访谈风格短片",
    "用赛博朋克风格做品牌开场",
  ],
  image: [
    "赛博朋克城市夜景，霓虹灯光，飞行汽车",
    "产品摄影，香水瓶，极简白色背景",
    "日式庭院，樱花飘落，柔光",
    "专业商务头像，现代办公室背景",
  ],
  video: [
    "一只北极熊在星空下行走，电影感",
    "产品旋转展示，白色背景，平滑运镜",
    "城市日出延时摄影，车流拉丝",
    "人物特写，浅景深，情绪氛围",
  ],
};

const FOOTER_SECTIONS = [
  {
    title: "创作",
    links: [
      { label: "图片创作", href: "/create/image" },
      { label: "视频创作", href: "/create/video" },
      { label: "AI Agent", href: "/agent" },
      { label: "全部工具", href: "/tools" },
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

type WorkCard = { prompt: string; model: string; type: "图片" | "视频"; image: string; video?: string };

function resolveMedia(url: string): string {
  if (!url) return url;
  if (url.startsWith("http")) return url;
  const origin = API_BASE.replace(/\/api\/v1$/, "");
  return `${origin}${url}`;
}

// ─── 真实作品瀑布流 (支持筛选) ──────────────────────────

function RealWorksSection() {
  const [works, setWorks] = useState<WorkCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "图片" | "视频">("all");

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE}/gallery/?sort=popular&limit=16`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!active || !d) return;
        const items = (Array.isArray(d) ? d : d.items || d.results || []) as any[];
        const cards: WorkCard[] = items.map((it) => ({
          prompt: it.prompt || "",
          model: it.model_used || it.model || "",
          type: it.media_type === "video" ? "视频" : "图片",
          image: resolveMedia(it.thumbnail || it.url),
          video: it.media_type === "video" ? resolveMedia(it.url) : undefined,
        }));
        if (cards.length) setWorks(cards);
      })
      .catch(() => {})
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const filtered = filter === "all" ? works : works.filter((w) => w.type === filter);
  if (!loading && works.length === 0) return null;

  return (
    <section className="px-4 pb-24">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-end justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">平台真实作品</h2>
            <p className="text-[13px] text-text-tertiary mt-0.5">全部由 betty 真实模型生成</p>
          </div>
          <Link href="/explore" className="flex items-center gap-1 text-[13px] text-text-secondary hover:text-text-primary transition-colors">
            探索全部 <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="flex items-center gap-2 mb-5">
          {(["all", "图片", "视频"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`chip h-8 px-3 text-xs ${
                filter === f ? "text-text-primary border-cosmic-border-hover bg-cosmic-subtle" : ""
              }`}
            >
              {f === "all" ? "全部" : f}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="columns-2 md:columns-3 lg:columns-4 gap-3 space-y-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="rounded-xl bg-cosmic-subtle/40 break-inside-avoid animate-pulse" style={{ height: `${120 + (i % 4) * 40}px` }} />
            ))}
          </div>
        ) : (
          <div className="columns-2 md:columns-3 lg:columns-4 gap-3 space-y-3">
            {filtered.map((w, i) => (
              <Link
                key={w.image + i}
                href="/explore"
                className="group relative block rounded-xl overflow-hidden break-inside-avoid ring-1 ring-cosmic-border hover:ring-cosmic-border-hover transition-all bg-cosmic-surface"
              >
                {w.video ? (
                  <video src={w.video} poster={w.image} muted loop playsInline
                    className="w-full object-cover align-middle"
                    onMouseEnter={(e) => (e.currentTarget as HTMLVideoElement).play().catch(() => {})}
                    onMouseLeave={(e) => (e.currentTarget as HTMLVideoElement).pause()} />
                ) : (
                  <img src={w.image} alt={w.prompt} loading="lazy"
                    className="w-full object-cover align-middle group-hover:scale-[1.02] transition-transform duration-500" />
                )}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-t from-black/80 via-transparent to-transparent flex flex-col justify-end p-3">
                  <p className="text-[11px] text-white/95 line-clamp-2 mb-1.5">{w.prompt}</p>
                  <div className="flex items-center gap-1.5">
                    {w.model && <span className="text-[10px] text-white/80 px-1.5 py-0.5 rounded-full bg-white/15 backdrop-blur-sm">{w.model}</span>}
                    <span className="text-[10px] text-white/70 px-1.5 py-0.5 rounded-full bg-white/10 backdrop-blur-sm">{w.type}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

// ─── Footer ────────────────────────────────────────────

function Footer() {
  return (
    <footer className="border-t border-cosmic-border px-4 py-12">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-10">
          {FOOTER_SECTIONS.map((section) => (
            <div key={section.title}>
              <h3 className="text-[13px] font-semibold text-text-primary mb-3">
                {section.title}
              </h3>
              <ul className="space-y-2">
                {section.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-[13px] text-text-tertiary hover:text-text-primary transition-colors duration-150"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="flex flex-col md:flex-row items-center justify-between gap-3 pt-8 border-t border-cosmic-border">
          <div className="flex items-center gap-2">
            <BrandMark className="w-5 h-5" />
            <span className="font-semibold text-[13px] text-text-primary">betty</span>
            <span className="text-xs text-text-tertiary ml-1">AI 内容创作平台</span>
          </div>
          <p className="text-xs text-text-tertiary">
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
  const [enhancePrompt, setEnhancePrompt] = useState(true);

  const heroGo = (override?: "agent" | "image" | "video") => {
    const m = override || heroMode;
    const path = m === "agent" ? "/agent" : m === "video" ? "/create/video" : "/create/image";
    const key = m === "agent" ? "brief" : "prompt";
    router.push(heroInput.trim() ? `${path}?${key}=${encodeURIComponent(heroInput)}` : path);
  };

  const modeModel = heroMode === "agent" ? "Director" : heroMode === "video" ? "Seedance 2.0" : "GPT Image 2";

  return (
    <div className="min-h-full relative">
      {/* 顶部品牌氛围光 — 克制, 非糖果 */}
      <div className="absolute inset-x-0 top-0 -z-10 h-[420px] bg-[radial-gradient(ellipse_at_top,_hsl(var(--brand)/0.10),_transparent_62%)] pointer-events-none" />

      {/* ═══ HERO: 居中创作台 ═══ */}
      <section className="relative">
        <div className="max-w-4xl mx-auto px-4 pt-20 md:pt-28 pb-16 flex flex-col items-center text-center">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          >
            <Link
              href="/create/video"
              className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full border border-cosmic-border bg-cosmic-surface/80 backdrop-blur-sm text-xs text-text-secondary hover:border-cosmic-border-hover hover:text-text-primary transition-colors mb-10"
            >
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-60"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-brand"></span>
              </span>
              <span className="font-medium">Seedance 2.0 &amp; Kling 3.0 已上线</span>
              <ChevronRight className="w-3.5 h-3.5 text-text-tertiary" />
            </Link>
          </motion.div>

          {/* Title — 大字号高质感, 无渐变 */}
          <motion.h1
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
            className="text-5xl md:text-6xl font-semibold tracking-[-0.03em] leading-[1.06] text-text-primary mb-5 text-balance"
          >
            {t("home.title1")}
            <span className="text-brand">{t("home.title2")}</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="text-lg md:text-xl text-text-secondary max-w-2xl mb-12 leading-relaxed text-balance"
          >
            {t("home.subtitle")}
          </motion.p>

          {/* 模式切换 — segmented */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="inline-flex items-center gap-0.5 p-1 rounded-xl bg-cosmic-surface border border-cosmic-border mb-5"
          >
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
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-[13px] font-medium transition-colors ${
                    active
                      ? "bg-cosmic-subtle text-text-primary"
                      : "text-text-tertiary hover:text-text-secondary"
                  }`}
                >
                  <m.icon className={`w-4 h-4 ${active ? "text-brand-strong" : ""}`} />
                  {m.label}
                </button>
              );
            })}
          </motion.div>

          {/* 大画布输入 — dzine 式一体化创作区（与图片/视频页同款） */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="rounded-2xl border border-cosmic-border bg-cosmic-surface shadow-elevation-lg overflow-visible w-full text-left"
          >
            {/* 文本区（左上上传图标） */}
            <div className="relative">
              <button
                type="button"
                title="上传参考图"
                onClick={() => heroGo("image")}
                className="absolute left-3 top-3 z-10 w-7 h-7 rounded-lg border border-cosmic-border bg-cosmic-elevated/60 text-text-secondary hover:text-brand-strong hover:border-brand/40 flex items-center justify-center transition-colors"
              >
                <ImagePlus className="w-4 h-4" />
              </button>
              <textarea
                value={heroInput}
                onChange={(e) => setHeroInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); heroGo(); }
                }}
                rows={4}
                placeholder={
                  heroMode === "agent"
                    ? t("home.placeholderAgent")
                    : heroMode === "video"
                    ? t("home.placeholderVideo")
                    : t("home.placeholderImage")
                }
                className="w-full bg-transparent border-none pl-12 pr-4 pt-3 pb-2 text-[15px] leading-relaxed text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-0 resize-none"
              />
            </div>

            {/* 底部工具条：模型 + 优化 + 字数/积分 + 圆形提交（贴合底部浅色条，一体化） */}
            <div className="flex items-center gap-2 px-3 py-2.5 bg-cosmic-subtle/35 rounded-b-2xl">
              <button
                type="button"
                onClick={() => heroGo()}
                className="chip h-8 px-3 text-xs border-brand/25 text-brand-strong hover:border-brand/40"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{modeModel}</span>
                <SlidersHorizontal className="w-3.5 h-3.5 opacity-60" />
              </button>

              <button
                type="button"
                onClick={() => setEnhancePrompt((v) => !v)}
                className={`chip h-8 px-3 text-xs transition-colors ${
                  enhancePrompt
                    ? "text-brand-strong border-brand/30 bg-brand/5"
                    : "text-text-secondary"
                }`}
              >
                {enhancePrompt ? <Check className="w-3.5 h-3.5" /> : <Wand2 className="w-3.5 h-3.5" />}
                提示词优化
              </button>

              <div className="ml-auto flex items-center gap-2.5">
                <span className="hidden sm:inline text-[11px] text-text-tertiary tabular-nums select-none">
                  {heroInput.length}/5000
                </span>
                <span className="hidden sm:inline-flex items-center gap-1 text-[11px] text-text-tertiary select-none">
                  <span className="w-1.5 h-1.5 rounded-full bg-brand" />~20
                </span>
                <button
                  type="button"
                  onClick={() => heroGo()}
                  aria-label={heroMode === "agent" ? t("home.startDirect") : t("home.startCreate")}
                  title={heroMode === "agent" ? t("home.startDirect") : t("home.startCreate")}
                  className="w-9 h-9 rounded-full bg-brand hover:bg-brand-strong text-brand-foreground flex items-center justify-center transition-colors"
                >
                  <ArrowUp className="w-4 h-4" />
                </button>
              </div>
            </div>
          </motion.div>

          {/* 建议词 — yapper 式轮廓药丸, 点击填充 */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.28, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-wrap justify-center gap-2 mt-6 max-w-2xl"
          >
            {SUGGESTIONS[heroMode].map((s) => (
              <button
                key={s}
                onClick={() => setHeroInput(s)}
                className="chip text-[13px]"
              >
                <Lightbulb className="w-3.5 h-3.5 opacity-70" />
                <span>{s}</span>
              </button>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ═══ 模型墙 (POWERED BY, 哑光文字标) ═══ */}
      <section className="px-4 pb-16">
        <div className="max-w-5xl mx-auto border-t border-cosmic-border/60 pt-10">
          <p className="text-center text-[11px] font-medium uppercase tracking-[0.2em] text-text-tertiary mb-6">
            已验证模型
          </p>
          <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-3">
            {MODELS.map((name) => (
              <span
                key={name}
                className="text-sm font-medium text-text-tertiary/80 hover:text-text-secondary transition-colors cursor-default select-none"
              >
                {name}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ 创作工具矩阵 ═══ */}
      <section className="px-4 pb-20">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-end justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-text-primary">创作工具</h2>
              <p className="text-[13px] text-text-tertiary mt-0.5">每个入口都是可用功能</p>
            </div>
            <Link href="/tools" className="flex items-center gap-1 text-[13px] text-text-secondary hover:text-text-primary transition-colors">
              全部工具 <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {TOOLS.map((tool, i) => (
              <motion.div
                key={tool.label}
                initial={{ opacity: 0, y: 10 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: Math.min(i * 0.03, 0.2), duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              >
                <Link
                  href={tool.href}
                  className="group flex items-center gap-3 p-3.5 rounded-xl border border-cosmic-border bg-cosmic-surface hover:border-cosmic-border-hover hover:bg-cosmic-elevated transition-colors duration-150 relative"
                >
                  <span className="icon-tile w-10 h-10 shrink-0">
                    <tool.icon className="w-[18px] h-[18px]" />
                  </span>
                  <div className="min-w-0">
                    <div className="text-[13px] font-semibold text-text-primary truncate">
                      {tool.label}
                    </div>
                    <div className="text-[11px] text-text-tertiary truncate mt-0.5">
                      {tool.desc}
                    </div>
                  </div>
                  {tool.tag && (
                    <span className="absolute top-2.5 right-2.5 text-[10px] font-medium text-brand-strong px-1.5 py-0.5 rounded-full bg-brand/10 border border-brand/20">
                      {tool.tag}
                    </span>
                  )}
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══ 真实作品 ═══ */}
      <RealWorksSection />

      {/* ═══ Footer ═══ */}
      <Footer />
    </div>
  );
}
