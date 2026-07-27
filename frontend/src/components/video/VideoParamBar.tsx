"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronDown, Link2, Clock, Hash, Check } from "lucide-react";
import { cn } from "@/lib/utils";

/* ════════════════════════════════════════════════════════════
   VideoParamBar — dzine 式视频参数工具条
   模型下拉(图标/NEW/对勾) + 统一参数面板(比例形状网格 + 分辨率
   + 质量 + 时长 + 数量) + 字数/积分
   ════════════════════════════════════════════════════════════ */

const ASPECTS = [
  { id: "16:9", w: 16, h: 9 },
  { id: "9:16", w: 9, h: 16 },
  { id: "1:1", w: 1, h: 1 },
  { id: "4:3", w: 4, h: 3 },
  { id: "21:9", w: 21, h: 9 },
] as const;

const SIZE_OPTIONS = ["720p", "1080p", "2K", "4K"] as const;
const QUALITY_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "fast", label: "快速" },
  { value: "balanced", label: "均衡" },
  { value: "high", label: "高质量" },
];
const DURATION_OPTIONS = [5, 10, 15];
const COUNT_OPTIONS = [1, 2, 4];

const MODEL_COLORS: Record<string, string> = {
  "auto": "#8b8b96",
  "seedance-2.0": "#4f8ef7",
  "seedance-2.0-fast": "#38bdf8",
  "seedance": "#4f8ef7",
  "kling": "#f59e0b",
};
function modelColor(id: string): string {
  if (MODEL_COLORS[id]) return MODEL_COLORS[id];
  const key = Object.keys(MODEL_COLORS).find((k) => id.includes(k));
  return key ? MODEL_COLORS[key] : "#8b8b96";
}
function isNewModel(id: string): boolean {
  return /seedance-2.0|kling-2.5|omni/i.test(id);
}
function modelInitial(id: string, name?: string): string {
  if (id === "auto") return "A";
  const n = (name || id).replace(/[^a-z0-9]/gi, "");
  return (n[0] || "M").toUpperCase();
}

function ModelIcon({ id, name }: { id: string; name?: string }) {
  return (
    <span
      className="w-5 h-5 rounded-[5px] inline-flex items-center justify-center text-[10px] font-bold shrink-0"
      style={{ backgroundColor: modelColor(id), color: "rgba(0,0,0,0.75)" }}
    >
      {modelInitial(id, name)}
    </span>
  );
}

function useDropdown() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);
  return { open, setOpen, ref };
}

export interface VideoParamBarProps {
  models: Array<{ id: string; name: string; desc?: string; badge?: string }>;
  selectedModel: string;
  onModelSelect: (id: string) => void;
  aspectRatio: string;
  onAspect: (a: string) => void;
  resolution: string;
  onResolution: (r: string) => void;
  quality: string;
  onQuality: (q: string) => void;
  duration: number;
  onDuration: (d: number) => void;
  count: number;
  onCount: (n: number) => void;
  promptLength: number;
  credits?: number;
  moreExpanded?: boolean;
  onMoreToggle?: (v: boolean) => void;
}

export function VideoParamBar({
  models, selectedModel, onModelSelect,
  aspectRatio, onAspect, resolution, onResolution,
  quality, onQuality, duration, onDuration, count, onCount,
  promptLength, credits = 20, moreExpanded, onMoreToggle,
}: VideoParamBarProps) {
  const modelDd = useDropdown();
  const paramDd = useDropdown();
  const current = models.find((m) => m.id === selectedModel) || models[0];
  const qLabel = quality === "fast" ? "快速" : quality === "high" ? "高质量" : "均衡";

  return (
    <div className="flex items-center gap-1.5 flex-wrap rounded-b-2xl border border-t-0 border-cosmic-border bg-cosmic-subtle/35 px-3 py-2.5 -mt-px">
      {/* Model select */}
      <div className="relative" ref={modelDd.ref}>
        <button
          type="button"
          aria-haspopup="listbox"
          aria-expanded={modelDd.open}
          data-testid="video-model-select"
          onClick={() => modelDd.setOpen((v) => !v)}
          className="toolbar-btn !text-brand-strong"
        >
          <ModelIcon id={current?.id || "auto"} name={current?.name} />
          <span className="font-medium">{current?.name}</span>
          <ChevronDown className="w-3.5 h-3.5 opacity-50" />
        </button>
        {modelDd.open && (
          <div className="absolute left-0 top-full mt-1.5 z-50 w-64 rounded-xl border border-cosmic-border bg-cosmic-elevated shadow-elevation-lg overflow-hidden">
            <p className="px-3.5 pt-3 pb-1.5 text-[11px] text-text-tertiary">Model</p>
            <div className="max-h-80 overflow-y-auto pb-1.5">
              {models.map((m) => {
                const active = m.id === selectedModel;
                return (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => { onModelSelect(m.id); modelDd.setOpen(false); }}
                    className={cn(
                      "w-full flex items-center gap-2.5 px-3.5 py-2 text-left transition-colors",
                      active ? "bg-brand/10" : "hover:bg-cosmic-subtle"
                    )}
                  >
                    <span className={cn("w-3.5 h-3.5 shrink-0 flex items-center justify-center", active ? "text-brand-strong" : "text-transparent")}>
                      <Check className="w-3.5 h-3.5" />
                    </span>
                    <ModelIcon id={m.id} name={m.name} />
                    <span className={cn("flex-1 min-w-0 truncate text-[13px]", active ? "text-brand-strong font-medium" : "text-text-primary")}>
                      {m.name}
                    </span>
                    {m.badge && (
                      <span className="shrink-0 text-[9px] font-semibold px-1 py-0.5 rounded bg-brand/10 text-brand-strong border border-brand/20">
                        {m.badge}
                      </span>
                    )}
                    {!m.badge && isNewModel(m.id) && (
                      <span className="shrink-0 text-[9px] font-semibold px-1 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        NEW
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Unified param dropdown */}
      <div className="relative" ref={paramDd.ref}>
        <button
          type="button"
          aria-haspopup="listbox"
          aria-expanded={paramDd.open}
          data-testid="video-param-select"
          onClick={() => paramDd.setOpen((v) => !v)}
          className="toolbar-btn"
        >
          <span className="text-text-primary font-medium">{aspectRatio}</span>
          <span className="text-text-tertiary/50">|</span>
          <span className="text-text-primary font-medium">{resolution}</span>
          <span className="text-text-tertiary/50">|</span>
          <span className="text-text-primary font-medium">{duration}s</span>
          <span className="text-text-tertiary/50">|</span>
          <span className="text-text-primary font-medium">{qLabel}</span>
          <ChevronDown className="w-3.5 h-3.5 opacity-50" />
        </button>
        {paramDd.open && (
          <div className="absolute left-0 top-full mt-1.5 z-50 w-[302px] rounded-xl border border-cosmic-border bg-cosmic-elevated shadow-elevation-lg p-3.5 space-y-3.5">
            {/* Aspect Ratio */}
            <div>
              <p className="text-[11px] text-text-tertiary mb-2">Aspect Ratio</p>
              <div className="grid grid-cols-5 gap-1.5">
                {ASPECTS.map((a) => {
                  const active = a.id === aspectRatio;
                  return (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => onAspect(a.id)}
                      title={a.id}
                      className={cn(
                        "flex flex-col items-center justify-center gap-1 py-1.5 rounded-lg border transition-colors",
                        active ? "border-brand/60 bg-brand/10" : "border-transparent hover:bg-cosmic-subtle"
                      )}
                    >
                      <span
                        className={cn("border rounded-[2px] block", active ? "border-brand-strong" : "border-text-tertiary")}
                        style={{
                          aspectRatio: `${a.w}/${a.h}`,
                          width: a.w >= a.h ? "20px" : undefined,
                          height: a.h > a.w ? "20px" : undefined,
                        }}
                      />
                      <span className={cn("text-[9px] leading-none", active ? "text-brand-strong" : "text-text-tertiary")}>
                        {a.id}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Resolution */}
            <div>
              <p className="text-[11px] text-text-tertiary mb-2">Resolution</p>
              <div className="grid grid-cols-4 gap-1.5">
                {SIZE_OPTIONS.map((s) => {
                  const active = s === resolution;
                  return (
                    <button
                      key={s}
                      type="button"
                      onClick={() => onResolution(s)}
                      className={cn(
                        "h-8 rounded-lg border text-xs font-medium transition-colors",
                        active ? "border-brand/60 bg-brand/10 text-brand-strong" : "border-cosmic-border text-text-secondary hover:border-cosmic-border-hover"
                      )}
                    >
                      {s}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Duration */}
            <div>
              <p className="text-[11px] text-text-tertiary mb-2">Duration</p>
              <div className="grid grid-cols-3 gap-1.5">
                {DURATION_OPTIONS.map((d) => {
                  const active = d === duration;
                  return (
                    <button
                      key={d}
                      type="button"
                      onClick={() => onDuration(d)}
                      className={cn(
                        "h-8 rounded-lg border text-xs font-medium transition-colors inline-flex items-center justify-center gap-1",
                        active ? "border-brand/60 bg-brand/10 text-brand-strong" : "border-cosmic-border text-text-secondary hover:border-cosmic-border-hover"
                      )}
                    >
                      <Clock className="w-3 h-3 opacity-60" />{d}s
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Quality */}
            <div>
              <p className="text-[11px] text-text-tertiary mb-2">Image Quality</p>
              <div className="grid grid-cols-3 gap-1.5">
                {QUALITY_OPTIONS.map((q) => {
                  const active = q.value === quality;
                  return (
                    <button
                      key={q.value}
                      type="button"
                      onClick={() => onQuality(q.value)}
                      className={cn(
                        "h-8 rounded-lg border text-xs font-medium transition-colors",
                        active ? "border-brand/60 bg-brand/10 text-brand-strong" : "border-cosmic-border text-text-secondary hover:border-cosmic-border-hover"
                      )}
                    >
                      {q.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Count */}
            <div>
              <p className="text-[11px] text-text-tertiary mb-2">Count</p>
              <div className="grid grid-cols-3 gap-1.5">
                {COUNT_OPTIONS.map((c) => {
                  const active = c === count;
                  return (
                    <button
                      key={c}
                      type="button"
                      onClick={() => onCount(c)}
                      className={cn(
                        "h-8 rounded-lg border text-xs font-medium transition-colors inline-flex items-center justify-center gap-1",
                        active ? "border-brand/60 bg-brand/10 text-brand-strong" : "border-cosmic-border text-text-secondary hover:border-cosmic-border-hover"
                      )}
                    >
                      <Hash className="w-3 h-3 opacity-60" />{c}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* More (advanced) */}
      {onMoreToggle && (
        <button
          type="button"
          onClick={() => onMoreToggle(!moreExpanded)}
          data-testid="video-more-toggle"
          className={cn(
            "toolbar-btn",
            moreExpanded && "!text-brand-strong !bg-brand/5"
          )}
        >
          More
          <ChevronDown className={cn("w-3.5 h-3.5 opacity-50 transition-transform", moreExpanded && "rotate-180")} />
        </button>
      )}

      {/* Right: char count + credits */}
      <div className="ml-auto flex items-center gap-2.5">
        <span className="hidden sm:inline text-[11px] text-text-tertiary tabular-nums select-none">
          {promptLength}/5000
        </span>
        <span className="hidden sm:inline-flex items-center gap-1 text-[11px] text-text-tertiary select-none">
          <span className="w-1.5 h-1.5 rounded-full bg-brand" />~{credits}
        </span>
      </div>
    </div>
  );
}
