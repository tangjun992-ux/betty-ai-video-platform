"use client";

import { useState, useRef, useEffect, useCallback, type DragEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Wand2, ImageIcon, X, Upload, ImagePlus } from "lucide-react";
import { cn } from "@/lib/utils";
import { CosmicGenerateButton } from "./CosmicGenerateButton";

/* ─────────────────────────────────────────────────────
   CosmicPromptCard
   深空 Prompt 输入卡 — 毛玻璃 + 渐变辉光 + 参考图 + 建议
   ───────────────────────────────────────────────────── */

export interface ReferenceFile {
  preview: string;
  name?: string;
}

interface CosmicPromptCardProps {
  onSubmit: (prompt: string) => void;
  placeholder?: string;
  suggestions?: string[];
  className?: string;
  loading?: boolean;
  mode?: string;
  initialValue?: string; // pre-fill (e.g. remix from explore/library)

  // Reference image support
  referenceFiles?: ReferenceFile[];
  onAddReference?: (file: File) => void;
  onRemoveReference?: (index: number) => void;
}

export function CosmicPromptCard({
  onSubmit,
  placeholder = "描述你想要的画面，AI 将为你创作...",
  suggestions = [],
  className,
  loading = false,
  mode,
  initialValue,
  referenceFiles = [],
  onAddReference,
  onRemoveReference,
}: CosmicPromptCardProps) {
  const [prompt, setPrompt] = useState("");

  // Sync external pre-fill into the internal textarea state
  useEffect(() => {
    if (initialValue) setPrompt(initialValue);
  }, [initialValue]);
  const [isFocused, setIsFocused] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea up to 200px
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 200) + "px";
  }, [prompt]);

  const handleSubmit = useCallback(() => {
    if (!prompt.trim() || loading) return;
    onSubmit(prompt.trim());
    setPrompt("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [prompt, loading, onSubmit]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f && onAddReference) onAddReference(f);
    e.target.value = "";
  };

  // Drag & drop
  const handleDragOver = (e: DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e: DragEvent) => { e.preventDefault(); setIsDragging(false); };
  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f && onAddReference) onAddReference(f);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        "relative w-full rounded-2xl",
        "bg-cosmic-surface",
        "border transition-all duration-300",
        isDragging
          ? "border-accent-cyan/40 shadow-glow-medium"
          : isFocused
          ? "border-accent-cyan/25 shadow-glow-subtle"
          : "border-cosmic-border/50",
        "shadow-elevation-md",
        className
      )}
    >
      {/* ── Drop overlay ── */}
      <AnimatePresence>
        {isDragging && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-20 bg-accent-cyan/5 backdrop-blur-sm rounded-2xl flex items-center justify-center"
          >
            <div className="text-center">
              <div className="w-14 h-14 mx-auto mb-2 rounded-xl bg-accent-cyan/10 border-2 border-dashed border-accent-cyan/30 flex items-center justify-center">
                <Upload className="w-6 h-6 text-accent-cyan" />
              </div>
              <p className="text-body-sm text-text-secondary font-medium">拖放图片到此处</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Top inner glow edge ── */}
      <div className="absolute inset-x-4 top-0 h-px bg-gradient-to-r from-transparent via-cosmic-border to-transparent" />

      {/* ── Mode badge ── */}
      {mode && (
        <div className="absolute -top-3 left-4 px-3 py-0.5 rounded-full bg-cosmic-surface border border-cosmic-border text-caption text-text-secondary shadow-elevation-sm z-10">
          <span className="flex items-center gap-1.5">
            <ImageIcon className="w-3 h-3 text-accent-cyan" />
            {mode}
          </span>
        </div>
      )}

      {/* ── Reference Images Strip ── */}
      {referenceFiles.length > 0 && (
        <div className="flex gap-2 px-5 pt-4 pb-0 flex-wrap">
          {referenceFiles.map((ref, i) => (
            <div
              key={i}
              className="relative group w-16 h-16 rounded-lg overflow-hidden border border-cosmic-border/60 flex-shrink-0"
            >
              <img src={ref.preview} alt={ref.name || "参考图"} className="w-full h-full object-cover" />
              {onRemoveReference && (
                <button
                  onClick={() => onRemoveReference(i)}
                  className="absolute top-0.5 right-0.5 w-5 h-5 rounded-full bg-black/70 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="w-3 h-3 text-white" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Prompt input area ── */}
      <div className="relative p-5 pb-4">
        {/* Left accent bar */}
        <div
          className={cn(
            "absolute left-0 top-1/3 bottom-1/3 w-0.5 rounded-r-full",
            "bg-gradient-to-b from-accent-cyan via-accent-blue to-accent-violet",
            "opacity-0 transition-opacity duration-300",
            (isFocused || prompt.length > 0) && "opacity-100"
          )}
        />

        <textarea
          ref={textareaRef}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={3}
          className={cn(
            "w-full resize-none bg-transparent",
            "text-body text-text-primary placeholder:text-text-tertiary/45",
            "focus:outline-none",
            "min-h-[80px]"
          )}
        />
      </div>

      {/* ── Bottom bar ── */}
      <div className="flex items-center justify-between px-5 pb-4 gap-3">
        {/* Left: suggestions + ref upload */}
        <div className="flex items-center gap-2 overflow-x-auto flex-1 scrollbar-hide">
          {suggestions.slice(0, 3).map((s) => (
            <button
              key={s}
              onClick={() => setPrompt(s)}
              className={cn(
                "flex-shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-full",
                "bg-cosmic-subtle border border-cosmic-border",
                "text-caption text-text-tertiary",
                "hover:bg-cosmic-subtle hover:text-text-secondary hover:border-cosmic-border-hover",
                "active:bg-cosmic-subtle",
                "transition-all duration-200"
              )}
            >
              <Wand2 className="w-3 h-3" />
              <span className="truncate max-w-[100px]">{s}</span>
            </button>
          ))}

          {/* Reference upload button */}
          {onAddReference && (
            <>
              <input
                ref={fileRef}
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
              />
              <button
                onClick={() => fileRef.current?.click()}
                className={cn(
                  "flex-shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-full",
                  "bg-cosmic-subtle border border-cosmic-border",
                  "text-caption text-text-tertiary",
                  "hover:bg-cosmic-subtle hover:text-text-secondary hover:border-cosmic-border-hover",
                  "transition-all duration-200"
                )}
              >
                <ImagePlus className="w-3 h-3" />
                <span className="truncate">添加参考图</span>
              </button>
            </>
          )}
        </div>

        {/* Right: actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {prompt.length > 800 && (
            <span className={cn("text-caption font-mono", prompt.length > 980 ? "text-destructive" : "text-text-tertiary")}>
              {prompt.length}/1000
            </span>
          )}

          {prompt && (
            <button
              onClick={() => setPrompt("")}
              className="p-1.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-cosmic-subtle transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          )}

          <CosmicGenerateButton
            onClick={handleSubmit}
            loading={loading}
            disabled={!prompt.trim()}
            size="md"
            icon={<Sparkles className="w-4 h-4" />}
          >
            生成
          </CosmicGenerateButton>
        </div>
      </div>
    </motion.div>
  );
}
