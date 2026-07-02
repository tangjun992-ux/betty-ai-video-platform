"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp, Settings2, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Quality } from "@/lib/stores";

interface Model {
  id: string;
  name: string;
  desc: string;
  badge?: string;
}

interface ParameterPanelProps {
  models: Model[];
  selectedModel: string;
  onModelSelect: (id: string) => void;
  aspectRatio: string;
  onAspectChange: (r: string) => void;
  resolution: string;
  onResolutionChange: (r: string) => void;
  quality: Quality;
  onQualityChange: (q: Quality) => void;
  count: number;
  onCountChange: (n: number) => void;
  duration?: number;
  onDurationChange?: (n: number) => void;
  type: "image" | "video";
}

const ASPECT_RATIOS = [
  { label: "1:1", value: "1080x1080", w: 1, h: 1 },
  { label: "16:9", value: "1920x1080", w: 16, h: 9 },
  { label: "9:16", value: "1080x1920", w: 9, h: 16 },
  { label: "4:3", value: "1280x960", w: 4, h: 3 },
  { label: "3:2", value: "1536x1024", w: 3, h: 2 },
];

const RESOLUTIONS = ["720p", "1080p", "2K", "4K"];
const COUNTS = [1, 2, 4, 8];
const DURATIONS = [3, 5, 10, 15, 30];

export function ParameterPanel({
  models,
  selectedModel,
  onModelSelect,
  aspectRatio,
  onAspectChange,
  resolution,
  onResolutionChange,
  quality,
  onQualityChange,
  count,
  onCountChange,
  duration = 5,
  onDurationChange,
  type,
}: ParameterPanelProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <div className="w-64 flex-shrink-0 space-y-5 pl-2">
      {/* Models */}
      <div>
        <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider mb-2">
          Models
        </p>
        <div className="space-y-1">
          {models.map((m) => (
            <button
              key={m.id}
              onClick={() => onModelSelect(m.id)}
              className={cn(
                "flex items-center justify-between w-full px-3 py-2 rounded-lg text-xs transition-all duration-200",
                selectedModel === m.id
                  ? "bg-accent-cyan/[0.08] border border-accent-cyan/20 text-accent-cyan"
                  : "text-text-secondary hover:text-text-accent-cyan hover:bg-cosmic-surface/30 border border-transparent"
              )}
            >
              <div className="flex flex-col items-start gap-0.5">
                <span className="font-medium">{m.name}</span>
                <span className="text-[10px] text-text-secondary/60">{m.desc}</span>
              </div>
              {m.badge && (
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-accent-cyan/[0.08] text-accent-cyan">
                  {m.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Aspect Ratio */}
      <div>
        <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider mb-2">
          比例
        </p>
        <div className="flex flex-wrap gap-1.5">
          {ASPECT_RATIOS.map((r) => (
            <button
              key={r.label}
              onClick={() => onAspectChange(r.label)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs border transition-all duration-200",
                aspectRatio === r.label
                  ? "bg-accent-cyan/[0.08] border-accent-cyan/20 text-accent-cyan"
                  : "border-cosmic-border/50 text-text-secondary hover:border-cosmic-border hover:text-text-accent-cyan"
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Resolution */}
      <div>
        <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider mb-2">
          分辨率
        </p>
        <div className="flex flex-wrap gap-1.5">
          {RESOLUTIONS.map((r) => (
            <button
              key={r}
              onClick={() => onResolutionChange(r)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs border transition-all duration-200",
                resolution === r
                  ? "bg-accent-cyan/[0.08] border-accent-cyan/20 text-accent-cyan"
                  : "border-cosmic-border/50 text-text-secondary hover:border-cosmic-border hover:text-text-accent-cyan"
              )}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Quantity */}
      <div>
        <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider mb-2">
          生成数量
        </p>
        <div className="flex gap-1.5">
          {COUNTS.map((n) => (
            <button
              key={n}
              onClick={() => onCountChange(n)}
              className={cn(
                "flex-1 py-1.5 rounded-lg text-xs border transition-all duration-200",
                count === n
                  ? "bg-accent-cyan/[0.08] border-accent-cyan/20 text-accent-cyan"
                  : "border-cosmic-border/50 text-text-secondary hover:border-cosmic-border hover:text-text-accent-cyan"
              )}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      {/* Video: Duration */}
      {type === "video" && onDurationChange && (
        <div>
          <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider mb-2">
            时长 (秒)
          </p>
          <div className="flex gap-1.5">
            {DURATIONS.map((d) => (
              <button
                key={d}
                onClick={() => onDurationChange(d)}
                className={cn(
                  "flex-1 py-1.5 rounded-lg text-xs border transition-all duration-200",
                  duration === d
                    ? "bg-accent-cyan/[0.08] border-accent-cyan/20 text-accent-cyan"
                    : "border-cosmic-border/50 text-text-secondary hover:border-cosmic-border hover:text-text-accent-cyan"
                )}
              >
                {d}s
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Advanced */}
      <div>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-accent-cyan transition-colors"
        >
          <Settings2 className="w-3.5 h-3.5" />
          <span>更多选项</span>
          {showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
        <AnimatePresence>
          {showAdvanced && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden mt-3 space-y-3"
            >
              {/* Quality */}
              <div>
                <p className="text-[11px] text-text-secondary/60 mb-1.5">质量</p>
                <div className="flex gap-1.5">
                  {(["fast", "balanced", "high"] as const).map((q) => (
                    <button
                      key={q}
                      onClick={() => onQualityChange(q)}
                      className={cn(
                        "flex-1 py-1.5 rounded-lg text-[10px] border transition-all duration-200",
                        quality === q
                          ? "bg-accent-cyan/[0.08] border-accent-cyan/20 text-accent-cyan"
                          : "border-cosmic-border/50 text-text-secondary hover:border-cosmic-border"
                      )}
                    >
                      {q === "fast" ? "快速" : q === "balanced" ? "均衡" : "高清"}
                    </button>
                  ))}
                </div>
              </div>

              {/* Info */}
              <div className="flex items-start gap-2 p-3 rounded-lg bg-cosmic-surface/30 border border-cosmic-border/40">
                <Info className="w-3.5 h-3.5 text-text-secondary flex-shrink-0 mt-0.5" />
                <p className="text-[10px] text-text-secondary/70 leading-relaxed">
                  高质量模式需要更多处理时间。建议在最终输出时使用。
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
