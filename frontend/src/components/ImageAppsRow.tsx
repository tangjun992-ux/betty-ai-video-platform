"use client";

import { useRef } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Palette, Sparkles, User, Layers, Maximize2, Scissors, ChevronLeft, ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ─────────────────────────────────────────────────────────────
   ImageAppsRow — Yapper-style horizontal gallery of Image tools.
   Groups every image tool into one professional card carousel.
   ───────────────────────────────────────────────────────────── */

interface AppCard {
  label: string;
  desc: string;
  icon: React.ElementType;
  gradient: string;
  href: string;
  badge?: string;
}

const APPS: AppCard[] = [
  { label: "专业图片编辑器", desc: "指令式 AI 图像编辑，专业级修图", icon: Palette, gradient: "from-blue-600 to-cyan-400", href: "/create/image-editor", badge: "App" },
  { label: "产品图", desc: "为电商批量生成专业产品摄影", icon: Sparkles, gradient: "from-amber-500 to-orange-400", href: "/create/product", badge: "App" },
  { label: "专业头像", desc: "商务/证件级 AI 写真头像", icon: User, gradient: "from-emerald-600 to-teal-400", href: "/create/headshots", badge: "App" },
  { label: "照片包", desc: "成套风格照片一次生成", icon: Layers, gradient: "from-purple-600 to-indigo-400", href: "/create/photo-packs" },
  { label: "图片扩展", desc: "智能外扩画布，改变画幅", icon: Maximize2, gradient: "from-fuchsia-500 to-pink-400", href: "/create/extend" },
  { label: "媒体放大", desc: "2×/4× 超分辨率画质提升", icon: Sparkles, gradient: "from-teal-500 to-cyan-400", href: "/create/upscale" },
  { label: "背景移除", desc: "一键抠图，透明背景输出", icon: Scissors, gradient: "from-slate-500 to-slate-400", href: "/create/bg-remove" },
];

export function ImageAppsRow({ className }: { className?: string }) {
  const router = useRouter();
  const scrollerRef = useRef<HTMLDivElement>(null);

  const scroll = (dir: -1 | 1) => {
    scrollerRef.current?.scrollBy({ left: dir * 360, behavior: "smooth" });
  };

  return (
    <div className={cn("", className)}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-text-primary inline-flex items-center gap-2">
          <Layers className="w-4 h-4 text-accent-cyan" /> Image Apps
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
            {/* Gradient banner */}
            <div className={cn("relative h-24 bg-gradient-to-br flex items-center justify-center", app.gradient)}>
              <app.icon className="w-9 h-9 text-white/90 group-hover:scale-110 transition-transform duration-200" />
              {app.badge && (
                <span className="absolute top-2 right-2 px-1.5 py-0.5 rounded-md text-[9px] font-medium bg-black/40 backdrop-blur-sm text-white/90">{app.badge}</span>
              )}
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
