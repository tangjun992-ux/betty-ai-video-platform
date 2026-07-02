"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { ArrowRight, Sparkles, Zap, ImageIcon } from "lucide-react";
import { useCreationStore } from "@/lib/stores";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function UpscalePage() {
  const router = useRouter();
  const { setPrompt } = useCreationStore();

  const handleGoToImage = () => {
    setPrompt("AI超分辨率放大，4倍画质提升");
    router.push("/create/image?tool=upscale");
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
            <span className="text-5xl">🔍</span>
          </motion.div>

          {/* ── Title + Description ── */}
          <div className="space-y-3">
            <h1 className="text-h2 text-text-primary tracking-tight">
              AI 放大
            </h1>
            <p className="text-body text-text-secondary max-w-md mx-auto leading-relaxed">
              2 倍 / 4 倍分辨率提升，无损画质。AI 超分辨率技术智能填补细节，让你的图片更清晰、更锐利。
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

          {/* ── Feature Highlights ── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.4 }}
            className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4"
          >
            {[
              { label: "2x 放大", desc: "分辨率翻倍，适合社交媒体分享", icon: "2️⃣" },
              { label: "4x 放大", desc: "极致细节增强，适合打印输出", icon: "4️⃣" },
            ].map((item) => (
              <div
                key={item.label}
                className="flex flex-col items-center gap-2 p-5 rounded-2xl bg-cosmic-surface border border-cosmic-border text-center"
              >
                <span className="text-2xl">{item.icon}</span>
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
                { label: "图片创作", href: "/create/image", icon: "🖼️" },
                { label: "去背景", href: "/create/bg-remove", icon: "✂️" },
                { label: "图片编辑器", href: "/create/image-editor", icon: "🎨" },
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
                  点击上方按钮跳转到图片创作页面，系统将自动预设"放大"工具参数。
                  上传你想要放大的图片，选择 2x 或 4x 倍率，AI 将自动完成超分辨率处理。
                </p>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
