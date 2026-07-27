"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  SlidersHorizontal, ChevronDown, Sparkles, Zap,
  Timer, Maximize, Grid3X3, Layers, Settings2,
  Info, Crown, Gauge, Film,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ═════════════════════════════════════════════════════════
   CosmicVideoParamPanel
   视频参数面板 — 折叠分组 · 大型预设 · 模型卡片 · 质量预设
   ═════════════════════════════════════════════════════════ */

/* ─── Types ──────────────────────────────────────────── */

interface ModelOption {
  id: string;
  name: string;
  desc?: string;
  badge?: string;
  icon?: string;
}

interface AspectRatioOption {
  value: string;
  label: string;
  icon?: string;
}

interface CosmicVideoParamPanelProps {
  // Model
  models: ModelOption[];
  selectedModel: string;
  onModelSelect: (id: string) => void;

  // Aspect Ratio
  aspectRatio: string;
  onAspectChange: (v: string) => void;
  aspectRatios?: AspectRatioOption[];

  // Resolution
  resolution: string;
  onResolutionChange: (v: string) => void;
  resolutions?: string[];

  // Duration
  duration: number;
  onDurationChange: (v: number) => void;
  durationRange?: [number, number];

  // Count
  count: number;
  onCountChange: (v: number) => void;

  // Quality
  quality: string;
  onQualityChange: (v: string) => void;
  qualityPresets?: Array<{ id: string; label: string; desc: string; icon?: React.ReactNode }>;

  // Advanced
  loraScale?: number;
  onLoraScaleChange?: (v: number) => void;
  cfgScale?: number;
  onCfgScaleChange?: (v: number) => void;

  className?: string;
}

/* ─── Data ───────────────────────────────────────────── */

const DEFAULT_ASPECT_RATIOS: AspectRatioOption[] = [
  { value: "16:9", label: "16:9", icon: "▬" },
  { value: "9:16", label: "9:16", icon: "▮" },
  { value: "1:1", label: "1:1", icon: "■" },
  { value: "4:3", label: "4:3", icon: "▯" },
  { value: "21:9", label: "21:9", icon: "▬▬" },
];

const DEFAULT_RESOLUTIONS = ["720p", "1080p", "2K", "4K"];

const DEFAULT_QUALITY_PRESETS = [
  { id: "fast", label: "快速", desc: "30秒内", icon: <Zap className="w-4 h-4" /> },
  { id: "balanced", label: "均衡", desc: "1分钟", icon: <Gauge className="w-4 h-4" /> },
  { id: "quality", label: "高质量", desc: "2-3分钟", icon: <Sparkles className="w-4 h-4" /> },
  { id: "pro", label: "专业", desc: "3-5分钟", icon: <Crown className="w-4 h-4" /> },
];

/* ─── Sub-components ─────────────────────────────────── */

/** Collapsible group wrapper */
function ParamGroup({
  id,
  label,
  icon,
  defaultOpen = true,
  children,
}: {
  id: string;
  label: string;
  icon?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="group/param">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full py-3"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="text-caption font-semibold text-text-secondary uppercase tracking-wide">
            {label}
          </span>
        </div>
        <ChevronDown
          className={cn(
            "w-3.5 h-3.5 text-text-tertiary/60 transition-transform duration-200",
            !open && "-rotate-90"
          )}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="pb-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/** Large preset button chip */
function PresetChip({
  active,
  onClick,
  children,
  icon,
  className,
}: {
  active?: boolean;
  onClick: () => void;
  children: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-xl text-body-sm font-medium transition-all duration-200",
        "border",
        active
          ? "bg-accent-cyan/[0.08] border-accent-cyan/25 text-accent-cyan shadow-glow-subtle"
          : "bg-white/[0.02] border-white/[0.06] text-text-tertiary hover:bg-white/[0.05] hover:text-text-secondary hover:border-white/[0.1]",
        className
      )}
    >
      {icon}
      {children}
    </button>
  );
}

/** Large quality preset card */
function QualityCard({
  preset,
  active,
  onClick,
}: {
  preset: { id: string; label: string; desc: string; icon?: React.ReactNode };
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 w-full p-3 rounded-xl border transition-all duration-200 text-left",
        active
          ? "bg-accent-cyan/[0.06] border-accent-cyan/20 shadow-glow-subtle"
          : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04]"
      )}
    >
      <div
        className={cn(
          "flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center",
          active ? "bg-accent-cyan/15 text-accent-cyan" : "bg-white/[0.04] text-text-tertiary"
        )}
      >
        {preset.icon}
      </div>
      <div>
        <div
          className={cn(
            "text-body-sm font-semibold",
            active ? "text-accent-cyan" : "text-text-secondary"
          )}
        >
          {preset.label}
        </div>
        <div className="text-caption text-text-tertiary">{preset.desc}</div>
      </div>
    </button>
  );
}

/** Custom slider */
function ParamSlider({
  value,
  onChange,
  min,
  max,
  step = 1,
  leftLabel,
  rightLabel,
  showValue = true,
  gradient = true,
}: {
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
  leftLabel?: string;
  rightLabel?: string;
  showValue?: boolean;
  gradient?: boolean;
}) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className="space-y-2">
      {showValue && (
        <div className="flex justify-end">
          <span className="text-caption font-mono font-medium text-accent-cyan tabular-nums">
            {value}
          </span>
        </div>
      )}
      <div className="relative h-6 flex items-center">
        <div className="absolute inset-x-0 h-1.5 rounded-full bg-cosmic-border/50">
          <div
            className="h-full rounded-full transition-all duration-150"
            style={{
              width: `${pct}%`,
              background: gradient
                ? "linear-gradient(90deg, hsl(189 94% 48%), hsl(217 91% 60%), hsl(255 92% 66%))"
                : "hsl(189 94% 48%)",
            }}
          />
        </div>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-[18px] h-[18px] rounded-full bg-white shadow-glow-cyan border-2 border-accent-cyan pointer-events-none transition-all duration-150 z-0"
          style={{ left: `calc(${pct}% - 9px)` }}
        />
      </div>
      {leftLabel && rightLabel && (
        <div className="flex justify-between text-[10px] text-text-tertiary/70">
          <span>{leftLabel}</span>
          <span>{rightLabel}</span>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Main Component
   ═══════════════════════════════════════════════════════ */

export function CosmicVideoParamPanel({
  models,
  selectedModel,
  onModelSelect,
  aspectRatio,
  onAspectChange,
  aspectRatios = DEFAULT_ASPECT_RATIOS,
  resolution,
  onResolutionChange,
  resolutions = DEFAULT_RESOLUTIONS,
  duration,
  onDurationChange,
  durationRange = [3, 30],
  count,
  onCountChange,
  quality,
  onQualityChange,
  qualityPresets = DEFAULT_QUALITY_PRESETS,
  loraScale,
  onLoraScaleChange,
  cfgScale,
  onCfgScaleChange,
  className,
}: CosmicVideoParamPanelProps) {
  return (
    <div
      className={cn(
        "flex flex-col h-full",
        // Glass panel
        "bg-cosmic-surface/30 backdrop-blur-2xl backdrop-saturate-150",
        "border-l border-cosmic-border/40",
        "overflow-hidden",
        className
      )}
    >
      {/* ── Header ── */}
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-cosmic-border/30">
        <div className="p-1.5 rounded-lg bg-accent-cyan/8">
          <SlidersHorizontal className="w-3.5 h-3.5 text-accent-cyan" />
        </div>
        <span className="text-body-sm font-semibold text-text-accent-cyan">视频参数</span>
        <Sparkles className="w-3.5 h-3.5 text-accent-cyan/40 ml-auto" />
      </div>

      {/* ── Scrollable content ── */}
      <div className="flex-1 overflow-y-auto px-5 scrollbar-hide">
        {/* ── 1. MODEL ── */}
        <ParamGroup id="model" label="模型选择" icon={<Settings2 className="w-3.5 h-3.5 text-accent-cyan/60" />}>
          <div className="space-y-2">
            {models.map((m) => (
              <button
                key={m.id}
                onClick={() => onModelSelect(m.id)}
                className={cn(
                  "flex items-center gap-3 w-full p-3 rounded-xl border transition-all duration-200 text-left",
                  selectedModel === m.id
                    ? "bg-accent-cyan/[0.06] border-accent-cyan/25 shadow-glow-subtle"
                    : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04]"
                )}
              >
                <div
                  className={cn(
                    "flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center text-lg",
                    selectedModel === m.id
                      ? "bg-accent-cyan/15"
                      : "bg-white/[0.04]"
                  )}
                >
                  {m.icon || <Film className="w-5 h-5 text-text-tertiary" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div
                    className={cn(
                      "text-body-sm font-semibold",
                      selectedModel === m.id ? "text-accent-cyan" : "text-text-secondary"
                    )}
                  >
                    {m.name}
                  </div>
                  {m.desc && (
                    <div className="text-caption text-text-tertiary truncate">{m.desc}</div>
                  )}
                </div>
                {m.badge && (
                  <span
                    className={cn(
                      "flex-shrink-0 px-2 py-0.5 rounded-full text-[10px] font-semibold",
                      m.badge === "Pro" && "bg-violet-500/15 text-violet-400 border border-violet-500/20",
                      m.badge === "Fast" && "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20",
                      m.badge === "New" && "bg-blue-500/15 text-blue-400 border border-blue-500/20"
                    )}
                  >
                    {m.badge}
                  </span>
                )}
              </button>
            ))}
          </div>
        </ParamGroup>

        <div className="divider-soft" />

        {/* ── 2. ASPECT RATIO ── */}
        <ParamGroup id="aspect" label="画面比例" icon={<Maximize className="w-3.5 h-3.5 text-accent-blue/60" />}>
          <div className="grid grid-cols-5 gap-1.5">
            {aspectRatios.map((ar) => (
              <button
                key={ar.value}
                onClick={() => onAspectChange(ar.value)}
                className={cn(
                  "flex flex-col items-center gap-1 py-2.5 rounded-lg border transition-all duration-200",
                  aspectRatio === ar.value
                    ? "bg-accent-blue/[0.08] border-accent-blue/25 text-accent-blue"
                    : "bg-white/[0.02] border-white/[0.06] text-text-tertiary hover:bg-white/[0.05]"
                )}
              >
                <span className="text-xs">{ar.icon}</span>
                <span className="text-[10px] font-medium">{ar.label}</span>
              </button>
            ))}
          </div>
        </ParamGroup>

        <div className="divider-soft" />

        {/* ── 3. RESOLUTION + DURATION ── */}
        <ParamGroup id="settings" label="分辨率 & 时长" icon={<Film className="w-3.5 h-3.5 text-accent-violet/60" />}>
          {/* Resolution */}
          <div className="mb-4">
            <span className="text-caption text-text-tertiary block mb-2">分辨率</span>
            <div className="flex gap-1.5">
              {resolutions.map((r) => (
                <PresetChip
                  key={r}
                  active={resolution === r}
                  onClick={() => onResolutionChange(r)}
                >
                  {r}
                </PresetChip>
              ))}
            </div>
          </div>

          {/* Duration */}
          <div>
            <span className="text-caption text-text-tertiary block mb-2">
              时长 <span className="font-mono text-accent-cyan">{duration}s</span>
            </span>
            <ParamSlider
              value={duration}
              onChange={onDurationChange}
              min={durationRange[0]}
              max={durationRange[1]}
              leftLabel={`${durationRange[0]}s`}
              rightLabel={`${durationRange[1]}s`}
              showValue={false}
            />
          </div>
        </ParamGroup>

        <div className="divider-soft" />

        {/* ── 4. COUNT ── */}
        <ParamGroup id="count" label="生成数量" icon={<Grid3X3 className="w-3.5 h-3.5 text-accent-purple/60" />}>
          <div className="flex gap-1.5">
            {[1, 2, 4, 8].map((n) => (
              <PresetChip
                key={n}
                active={count === n}
                onClick={() => onCountChange(n)}
              >
                {n}
              </PresetChip>
            ))}
          </div>
        </ParamGroup>

        <div className="divider-soft" />

        {/* ── 5. QUALITY ── */}
        <ParamGroup id="quality" label="质量预设" icon={<Gauge className="w-3.5 h-3.5 text-amber-400/60" />}>
          <div className="space-y-2">
            {qualityPresets.map((qp) => (
              <QualityCard
                key={qp.id}
                preset={qp}
                active={quality === qp.id}
                onClick={() => onQualityChange(qp.id)}
              />
            ))}
          </div>
        </ParamGroup>

        {/* ── 6. ADVANCED (conditionally shown) ── */}
        {(onLoraScaleChange || onCfgScaleChange) && (
          <>
            <div className="divider-soft" />
            <ParamGroup
              id="advanced"
              label="高级参数"
              icon={<Layers className="w-3.5 h-3.5 text-text-tertiary/40" />}
              defaultOpen={false}
            >
              {onLoraScaleChange && loraScale !== undefined && (
                <div className="mb-4">
                  <span className="text-caption text-text-tertiary block mb-2">
                    LoRA 强度
                  </span>
                  <ParamSlider
                    value={loraScale}
                    onChange={onLoraScaleChange}
                    min={0}
                    max={100}
                    leftLabel="0"
                    rightLabel="100"
                    showValue={true}
                  />
                </div>
              )}
              {onCfgScaleChange && cfgScale !== undefined && (
                <div>
                  <span className="text-caption text-text-tertiary block mb-2">
                    CFG Scale
                  </span>
                  <ParamSlider
                    value={cfgScale}
                    onChange={onCfgScaleChange}
                    min={1}
                    max={20}
                    step={0.5}
                    leftLabel="1"
                    rightLabel="20"
                    showValue={true}
                  />
                </div>
              )}
            </ParamGroup>
          </>
        )}
      </div>

      {/* ── Bottom accent glow ── */}
      <div className="absolute inset-x-4 bottom-0 h-px bg-gradient-to-r from-transparent via-accent-violet/15 to-transparent" />
    </div>
  );
}
