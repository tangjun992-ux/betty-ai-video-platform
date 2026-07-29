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
  { label: "Seedance 2.0 Omni", desc: "多模态输入 + 唇形 + 多镜头叙事", icon: Film, gradient: "from-indigo-600 to-blue-400", href: "/create/video", tag: "Video" },
  { label: "工作室唇形同步", desc: "口播 / 数字分身 / 政治讽刺短片", icon: Mic, gradient: "from-purple-600 to-fuchsia-400", href: "/create/lipsync", tag: "Video" },
  { label: "动态控制", desc: "用参考视频 + 角色图精准引导运动", icon: Sparkles, gradient: "from-rose-500 to-orange-400", href: "/create/motion", tag: "Video" },
  { label: "数字人", desc: "图片 + 音频，一键生成说话数字人", icon: User, gradient: "from-emerald-600 to-teal-400", href: "/create/avatar", tag: "Video" },
  { label: "媒体放大", desc: "AI 超分辨率，2×/4× 画质提升", icon: Maximize2, gradient: "from-cyan-500 to-sky-400", href: "/create/upscale", tag: "Utility" },
  { label: "提示词提取", desc: "从任意图片/视频反推可复用提示词", icon: ScanText, gradient: "from-amber-500 to-yellow-400", href: "/create/extract", tag: "Utility" },
  { label: "时间线编辑器", desc: "多片段剪辑、转场、字幕与配音合成", icon: Clapperboard, gradient: "from-slate-500 to-slate-400", href: "/create/timeline", tag: "Utility" },
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
