"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ImageIcon, Video, ArrowUp } from "lucide-react";
import { cn } from "@/lib/utils";

/* ─────────────────────────────────────────────────────
   HomeComposer
   首页 hero 创作入口 — 模式切换 + prompt 输入 + 快捷建议
   AURORA 亮色主题
   ───────────────────────────────────────────────────── */

type HomeMode = "agent" | "image" | "video";

interface ModeOption {
  id: HomeMode;
  label: string;
  icon: typeof Sparkles;
  href: string;
}

const MODES: ModeOption[] = [
  { id: "agent", label: "Agent", icon: Sparkles, href: "/agent" },
  { id: "image", label: "图片生成", icon: ImageIcon, href: "/create/image" },
  { id: "video", label: "视频生成", icon: Video, href: "/create/video" },
];

const SUGGESTIONS = [
  "电影级东京夜景，霓虹灯反射",
  "亚麻布上的哑光陶瓷杯，柔和窗光",
  "把这张自拍变成90年代动漫肖像",
];

export function HomeComposer() {
  const router = useRouter();
  const [mode, setMode] = useState<HomeMode>("agent");
  const [prompt, setPrompt] = useState("");

  const handleSubmit = useCallback(() => {
    if (!prompt.trim()) return;
    const encoded = encodeURIComponent(prompt.trim());
    const activeMode = MODES.find((m) => m.id === mode);
    if (activeMode) {
      router.push(`${activeMode.href}?prompt=${encoded}`);
    }
  }, [prompt, mode, router]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setPrompt(suggestion);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="w-full max-w-2xl mx-auto"
    >
      {/* ── Card ── */}
      <div
        className={cn(
          "relative rounded-xl",
          "bg-cosmic-surface border border-cosmic-border",
          "shadow-elevation-md"
        )}
      >
        {/* ── Mode Tabs ── */}
        <div className="flex items-center gap-1 px-3 pt-3 pb-2">
          {MODES.map((m) => {
            const Icon = m.icon;
            const isActive = mode === m.id;
            return (
              <motion.button
                key={m.id}
                onClick={() => setMode(m.id)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                className={cn(
                  "relative flex items-center gap-1.5 px-3.5 py-2 rounded-full",
                  "text-sm font-medium transition-colors duration-200",
                  isActive
                    ? "bg-brand/[0.08] text-brand"
                    : "text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle"
                )}
              >
                <Icon className="w-4 h-4" />
                <span>{m.label}</span>
                {isActive && (
                  <motion.div
                    layoutId="homeModePill"
                    className="absolute inset-0 rounded-full bg-brand/[0.08]"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
              </motion.button>
            );
          })}
        </div>

        {/* ── Prompt Input ── */}
        <AnimatePresence mode="wait">
          <motion.div
            key={mode}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="px-4 pb-3"
          >
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="描述你想要创作的内容…"
              rows={3}
              className={cn(
                "w-full resize-none rounded-lg px-3.5 py-3",
                "bg-cosmic-subtle",
                "text-body text-text-primary placeholder:text-text-tertiary/50",
                "focus:outline-none focus:ring-2 focus:ring-brand/40 focus:bg-cosmic-surface",
                "transition-all duration-200"
              )}
            />
          </motion.div>
        </AnimatePresence>

        {/* ── Bottom Bar: Suggestions + Submit + Shortcut ── */}
        <div className="flex items-center justify-between px-4 pb-4 gap-3">
          {/* Suggestions */}
          <div className="flex items-center gap-2 flex-wrap flex-1">
            {SUGGESTIONS.map((s, i) => (
              <motion.button
                key={s}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + i * 0.06, duration: 0.3 }}
                onClick={() => handleSuggestionClick(s)}
                className={cn(
                  "inline-flex items-center px-2.5 py-1.5 rounded-full",
                  "bg-cosmic-subtle border border-cosmic-border",
                  "text-caption text-text-secondary",
                  "hover:bg-brand/[0.06] hover:border-brand/20 hover:text-brand",
                  "active:bg-brand/[0.10]",
                  "transition-all duration-200",
                  "whitespace-nowrap"
                )}
              >
                {s}
              </motion.button>
            ))}
          </div>

          {/* Submit Button + Shortcut Hint */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-text-tertiary text-xs hidden sm:inline">
              ⌘ + ↵ 发送
            </span>
            <motion.button
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.96 }}
              onClick={handleSubmit}
              disabled={!prompt.trim()}
              className={cn(
                "flex items-center justify-center w-9 h-9 rounded-lg",
                "transition-all duration-200",
                prompt.trim()
                  ? "bg-brand text-white shadow-button-glow hover:bg-brand-600"
                  : "bg-cosmic-subtle text-text-disabled cursor-not-allowed"
              )}
            >
              <ArrowUp className="w-4 h-4" />
            </motion.button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
