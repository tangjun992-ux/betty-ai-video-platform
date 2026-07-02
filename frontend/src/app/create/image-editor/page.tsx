"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { ArrowRight, Sparkles, Zap, ImageIcon, Palette, Crop, Wand2 } from "lucide-react";
import { useCreationStore } from "@/lib/stores";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function ImageEditorPage() {
  const router = useRouter();
  const { setPrompt } = useCreationStore();

  const handleGoToImage = () => {
    router.push("/create/image");
  };

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
            <span className="text-5xl">🎨</span>
          </motion.div>

          {/* ── Title + Description ── */}
          <div className="space-y-3">
            <h1 className="text-h2 text-text-primary tracking-tight">
              图片编辑器
            </h1>
            <p className="text-body text-text-secondary max-w-md mx-auto leading-relaxed">
              AI 驱动的专业图片编辑工具。提供局部重绘、风格迁移、智能修复等强大编辑能力，让修图变得简单高效。
            </p>
          </div>

          {/* ── Status Badge ── */}
          <div className="flex items-center justify-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-success-muted border border-success/20 text-success text-caption font-semibold">
              <Zap className="w-3.5 h-3.5" />
              可用
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
              onClick={handleGoToImage}
              className="btn-primary text-base px-8 py-3 h-auto gap-2"
            >
              <ImageIcon className="w-4 h-4" />
              跳转到图片创作
              <ArrowRight className="w-4 h-4" />
            </button>
          </motion.div>

          {/* ── Feature Cards ── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.4 }}
            className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4"
          >
            {[
              { label: "AI 重绘", desc: "涂抹指定区域，AI 智能重绘", icon: Wand2, color: "text-accent-cyan" },
              { label: "风格迁移", desc: "一键将照片转换为艺术风格", icon: Palette, color: "text-accent-violet" },
              { label: "智能修复", desc: "修复老照片、去除水印和瑕疵", icon: Sparkles, color: "text-accent-blue" },
              { label: "图片扩展", desc: "扩展画布，AI 智能填充边缘", icon: Crop, color: "text-accent-purple" },
            ].map((item) => (
              <div
                key={item.label}
                className="flex items-start gap-3 p-5 rounded-2xl bg-cosmic-surface border border-cosmic-border text-left"
              >
                <item.icon className={cn("w-6 h-6 mt-0.5 flex-shrink-0", item.color)} />
                <div>
                  <span className="text-body-sm font-semibold text-text-primary block">
                    {item.label}
                  </span>
                  <span className="text-caption text-text-tertiary">
                    {item.desc}
                  </span>
                </div>
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
                { label: "图片创作", href: "/create/image", icon: "🖼️" },
                { label: "AI 放大", href: "/create/upscale", icon: "🔍" },
                { label: "去背景", href: "/create/bg-remove", icon: "✂️" },
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

          {/* ── Info Notice ── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.4 }}
            className="mt-4 p-5 rounded-2xl bg-cosmic-subtle/50 border border-cosmic-border/60 text-left"
          >
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-accent-cyan mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="text-body-sm font-semibold text-text-primary mb-1">
                  使用说明
                </h3>
                <p className="text-body-sm text-text-secondary">
                  图片编辑器已集成在图片创作页面中。点击上方按钮进入图片创作，
                  上传图片后即可使用 AI 重绘、风格迁移、图片扩展等编辑功能。
                  支持通过 Prompt 精确控制编辑效果。
                </p>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
