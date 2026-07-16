"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  Palette, Sparkles, User, Layers, Maximize2, Scissors, Wand2,
  Video, Music, Bot, Camera, Search, Grid3X3, Play, Mic,
  ArrowRight, Move, Clapperboard, FileSearch
} from "lucide-react";
import { Empty } from "@/components/StatusStates";
import { cn } from "@/lib/utils";

/** Yapper-aligned tool matrix — every href is a real create/agent route. */

interface Tool {
  icon: any;
  label: string;
  desc: string;
  href: string;
  color: string;
  badge?: string;
  useCase?: string;
  group: "image" | "video" | "audio" | "utility" | "agent";
}

const ALL_TOOLS: Tool[] = [
  // Agent
  { icon: Bot, label: "Yapper-style Agent", desc: "Don't prompt, just direct — 规划/分镜/生成一站式", href: "/agent", color: "from-blue-400 to-indigo-500", badge: "Core", useCase: "广告、短剧、UGC", group: "agent" },
  // Video (Yapper video apps)
  { icon: Video, label: "视频生成", desc: "文生/图生视频，多镜头叙事", href: "/create/video", color: "from-blue-400 to-blue-500", badge: "Hot", useCase: "短视频、广告", group: "video" },
  { icon: Mic, label: "唇形同步", desc: "Studio Lip-Syncing — 图+文/音频说话视频", href: "/create/lipsync", color: "from-purple-500 to-pink-500", badge: "Core", useCase: "虚拟主播、口播", group: "video" },
  { icon: User, label: "Talking Avatar", desc: "头像说话视频（图+音频优先）", href: "/create/avatar", color: "from-fuchsia-500 to-pink-600", useCase: "数字人、克隆", group: "video" },
  { icon: Move, label: "运动控制", desc: "参考视频动作迁移（best-effort）", href: "/create/motion", color: "from-rose-500 to-red-600", badge: "Beta", useCase: "舞蹈、动作复制", group: "video" },
  { icon: Clapperboard, label: "时间轴编辑", desc: "片段编排、字幕与合成", href: "/create/timeline", color: "from-sky-500 to-blue-600", useCase: "后期成片", group: "video" },
  // Image
  { icon: Sparkles, label: "图片生成", desc: "多模型文生图 / 多参考图 i2i", href: "/create/image", color: "from-violet-500 to-purple-600", badge: "Hot", useCase: "创意、产品图", group: "image" },
  { icon: Palette, label: "图片编辑", desc: "AI 指令编辑", href: "/create/image-editor", color: "from-violet-500 to-purple-600", useCase: "后期处理", group: "image" },
  { icon: Maximize2, label: "AI 放大", desc: "2x/4x 超分", href: "/create/upscale", color: "from-blue-400 to-indigo-500", useCase: "打印、修复", group: "image" },
  { icon: Scissors, label: "背景移除", desc: "一键抠图透明 PNG", href: "/create/bg-remove", color: "from-emerald-500 to-teal-600", useCase: "电商素材", group: "image" },
  { icon: Layers, label: "扩图", desc: "智能外扩构图", href: "/create/extend", color: "from-amber-500 to-orange-600", useCase: "改构图", group: "image" },
  { icon: Camera, label: "产品摄影", desc: "电商产品图工作流（进图片生成）", href: "/create/image", color: "from-cyan-400 to-cyan-500", useCase: "电商", group: "image" },
  // Audio / Utility
  { icon: Music, label: "语音合成", desc: "Generate Audio — TTS 配音", href: "/create/audio", color: "from-orange-500 to-yellow-600", useCase: "配音、口播", group: "audio" },
  { icon: FileSearch, label: "Prompt Extractor", desc: "从图片/视频反推提示词", href: "/create/extract", color: "from-teal-400 to-emerald-500", badge: "New", useCase: "复用爆款构图", group: "utility" },
];

const USE_CASES = [
  { icon: Camera, title: "电商卖家", desc: "产品图、抠图、扩图一站完成。", tools: ["产品摄影", "背景移除", "扩图"] },
  { icon: Video, title: "内容创作者", desc: "视频 + 唇形 + 头像 + 时间轴成片。", tools: ["视频生成", "唇形同步", "Talking Avatar"] },
  { icon: Sparkles, title: "广告团队", desc: "Agent 导演式多镜叙事 + 运动迁移。", tools: ["Yapper-style Agent", "运动控制", "时间轴编辑"] },
  { icon: FileSearch, title: "灵感复用", desc: "Extractor 反推提示词再 Remix。", tools: ["Prompt Extractor", "图片生成", "视频生成"] },
];

type Tab = "all" | "agent" | "image" | "video" | "audio" | "utility";

export default function ToolsPage() {
  const [tab, setTab] = useState<Tab>("all");
  const [search, setSearch] = useState("");

  const visible = ALL_TOOLS.filter((t) => {
    if (tab !== "all" && t.group !== tab) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      t.label.toLowerCase().includes(q) ||
      t.desc.toLowerCase().includes(q) ||
      (t.useCase || "").toLowerCase().includes(q)
    );
  });

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-10">
        <h1 className="text-3xl md:text-4xl font-bold mb-3 gradient-text-static">All Tools</h1>
        <p className="text-text-secondary max-w-lg mx-auto mb-8">
          对标 Yapper AI Content Studio — 每个入口都是真实可点功能，无「即将推出」死胡同
        </p>
        <div className="relative max-w-md mx-auto">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索工具…"
            className="input-primary-lg"
          />
        </div>
      </motion.div>

      <div className="flex flex-wrap justify-center gap-2 mb-10">
        {([
          { id: "all" as const, label: "全部", icon: Grid3X3 },
          { id: "agent" as const, label: "Agent", icon: Bot },
          { id: "video" as const, label: "视频", icon: Play },
          { id: "image" as const, label: "图片", icon: Sparkles },
          { id: "audio" as const, label: "音频", icon: Music },
          { id: "utility" as const, label: "工具", icon: Wand2 },
        ]).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-all",
              tab === t.id
                ? "bg-white text-black shadow-md"
                : "bg-white/[0.03] border border-white/[0.06] text-text-secondary hover:text-text-accent-cyan"
            )}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {visible.length === 0 ? (
          <Empty title="未找到匹配工具" description={`没有与「${search}」相关的工具`} />
        ) : (
          <motion.div
            key={tab + search}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            {visible.map((tool) => (
              <Link key={tool.href + tool.label} href={tool.href} className="group block">
                <div className="h-full rounded-2xl border border-white/[0.06] bg-white/[0.03] p-5 hover:bg-white/[0.06] hover:border-white/[0.12] transition-all">
                  <div className="flex items-start justify-between mb-3">
                    <div className={cn("w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center", tool.color)}>
                      <tool.icon className="w-5 h-5 text-white" />
                    </div>
                    {tool.badge && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-white/10">{tool.badge}</span>
                    )}
                  </div>
                  <h3 className="font-semibold mb-1 group-hover:text-white transition-colors">{tool.label}</h3>
                  <p className="text-sm text-text-secondary mb-3 leading-relaxed">{tool.desc}</p>
                  {tool.useCase && (
                    <p className="text-[11px] text-text-tertiary mb-3">用例 · {tool.useCase}</p>
                  )}
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-brand">
                    打开 <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </span>
                </div>
              </Link>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {USE_CASES.map((uc) => (
          <div key={uc.title} className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
            <uc.icon className="w-5 h-5 mb-2 text-text-secondary" />
            <h4 className="font-semibold text-sm mb-1">{uc.title}</h4>
            <p className="text-xs text-text-secondary mb-2">{uc.desc}</p>
            <p className="text-[11px] text-text-tertiary">{uc.tools.join(" · ")}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
