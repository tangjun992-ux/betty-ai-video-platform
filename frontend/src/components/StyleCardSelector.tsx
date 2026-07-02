"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  Camera, Sparkles, Palette, PenTool, Film, Mountain,
  Zap, Heart, Cloud, Moon, Sun, Leaf,
} from "lucide-react";

// ─── Style definitions ──────────────────────────────────

export interface StyleOption {
  id: string;
  label: string;
  icon: React.ElementType;
  gradient: string;  // Tailwind gradient classes
  description: string;
  tags: string[];
}

export const STYLE_OPTIONS: StyleOption[] = [
  {
    id: "photorealistic",
    label: "写实摄影",
    icon: Camera,
    gradient: "from-blue-600 to-cyan-400",
    description: "超写实风格，细节丰富",
    tags: ["写实", "摄影", "高细节"],
  },
  {
    id: "anime",
    label: "动漫风格",
    icon: Sparkles,
    gradient: "from-pink-500 to-rose-400",
    description: "二次元动漫/漫画风格",
    tags: ["动漫", "二次元", "插画"],
  },
  {
    id: "oil-painting",
    label: "油画艺术",
    icon: Palette,
    gradient: "from-amber-500 to-orange-400",
    description: "古典油画质感",
    tags: ["油画", "艺术", "古典"],
  },
  {
    id: "sketch",
    label: "素描线条",
    icon: PenTool,
    gradient: "from-gray-400 to-gray-300",
    description: "铅笔/钢笔素描风格",
    tags: ["素描", "线条", "黑白"],
  },
  {
    id: "cinematic",
    label: "电影质感",
    icon: Film,
    gradient: "from-yellow-600 to-red-500",
    description: "电影级光影与构图",
    tags: ["电影", "光影", "大片"],
  },
  {
    id: "landscape",
    label: "自然风光",
    icon: Mountain,
    gradient: "from-emerald-600 to-teal-400",
    description: "壮丽的自然景观",
    tags: ["风景", "自然", "户外"],
  },
  {
    id: "fantasy",
    label: "奇幻世界",
    icon: Zap,
    gradient: "from-purple-600 to-indigo-400",
    description: "魔法与奇幻场景",
    tags: ["奇幻", "魔法", "科幻"],
  },
  {
    id: "3d-render",
    label: "3D 渲染",
    icon: Cloud,
    gradient: "from-violet-500 to-fuchsia-400",
    description: "三维建模渲染风格",
    tags: ["3D", "渲染", "CGI"],
  },
  {
    id: "watercolor",
    label: "水彩晕染",
    icon: Heart,
    gradient: "from-cyan-500 to-blue-300",
    description: "柔和水彩画效果",
    tags: ["水彩", "柔和", "艺术"],
  },
  {
    id: "dark-moody",
    label: "暗调氛围",
    icon: Moon,
    gradient: "from-slate-700 to-slate-500",
    description: "暗调光影氛围",
    tags: ["暗调", "氛围", "情绪"],
  },
  {
    id: "bright-clean",
    label: "明亮干净",
    icon: Sun,
    gradient: "from-yellow-400 to-orange-300",
    description: "明亮干净的视觉风格",
    tags: ["明亮", "干净", "清新"],
  },
  {
    id: "botanical",
    label: "植物花卉",
    icon: Leaf,
    gradient: "from-green-500 to-lime-400",
    description: "植物与花卉特写",
    tags: ["植物", "花卉", "自然"],
  },
];

// ─── Component ──────────────────────────────────────────

interface StyleCardSelectorProps {
  selected: string | null;
  onChange: (styleId: string) => void;
  className?: string;
}

export function StyleCardSelector({ selected, onChange, className }: StyleCardSelectorProps) {
  return (
    <div className={cn("space-y-2", className)}>
      <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">
        风格
      </p>
      <div className="grid grid-cols-2 gap-2">
        {STYLE_OPTIONS.map((style, index) => {
          const isSelected = selected === style.id;
          const Icon = style.icon;

          return (
            <motion.button
              key={style.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.03 }}
              onClick={() => onChange(style.id)}
              className={cn(
                "group relative flex flex-col items-start gap-2 p-3 rounded-xl border text-left transition-all duration-200 overflow-hidden",
                isSelected
                  ? "border-accent-cyan/40 bg-accent-cyan/[0.04] ring-1 ring-accent-cyan/20"
                  : "border-cosmic-border/40 bg-card/30 hover:border-cosmic-border hover:bg-card/50"
              )}
            >
              {/* Gradient icon background */}
              <div
                className={cn(
                  "w-8 h-8 rounded-lg flex items-center justify-center transition-transform duration-200 group-hover:scale-110",
                  "bg-gradient-to-br",
                  style.gradient
                )}
              >
                <Icon className="w-4 h-4 text-text-accent-cyan" />
              </div>

              {/* Label + description */}
              <div className="flex-1 min-w-0">
                <p className={cn(
                  "text-xs font-medium truncate transition-colors",
                  isSelected ? "text-accent-cyan" : "text-text-accent-cyan"
                )}>
                  {style.label}
                </p>
                <p className="text-[10px] text-text-secondary/60 mt-0.5 line-clamp-1">
                  {style.description}
                </p>
              </div>

              {/* Selected indicator */}
              {isSelected && (
                <motion.div
                  layoutId="style-selected"
                  className="absolute top-2 right-2 w-5 h-5 rounded-full bg-accent-cyan flex items-center justify-center"
                >
                  <svg className="w-3 h-3 text-black" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </motion.div>
              )}
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
