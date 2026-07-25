"use client";

import { motion } from "framer-motion";
import { FileText, Music, Film } from "lucide-react";
import { cn } from "@/lib/utils";
import { ComingSoonPage } from "@/components/ComingSoonPage";

const EXTRACT_CAPABILITIES = [
  { label: "文字提取", desc: "OCR 图片文字识别，提取视频字幕", icon: FileText, color: "text-accent-cyan" },
  { label: "音频提取", desc: "从视频中分离音频轨道", icon: Music, color: "text-accent-violet" },
  { label: "关键帧", desc: "智能识别视频精彩画面", icon: Film, color: "text-accent-blue" },
];

export default function ExtractPage() {
  return (
    <ComingSoonPage
      emoji="📋"
      title="内容提取"
      description="从媒体中提取文字、音频、关键帧。智能解析你的图片、视频和音频文件，提取其中有价值的内容。"
      cta={
        <p className="text-body-sm text-text-tertiary">
          此功能正在开发中，敬请期待。功能上线后您将可以一站式提取各类媒体内容。
        </p>
      }
      extra={
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4, duration: 0.4 }}
          className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4"
        >
          {EXTRACT_CAPABILITIES.map((item) => (
            <div
              key={item.label}
              className="flex flex-col items-center gap-2 p-5 rounded-2xl bg-cosmic-surface border border-cosmic-border text-center"
            >
              <item.icon className={cn("w-8 h-8", item.color)} />
              <span className="text-body-sm font-semibold text-text-primary">{item.label}</span>
              <span className="text-caption text-text-tertiary">{item.desc}</span>
            </div>
          ))}
        </motion.div>
      }
      relatedTools={[
        { label: "视频创作", href: "/create/video", icon: "🎬" },
        { label: "图片创作", href: "/create/image", icon: "🖼️" },
        { label: "时间线", href: "/create/timeline", icon: "⏱️" },
      ]}
      upcomingFeatures={[
        "支持中、英、日、韩等多语言 OCR 文字识别",
        "智能提取视频中的人物对话和背景音频",
        "自动识别视频中的关键场景切换帧",
        "支持批量处理，导出提取结果为通用格式",
      ]}
    />
  );
}
