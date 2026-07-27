"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, ImagePlus, Upload, X, Clock, RefreshCw,
  Download, Video, ExternalLink, ImageIcon, Wand2, CheckCircle2,
  ChevronDown, Hash, SlidersHorizontal, Link2,
  Scissors, Expand, Maximize2, Layers, User, Package, Check, ArrowUp,
} from "lucide-react";
import { StyleCardSelector } from "@/components/StyleCardSelector";
import { CreativitySlider } from "@/components/CreativitySlider";
import { BatchPromptInput } from "@/components/BatchPromptInput";
import { Empty, ErrorState } from "@/components/StatusStates";
import { useAuthStore, useCreationStore, useOnboardingStore } from "@/lib/stores";
import { useToast } from "@/components/Toast";
import { submitGeneration, getTaskStatus, uploadImage, trackOnboarding, resolveMediaUrl, type GenerateResponse, type TaskResult, API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

// ═══════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════

const IMAGE_MODELS_FALLBACK = [
  { id: "auto", name: "Auto", desc: "智能选择" },
  { id: "gpt-image-2-text-to-image", name: "GPT Image 2", desc: "最高质量", badge: "Pro" },
  { id: "nano-banana-2", name: "Nano Banana 2", desc: "快速生成", badge: "Fast" },
];

const SUGGESTIONS = [
  "赛博朋克城市夜景，霓虹灯光，飞行汽车",
  "产品摄影，香水瓶，极简白色背景",
  "日式庭院，樱花飘落，柔光",
  "专业商务头像，现代办公室背景",
];

const PROMPT_TABS = [
  { id: "prompt" as const, label: "Prompt" },
  { id: "edit" as const, label: "编辑" },
  { id: "combine" as const, label: "合并图像" },
];

const QUALITY_OPTIONS: Array<{ value: "fast" | "balanced" | "high"; label: string }> = [
  { value: "fast", label: "快速" },
  { value: "balanced", label: "均衡" },
  { value: "high", label: "高质量" },
];
const COUNT_OPTIONS = [1, 2, 4, 8];

// ─── dzine 式比例 / 尺寸体系 ──────────────────────────────
const ASPECTS = [
  { id: "21:9", w: 21, h: 9 },
  { id: "16:9", w: 16, h: 9 },
  { id: "3:2", w: 3, h: 2 },
  { id: "4:3", w: 4, h: 3 },
  { id: "1:1", w: 1, h: 1 },
  { id: "4:5", w: 4, h: 5 },
  { id: "3:4", w: 3, h: 4 },
  { id: "9:16", w: 9, h: 16 },
] as const;
const SIZE_OPTIONS = ["1K", "2K", "4K"] as const;
type ImageSize = (typeof SIZE_OPTIONS)[number];

/** 按 dzine 规则计算最终输出尺寸（2K·16:9 = 2048×1152） */
function dimsFor(aspect: string, size: ImageSize): { w: number; h: number } {
  const longSide = size === "4K" ? 3840 : size === "2K" ? 2048 : 1280;
  const [aw, ah] = aspect.split(":").map(Number);
  let w: number, h: number;
  if (aw >= ah) {
    w = longSide;
    h = Math.max(8, Math.round((longSide * ah) / aw / 8) * 8);
  } else {
    h = longSide;
    w = Math.max(8, Math.round((longSide * aw) / ah / 8) * 8);
  }
  return { w, h };
}

// ─── 模型图标 / 参数随模型变化 ─────────────────────────────
const MODEL_COLORS: Record<string, string> = {
  "auto": "#8b8b96",
  "gpt-image-2": "#4f8ef7",
  "gpt-image-2-text-to-image": "#4f8ef7",
  "nano-banana": "#f5c518",
  "nano-banana-2": "#f5c518",
  "nano-banana-pro": "#f59e0b",
  "imagen-4": "#34d399",
  "imagen-4-fast": "#34d399",
  "imagen-4-ultra": "#34d399",
};
function modelColor(id: string): string {
  if (MODEL_COLORS[id]) return MODEL_COLORS[id];
  const key = Object.keys(MODEL_COLORS).find((k) => id.includes(k));
  return key ? MODEL_COLORS[key] : "#8b8b96";
}
function isNewModel(id: string): boolean {
  return /nano-banana-pro|imagen-4|seedream|flux/i.test(id);
}
function modelInitial(id: string, name?: string): string {
  if (id === "auto") return "A";
  const n = (name || id).replace(/[^a-z0-9]/gi, "");
  return (n[0] || "M").toUpperCase();
}

interface ModelParamConfig { sizes: ImageSize[]; aspects: string[]; }
const ALL_ASPECTS = ASPECTS.map((a) => a.id);
const MODEL_PARAMS: Record<string, ModelParamConfig> = {
  "gpt-image-2": { sizes: ["1K", "2K", "4K"], aspects: ALL_ASPECTS },
  "gpt-image-2-text-to-image": { sizes: ["1K", "2K", "4K"], aspects: ALL_ASPECTS },
  "nano-banana": { sizes: ["1K", "2K"], aspects: ["1:1", "16:9", "9:16", "4:3", "3:2"] },
  "nano-banana-2": { sizes: ["1K", "2K"], aspects: ["1:1", "16:9", "9:16", "4:3", "3:2"] },
  "nano-banana-pro": { sizes: ["1K", "2K", "4K"], aspects: ALL_ASPECTS },
  "imagen-4": { sizes: ["1K", "2K", "4K"], aspects: ALL_ASPECTS },
};
const DEFAULT_PARAMS: ModelParamConfig = { sizes: [...SIZE_OPTIONS], aspects: ALL_ASPECTS };
function paramConfigFor(modelId: string): ModelParamConfig {
  const key = Object.keys(MODEL_PARAMS).find((k) => modelId === k || modelId.includes(k));
  return key ? MODEL_PARAMS[key] : DEFAULT_PARAMS;
}

const IMAGE_APPS = [
  { icon: Wand2, label: "图片编辑器", desc: "AI 指令修图", href: "/create/image-editor" },
  { icon: Package, label: "产品图", desc: "电商产品摄影", href: "/create/product" },
  { icon: User, label: "专业头像", desc: "AI 写真头像", href: "/create/avatar" },
  { icon: Layers, label: "照片包", desc: "批量生成变体", href: "/create/photo-packs" },
  { icon: Expand, label: "图片扩展", desc: "智能外扩构图", href: "/create/extend" },
  { icon: Scissors, label: "去背景", desc: "一键透明 PNG", href: "/create/bg-remove" },
  { icon: Maximize2, label: "AI 放大", desc: "4K 超分辨率", href: "/create/upscale" },
];

// ═══════════════════════════════════════════════════════════
// Toolbar primitives (Yapper-style inline selects)
// ═══════════════════════════════════════════════════════════

interface ToolSelectProps<T extends string | number> {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: T;
  options: Array<{ value: T; label: string }>;
  onChange: (v: T) => void;
  minWidth?: string;
  testId?: string;
}

function ToolSelect<T extends string | number>({ icon: Icon, label, value, options, onChange, minWidth = "min-w-[120px]", testId }: ToolSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = options.find((o) => o.value === value);

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

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        data-testid={testId}
        onClick={() => setOpen((v) => !v)}
        className="toolbar-btn"
      >
        <Icon className="w-3.5 h-3.5 opacity-70" />
        <span className="text-text-tertiary">{label}</span>
        <span className="text-text-primary font-medium">{current?.label ?? value}</span>
        <ChevronDown className="w-3.5 h-3.5 opacity-50" />
      </button>
      {open && (
        <div className={`absolute left-0 top-full mt-1.5 z-50 ${minWidth} rounded-xl border border-cosmic-border bg-cosmic-elevated shadow-elevation-lg p-1`}>
          {options.map((opt) => (
            <button
              key={String(opt.value)}
              type="button"
              onClick={() => { onChange(opt.value); setOpen(false); }}
              className={cn(
                "w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-xs text-left transition-colors",
                opt.value === value
                  ? "bg-brand/10 text-brand-strong"
                  : "text-text-secondary hover:bg-cosmic-subtle hover:text-text-primary"
              )}
            >
              <span>{opt.label}</span>
              {opt.value === value && <Check className="w-3.5 h-3.5" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

interface ModelSelectProps {
  models: Array<{ id: string; name: string; desc?: string; badge?: string }>;
  value: string;
  onChange: (id: string) => void;
  testId?: string;
}

function ModelSelect({ models, value, onChange, testId }: ModelSelectProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = models.find((m) => m.id === value) || models[0];

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

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        data-testid={testId}
        onClick={() => setOpen((v) => !v)}
        className="toolbar-btn !text-brand-strong"
      >
        <ModelIcon id={current?.id || "auto"} name={current?.name} />
        <span className="font-medium">{current?.name}</span>
        <ChevronDown className="w-3.5 h-3.5 opacity-50" />
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1.5 z-50 w-64 rounded-xl border border-cosmic-border bg-cosmic-elevated shadow-elevation-lg overflow-hidden">
          <p className="px-3.5 pt-3 pb-1.5 text-[11px] text-text-tertiary">Model</p>
          <div className="max-h-80 overflow-y-auto pb-1.5">
            {models.map((m) => {
              const active = m.id === value;
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => { onChange(m.id); setOpen(false); }}
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
                  {isNewModel(m.id) && (
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
  );
}

// ─── dzine 式模型小图标 ────────────────────────────────────
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

// ─── dzine 式统一参数面板（比例形状网格 + 尺寸 + 质量 + 宽高联动）───
interface ParamDropdownProps {
  aspect: string;
  onAspect: (a: string) => void;
  size: ImageSize;
  onSize: (s: ImageSize) => void;
  quality: "fast" | "balanced" | "high";
  onQuality: (q: "fast" | "balanced" | "high") => void;
  config: ModelParamConfig;
  testId?: string;
}

function ParamDropdown({ aspect, onAspect, size, onSize, quality, onQuality, config, testId }: ParamDropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const dims = dimsFor(aspect, size);
  const qLabel = quality === "fast" ? "快速" : quality === "high" ? "高质量" : "均衡";

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

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        data-testid={testId}
        onClick={() => setOpen((v) => !v)}
        className="toolbar-btn"
      >
        <span className="text-text-primary font-medium">{aspect}</span>
        <span className="text-text-tertiary/50">|</span>
        <span className="text-text-primary font-medium">{size}</span>
        <span className="text-text-tertiary/50">|</span>
        <span className="text-text-primary font-medium">{qLabel}</span>
        <ChevronDown className="w-3.5 h-3.5 opacity-50" />
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-1.5 z-50 w-[302px] rounded-xl border border-cosmic-border bg-cosmic-elevated shadow-elevation-lg p-3.5 space-y-3.5">
          {/* Aspect Ratio */}
          <div>
            <p className="text-[11px] text-text-tertiary mb-2">Aspect Ratio</p>
            <div className="grid grid-cols-5 gap-1.5">
              {ASPECTS.map((a) => {
                const enabled = config.aspects.includes(a.id);
                const active = a.id === aspect;
                return (
                  <button
                    key={a.id}
                    type="button"
                    disabled={!enabled}
                    onClick={() => onAspect(a.id)}
                    title={a.id}
                    className={cn(
                      "flex flex-col items-center justify-center gap-1 py-1.5 rounded-lg border transition-colors",
                      active ? "border-brand/60 bg-brand/10" : "border-transparent hover:bg-cosmic-subtle",
                      !enabled && "opacity-30 cursor-not-allowed"
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

          {/* Image Size */}
          <div>
            <p className="text-[11px] text-text-tertiary mb-2">Image Size</p>
            <div className="grid grid-cols-3 gap-1.5">
              {SIZE_OPTIONS.map((s) => {
                const enabled = config.sizes.includes(s);
                const active = s === size;
                return (
                  <button
                    key={s}
                    type="button"
                    disabled={!enabled}
                    onClick={() => onSize(s)}
                    className={cn(
                      "h-8 rounded-lg border text-xs font-medium transition-colors",
                      active ? "border-brand/60 bg-brand/10 text-brand-strong" : "border-cosmic-border text-text-secondary hover:border-cosmic-border-hover",
                      !enabled && "opacity-30 cursor-not-allowed"
                    )}
                  >
                    {s}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Image Quality */}
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

          {/* Width / Height */}
          <div className="flex items-end gap-2 pt-0.5">
            <div className="flex-1">
              <p className="text-[10px] text-text-tertiary mb-1">Width</p>
              <div className="h-8 px-2.5 rounded-lg bg-cosmic-subtle border border-cosmic-border flex items-center justify-between text-xs text-text-primary">
                <span>{dims.w}</span>
                <span className="text-text-tertiary text-[10px]">px</span>
              </div>
            </div>
            <Link2 className="w-3.5 h-3.5 text-text-tertiary mb-2 shrink-0" />
            <div className="flex-1">
              <p className="text-[10px] text-text-tertiary mb-1">Height</p>
              <div className="h-8 px-2.5 rounded-lg bg-cosmic-subtle border border-cosmic-border flex items-center justify-between text-xs text-text-primary">
                <span>{dims.h}</span>
                <span className="text-text-tertiary text-[10px]">px</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// Page Component
// ═══════════════════════════════════════════════════════════

export default function CreateImagePage() {
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const completeOnboarding = useOnboardingStore((s) => s.completeFor);

  const {
    prompt, setPrompt, selectedModel, setSelectedModel,
    quality, setQuality, style, setStyle, creativity, setCreativity,
    resolution, setResolution, aspectRatio, setAspectRatio,
    count, setCount, referenceFiles, addReference, removeReference,
    addRecentPrompt, addResult, results,
    activeTab, setActiveTab,
  } = useCreationStore();

  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [prefillPrompt, setPrefillPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [moderationBlocked, setModerationBlocked] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [showMore, setShowMore] = useState(false);
  const [imageSize, setImageSize] = useState<ImageSize>("2K");

  const [progress, setProgress] = useState(0);
  const [progressStage, setProgressStage] = useState<string>("");
  const [estimatedSeconds, setEstimatedSeconds] = useState<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const [hasSubmitted, setHasSubmitted] = useState(false);
  const [imageModels, setImageModels] = useState(IMAGE_MODELS_FALLBACK);
  const [remixImageUrl, setRemixImageUrl] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/models/?status=active`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        const active = (d.active || []).filter(
          (m: { capabilities?: { media_types?: string[] } }) =>
            m.capabilities?.media_types?.includes("image")
        );
        if (!active.length) return;
        setImageModels([
          IMAGE_MODELS_FALLBACK[0],
          ...active.map((m: { id: string; display_name: string; description?: string; provider?: string }) => ({
            id: m.id,
            name: m.display_name,
            desc: (m.description || m.provider || "").slice(0, 48),
            badge: "已验证",
          })),
        ]);
      })
      .catch(() => {});
  }, []);

  const fileRef = useRef<HTMLInputElement>(null);
  const elapsedTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const toolPresets: Record<string, { tool: string; prompt: string }> = {
    editor:   { tool: "图片编辑器", prompt: "" },
    product:  { tool: "产品图", prompt: "产品摄影，白色背景，专业灯光，高清细节" },
    avatar:   { tool: "专业头像", prompt: "专业商务头像，现代办公室背景，柔和光线，高分辨率" },
    batch:    { tool: "照片包", prompt: "批量生成产品多角度展示图，统一白色背景" },
    expand:   { tool: "图片扩展", prompt: "扩展图片画面，智能填充边缘" },
    removebg: { tool: "去背景", prompt: "移除背景，保留主体，透明背景PNG输出" },
    upscale:  { tool: "放大", prompt: "AI超分辨率放大，4倍画质提升" },
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const toolParam = params.get("tool");
    if (toolParam && toolPresets[toolParam]) {
      const preset = toolPresets[toolParam];
      setActiveTool(preset.tool);
      if (preset.prompt && !prompt) setPrompt(preset.prompt);
    }
    const remixPrompt = params.get("prompt");
    const remixModel = params.get("model");
    const remixImage = params.get("image_url") || params.get("ref");
    if (remixPrompt) {
      setPrompt(remixPrompt);
      setPrefillPrompt(remixPrompt);
    }
    if (remixModel) {
      const short = remixModel.split("/").pop() || remixModel;
      const matched = imageModels.find(
        (m) => m.id === remixModel || m.id.endsWith(`/${short}`) || m.id.startsWith(short)
      );
      if (matched) setSelectedModel(matched.id);
    }
    if (remixImage) {
      setRemixImageUrl(remixImage);
    }
  }, [imageModels, setPrompt, setSelectedModel]);

  useEffect(() => {
    if (submitting) {
      elapsedTimerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (elapsedTimerRef.current) {
        clearInterval(elapsedTimerRef.current);
        elapsedTimerRef.current = null;
      }
      setElapsedSeconds(0);
    }
    return () => {
      if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
    };
  }, [submitting]);

  // ─── dzine 参数体系：模型参数配置 + 最终输出尺寸 ──────────
  const paramConfig = paramConfigFor(selectedModel);
  const finalDims = dimsFor(aspectRatio, imageSize);
  const finalResolution = `${finalDims.w}x${finalDims.h}`;

  const handleAddReference = useCallback((file: File) => {
    const preview = URL.createObjectURL(file);
    addReference(file, preview, "image");
  }, [addReference]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    for (const f of files.slice(0, 4)) handleAddReference(f);
    e.target.value = "";
  }, [handleAddReference]);

  const MAX_ATTEMPTS = 3;

  const handleSubmit = useCallback(async () => {
    if (!prompt.trim() || submitting) return;
    if (activeTab === "edit" && referenceFiles.length < 1) {
      const msg = "编辑模式需要先上传 1 张参考图";
      setError(msg);
      toast.error("缺少参考图", msg);
      return;
    }
    if (activeTab === "combine" && referenceFiles.length < 2) {
      const msg = "合并模式需要至少 2 张参考图";
      setError(msg);
      toast.error("缺少参考图", msg);
      return;
    }

    setSubmitting(true);
    setError(null);
    setModerationBlocked(null);
    setRetryCount(0);
    setProgress(0);
    setProgressStage("正在提交...");
    setEstimatedSeconds(null);
    addRecentPrompt(prompt);

    // 单次生成（上传参考图 → 提交 → 轮询），失败时抛出错误供重试逻辑判断
    const runOnce = async (): Promise<{ results: Array<{ url: string; type: string; seed?: number }>; model: string }> => {
      let referenceImages: string[] | undefined;
      if (referenceFiles.length > 0) {
        setProgressStage("上传参考图...");
        const urls: string[] = [];
        for (const ref of referenceFiles.slice(0, 4)) {
          const uploaded = await uploadImage(ref.file);
          if (uploaded.url) urls.push(uploaded.url);
        }
        referenceImages = urls.length ? urls : undefined;
      }
      if (remixImageUrl) {
        referenceImages = [remixImageUrl, ...(referenceImages || [])].slice(0, 4);
      }

      const res: GenerateResponse = await submitGeneration({
        prompt,
        media_type: "image",
        model: selectedModel === "auto" ? undefined : selectedModel,
        quality,
        resolution: finalResolution,
        count,
        style: style || undefined,
        // 编辑/合并是指令式 i2i，关闭提示词改写以保留原始指令
        enhance_prompt: activeTab === "prompt" ? creativity !== "wild" : false,
        image_url: referenceImages?.[0],
        reference_images: referenceImages,
      });

      setTaskId(res.task_id);
      if (user?.id) trackOnboarding("generation_submitted");
      setEstimatedSeconds(res.estimated_time_seconds || 30);
      setProgress(5);
      setProgressStage("模型推理中...");

      const pollInterval = 2000;
      const maxPolls = 150;
      let polls = 0;

      const poll = async (): Promise<TaskResult> => {
        if (polls++ > maxPolls) throw new Error("生成超时，请重试");
        const status = await getTaskStatus(res.task_id);
        if ("progress" in status && typeof status.progress === "number") {
          setProgress(Math.min(status.progress, 99));
        }
        if ("current_stage" in status && status.current_stage) {
          setProgressStage(status.current_stage);
        }
        if (status.status === "completed" || status.status === "failed") {
          return status as TaskResult;
        }
        await new Promise((r) => setTimeout(r, pollInterval));
        return poll();
      };

      const result = await poll();
      if (result.status === "failed") {
        throw new Error(result.error_message || "生成失败");
      }
      setProgress(100);
      return {
        results: (result.results || []) as Array<{ url: string; type: string; seed?: number }>,
        model: res.estimated_model || selectedModel,
      };
    };

    try {
      let outcome: { results: Array<{ url: string; type: string; seed?: number }>; model: string } | null = null;
      let lastErr: any = null;

      for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
        setRetryCount(attempt - 1);
        try {
          if (attempt > 1) {
            setProgress(5);
            setProgressStage(`第 ${attempt - 1} 次自动重试...`);
            setEstimatedSeconds(null);
          }
          outcome = await runOnce();
          break;
        } catch (err: any) {
          lastErr = err;
          // 内容安全过滤 / 计费问题：不可重试
          const msg = String(err?.message || "");
          const nonRetryable =
            err?.code === "CONTENT_MODERATION_BLOCKED" ||
            err?.status === 402 ||
            msg.includes("积分不足");
          if (nonRetryable || attempt >= MAX_ATTEMPTS) throw err;
          setProgressStage(`生成失败，正在重试（${attempt}/${MAX_ATTEMPTS}）...`);
          await new Promise((r) => setTimeout(r, 1200 * attempt));
        }
      }

      if (!outcome) throw lastErr || new Error("生成失败");

      const resultCount = outcome.results.length;
      for (const r of outcome.results) {
        addResult({
          url: resolveMediaUrl(r.url),
          type: (r.type || "image") as "image" | "video",
          prompt: prompt,
          model: outcome.model,
          seed: r.seed,
        });
      }

      setHasSubmitted(true);
      toast.success("生成完成", `已生成 ${resultCount} 张图片`);
      if (resultCount > 0 && user?.id) {
        completeOnboarding(String(user.id));
        trackOnboarding("first_work_completed");
      }
    } catch (err: any) {
      // 业务错误只走 UI 提示，不打 console.error，避免触发 Next.js 错误遮罩。
      if (err?.code === "CONTENT_MODERATION_BLOCKED") {
        setModerationBlocked(err.message || "提示词包含受限内容，请修改后重试");
        toast.error("内容安全过滤", err.message || "提示词包含受限内容");
      } else {
        const message = err.message || "生成失败，请重试";
        setError(message);
        toast.error("生成失败", message);
      }
    } finally {
      setSubmitting(false);
      setTaskId(null);
      setProgress(0);
      setProgressStage("");
      setEstimatedSeconds(null);
      setRetryCount(0);
    }
  }, [
    prompt, selectedModel, quality, resolution, aspectRatio, count,
    style, creativity, submitting, referenceFiles, addRecentPrompt, addResult, toast,
    user?.id, completeOnboarding, activeTab, remixImageUrl, finalResolution,
  ]);

  const iterate = useCallback(async (
    mode: "vary" | "reproduce",
    src: { prompt: string; model: string; seed?: number },
  ) => {
    if (submitting) return;
    if (mode === "reproduce" && src.seed == null) { toast.error("无法复现", "该结果缺少种子信息"); return; }
    setSubmitting(true); setError(null); setProgress(5);
    setProgressStage(mode === "vary" ? "生成变体中..." : "按种子复现中...");
    try {
      const res = await submitGeneration({
        prompt: src.prompt, media_type: "image",
        model: src.model && src.model !== "auto" ? src.model : undefined,
        quality, count: mode === "vary" ? 4 : 1, enhance_prompt: false,
        ...(mode === "reproduce" ? { seed: src.seed } : {}),
      });
      setTaskId(res.task_id);
      let polls = 0;
      const poll = async (): Promise<TaskResult> => {
        if (polls++ > 150) throw new Error("生成超时");
        const s = await getTaskStatus(res.task_id);
        if ("progress" in s && typeof s.progress === "number") setProgress(Math.min(s.progress, 99));
        if ("current_stage" in s && s.current_stage) setProgressStage(s.current_stage);
        if (s.status === "completed" || s.status === "failed") return s as TaskResult;
        await new Promise((r) => setTimeout(r, 2000));
        return poll();
      };
      const result = await poll();
      setProgress(100);
      if (result.status === "failed") throw new Error(result.error_message || "生成失败");
      for (const r of (result.results || [])) {
        addResult({ url: resolveMediaUrl(r.url), type: (r.type || "image") as "image" | "video",
          prompt: src.prompt, model: res.estimated_model || src.model, seed: (r as any).seed });
      }
      toast.success(mode === "vary" ? "变体已生成" : "已复现", mode === "vary" ? "已按新种子生成变体" : `种子 ${src.seed}`);
    } catch (e: any) {
      setError(e.message || "生成失败"); toast.error("失败", e.message || "");
    } finally {
      setSubmitting(false); setTaskId(null); setProgress(0); setProgressStage("");
    }
  }, [submitting, quality, addResult, toast]);

  const handleRetry = useCallback(() => {
    setError(null);
    handleSubmit();
  }, [handleSubmit]);

  const handleDismissError = useCallback(() => {
    setError(null);
  }, []);

  const handleBatchSubmit = useCallback(async (prompts: string[]) => {
    for (const p of prompts) {
      setPrompt(p);
      await new Promise(r => setTimeout(r, 500));
      if (!p.trim()) continue;
      setSubmitting(true);
      setError(null);
      setProgress(0);
      setProgressStage("正在提交...");
      setEstimatedSeconds(null);
      addRecentPrompt(p);

      try {
        const res = await submitGeneration({
          prompt: p,
          media_type: "image",
          model: selectedModel === "auto" ? undefined : selectedModel,
          quality,
          resolution: finalResolution,
          count,
          style: style || undefined,
          enhance_prompt: creativity !== "wild",
        });

        setTaskId(res.task_id);
        setEstimatedSeconds(res.estimated_time_seconds || 30);
        setProgress(5);
        setProgressStage("模型推理中...");

        const pollInterval = 2000;
        const maxPolls = 150;
        let polls = 0;

        const poll = async () => {
          if (polls++ > maxPolls) throw new Error("生成超时，请重试");
          const status = await getTaskStatus(res.task_id);
          if ("progress" in status && typeof status.progress === "number") {
            setProgress(Math.min(status.progress, 99));
          }
          if ("current_stage" in status && status.current_stage) {
            setProgressStage(status.current_stage);
          }
          if (status.status === "completed" || status.status === "failed") {
            return status as TaskResult;
          }
          await new Promise(r => setTimeout(r, pollInterval));
          return poll();
        };

        const result = await poll();
        setProgress(100);

        if (result.status === "failed") {
          throw new Error(result.error_message || "生成失败");
        }

        const resultCount = result.results?.length || 0;
        if (result.results && result.results.length > 0) {
          for (const r of result.results) {
            addResult({
              url: resolveMediaUrl(r.url),
              type: (r.type || "image") as "image" | "video",
              prompt: p,
              model: res.estimated_model || selectedModel,
            });
          }
        }

        setHasSubmitted(true);
        toast.success("生成完成", `已生成 ${resultCount} 张图片`);
      } catch (err: any) {
        const message = err.message || "生成失败，请重试";
        setError(message);
        toast.error("生成失败", message);
      } finally {
        setSubmitting(false);
        setTaskId(null);
        setProgress(0);
        setProgressStage("");
        setEstimatedSeconds(null);
      }
    }
  }, [selectedModel, quality, aspectRatio, count, style, creativity, addRecentPrompt, addResult, toast, setPrompt, finalResolution]);

  const imageResults = results.filter((r) => r.type === "image");
  const showEmpty = !submitting && !error && !moderationBlocked && imageResults.length === 0;
  const showResults = imageResults.length > 0;

  const remainingSeconds = estimatedSeconds ? Math.max(0, estimatedSeconds - elapsedSeconds) : null;
  const remainingDisplay = remainingSeconds
    ? remainingSeconds > 60
      ? `约 ${Math.ceil(remainingSeconds / 60)} 分钟`
      : `约 ${remainingSeconds} 秒`
    : null;

  const displayProgress = progress > 0 ? progress : (estimatedSeconds && elapsedSeconds > 0
    ? Math.min(95, Math.round((elapsedSeconds / estimatedSeconds) * 100))
    : 0);

  const qualityLabel = QUALITY_OPTIONS.find((q) => q.value === quality)?.label || quality;

  // ─── 参数随模型变化：越界时回落到模型支持的第一项 ──────────
  useEffect(() => {
    if (!paramConfig.aspects.includes(aspectRatio)) {
      setAspectRatio(paramConfig.aspects[0]);
    }
    if (!paramConfig.sizes.includes(imageSize)) {
      setImageSize(paramConfig.sizes[paramConfig.sizes.length - 1]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedModel]);

  // ─── 编辑/合并模式校验（对标 Yapper: edit=1+ 参考图, combine=2+ 参考图）───
  const requiredRefs = activeTab === "edit" ? 1 : activeTab === "combine" ? 2 : 0;
  const refsOk = referenceFiles.length >= requiredRefs;
  const modeHint =
    activeTab === "edit"
      ? "编辑模式：上传 1 张图片，用一句话描述修改指令"
      : activeTab === "combine"
      ? "合并模式：上传 2–4 张图片，描述如何把它们合并"
      : null;
  const placeholder =
    activeTab === "edit"
      ? "描述要如何编辑这张图片，例如：把背景换成海边日落、移除画面中的文字、换成纯白产品背景..."
      : activeTab === "combine"
      ? "描述如何合并这些图片，例如：把图1的人物放进图2的场景，保持图2的光线与构图..."
      : "描述你想要创作的图像，或上传图片进行编辑...";
  const submitDisabled = !prompt.trim() || submitting || !refsOk;
  const submitTitle = !refsOk
    ? requiredRefs === 1
      ? "编辑模式需要先上传 1 张参考图"
      : "合并模式需要先上传至少 2 张参考图"
    : "生成";

  return (
    <div className="flex flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 pt-10 pb-20">
          {/* Header */}
          <motion.header
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="text-center mb-8"
          >
            <h1 className="text-2xl md:text-3xl font-semibold tracking-[-0.02em] text-text-primary">
              提示词 · 编辑 · 合并专业图片
            </h1>
            <p className="text-sm text-text-secondary mt-2">
              描述你想要的画面，选择模型与参数，一键生成
            </p>
          </motion.header>

          {/* Tabs */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
            className="flex items-center justify-center gap-1 mb-4"
          >
            {PROMPT_TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200",
                  activeTab === tab.id
                    ? "bg-brand/10 text-brand-strong"
                    : "text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle"
                )}
              >
                {tab.label}
              </button>
            ))}
          </motion.div>

          {/* Prompt workbench — Yapper 式大输入框 + 内联工具栏 */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="rounded-2xl border border-cosmic-border bg-cosmic-surface shadow-elevation-lg overflow-visible"
          >
            {/* 模式提示（编辑/合并） */}
            {modeHint && (
              <div className="flex items-center gap-2 px-4 pt-3 text-xs text-text-secondary">
                <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", refsOk ? "bg-brand" : "bg-warning")} />
                <span>
                  {modeHint}
                  <span className={cn("ml-2", refsOk ? "text-brand-strong" : "text-warning")}>
                    已上传 {referenceFiles.length}/{requiredRefs}
                  </span>
                </span>
              </div>
            )}

            {/* Reference previews */}
            {referenceFiles.length > 0 && (
              <div className="flex items-center gap-2 px-4 pt-3 pb-1 flex-wrap">
                {referenceFiles.map((ref, i) => (
                  <div key={ref.preview + i} className="relative group">
                    <img src={ref.preview} alt="参考图" className="w-14 h-14 rounded-lg object-cover border border-cosmic-border" />
                    <button
                      type="button"
                      onClick={() => removeReference(i)}
                      className="absolute -top-1.5 -right-1.5 w-4.5 h-4.5 rounded-full bg-black/70 border border-cosmic-border text-white/80 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <X className="w-2.5 h-2.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="relative">
              <button
                type="button"
                aria-label="添加参考图"
                title="添加参考图（也可在下方工具栏上传）"
                onClick={() => fileRef.current?.click()}
                className="absolute left-3 top-3 z-10 w-7 h-7 rounded-lg border border-cosmic-border bg-cosmic-elevated/60 text-text-secondary hover:text-brand-strong hover:border-brand/40 flex items-center justify-center transition-colors"
              >
                <ImagePlus className="w-4 h-4" />
              </button>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
                }}
                rows={4}
                placeholder={placeholder}
                data-testid="image-prompt-input"
                className="w-full bg-transparent border-none pl-12 pr-4 pt-3 pb-2 text-[15px] leading-relaxed text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-0 resize-none"
              />
            </div>

            {/* Inline toolbar — Yapper/dzine 式一体化工具条, 无套叠边框 */}
            <div className={cn(
              "flex items-center gap-1.5 flex-wrap px-3 py-2.5 bg-cosmic-subtle/35",
              !showMore && "rounded-b-2xl"
            )}>
              <ModelSelect models={imageModels} value={selectedModel} onChange={setSelectedModel} testId="model-select" />
              <ParamDropdown
                aspect={aspectRatio}
                onAspect={setAspectRatio}
                size={imageSize}
                onSize={setImageSize}
                quality={quality}
                onQuality={setQuality}
                config={paramConfig}
                testId="param-select"
              />
              <ToolSelect
                icon={Hash}
                label="数量"
                value={count}
                options={COUNT_OPTIONS.map((c) => ({ value: c, label: String(c) }))}
                onChange={setCount}
                testId="count-select"
              />

              <input ref={fileRef} type="file" accept="image/*" multiple className="hidden" onChange={handleFileChange} />
              <button
                type="button"
                aria-label="添加参考图"
                title={requiredRefs > 0 ? `上传参考图（需要 ${requiredRefs} 张）` : "添加参考图"}
                onClick={() => fileRef.current?.click()}
                className={cn(
                  "toolbar-btn justify-center",
                  requiredRefs > 0 ? "px-2.5" : "!px-0 w-8",
                  requiredRefs > 0 && !refsOk && "!text-warning"
                )}
              >
                <ImagePlus className="w-4 h-4" />
                {requiredRefs > 0 && <span>上传图片</span>}
              </button>

              <button
                type="button"
                onClick={() => setShowMore((v) => !v)}
                data-testid="more-toggle"
                className={cn(
                  "toolbar-btn",
                  showMore && "!text-brand-strong !bg-brand/5"
                )}
              >
                <SlidersHorizontal className="w-3.5 h-3.5 opacity-70" />
                更多
                <ChevronDown className={cn("w-3.5 h-3.5 opacity-50 transition-transform", showMore && "rotate-180")} />
              </button>

              <div className="ml-auto flex items-center gap-2.5">
                <span className="hidden sm:inline text-[11px] text-text-tertiary tabular-nums select-none">
                  {prompt.length}/5000
                </span>
                <span className="hidden sm:inline-flex items-center gap-1 text-[11px] text-text-tertiary select-none">
                  <span className="w-1.5 h-1.5 rounded-full bg-brand" />~20
                </span>
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={submitDisabled}
                  aria-label="生成"
                  title={submitTitle}
                  data-testid="image-submit"
                  className="w-8 h-8 rounded-full bg-brand hover:bg-brand-strong text-brand-foreground flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {submitting ? (
                    <span className="w-3.5 h-3.5 border-2 border-brand-foreground/40 border-t-brand-foreground rounded-full animate-spin" />
                  ) : (
                    <ArrowUp className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* More options: 风格 / 创意度 */}
            <AnimatePresence>
              {showMore && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-t border-cosmic-border/70 overflow-hidden"
                >
                  <div className="px-4 py-4 space-y-4">
                    <StyleCardSelector selected={style} onChange={setStyle} />
                    <CreativitySlider value={creativity as any} onChange={setCreativity} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* Suggestions */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-wrap justify-center gap-2 mt-5"
          >
            {SUGGESTIONS.map((s) => (
              <button key={s} type="button" onClick={() => setPrompt(s)} className="chip text-[13px]">
                {s}
              </button>
            ))}
          </motion.div>

          {/* Batch */}
          <motion.div
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.18, ease: [0.16, 1, 0.3, 1] }}
          >
            <BatchPromptInput onSubmit={handleBatchSubmit} loading={submitting} className="mt-5" />
          </motion.div>

          {/* Generation progress — Yapper 式: 结果位骨架 + 进度 + 重试状态 */}
          <AnimatePresence mode="wait">
            {submitting && (
              <motion.div
                key="generating"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mt-6 rounded-2xl border border-cosmic-border bg-cosmic-surface p-4"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2 text-sm text-text-primary min-w-0">
                    <span className="w-3.5 h-3.5 shrink-0 border-2 border-brand/40 border-t-brand rounded-full animate-spin" />
                    <span className="truncate">{progressStage || "AI 正在生成..."}</span>
                    {retryCount > 0 && (
                      <span data-testid="retry-badge" className="shrink-0 text-[11px] font-medium text-warning px-1.5 py-0.5 rounded-full bg-warning/10 border border-warning/20">
                        重试 {retryCount}/{MAX_ATTEMPTS}
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-text-secondary tabular-nums">{displayProgress}%</span>
                </div>

                <div className={cn(
                  "grid gap-2",
                  count <= 1 ? "grid-cols-1" : count === 2 ? "grid-cols-2" : "grid-cols-4"
                )}>
                  {Array.from({ length: count }).map((_, i) => (
                    <div key={i} data-testid="progress-skeleton" className="relative aspect-square rounded-xl bg-cosmic-subtle overflow-hidden">
                      <div className="absolute inset-0 animate-pulse bg-gradient-to-br from-cosmic-subtle to-cosmic-elevated" />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <ImageIcon className="w-6 h-6 text-text-tertiary/40" />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="relative w-full h-1.5 rounded-full bg-cosmic-subtle overflow-hidden mt-3">
                  <motion.div
                    className="absolute inset-y-0 left-0 rounded-full bg-brand"
                    initial={{ width: "0%" }}
                    animate={{ width: `${displayProgress}%` }}
                    transition={{ type: "spring", stiffness: 100, damping: 20 }}
                  />
                </div>
                <div className="flex items-center justify-between mt-2">
                  <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                    <Clock className="w-3 h-3" />
                    <span>已耗时 {elapsedSeconds}s</span>
                  </div>
                  {remainingDisplay && (
                    <span className="text-xs text-text-secondary/60">
                      预计剩余 {remainingDisplay}
                    </span>
                  )}
                </div>
                {taskId && (
                  <p className="text-[10px] text-text-secondary/40 mt-2 font-mono">
                    任务 {taskId.slice(0, 12)}...
                  </p>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* 内容安全过滤提示（不可重试） */}
          <AnimatePresence mode="wait">
            {moderationBlocked && !submitting && (
              <motion.div
                key="moderation"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mt-6 rounded-2xl border border-warning/30 bg-warning/[0.06] p-4"
                data-testid="moderation-notice"
              >
                <div className="flex items-start gap-3">
                  <span className="shrink-0 w-8 h-8 rounded-lg bg-warning/15 border border-warning/25 flex items-center justify-center">
                    <X className="w-4 h-4 text-warning" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-text-primary">内容安全过滤</p>
                    <p className="text-[13px] text-text-secondary mt-0.5 leading-relaxed">
                      {moderationBlocked}
                    </p>
                    <div className="flex items-center gap-3 mt-2.5">
                      <button
                        type="button"
                        onClick={() => setModerationBlocked(null)}
                        className="text-xs text-text-secondary hover:text-text-primary transition-colors"
                      >
                        我知道了
                      </button>
                      <a href="/content-policy" className="text-xs text-brand-strong hover:underline">
                        查看内容政策
                      </a>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Error */}
          <AnimatePresence mode="wait">
            {error && !submitting && (
              <motion.div
                key="error"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mt-6"
              >
                <ErrorState
                  title="生成失败"
                  message={error}
                  onRetry={handleRetry}
                  onDismiss={handleDismissError}
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Empty */}
          <AnimatePresence mode="wait">
            {showEmpty && (
              <motion.div
                key="empty"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mt-6"
              >
                <Empty
                  icon={<Wand2 className="w-7 h-7 text-text-secondary/40" />}
                  title={hasSubmitted ? "没有生成结果" : "开始创作"}
                  description={
                    hasSubmitted
                      ? "生成已完成但未返回图片，请尝试调整参数后重试"
                      : "输入 prompt 描述你想要的画面，AI 将为你生成精美图片"
                  }
                  action={hasSubmitted ? { label: "重新生成", onClick: handleRetry } : undefined}
                  secondaryAction={!hasSubmitted ? { label: "试试推荐词", onClick: () => setPrompt(SUGGESTIONS[0]) } : undefined}
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Results */}
          <AnimatePresence mode="wait">
            {showResults && (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mt-8"
                data-testid="image-results"
              >
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">
                    生成结果 ({imageResults.length})
                  </p>
                </div>
                <div className={cn(
                  "grid gap-3",
                  imageResults.length <= 1 ? "grid-cols-1" : "grid-cols-2"
                )}>
                  {imageResults.map((item, i) => (
                    <motion.div
                      key={`${item.url}-${i}`}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.1, type: "spring", stiffness: 300, damping: 25 }}
                      className="group relative rounded-2xl overflow-hidden border border-cosmic-border bg-cosmic-subtle hover:scale-[1.02] transition-transform duration-300"
                    >
                      <img
                        src={item.url}
                        alt={item.prompt}
                        className="w-full aspect-square object-cover"
                        loading="lazy"
                      />
                      <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-black/50 backdrop-blur-sm text-[10px] text-white/80 flex items-center gap-1">
                        <ImageIcon className="w-3 h-3" />
                        <span>{item.model}</span>
                      </div>
                      {item.seed != null && (
                        <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-black/50 backdrop-blur-sm text-[10px] text-white/70 font-mono" title="随机种子">
                          {item.seed}
                        </div>
                      )}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-end justify-center gap-2 p-3">
                        <button
                          onClick={() => iterate("vary", { prompt: item.prompt, model: item.model, seed: item.seed })}
                          disabled={submitting}
                          className="btn-icon bg-brand/[0.85] hover:bg-brand backdrop-blur-sm text-white disabled:opacity-50"
                          title="生成变体（同提示词，新随机种子）"
                        >
                          <Wand2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => iterate("reproduce", { prompt: item.prompt, model: item.model, seed: item.seed })}
                          disabled={submitting || item.seed == null}
                          className="btn-icon bg-white/10 hover:bg-white/20 backdrop-blur-sm text-white disabled:opacity-40"
                          title={item.seed != null ? `按种子复现 (${item.seed})` : "无种子信息"}
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                        <a
                          href={item.url}
                          download
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-icon bg-white/10 hover:bg-white/20 backdrop-blur-sm text-white"
                          title="下载"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                        <button
                          onClick={() => router.push("/create/video")}
                          className="btn-icon bg-white/10 hover:bg-white/20 backdrop-blur-sm text-white"
                          title="用于视频"
                        >
                          <Video className="w-4 h-4" />
                        </button>
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-icon bg-white/10 hover:bg-white/20 backdrop-blur-sm text-white"
                          title="新窗口打开"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Image Apps — Yapper 式卡片矩阵（置于反馈区之后） */}
          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="mt-12"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-text-primary">Image Apps</h2>
              <span className="text-[11px] text-text-tertiary">专业图像工具</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {IMAGE_APPS.map((app) => (
                <button
                  key={app.label}
                  type="button"
                  onClick={() => router.push(app.href)}
                  className="group flex items-center gap-3 p-3.5 rounded-xl border border-cosmic-border bg-cosmic-surface hover:border-cosmic-border-hover hover:bg-cosmic-elevated transition-colors text-left"
                >
                  <span className="icon-tile w-10 h-10 shrink-0">
                    <app.icon className="w-[18px] h-[18px]" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[13px] font-semibold text-text-primary truncate">{app.label}</span>
                    <span className="block text-[11px] text-text-tertiary truncate mt-0.5">{app.desc}</span>
                  </span>
                </button>
              ))}
            </div>
          </motion.section>
        </div>
      </div>
    </div>
  );
}
