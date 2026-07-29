"use client";

import { useState } from "react";
import {
  ChevronDown, Coins, Sparkles, Ratio, Monitor, Hash, SlidersHorizontal,
  Dice5, Ban, Check,
} from "lucide-react";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { STYLE_OPTIONS } from "@/components/StyleCardSelector";
import type { CreativityLevel } from "@/components/CreativitySlider";
import type { Quality } from "@/lib/stores";
import { cn } from "@/lib/utils";

/* ─────────────────────────────────────────────────────────────
   ImageParamBar — Yapper-style compact toolbar.
   All generation parameters collapsed into a single row of
   dropdown "chips" that sits directly under the prompt input.
   ───────────────────────────────────────────────────────────── */

export interface ParamModel {
  id: string;
  name: string;
  desc: string;
  badge?: string;
  credits?: number;
}

const ASPECTS = [
  { label: "1:1", w: 1, h: 1 },
  { label: "16:9", w: 16, h: 9 },
  { label: "9:16", w: 9, h: 16 },
  { label: "4:3", w: 4, h: 3 },
  { label: "3:4", w: 3, h: 4 },
];
const RESOLUTIONS = ["720p", "1080p", "2K", "4K"];
const COUNTS = [1, 2, 4];
const QUALITIES: { id: Quality; label: string }[] = [
  { id: "fast", label: "快速" },
  { id: "balanced", label: "均衡" },
  { id: "high", label: "高清" },
];
const CREATIVITY: { id: CreativityLevel; label: string }[] = [
  { id: "precise", label: "精准" },
  { id: "balanced", label: "均衡" },
  { id: "creative", label: "创意" },
  { id: "wild", label: "狂野" },
];

interface Props {
  models: ParamModel[];
  selectedModel: string;
  onModelSelect: (id: string) => void;
  aspectRatio: string;
  onAspectChange: (r: string) => void;
  resolution: string;
  onResolutionChange: (r: string) => void;
  count: number;
  onCountChange: (n: number) => void;
  quality: Quality;
  onQualityChange: (q: Quality) => void;
  seedInput: string;
  onSeedChange: (v: string) => void;
  negativePrompt: string;
  onNegativeChange: (v: string) => void;
  style: string | null;
  onStyleChange: (id: string) => void;
  creativity: string;
  onCreativityChange: (c: CreativityLevel) => void;
}

function Chip({
  icon: Icon, label, value, children, className,
}: {
  icon: React.ElementType;
  label: string;
  value?: string;
  children: React.ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex items-center gap-1.5 h-8 px-2.5 rounded-lg text-xs whitespace-nowrap transition-colors",
            "border border-cosmic-border/60 bg-cosmic-surface/40 text-text-secondary",
            "hover:border-accent-cyan/40 hover:text-text-primary",
            open && "border-accent-cyan/40 text-text-primary bg-accent-cyan/[0.06]",
            className,
          )}
        >
          <Icon className="w-3.5 h-3.5 opacity-80" />
          <span className="text-text-secondary/70">{label}</span>
          {value && <span className="font-medium text-text-primary">{value}</span>}
          <ChevronDown className={cn("w-3 h-3 opacity-60 transition-transform", open && "rotate-180")} />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" sideOffset={6} className="w-64 border-cosmic-border bg-cosmic-surface p-2">
        {children}
      </PopoverContent>
    </Popover>
  );
}

function OptionRow({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center justify-between w-full px-2.5 py-2 rounded-md text-xs text-left transition-colors",
        active ? "bg-accent-cyan/[0.1] text-accent-cyan" : "text-text-secondary hover:bg-cosmic-subtle hover:text-text-primary",
      )}
    >
      {children}
      {active && <Check className="w-3.5 h-3.5 flex-shrink-0" />}
    </button>
  );
}

export function ImageParamBar(p: Props) {
  const selected = p.models.find((m) => m.id === p.selectedModel);
  const modelLabel = selected?.name || "Auto";
  const activeStyle = STYLE_OPTIONS.find((s) => s.id === p.style);

  return (
    <>
      {/* Models */}
      <Chip icon={Sparkles} label="模型" value={modelLabel}>
        <div className="max-h-72 overflow-y-auto space-y-0.5">
          {p.models.map((m) => (
            <OptionRow key={m.id} active={p.selectedModel === m.id} onClick={() => p.onModelSelect(m.id)}>
              <span className="flex flex-col items-start gap-0.5 min-w-0">
                <span className="flex items-center gap-1.5">
                  <span className="font-medium truncate">{m.name}</span>
                  {m.badge && <span className="px-1 py-0.5 rounded text-[9px] bg-accent-cyan/[0.1] text-accent-cyan">{m.badge}</span>}
                </span>
                <span className="text-[10px] text-text-secondary/60 truncate">{m.desc}</span>
              </span>
              {m.credits != null && (
                <span className="inline-flex items-center gap-0.5 text-[10px] text-text-secondary/70 ml-2">
                  <Coins className="w-2.5 h-2.5" />{m.credits}
                </span>
              )}
            </OptionRow>
          ))}
        </div>
      </Chip>

      {/* Aspect ratio */}
      <Chip icon={Ratio} label="比例" value={p.aspectRatio}>
        <div className="grid grid-cols-3 gap-1.5">
          {ASPECTS.map((a) => (
            <button
              key={a.label}
              onClick={() => p.onAspectChange(a.label)}
              className={cn(
                "flex flex-col items-center gap-1 py-2 rounded-md text-[11px] border transition-colors",
                p.aspectRatio === a.label
                  ? "border-accent-cyan/40 bg-accent-cyan/[0.08] text-accent-cyan"
                  : "border-cosmic-border/50 text-text-secondary hover:border-cosmic-border",
              )}
            >
              <span
                className="border border-current opacity-70 rounded-[2px]"
                style={{ width: 18 * (a.w >= a.h ? 1 : a.w / a.h), height: 18 * (a.h >= a.w ? 1 : a.h / a.w) }}
              />
              {a.label}
            </button>
          ))}
        </div>
      </Chip>

      {/* Resolution */}
      <Chip icon={Monitor} label="分辨率" value={p.resolution}>
        <div className="grid grid-cols-2 gap-1.5">
          {RESOLUTIONS.map((r) => (
            <OptionRow key={r} active={p.resolution === r} onClick={() => p.onResolutionChange(r)}>
              {r}
            </OptionRow>
          ))}
        </div>
      </Chip>

      {/* Count */}
      <Chip icon={Hash} label="数量" value={String(p.count)}>
        <div className="grid grid-cols-3 gap-1.5">
          {COUNTS.map((n) => (
            <OptionRow key={n} active={p.count === n} onClick={() => p.onCountChange(n)}>
              {n} 张
            </OptionRow>
          ))}
        </div>
      </Chip>

      {/* More: quality / seed / negative / style / creativity */}
      <Chip icon={SlidersHorizontal} label="更多" value={activeStyle ? activeStyle.label : undefined}>
        <div className="space-y-3">
          {/* Quality */}
          <div>
            <p className="text-[10px] text-text-secondary/60 mb-1.5">质量</p>
            <div className="flex gap-1.5">
              {QUALITIES.map((q) => (
                <button
                  key={q.id}
                  onClick={() => p.onQualityChange(q.id)}
                  className={cn(
                    "flex-1 py-1.5 rounded-md text-[11px] border transition-colors",
                    p.quality === q.id ? "border-accent-cyan/40 bg-accent-cyan/[0.08] text-accent-cyan" : "border-cosmic-border/50 text-text-secondary hover:border-cosmic-border",
                  )}
                >{q.label}</button>
              ))}
            </div>
          </div>

          {/* Creativity */}
          <div>
            <p className="text-[10px] text-text-secondary/60 mb-1.5">创造力</p>
            <div className="flex gap-1.5">
              {CREATIVITY.map((c) => (
                <button
                  key={c.id}
                  onClick={() => p.onCreativityChange(c.id)}
                  className={cn(
                    "flex-1 py-1.5 rounded-md text-[11px] border transition-colors",
                    p.creativity === c.id ? "border-accent-cyan/40 bg-accent-cyan/[0.08] text-accent-cyan" : "border-cosmic-border/50 text-text-secondary hover:border-cosmic-border",
                  )}
                >{c.label}</button>
              ))}
            </div>
          </div>

          {/* Seed */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <p className="inline-flex items-center gap-1 text-[10px] text-text-secondary/60"><Dice5 className="w-3 h-3" />种子</p>
              {p.seedInput ? (
                <button onClick={() => p.onSeedChange("")} className="text-[10px] text-text-secondary/60 hover:text-accent-cyan">随机</button>
              ) : (
                <button onClick={() => p.onSeedChange(String(Math.floor(Math.random() * 2147483647)))} className="text-[10px] text-text-secondary/60 hover:text-accent-cyan">固定</button>
              )}
            </div>
            <input
              type="text"
              inputMode="numeric"
              value={p.seedInput}
              onChange={(e) => p.onSeedChange(e.target.value.replace(/[^0-9]/g, "").slice(0, 10))}
              placeholder="留空 = 每次随机"
              className="w-full px-2.5 py-1.5 rounded-md text-xs bg-cosmic-surface/60 border border-cosmic-border/50 text-text-primary placeholder:text-text-tertiary/50 focus:outline-none focus:border-accent-cyan/40"
            />
          </div>

          {/* Negative prompt */}
          <div>
            <p className="inline-flex items-center gap-1 text-[10px] text-text-secondary/60 mb-1.5"><Ban className="w-3 h-3" />负向提示词</p>
            <textarea
              value={p.negativePrompt}
              onChange={(e) => p.onNegativeChange(e.target.value.slice(0, 2000))}
              rows={2}
              placeholder="不希望出现的元素，如：模糊, 水印"
              className="w-full resize-none px-2.5 py-1.5 rounded-md text-xs bg-cosmic-surface/60 border border-cosmic-border/50 text-text-primary placeholder:text-text-tertiary/50 focus:outline-none focus:border-accent-cyan/40"
            />
          </div>

          {/* Style */}
          <div>
            <p className="text-[10px] text-text-secondary/60 mb-1.5">风格</p>
            <div className="grid grid-cols-2 gap-1 max-h-40 overflow-y-auto">
              {STYLE_OPTIONS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => p.onStyleChange(s.id)}
                  className={cn(
                    "flex items-center gap-1.5 px-2 py-1.5 rounded-md text-[11px] border transition-colors text-left",
                    p.style === s.id ? "border-accent-cyan/40 bg-accent-cyan/[0.08] text-accent-cyan" : "border-cosmic-border/50 text-text-secondary hover:border-cosmic-border",
                  )}
                >
                  <span className={cn("w-4 h-4 rounded flex items-center justify-center bg-gradient-to-br flex-shrink-0", s.gradient)}>
                    <s.icon className="w-2.5 h-2.5 text-white" />
                  </span>
                  <span className="truncate">{s.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </Chip>
    </>
  );
}
