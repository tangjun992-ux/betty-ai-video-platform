"use client";

import { useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Film, Mic, Sparkles, User, Maximize2, ScanText, Clapperboard, ChevronLeft, ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface AppCard {
  label: string;
  desc: string;
  icon: React.ElementType;
  gradient: string;
  href: string;
  tag: string;
}

const APPS: AppCard[] = [
  { label: "Seedance 2.0 Omni", desc: "多模态输入 + 唇形 + 多镜头叙事", icon: Film, gradient: "from-accent-blue to-accent-violet", href: "/create/video", tag: "Video" },
  { label: "工作室唇形同步", desc: "口播 / 数字分身（Kling Avatar）", icon: Mic, gradient: "from-accent-violet to-accent-fuchsia", href: "/create/lipsync", tag: "Video" },
  { label: "动态控制", desc: "参考视频 + 角色图引导运动（≠ Act-One）", icon: Sparkles, gradient: "from-accent-fuchsia to-brand", href: "/create/motion", tag: "Video" },
  { label: "数字人", desc: "图片 + 音频，说话数字人", icon: User, gradient: "from-brand to-accent-blue", href: "/create/avatar", tag: "Video" },
  { label: "媒体放大", desc: "AI 超分辨率，2×/4×", icon: Maximize2, gradient: "from-accent-blue to-brand", href: "/create/upscale", tag: "Utility" },
  { label: "URL-to-Viral", desc: "链接反推提示词 + 投放规格（非原片搬运）", icon: ScanText, gradient: "from-accent-violet to-accent-blue", href: "/create/extract", tag: "Utility" },
  { label: "时间线编辑器", desc: "多片段、字幕与配音合成", icon: Clapperboard, gradient: "from-brand-strong to-accent-violet", href: "/create/timeline", tag: "Utility" },
];

export function VideoAppsRow({ className }: { className?: string }) {
  const router = useRouter();
  const scrollerRef = useRef<HTMLDivElement>(null);
  const scroll = (dir: -1 | 1) => scrollerRef.current?.scrollBy({ left: dir * 360, behavior: "smooth" });

  return (
    <div className={cn("", className)}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-text-primary inline-flex items-center gap-2">
          <Film className="w-4 h-4 text-accent-cyan" /> Video Apps
        </h2>
        <div className="flex items-center gap-1.5">
          <button onClick={() => scroll(-1)} className="w-7 h-7 rounded-full border border-cosmic-border/60 flex items-center justify-center text-text-secondary hover:text-accent-cyan hover:border-accent-cyan/40 transition-colors" aria-label="向左">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button onClick={() => scroll(1)} className="w-7 h-7 rounded-full border border-cosmic-border/60 flex items-center justify-center text-text-secondary hover:text-accent-cyan hover:border-accent-cyan/40 transition-colors" aria-label="向右">
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div ref={scrollerRef} className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide snap-x">
        {APPS.map((app, i) => (
          <motion.button
            key={app.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
            onClick={() => router.push(app.href)}
            className="group relative flex-shrink-0 w-56 text-left rounded-2xl overflow-hidden border border-cosmic-border/50 bg-cosmic-surface/40 hover:border-accent-cyan/40 hover:bg-cosmic-surface/70 transition-all duration-200 snap-start"
          >
            <div className={cn("relative h-24 bg-gradient-to-br flex items-center justify-center", app.gradient)}>
              <app.icon className="w-9 h-9 text-white/90 group-hover:scale-110 transition-transform duration-200" />
              <span className="absolute top-2 right-2 px-1.5 py-0.5 rounded-md text-[9px] font-medium bg-black/40 backdrop-blur-sm text-white/90">{app.tag}</span>
            </div>
            <div className="p-3">
              <p className="text-xs font-semibold text-text-primary">{app.label}</p>
              <p className="text-[11px] text-text-secondary/70 mt-0.5 line-clamp-2 leading-relaxed">{app.desc}</p>
            </div>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
