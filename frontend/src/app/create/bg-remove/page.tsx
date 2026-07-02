"use client";

import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { ArrowRight, Sparkles, Zap, Scissors } from "lucide-react";
import { useCreationStore } from "@/lib/stores";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function BgRemovePage() {
  const router = useRouter();
  const { setPrompt } = useCreationStore();

  const handleGoToImage = () => {
    setPrompt("移除背景，保留主体，透明背景PNG输出");
    router.push("/create/image?tool=removebg");
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
            <span className="text-5xl">✂️</span>
          </motion.div>

          {/* ── Title + Description ── */}
          <div className="space-y-3">
            <h1 className="text-h2 text-text-primary tracking-tight">
              AI 去背景
            </h1>
            <p className="text-body text-text-secondary max-w-md mx-auto leading-relaxed">
              智能移除图片背景，输出透明 PNG。精准识别主体轮廓，一键去除背景，适用于电商产品图、人物抠图等场景。
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
              <Scissors className="w-4 h-4" />
              跳转到图片创作
              <ArrowRight className="w-4 h-4" />
            </button>
          </motion.div>

          {/* ── Feature Highlights ── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.4 }}
            className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4"
          >
            {[
              { label: "智能识别", desc: "AI 自动识别主体与背景边界" },
              { label: "透明输出", desc: "导出标准透明 PNG 格式" },
              { label: "高清保留", desc: "原始分辨率无损输出" },
            ].map((item) => (
              <div
                key={item.label}
                className="flex flex-col items-center gap-2 p-5 rounded-2xl bg-cosmic-surface border border-cosmic-border text-center"
              >
                <Sparkles className="w-6 h-6 text-accent-cyan" />
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
                { label: "AI 放大", href: "/create/upscale", icon: "🔍" },
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

          {/* ── Use Cases ── */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.4 }}
            className="mt-4 p-6 rounded-2xl bg-cosmic-subtle/50 border border-cosmic-border/60 text-left"
          >
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-accent-cyan mt-0.5 flex-shrink-0" />
              <div>
                <h3 className="text-body-sm font-semibold text-text-primary mb-1">
                  适用场景
                </h3>
                <ul className="space-y-1.5 text-body-sm text-text-secondary">
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan/60 flex-shrink-0" />
                    电商产品图：一键去背景，生成白底图或透明图
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan/60 flex-shrink-0" />
                    人物抠图：精确识别发丝边缘，保留细节
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan/60 flex-shrink-0" />
                    设计素材：快速提取设计元素用于合成
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
