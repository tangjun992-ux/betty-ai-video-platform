"use client";

import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { ImagePlus, X, Upload, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface PromptAreaProps {
  prompt: string;
  onPromptChange: (p: string) => void;
  onSubmit: () => void;
  loading?: boolean;
  activeTab: "prompt" | "edit" | "combine";
  onTabChange: (t: "prompt" | "edit" | "combine") => void;
  referenceFiles: Array<{ preview: string }>;
  onAddReference: (f: File) => void;
  onRemoveReference: (idx: number) => void;
  suggestions?: string[];
  onSuggestionClick?: (s: string) => void;
}

const TABS = [
  { id: "prompt" as const, label: "Prompt" },
  { id: "edit" as const, label: "编辑" },
  { id: "combine" as const, label: "合并图像" },
];

export function PromptArea({
  prompt,
  onPromptChange,
  onSubmit,
  loading,
  activeTab,
  onTabChange,
  referenceFiles,
  onAddReference,
  onRemoveReference,
  suggestions = [],
  onSuggestionClick,
}: PromptAreaProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [focused, setFocused] = useState(false);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) onAddReference(f);
    e.target.value = "";
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (prompt.trim()) onSubmit();
    }
  };

  return (
    <div className="flex-1 flex flex-col">
      {/* Tabs */}
      <div className="flex items-center gap-1 mb-3">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              "px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200",
              activeTab === tab.id
                ? "bg-accent-cyan/[0.08] text-accent-cyan"
                : "text-text-secondary hover:text-text-accent-cyan hover:bg-cosmic-subtle"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Input */}
      <motion.div
        animate={{
          boxShadow: focused
            ? "0 0 0 2px hsl(252 78% 63% / 0.25), 0 0 20px hsl(252 78% 63% / 0.08)"
            : "0 0 0 1px hsl(240 12% 90% / 1)",
        }}
        className="flex-1 flex flex-col rounded-2xl bg-cosmic-surface/30 border border-cosmic-border/50 overflow-hidden transition-all duration-300"
      >
        {/* Reference Images */}
        {referenceFiles.length > 0 && (
          <div className="flex gap-2 p-3 pb-0 flex-wrap">
            {referenceFiles.map((ref, i) => (
              <div key={i} className="relative group w-16 h-16 rounded-lg overflow-hidden border border-cosmic-border/50">
                <img src={ref.preview} alt="参考图" className="w-full h-full object-cover" />
                <button
                  onClick={() => onRemoveReference(i)}
                  className="absolute top-0.5 right-0.5 w-5 h-5 rounded-full bg-black/60 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="w-3 h-3 text-text-accent-cyan" />
                </button>
              </div>
            ))}
          </div>
        )}

        <textarea
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder="描述你想要创作的图像，或上传图片进行编辑..."
          rows={3}
          className="flex-1 w-full bg-transparent border-0 resize-none px-4 py-3 text-sm placeholder:text-text-secondary/50 focus:outline-none"
        />

        {/* Bottom Bar */}
        <div className="flex items-center justify-between px-4 py-2.5 border-t border-cosmic-border/40">
          <div className="flex items-center gap-2">
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              onChange={handleFile}
              className="hidden"
            />
            <button
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-accent-cyan hover:bg-cosmic-subtle transition-all"
            >
              <ImagePlus className="w-3.5 h-3.5" />
              <span>添加参考图</span>
            </button>
            <button
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-accent-cyan hover:bg-cosmic-subtle transition-all"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>上传</span>
            </button>
          </div>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={onSubmit}
            disabled={!prompt.trim() || loading}
            className={cn(
              "flex items-center gap-2 px-6 py-2 rounded-xl text-sm font-semibold transition-all duration-200",
              prompt.trim() && !loading
                ? "bg-accent-cyan text-white hover:bg-accent-cyan/90 shadow-button-glow"
                : "bg-cosmic-subtle text-text-secondary cursor-not-allowed"
            )}
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>生成中...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>生成</span>
              </>
            )}
          </motion.button>
        </div>
      </motion.div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {suggestions.map((s, i) => (
            <motion.button
              key={i}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => onSuggestionClick?.(s)}
              className="px-3 py-1.5 rounded-full text-xs bg-cosmic-surface/50 border border-cosmic-border/40 text-text-secondary hover:text-text-accent-cyan hover:border-cosmic-border transition-all"
            >
              {s}
            </motion.button>
          ))}
        </div>
      )}
    </div>
  );
}
