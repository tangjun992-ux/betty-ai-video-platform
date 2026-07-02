"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { ArrowRight, Sparkles, Clock, Mic } from "lucide-react";
import { useCreationStore } from "@/lib/stores";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function AvatarPage() {
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
            <span className="text-5xl">👤</span>
          </motion.div>

          {/* ── Title + Description ── */}
          <div className="space-y-3">
            <h1 className="text-h2 text-text-primary tracking-tight">
              AI 头像
            </h1>
            <p className="text-body text-text-secondary max-w-md mx-auto leading-relaxed">
              上传一张照片和一段音频，生成说话视频。让静态肖像开口说话，适用于虚拟主播、数字人播报等场景。
            </p>
          </div>

          {/* ── Status Badge ── */}
          <div className="flex items-center justify-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-warning-muted border border-warning/20 text-warning text-caption font-semibold">
              <Clock className="w-3.5 h-3.5" />
              即将推出
            </span>
          </div>

          {/* ── CTA Button ── */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.4 }}
            className="pt-2"
          >
            <button
              onClick={() => {
                setPrompt("生成头像说话视频");
                router.push("/create/lipsync");
              }}
              className="btn-primary text-base px-8 py-3 h-auto gap-2"
            >
              <Mic className="w-4 h-4" />
              跳转到唇形同步
              <ArrowRight className="w-4 h-4" />
            </button>
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
                { label: "唇形同步", href: "/create/lipsync", icon: "🎤" },
                { label: "动态同步", href: "/create/motion", icon: "🎬" },
                { label: "图片创作", href: "/create/image", icon: "🖼️" },
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
                    上传任意肖像照片，AI 自动识别面部特征
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan/60 flex-shrink-0" />
                    支持文本转语音或上传自定义音频
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan/60 flex-shrink-0" />
                    生成自然的口型同步视频，支持多种语言
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan/60 flex-shrink-0" />
                    输出 1080p 高清视频，适用于社交媒体
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
