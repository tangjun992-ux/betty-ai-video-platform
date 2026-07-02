"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Sparkles, Clock, FileText, Music, Film } from "lucide-react";
import { useCreationStore } from "@/lib/stores";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function ExtractPage() {
  const router = useRouter();
  const { setPrompt } = useCreationStore();

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-cosmic-deep">
      <div className="max-w-2xl mx-auto px-4 py-16 md:py-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="text-center space-y-6"
        >
          {/* ── Emoji / Icon Display ── */}
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.1, duration: 0.4, ease: [0.34, 1.56, 0.64, 1] }}
            className="inline-flex items-center justify-center w-24 h-24 rounded-3xl bg-brand-50 border border-cosmic-border shadow-elevation-sm"
          >
            <span className="text-5xl">📋</span>
          </motion.div>

          {/* ── Title + Description ── */}
          <div className="space-y-3">
            <h1 className="text-h2 text-text-primary tracking-tight">
              内容提取
            </h1>
            <p className="text-body text-text-secondary max-w-md mx-auto leading-relaxed">
              从媒体中提取文字、音频、关键帧。智能解析你的图片、视频和音频文件，提取其中有价值的内容。
            </p>
          </div>

          {/* ── Status Badge ── */}
          <div className="flex items-center justify-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-warning-muted border border-warning/20 text-warning text-caption font-semibold">
              <Clock className="w-3.5 h-3.5" />
              即将推出
            </span>
          </div>

          {/* ── CTA Area ── */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
            className="pt-2"
          >
            <p className="text-body-sm text-text-tertiary">
              此功能正在开发中，敬请期待。功能上线后您将可以一站式提取各类媒体内容。
            </p>
          </motion.div>

          {/* ── Feature Cards ── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.4 }}
            className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4"
          >
            {[
              { label: "文字提取", desc: "OCR 图片文字识别，提取视频字幕", icon: FileText, color: "text-accent-cyan" },
              { label: "音频提取", desc: "从视频中分离音频轨道", icon: Music, color: "text-accent-violet" },
              { label: "关键帧", desc: "智能识别视频精彩画面", icon: Film, color: "text-accent-blue" },
            ].map((item) => (
              <div
                key={item.label}
                className="flex flex-col items-center gap-2 p-5 rounded-2xl bg-cosmic-surface border border-cosmic-border text-center"
              >
                <item.icon className={cn("w-8 h-8", item.color)} />
                <span className="text-body-sm font-semibold text-text-primary">
                  {item.label}
                </span>
                <span className="text-caption text-text-tertiary">
                  {item.desc}
                </span>
              </div>
            ))}
          </motion.div>

          {/* ── Suggested Tools ── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 0.4 }}
            className="pt-8 border-t border-cosmic-border/60"
          >
            <p className="text-caption text-text-tertiary mb-4">相关工具</p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              {[
                { label: "视频创作", href: "/create/video", icon: "🎬" },
                { label: "图片创作", href: "/create/image", icon: "🖼️" },
                { label: "时间线", href: "/create/timeline", icon: "⏱️" },
              ].map((tool) => (
                <button
                  key={tool.href}
                  onClick={() => router.push(tool.href)}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cosmic-surface border border-cosmic-border text-body-sm text-text-secondary hover:text-text-primary hover:border-cosmic-border-hover hover:shadow-elevation-sm transition-all duration-200"
                >
                  <span>{tool.icon}</span>
                  <span>{tool.label}</span>
                </button>
              ))}
            </div>
          </motion.div>

          {/* ── Coming Soon Feature Preview ── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.4 }}
            className="mt-6 p-6 rounded-2xl bg-cosmic-subtle/50 border border-dashed border-cosmic-border/80 text-left"
          >
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-accent-cyan mt-0.5 flex-shrink-0" />
              <div className="space-y-2">
                <h3 className="text-body-sm font-semibold text-text-primary">
                  功能预告
                </h3>
                <ul className="space-y-1.5 text-body-sm text-text-secondary">
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan/60 flex-shrink-0" />
                    支持中、英、日、韩等多语言 OCR 文字识别
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan/60 flex-shrink-0" />
                    智能提取视频中的人物对话和背景音频
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan/60 flex-shrink-0" />
                    自动识别视频中的关键场景切换帧
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan/60 flex-shrink-0" />
                    支持批量处理，导出提取结果为通用格式
                  </li>
                </ul>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
