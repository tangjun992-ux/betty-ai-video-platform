"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Palette, Sparkles, User, Layers, Maximize2, Scissors, Wand2,
  Video, Bot, Camera, Search, Grid3X3, Play, Mic,
  ArrowRight, Move, Clapperboard, FileSearch, Drama, Blend, Volume2,
} from "lucide-react";
import { Empty } from "@/components/StatusStates";
import { cn } from "@/lib/utils";

/** Studio tool matrix — every href is a live create/agent route. No competitor name in product UI. */

type Group = "agent" | "video" | "image" | "utility";

interface Tool {
  icon: React.ElementType;
  label: string;
  desc: string;
  href: string;
  badge?: string;
  useCase?: string;
  group: Group;
  tag: "Agent" | "Video" | "Image" | "Utility";
}

const ALL_TOOLS: Tool[] = [
  { icon: Bot, label: "AI Agent", desc: "一句话导演：规划、分镜、生成、精修", href: "/agent", badge: "Core", useCase: "广告、短剧、UGC", group: "agent", tag: "Agent" },
  { icon: Video, label: "视频生成", desc: "Seedance 2.0 文生/图生视频，多镜头叙事", href: "/create/video", badge: "Hot", useCase: "短视频、广告", group: "video", tag: "Video" },
  { icon: Mic, label: "唇形同步", desc: "图 + 文/音频说话视频（Kling Avatar）", href: "/create/lipsync", badge: "Core", useCase: "虚拟主播、口播", group: "video", tag: "Video" },
  { icon: User, label: "Talking Avatar", desc: "头像说话视频，图+音频优先", href: "/create/avatar", useCase: "数字人", group: "video", tag: "Video" },
  { icon: Move, label: "运动控制", desc: "原生 Kling Motion + 可选旁白（≠ Act-One）", href: "/create/motion", useCase: "动作复制", group: "video", tag: "Video" },
  { icon: Drama, label: "Performance Drive", desc: "Motion + 可选口播，表演驱动成片", href: "/create/performance", badge: "New", useCase: "表演成片", group: "video", tag: "Video" },
  { icon: Clapperboard, label: "时间轴编辑", desc: "片段编排、字幕与合成", href: "/create/timeline", useCase: "后期成片", group: "video", tag: "Video" },
  { icon: Sparkles, label: "图片生成", desc: "多模型文生图 / 多参考图 i2i", href: "/create/image", badge: "Hot", useCase: "创意、产品图", group: "image", tag: "Image" },
  { icon: Blend, label: "AI 换脸", desc: "双图 i2i 换脸（已 live 验证）", href: "/create/face-swap", badge: "Live", useCase: "玩法模板", group: "image", tag: "Image" },
  { icon: Palette, label: "图片编辑", desc: "AI 指令编辑", href: "/create/image-editor", useCase: "后期处理", group: "image", tag: "Image" },
  { icon: Maximize2, label: "AI 放大", desc: "2x/4x 超分", href: "/create/upscale", useCase: "打印、修复", group: "image", tag: "Image" },
  { icon: Scissors, label: "背景移除", desc: "一键抠图透明 PNG", href: "/create/bg-remove", useCase: "电商素材", group: "image", tag: "Image" },
  { icon: Layers, label: "扩图", desc: "智能外扩构图", href: "/create/extend", useCase: "改构图", group: "image", tag: "Image" },
  { icon: Camera, label: "产品摄影", desc: "电商产品图批量 SKU", href: "/create/product", useCase: "电商", group: "image", tag: "Image" },
  { icon: User, label: "职业头像", desc: "Headshots 批量套系", href: "/create/headshots", useCase: "LinkedIn", group: "image", tag: "Image" },
  { icon: Grid3X3, label: "Photo Packs", desc: "成套风格照片批量生成", href: "/create/photo-packs", badge: "New", useCase: "批量素材", group: "image", tag: "Image" },
  { icon: Volume2, label: "语音合成", desc: "TTS 配音（非实时变声）", href: "/create/audio", useCase: "配音、口播", group: "utility", tag: "Utility" },
  { icon: FileSearch, label: "URL-to-Viral", desc: "链接反推提示词 + 投放规格（非原片搬运）", href: "/create/extract", badge: "New", useCase: "复用结构", group: "utility", tag: "Utility" },
];

const SECTIONS: { id: Group; title: string; kicker: string; testId: string }[] = [
  { id: "video", title: "Video Tools", kicker: "成片", testId: "tools-video-section" },
  { id: "image", title: "Image Tools", kicker: "静态", testId: "tools-image-section" },
  { id: "utility", title: "Utility", kicker: "后期 / 结构", testId: "tools-utility-section" },
];

type Tab = "all" | Group;

function ToolCard({ tool }: { tool: Tool }) {
  return (
    <Link
      href={tool.href}
      data-testid={`tool-card-${tool.href.replace(/\//g, "-")}`}
      className="group block h-full rounded-2xl border border-cosmic-border bg-cosmic-surface p-5 hover:border-cosmic-border-hover hover:shadow-md transition-all"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="w-10 h-10 rounded-xl bg-brand/10 border border-brand/15 flex items-center justify-center">
          <tool.icon className="w-5 h-5 text-brand" />
        </div>
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-cosmic-subtle text-text-tertiary">
          {tool.tag}
        </span>
      </div>
      <div className="flex items-center gap-2 mb-1">
        <h3 className="font-semibold text-text-primary group-hover:text-brand transition-colors">{tool.label}</h3>
        {tool.badge && (
          <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-md bg-accent-violet/10 text-accent-violet">
            {tool.badge}
          </span>
        )}
      </div>
      <p className="text-sm text-text-secondary mb-3 leading-relaxed">{tool.desc}</p>
      {tool.useCase && (
        <p className="text-[11px] text-text-tertiary mb-3">用例 · {tool.useCase}</p>
      )}
      <span className="inline-flex items-center gap-1 text-xs font-medium text-brand">
        打开 <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
      </span>
    </Link>
  );
}

export default function ToolsPage() {
  const [tab, setTab] = useState<Tab>("all");
  const [search, setSearch] = useState("");

  const visible = useMemo(() => ALL_TOOLS.filter((t) => {
    if (tab !== "all" && t.group !== tab) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      t.label.toLowerCase().includes(q) ||
      t.desc.toLowerCase().includes(q) ||
      (t.useCase || "").toLowerCase().includes(q)
    );
  }), [tab, search]);

  const agent = visible.filter((t) => t.group === "agent");

  return (
    <div className="max-w-6xl mx-auto px-4 py-12">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-10">
        <p className="text-overline text-text-tertiary uppercase tracking-[0.18em] mb-2">Studio</p>
        <h1 className="text-3xl md:text-4xl font-semibold mb-3 text-text-primary">全部工具</h1>
        <p className="text-text-secondary max-w-lg mx-auto mb-8">
          每个入口都是真实可点的创作页，没有「即将推出」。货架以已验证模型为准。
        </p>
        <div className="relative max-w-md mx-auto">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索工具…"
            className="input-primary-lg"
            data-testid="tools-search"
          />
        </div>
      </motion.div>

      <div className="flex flex-wrap justify-center gap-2 mb-10">
        {([
          { id: "all" as const, label: "全部", icon: Grid3X3 },
          { id: "agent" as const, label: "Agent", icon: Bot },
          { id: "video" as const, label: "视频", icon: Play },
          { id: "image" as const, label: "图片", icon: Sparkles },
          { id: "utility" as const, label: "工具", icon: Wand2 },
        ]).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-all border",
              tab === t.id
                ? "bg-brand text-white border-brand shadow-sm"
                : "bg-cosmic-surface border-cosmic-border text-text-secondary hover:text-text-primary hover:border-cosmic-border-hover"
            )}
          >
            <t.icon className="w-4 h-4" />
            {t.label}
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <Empty title="未找到匹配工具" description={`没有与「${search}」相关的工具`} />
      ) : (
        <>
          {agent.length > 0 && (tab === "all" || tab === "agent") && (
            <Link
              href="/agent"
              data-testid="tools-agent-banner"
              className="mb-10 flex flex-col md:flex-row md:items-center gap-4 rounded-2xl border border-brand/20 bg-gradient-to-r from-brand/10 via-accent-violet/10 to-accent-blue/10 p-6 hover:border-brand/40 transition-colors"
            >
              <div className="w-12 h-12 rounded-xl bg-brand text-white flex items-center justify-center shrink-0">
                <Bot className="w-6 h-6" />
              </div>
              <div className="flex-1 text-left">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-brand mb-1">Just Direct</p>
                <h2 className="text-lg font-semibold text-text-primary">AI Agent · 当导演，不要写提示词</h2>
                <p className="text-sm text-text-secondary mt-1">描述你要的成片，Agent 规划到精修。任意媒介、任意风格。</p>
              </div>
              <span className="inline-flex items-center gap-1 text-sm font-medium text-brand">
                开始导演 <ArrowRight className="w-4 h-4" />
              </span>
            </Link>
          )}

          {SECTIONS.map((sec) => {
            const items = visible.filter((t) => t.group === sec.id);
            if (!items.length) return null;
            return (
              <section key={sec.id} data-testid={sec.testId} className="mb-12">
                <div className="flex items-end justify-between mb-4">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.16em] text-text-tertiary mb-1">{sec.kicker}</p>
                    <h2 className="text-xl font-semibold text-text-primary">{sec.title}</h2>
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {items.map((tool) => (
                    <ToolCard key={tool.href + tool.label} tool={tool} />
                  ))}
                </div>
              </section>
            );
          })}
        </>
      )}
    </div>
  );
}
