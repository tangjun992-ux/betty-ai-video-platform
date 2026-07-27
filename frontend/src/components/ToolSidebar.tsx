"use client";

import { cn } from "@/lib/utils";
import { motion } from "framer-motion";
import { Palette, Sparkles, User, Layers, Maximize2, Scissors, Wand2 } from "lucide-react";

const TOOLS = [
  { icon: Palette, label: "图片编辑器", desc: "AI 智能编辑" },
  { icon: Sparkles, label: "产品图", desc: "电商产品摄影" },
  { icon: User, label: "专业头像", desc: "AI 写真头像" },
  { icon: Layers, label: "照片包", desc: "批量生成变体" },
  { icon: Maximize2, label: "图片扩展", desc: "智能外扩画面" },
  { icon: Scissors, label: "去背景", desc: "一键移除背景" },
  { icon: Wand2, label: "放大", desc: "4K 超分辨率" },
];

interface ToolSidebarProps {
  activeTool: string | null;
  onToolSelect: (label: string) => void;
}

export function ToolSidebar({ activeTool, onToolSelect }: ToolSidebarProps) {
  return (
    <div className="w-56 flex-shrink-0 space-y-1 pr-2">
      <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider px-2 mb-2">
        Image Apps
      </p>
      {TOOLS.map((tool, i) => (
        <motion.button
          key={tool.label}
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.05 }}
          onClick={() => onToolSelect(tool.label)}
          className={cn(
            "flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm transition-all duration-200 text-left",
            activeTool === tool.label
              ? "bg-accent-cyan/[0.08] text-accent-cyan border border-accent-cyan/20"
              : "text-text-secondary hover:text-text-accent-cyan hover:bg-cosmic-subtle border border-transparent"
          )}
        >
          <tool.icon className="w-4 h-4 flex-shrink-0" />
          <div className="flex flex-col items-start">
            <span className="font-medium text-xs">{tool.label}</span>
            <span className="text-[10px] text-text-secondary/60">{tool.desc}</span>
          </div>
        </motion.button>
      ))}
    </div>
  );
}
