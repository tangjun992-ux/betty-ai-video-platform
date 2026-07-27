"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  Palette, Sparkles, User, Layers, Maximize2, Scissors, Wand2,
  Video, Music, Bot, Camera, Search, Grid3X3, Play, Mic,
  ArrowRight, Move, Clapperboard, FileSearch, Drama, Blend
} from "lucide-react";
import { Empty } from "@/components/StatusStates";
import { cn } from "@/lib/utils";

/* ═══════════════════════════════════════════════════════
   Tools — STUDIO v5
   全部创作工具矩阵: 统一 icon-tile 哑光卡片, 无彩虹渐变
   ═══════════════════════════════════════════════════════ */

interface Tool {
  icon: any;
  label: string;
  desc: string;
  href: string;
  badge?: string;
  useCase?: string;
  group: "image" | "video" | "audio" | "utility" | "agent";
}

const ALL_TOOLS: Tool[] = [
  // Agent
  { icon: Bot, label: "AI Agent 导演", desc: "一句话描述创意，自动规划、分镜、生成、合成", href: "/agent", badge: "核心", useCase: "广告、短剧、UGC", group: "agent" },
  // Video
  { icon: Video, label: "视频生成", desc: "文生 / 图生视频，多镜头叙事", href: "/create/video", badge: "热门", useCase: "短视频、广告", group: "video" },
  { icon: Mic, label: "唇形同步", desc: "图片 + 文本/音频生成说话视频", href: "/create/lipsync", useCase: "虚拟主播、口播", group: "video" },
  { icon: User, label: "数字人口播", desc: "头像说话视频（图+音频优先）", href: "/create/avatar", useCase: "数字人、讲解", group: "video" },
  { icon: Move, label: "运动控制", desc: "参考视频精准动作迁移", href: "/create/motion", useCase: "舞蹈、动作复制", group: "video" },
  { icon: Drama, label: "表演驱动", desc: "动作 + 可选口播的表演成片", href: "/create/performance", badge: "新", useCase: "表演驱动成片", group: "video" },
  { icon: Clapperboard, label: "时间轴编辑", desc: "片段编排、字幕与合成", href: "/create/timeline", useCase: "后期成片", group: "video" },
  // Image
  { icon: Sparkles, label: "图片生成", desc: "多模型文生图 / 多参考图", href: "/create/image", badge: "热门", useCase: "创意、产品图", group: "image" },
  { icon: Blend, label: "AI 换脸", desc: "双图换脸，已验证可用", href: "/create/face-swap", useCase: "创意玩法", group: "image" },
  { icon: Palette, label: "图片编辑", desc: "AI 指令编辑", href: "/create/image-editor", useCase: "后期处理", group: "image" },
  { icon: Maximize2, label: "AI 放大", desc: "2x / 4x 超分辨率", href: "/create/upscale", useCase: "打印、修复", group: "image" },
  { icon: Scissors, label: "背景移除", desc: "一键抠图透明 PNG", href: "/create/bg-remove", useCase: "电商素材", group: "image" },
  { icon: Layers, label: "AI 扩图", desc: "智能外扩构图", href: "/create/extend", useCase: "改构图", group: "image" },
  { icon: Camera, label: "产品摄影", desc: "电商产品图专用工作流", href: "/create/product", useCase: "电商", group: "image" },
  { icon: User, label: "职业头像", desc: "专业形象照提示词包", href: "/create/headshots", useCase: "名片 / LinkedIn", group: "image" },
  { icon: Grid3X3, label: "写真套装", desc: "成套提示词包一键开拍", href: "/create/photo-packs", badge: "新", useCase: "批量素材", group: "image" },
  // Audio / Utility
  { icon: Music, label: "语音合成", desc: "TTS 配音与音效", href: "/create/audio", useCase: "配音、口播", group: "audio" },
  { icon: FileSearch, label: "提示词提取", desc: "从图片/视频反推提示词", href: "/create/extract", badge: "新", useCase: "复用爆款构图", group: "utility" },
];

const USE_CASES = [
  { icon: Camera, title: "电商卖家", desc: "产品图、抠图、扩图一站完成", tools: ["产品摄影", "背景移除", "AI 扩图"] },
  { icon: Video, title: "内容创作者", desc: "视频 + 唇形 + 数字人 + 时间轴成片", tools: ["视频生成", "唇形同步", "数字人口播"] },
  { icon: Sparkles, title: "广告团队", desc: "Agent 导演式多镜叙事 + 运动迁移", tools: ["AI Agent 导演", "运动控制", "时间轴编辑"] },
  { icon: FileSearch, title: "灵感复用", desc: "提取提示词再二创 Remix", tools: ["提示词提取", "图片生成", "视频生成"] },
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
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-10">
        <h1 className="text-2xl md:text-3xl font-semibold text-text-primary mb-2">全部工具</h1>
        <p className="text-sm text-text-secondary max-w-md mx-auto mb-7">
          每个入口都是真实可用功能，即点即创作
        </p>
        <div className="relative max-w-md mx-auto">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索工具…"
            className="input-cosmic input-cosmic-lg pl-10"
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
              "flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-[13px] font-medium transition-colors",
              tab === t.id
                ? "bg-cosmic-subtle text-text-primary border border-cosmic-border-hover"
                : "border border-cosmic-border bg-cosmic-surface text-text-secondary hover:text-text-primary hover:border-cosmic-border-hover"
            )}
          >
            <t.icon className={cn("w-3.5 h-3.5", tab === t.id && "text-brand-strong")} />
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
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
          >
            {visible.map((tool) => (
              <Link key={tool.href + tool.label} href={tool.href} className="group block">
                <div className="h-full rounded-xl border border-cosmic-border bg-cosmic-surface p-4 hover:border-cosmic-border-hover hover:bg-cosmic-elevated transition-colors duration-150">
                  <div className="flex items-start justify-between mb-3">
                    <span className="icon-tile w-10 h-10">
                      <tool.icon className="w-[18px] h-[18px]" />
                    </span>
                    {tool.badge && (
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-brand/10 text-brand-strong border border-brand/20">{tool.badge}</span>
                    )}
                  </div>
                  <h3 className="text-[14px] font-semibold text-text-primary mb-1">{tool.label}</h3>
                  <p className="text-[13px] text-text-secondary mb-3 leading-relaxed">{tool.desc}</p>
                  {tool.useCase && (
                    <p className="text-[11px] text-text-tertiary mb-3">适用 · {tool.useCase}</p>
                  )}
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-brand-strong">
                    打开 <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </span>
                </div>
              </Link>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mt-14 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {USE_CASES.map((uc) => (
          <div key={uc.title} className="rounded-xl border border-cosmic-border bg-cosmic-surface p-4">
            <span className="icon-tile w-8 h-8 mb-2.5">
              <uc.icon className="w-4 h-4" />
            </span>
            <h4 className="font-semibold text-[13px] text-text-primary mb-1">{uc.title}</h4>
            <p className="text-xs text-text-secondary mb-2 leading-relaxed">{uc.desc}</p>
            <p className="text-[11px] text-text-tertiary">{uc.tools.join(" · ")}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
