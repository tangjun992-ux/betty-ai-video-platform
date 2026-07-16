"use client";

import { useState, useRef, useCallback, useEffect, type DragEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, Send, Wand2, ImagePlus, Video, Music, X, Play, Upload,
  Film, Layers, GripHorizontal, Plus, ChevronRight, Zap,
  RefreshCw, Lightbulb, Link2, Camera,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { CosmicGenerateButton } from "@/components/cosmic/CosmicGenerateButton";

/* ═════════════════════════════════════════════════════════
   CosmicVideoPromptArea
   视频 Prompt 输入区 — 风格标签 · 参考素材 · AI 优化 · 多镜头
   ═════════════════════════════════════════════════════════ */

export interface ReferenceMedia {
  id: string;
  type: "image" | "video" | "audio";
  file: File;
  preview: string;
  name: string;
}

export interface MultiShot {
  id: string;
  prompt: string;
  label: string;
}

interface CosmicVideoPromptAreaProps {
  prompt: string;
  onPromptChange: (p: string) => void;
  onSubmit: () => void;
  loading?: boolean;

  // References
  references: ReferenceMedia[];
  onAddReference: (f: File, type: "image" | "video" | "audio") => void;
  onRemoveReference: (id: string) => void;

  // Multi-shot
  multiShotMode: boolean;
  onMultiShotToggle: (v: boolean) => void;
  shots: MultiShot[];
  onShotAdd: () => void;
  onShotUpdate: (id: string, prompt: string) => void;
  onShotRemove: (id: string) => void;

  // AI enhance
  onOptimizePrompt?: () => void;
  enhancingPrompt?: boolean;

  // Suggestions
  suggestions?: string[];
  onSuggestionClick?: (s: string) => void;

  // Quick styles
  styleTags?: Array<{ label: string; icon?: React.ReactNode }>;
  onStyleClick?: (tag: string) => void;

  // Omni 一体控件
  generateAudio?: boolean;
  onGenerateAudioChange?: (v: boolean) => void;
  postLipsync?: boolean;
  onPostLipsyncChange?: (v: boolean) => void;

  className?: string;
}

export function CosmicVideoPromptArea({
  prompt,
  onPromptChange,
  onSubmit,
  loading = false,
  references,
  onAddReference,
  onRemoveReference,
  multiShotMode,
  onMultiShotToggle,
  shots,
  onShotAdd,
  onShotUpdate,
  onShotRemove,
  onOptimizePrompt,
  enhancingPrompt = false,
  suggestions = [],
  onSuggestionClick,
  styleTags = [],
  onStyleClick,
  generateAudio = false,
  onGenerateAudioChange,
  postLipsync = false,
  onPostLipsyncChange,
  className,
}: CosmicVideoPromptAreaProps) {
  const [isFocused, setIsFocused] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [activeShot, setActiveShot] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 180) + "px";
  }, [prompt]);

  // Keyboard submit
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (prompt.trim() && !loading) onSubmit();
    }
  };

  // Drag & drop
  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };
  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const files = Array.from(e.dataTransfer.files);
      for (const f of files) {
        const type = f.type.startsWith("video/")
          ? "video"
          : f.type.startsWith("audio/")
          ? "audio"
          : "image";
        onAddReference(f, type);
      }
    },
    [onAddReference]
  );

  const defaultStyleTags = [
    { label: "电影感", icon: <Film className="w-3 h-3" /> },
    { label: "赛博朋克", icon: <Zap className="w-3 h-3" /> },
    { label: "慢镜头", icon: <Play className="w-3 h-3" /> },
    { label: "延时摄影", icon: <Camera className="w-3 h-3" /> },
    { label: "第一视角", icon: <ChevronRight className="w-3 h-3" /> },
    { label: "航拍", icon: <Layers className="w-3 h-3" /> },
  ];
  const tags = styleTags.length > 0 ? styleTags : defaultStyleTags;

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      {/* ── Style Tags ── */}
      <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide pb-1">
        <span className="text-caption text-text-tertiary/70 flex-shrink-0 font-medium">
          风格
        </span>
        {tags.map((tag) => (
          <button
            key={tag.label}
            onClick={() => onStyleClick?.(tag.label)}
            className={cn(
              "flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full",
              "bg-cosmic-subtle border border-cosmic-border",
              "text-caption text-text-tertiary",
              "hover:bg-cosmic-subtle hover:text-text-secondary hover:border-cosmic-border-hover",
              "active:bg-cosmic-subtle active:scale-95",
              "transition-all duration-200"
            )}
          >
            {tag.icon}
            <span>{tag.label}</span>
          </button>
        ))}
        <button className="flex-shrink-0 inline-flex items-center justify-center w-7 h-7 rounded-full bg-cosmic-subtle border border-cosmic-border text-text-tertiary/60 hover:text-text-tertiary hover:border-cosmic-border-hover transition-all">
          <Plus className="w-3 h-3" />
        </button>
      </div>

      {/* ── Main Prompt Card ── */}
      <motion.div
        ref={dropZoneRef}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        animate={{
          borderColor: isDragging
            ? "hsl(248 75% 63% / 0.5)"
            : isFocused
            ? "hsl(248 75% 63% / 0.3)"
            : "hsl(240 20% 91%)",
          boxShadow: isDragging
            ? "0 8px 24px -6px hsl(248 75% 63% / 0.25)"
            : isFocused
            ? "0 6px 18px -6px hsl(248 75% 63% / 0.18)"
            : "0 1px 3px 0 rgb(18 18 28 / 0.06)",
        }}
        className={cn(
          "relative rounded-2xl overflow-hidden",
          "bg-cosmic-surface",
          "border border-cosmic-border",
          "shadow-elevation-md",
          "transition-all duration-300"
        )}
      >
        {/* Drop overlay */}
        <AnimatePresence>
          {isDragging && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-20 bg-accent-cyan/5 backdrop-blur-sm flex items-center justify-center"
            >
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-3 rounded-2xl bg-accent-cyan/10 border-2 border-dashed border-accent-cyan/30 flex items-center justify-center">
                  <Upload className="w-7 h-7 text-accent-cyan" />
                </div>
                <p className="text-body-sm text-text-secondary font-medium">
                  拖放图片/视频/音频到此处
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Reference Media Strip ── */}
        {references.length > 0 && (
          <div className="flex gap-2 p-3 pb-0 overflow-x-auto scrollbar-hide">
            {references.map((ref) => (
              <div
                key={ref.id}
                className="relative group flex-shrink-0 w-16 h-16 rounded-lg overflow-hidden border border-cosmic-border/60"
              >
                {ref.type === "video" ? (
                  <video src={ref.preview} className="w-full h-full object-cover" />
                ) : ref.type === "image" ? (
                  <img src={ref.preview} alt={ref.name} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full bg-cosmic-subtle flex items-center justify-center">
                    <Music className="w-5 h-5 text-text-tertiary" />
                  </div>
                )}
                {/* Type badge */}
                <span
                  className={cn(
                    "absolute top-0.5 left-0.5 px-1 py-0 text-[9px] font-semibold rounded",
                    ref.type === "video" && "bg-blue-500/80 text-white",
                    ref.type === "image" && "bg-amber-500/80 text-white",
                    ref.type === "audio" && "bg-emerald-500/80 text-white"
                  )}
                >
                  {ref.type === "video" ? "VID" : ref.type === "image" ? "IMG" : "AUD"}
                </span>
                <button
                  onClick={() => onRemoveReference(ref.id)}
                  className="absolute top-0.5 right-0.5 w-5 h-5 rounded-full bg-black/70 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <X className="w-3 h-3 text-white" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* ── Multi-Shot Strip ── */}
        {multiShotMode && shots.length > 0 && (
          <div className="px-3 pt-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Film className="w-3.5 h-3.5 text-accent-violet" />
              <span className="text-caption font-semibold text-accent-violet">
                多镜头模式 · {shots.length} 镜头
              </span>
            </div>
            <div className="flex gap-2 overflow-x-auto scrollbar-hide pb-1">
              {shots.map((shot, idx) => (
                <button
                  key={shot.id}
                  onClick={() => setActiveShot(shot.id === activeShot ? null : shot.id)}
                  className={cn(
                    "flex-shrink-0 flex flex-col gap-0.5 p-2 rounded-lg border transition-all duration-200 text-left min-w-[120px]",
                    activeShot === shot.id
                      ? "bg-accent-violet/10 border-accent-violet/30"
                      : "bg-cosmic-subtle border-cosmic-border hover:border-cosmic-border-hover"
                  )}
                >
                  <span className="text-[10px] font-semibold text-text-tertiary">
                    镜头 {idx + 1}
                  </span>
                  <span className="text-caption text-text-secondary line-clamp-2 leading-tight">
                    {shot.prompt || "描述这个镜头..."}
                  </span>
                  <span className="text-[9px] text-text-tertiary/50 mt-0.5">
                    {shot.label}
                  </span>
                </button>
              ))}
              <button
                onClick={onShotAdd}
                className="flex-shrink-0 w-12 h-16 rounded-lg border border-dashed border-cosmic-border/60 flex items-center justify-center hover:border-accent-violet/30 hover:bg-accent-violet/[0.03] transition-all"
              >
                <Plus className="w-4 h-4 text-text-tertiary" />
              </button>
            </div>
          </div>
        )}

        {/* ── Active Shot Editor ── */}
        <AnimatePresence>
          {multiShotMode &&
            activeShot &&
            (() => {
              const shot = shots.find((s) => s.id === activeShot);
              if (!shot) return null;
              return (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden border-t border-cosmic-border/30"
                >
                  <div className="p-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-caption font-medium text-accent-violet">
                        编辑镜头
                      </span>
                      <button
                        onClick={() => onShotRemove(shot.id)}
                        className="text-[10px] text-destructive/70 hover:text-destructive transition-colors"
                      >
                        移除
                      </button>
                    </div>
                    <textarea
                      value={shot.prompt}
                      onChange={(e) => onShotUpdate(shot.id, e.target.value)}
                      placeholder={`镜头 ${shots.indexOf(shot) + 1} 的 prompt...`}
                      rows={2}
                      className="w-full bg-cosmic-subtle border border-cosmic-border rounded-lg px-3 py-2 text-body-sm text-text-accent-cyan placeholder:text-text-tertiary/50 resize-none focus:outline-none focus:border-accent-violet/30 transition-all"
                    />
                  </div>
                </motion.div>
              );
            })()}
        </AnimatePresence>

        {/* ── Textarea ── */}
        <div className="relative p-4 pb-2">
          <div
            className={cn(
              "absolute left-0 top-1/3 bottom-1/3 w-0.5 rounded-r-full transition-all duration-300",
              "bg-gradient-to-b from-accent-cyan via-accent-blue to-accent-violet",
              (isFocused || prompt.length > 0) ? "opacity-100" : "opacity-0"
            )}
          />
          <textarea
            ref={textareaRef}
            value={prompt}
            onChange={(e) => onPromptChange(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onKeyDown={handleKeyDown}
            placeholder="描述你想要的视频画面：场景、运镜、光影、氛围..."
            rows={3}
            className={cn(
              "w-full resize-none bg-transparent",
              "text-body text-text-accent-cyan placeholder:text-text-tertiary/45",
              "focus:outline-none",
              "min-h-[72px]"
            )}
          />
        </div>

        {/* ── Bottom Action Bar ── */}
        <div className="flex items-center justify-between px-4 pb-3 gap-2 flex-wrap">
          {/* Left: Feature toggles */}
          <div className="flex items-center gap-1.5">
            {/* AI Optimize */}
            {onOptimizePrompt && (
              <button
                onClick={onOptimizePrompt}
                disabled={enhancingPrompt || !prompt.trim()}
                className={cn(
                  "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-caption transition-all duration-200",
                  "bg-accent-cyan/[0.06] border border-accent-cyan/15",
                  "text-accent-cyan hover:bg-accent-cyan/[0.12] hover:border-accent-cyan/30",
                  "disabled:opacity-30 disabled:cursor-not-allowed"
                )}
              >
                {enhancingPrompt ? (
                  <RefreshCw className="w-3 h-3 animate-spin" />
                ) : (
                  <Lightbulb className="w-3 h-3" />
                )}
                <span>AI 优化</span>
              </button>
            )}

            {/* Bind Elements — insert @ImageN/@VideoN/@AudioN for Seedance Omni */}
            <button
              type="button"
              onClick={() => {
                const imgs = references.filter((r) => r.type === "image");
                const vids = references.filter((r) => r.type === "video");
                const auds = references.filter((r) => r.type === "audio");
                const tags = [
                  ...imgs.map((_, i) => `@Image${i + 1}`),
                  ...vids.map((_, i) => `@Video${i + 1}`),
                  ...auds.map((_, i) => `@Audio${i + 1}`),
                ];
                if (!tags.length) return;
                const prefix = tags.join(" ");
                onPromptChange(prompt.trim() ? `${prompt.trim()}\n${prefix}` : prefix);
              }}
              disabled={references.length === 0}
              className={cn(
                "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-caption transition-all duration-200",
                "bg-cosmic-subtle border border-cosmic-border",
                "text-text-tertiary hover:text-text-secondary hover:bg-cosmic-subtle",
                "disabled:opacity-30 disabled:cursor-not-allowed"
              )}
              title="将参考素材绑定为 @ImageN / @VideoN / @AudioN"
            >
              <Link2 className="w-3 h-3" />
              <span>绑定元素</span>
            </button>

            {/* Seedance generate_audio (not Kling lipsync) */}
            {onGenerateAudioChange && (
              <button
                type="button"
                onClick={() => onGenerateAudioChange(!generateAudio)}
                className={cn(
                  "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-caption transition-all duration-200",
                  generateAudio
                    ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-600"
                    : "bg-cosmic-subtle border border-cosmic-border text-text-tertiary hover:text-text-secondary"
                )}
                title="Seedance Omni 生成音轨（非口型同步）"
              >
                <Music className="w-3 h-3" />
                <span>生成音轨</span>
              </button>
            )}

            {/* Post → Studio Lip-Sync (separate SKU) */}
            {onPostLipsyncChange && (
              <button
                type="button"
                onClick={() => onPostLipsyncChange(!postLipsync)}
                className={cn(
                  "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-caption transition-all duration-200",
                  postLipsync
                    ? "bg-purple-500/10 border border-purple-500/30 text-purple-500"
                    : "bg-cosmic-subtle border border-cosmic-border text-text-tertiary hover:text-text-secondary"
                )}
                title="成片后跳转唇形同步（Kling avatar，≠ Act-One）"
              >
                <Camera className="w-3 h-3" />
                <span>完成后唇形</span>
              </button>
            )}

            {/* Multi-Shot Mode */}
            <button
              onClick={() => onMultiShotToggle(!multiShotMode)}
              className={cn(
                "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-caption transition-all duration-200",
                multiShotMode
                  ? "bg-accent-violet/[0.1] border border-accent-violet/25 text-accent-violet"
                  : "bg-cosmic-subtle border border-cosmic-border text-text-tertiary hover:text-text-secondary hover:bg-cosmic-subtle"
              )}
            >
              <Film className="w-3 h-3" />
              <span>Multi-Shot</span>
            </button>

            {/* Omni chip when multi-ref */}
            {(references.filter((r) => r.type === "image").length > 1
              || references.some((r) => r.type === "video" || r.type === "audio")) && (
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium bg-amber-500/10 border border-amber-500/25 text-amber-700 dark:text-amber-300">
                Omni · 图≤9 视≤3 音≤3
              </span>
            )}

            {/* Reference upload */}
            <label
              className={cn(
                "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-caption cursor-pointer transition-all duration-200",
                "bg-cosmic-subtle border border-cosmic-border",
                "text-text-tertiary hover:text-text-secondary hover:bg-cosmic-subtle"
              )}
            >
              <ImagePlus className="w-3 h-3" />
              <span>参考素材</span>
              <input
                type="file"
                accept="image/*,video/*,audio/*"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (!f) return;
                  const type = f.type.startsWith("video/")
                    ? "video"
                    : f.type.startsWith("audio/")
                    ? "audio"
                    : "image";
                  onAddReference(f, type);
                }}
              />
            </label>
          </div>

          {/* Right: Submit */}
          <CosmicGenerateButton
            onClick={onSubmit}
            loading={loading}
            disabled={!prompt.trim()}
            size="md"
            icon={<Sparkles className="w-4 h-4" />}
          >
            {multiShotMode ? `生成 ${shots.length} 镜头` : "生成视频"}
          </CosmicGenerateButton>
        </div>
      </motion.div>

      {/* ── Quick Suggestions ── */}
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s, i) => (
            <motion.button
              key={i}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              onClick={() => onSuggestionClick?.(s)}
              className="px-3 py-1.5 rounded-full text-caption bg-cosmic-subtle border border-cosmic-border text-text-tertiary hover:text-text-secondary hover:bg-cosmic-subtle hover:border-cosmic-border-hover transition-all duration-200"
            >
              <Wand2 className="w-3 h-3 inline mr-1 -mt-0.5 text-accent-cyan/60" />
              {s}
            </motion.button>
          ))}
        </div>
      )}
    </div>
  );
}
