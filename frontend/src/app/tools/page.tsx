"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  Palette, Sparkles, User, Layers, Maximize2, Scissors, Wand2,
  Video, Music, Bot, Camera, Search, Grid3X3, Play, Mic,
  ArrowRight, Zap
} from "lucide-react";
import { Empty } from "@/components/StatusStates";
import { cn } from "@/lib/utils";

// ─── Data ──────────────────────────────────────────────

interface Tool {
  icon: any;
  label: string;
  desc: string;
  href: string;
  color: string;
  badge?: string;
  useCase?: string;
}

// SVG icon for RefreshCw (avoids import naming conflict)
function RefreshCwIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M3 21v-5h5"/>
    </svg>
  );
}

const ALL_TOOLS: Record<string, Tool[]> = {
  image: [
    { icon: Sparkles, label: "图片生成", desc: "GPT Image 2.0 超高质量文本到图像生成", href: "/create/image", color: "from-violet-500 to-purple-600", badge: "Hot", useCase: "创意设计、概念艺术" },
    { icon: Camera, label: "产品摄影", desc: "AI 批量生成产品图，电商专用", href: "/create/image", color: "from-cyan-400 to-cyan-500", useCase: "电商、广告素材" },
    { icon: User, label: "AI 头像", desc: "专业商务头像，多风格可选", href: "/create/image", color: "from-pink-500 to-rose-600", useCase: "LinkedIn、简历" },
    { icon: Palette, label: "图片编辑器", desc: "AI 智能编辑：调色、风格迁移", href: "/create/image", color: "from-violet-500 to-purple-600", useCase: "后期处理" },
    { icon: Maximize2, label: "AI 放大", desc: "2倍/4倍分辨率提升，无损画质", href: "/create/image", color: "from-blue-400 to-indigo-500", useCase: "老照片修复、打印" },
    { icon: Scissors, label: "背景移除", desc: "一键移除背景，透明PNG输出", href: "/create/image", color: "from-emerald-500 to-teal-600", useCase: "抠图、素材制作" },
    { icon: Layers, label: "照片包", desc: "批量生成多角度产品变体", href: "/create/image", color: "from-amber-500 to-orange-600", useCase: "商品多角度展示" },
  ],
  video: [
    { icon: Video, label: "视频生成", desc: "Seedance 2.0 电影级画质，多模态输入", href: "/create/video", color: "from-blue-400 to-blue-500", badge: "New", useCase: "短视频、广告片" },
    { icon: Bot, label: "唇形同步", desc: "AI 语音驱动口型，精准同步", href: "/create/lipsync", color: "from-purple-500 to-pink-500", badge: "Beta", useCase: "虚拟主播、配音" },
    { icon: Video, label: "图转视频", desc: "静态图片转动态视频", href: "/create/video", color: "from-amber-500 to-orange-600", useCase: "老照片动态化" },
    { icon: RefreshCwIcon, label: "运动控制", desc: "参考视频引导动作迁移", href: "/create/motion", color: "from-rose-500 to-red-600", badge: "New", useCase: "舞蹈、动作复制" },
    { icon: Layers, label: "时间轴编辑", desc: "视频片段编排与剪辑", href: "/create/timeline", color: "from-sky-500 to-blue-600", useCase: "视频后期" },
  ],
  audio: [
    { icon: Music, label: "音频生成", desc: "AI 配乐与音效生成", href: "/agent", color: "from-orange-500 to-yellow-600", useCase: "视频配乐、BGM" },
    { icon: Mic, label: "语音合成", desc: "文本转语音，多语言多音色", href: "/agent", color: "from-rose-500 to-red-500", useCase: "配音、有声书" },
  ],
};

const USE_CASES = [
  { icon: Camera, title: "电商卖家", desc: "批量生成产品图，白色背景，统一风格。节省 90% 拍摄成本。", tools: ["产品摄影", "背景移除", "照片包"] },
  { icon: Video, title: "内容创作者", desc: "AI 生成短视频素材，从创意到成片一站式完成。", tools: ["视频生成", "唇形同步", "音频生成"] },
  { icon: Sparkles, title: "设计师", desc: "概念图、风格迁移、超分辨率放大，提升效率。", tools: ["图片生成", "图片编辑器", "AI 放大"] },
  { icon: User, title: "职场人士", desc: "专业头像、LinkedIn 照片，AI 写真一键生成。", tools: ["AI 头像", "背景移除", "图片编辑器"] },
];

// ─── Page ──────────────────────────────────────────────

type Tab = "all" | "image" | "video" | "audio";

export default function ToolsPage() {
  const [tab, setTab] = useState<Tab>("all");
  const [search, setSearch] = useState("");

  const getVisibleTools = (): Tool[] => {
    const tools = tab === "all"
      ? [...ALL_TOOLS.image, ...ALL_TOOLS.video, ...ALL_TOOLS.audio]
      : ALL_TOOLS[tab] || [];
    if (!search.trim()) return tools;
    const q = search.toLowerCase();
    return tools.filter(t =>
      t.label.toLowerCase().includes(q) ||
      t.desc.toLowerCase().includes(q) ||
      (t.useCase && t.useCase.toLowerCase().includes(q))
    );
  };

  const visibleTools = getVisibleTools();

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      {/* ─── Hero ─── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-10"
      >
        <h1 className="text-3xl md:text-4xl font-bold mb-3 gradient-text-static">
          探索所有工具
        </h1>
        <p className="text-text-secondary max-w-lg mx-auto mb-8">
          使用最先进的 AI 模型，在一个平台完成所有创作
        </p>

        {/* Search */}
        <div className="relative max-w-md mx-auto">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索工具..."
            className="input-primary-lg"
          />
        </div>
      </motion.div>

      {/* ─── Tabs ─── */}
      <div className="flex justify-center gap-2 mb-10">
        {([
          { id: "all", label: "全部", icon: Grid3X3 },
          { id: "image", label: "图片", icon: Sparkles },
          { id: "video", label: "视频", icon: Play },
          { id: "audio", label: "音频", icon: Music },
        ] as const).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-all duration-200",
              tab === t.id
                ? "bg-white text-black shadow-md"
                : "bg-white/[0.03] border border-white/[0.06] text-text-secondary hover:text-text-accent-cyan hover:bg-white/[0.06]"
            )}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* ─── Tools Grid ─── */}
      <AnimatePresence mode="wait">
        {visibleTools.length === 0 ? (
          <Empty
            title="未找到匹配工具"
            description={`没有找到与"${search}"相关的工具，试试其他关键词`}
          />
        ) : (
          <motion.div
            key={tab + search}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 mb-16 stagger-children"
          >
            {visibleTools.map((tool) => (
              <Link
                key={tool.label}
                href={tool.href}
                className="gradient-card group relative flex flex-col gap-3 p-5 rounded-2xl bg-white/[0.02] border border-white/[0.06] hover:bg-white/[0.05] hover:border-white/[0.12] transition-all duration-300 h-full"
              >
                {tool.badge && (
                  <span className={cn(
                    "absolute top-3 right-3 px-2 py-0.5 rounded-full text-[10px] font-semibold",
                    tool.badge === "New" ? "bg-info-muted text-info border border-info/20" :
                    tool.badge === "Hot" ? "bg-destructive-muted text-destructive border border-destructive/20" :
                    "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                  )}>
                    {tool.badge}
                  </span>
                )}
                <div className={cn("w-10 h-10 rounded-xl bg-gradient-to-br", tool.color, "flex items-center justify-center group-hover:scale-110 transition-transform duration-300")}>
                  <tool.icon className="w-5 h-5 text-text-accent-cyan" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-sm text-text-accent-cyan mb-1">{tool.label}</h3>
                  <p className="text-xs text-text-secondary leading-relaxed line-clamp-2">{tool.desc}</p>
                  {tool.useCase && (
                    <p className="text-[10px] text-accent-cyan/60 mt-1.5">{tool.useCase}</p>
                  )}
                </div>
                <div className="mt-auto flex items-center gap-1 text-xs text-accent-cyan opacity-0 group-hover:opacity-100 transition-opacity">
                  开始使用 <ArrowRight className="w-3 h-3" />
                </div>
              </Link>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Use Cases ─── */}
      <section className="mb-16">
        <h2 className="text-2xl font-bold text-center mb-8 text-text-accent-cyan">使用场景</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 stagger-children">
          {USE_CASES.map((uc) => (
            <div
              key={uc.title}
              className="surface-interactive p-6"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl bg-accent-cyan/[0.08] flex items-center justify-center flex-shrink-0">
                  <uc.icon className="w-5 h-5 text-accent-cyan" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-text-accent-cyan mb-1">{uc.title}</h3>
                  <p className="text-sm text-text-secondary mb-3">{uc.desc}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {uc.tools.map((t) => (
                      <span key={t} className="badge-primary">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── CTA ─── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="text-center p-10 rounded-3xl bg-gradient-to-br from-accent-cyan/8 to-purple-500/8 border border-white/[0.08]"
      >
        <h2 className="text-2xl font-bold mb-3 text-text-accent-cyan">找不到需要的工具？</h2>
        <p className="text-text-secondary mb-6">用 AI Agent 描述需求，自动调用最优工具完成创作</p>
        <Link href="/agent" className="btn-primary">
          <Zap className="w-5 h-5" />
          试试 AI Agent
        </Link>
      </motion.div>
    </div>
  );
}
