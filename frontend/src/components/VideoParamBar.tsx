"use client";

import { useState } from "react";
import {
  ChevronsUpDown, Sparkles, Ratio, Monitor, Hash, SlidersHorizontal,
  Gauge, Timer, Check, Music, Mic,
} from "lucide-react";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import type { Quality } from "@/lib/stores";
import { cn } from "@/lib/utils";

/* Compact borderless param chips for the video composer (Yapper-style). */

export interface VideoParamModel {
  id: string;
  name: string;
  desc?: string;
  badge?: string;
  icon?: string;
}

const ASPECTS = [
  { label: "16:9", w: 16, h: 9 },
  { label: "9:16", w: 9, h: 16 },
  { label: "1:1", w: 1, h: 1 },
  { label: "4:3", w: 4, h: 3 },
  { label: "21:9", w: 21, h: 9 },
];
const RESOLUTIONS = ["720p", "1080p", "2K", "4K"];
const DURATIONS = [3, 5, 8, 10, 15];
const COUNTS = [1, 2, 4];
const QUALITIES: { id: Quality; label: string }[] = [
  { id: "fast", label: "快速" },
  { id: "balanced", label: "均衡" },
  { id: "high", label: "高清" },
];

interface Props {
  models: VideoParamModel[];
  selectedModel: string;
  onModelSelect: (id: string) => void;
  aspectRatio: string;
  onAspectChange: (r: string) => void;
  resolution: string;
  onResolutionChange: (r: string) => void;
  duration: number;
  onDurationChange: (n: number) => void;
  count: number;
  onCountChange: (n: number) => void;
  quality: Quality;
  onQualityChange: (q: Quality) => void;
  generateAudio: boolean;
  onGenerateAudioChange: (v: boolean) => void;
  postLipsync: boolean;
  onPostLipsyncChange: (v: boolean) => void;
  multiShot: boolean;
  onMultiShotChange: (v: boolean) => void;
}

function Chip({ icon: Icon, label, value, children }: {
  icon: React.ElementType; label: string; value?: string; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex items-center gap-1 h-7 px-1.5 rounded-md text-xs whitespace-nowrap transition-colors",
            "text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle/60",
            open && "text-text-primary bg-cosmic-subtle/60",
          )}
        >
          <Icon className="w-3.5 h-3.5 opacity-70" />
          <span className="text-text-secondary/55">{label}</span>
          {value && <span className="font-medium text-text-primary/90">{value}</span>}
          <ChevronsUpDown className="w-3.5 h-3.5 opacity-70 text-text-secondary" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" sideOffset={6} className="w-60 border-cosmic-border bg-cosmic-surface p-2">
        {children}
      </PopoverContent>
    </Popover>
  );
}

function Row({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
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

function Toggle({ label, icon: Icon, on, onChange, note }: {
  label: string; icon: React.ElementType; on: boolean; onChange: (v: boolean) => void; note?: string;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!on)}
      className="flex items-center justify-between w-full px-2.5 py-2 rounded-md text-xs hover:bg-cosmic-subtle transition-colors"
    >
      <span className="flex items-center gap-2 text-text-secondary">
        <Icon className="w-3.5 h-3.5" />
        <span className="flex flex-col items-start">
          <span className="text-text-primary/90">{label}</span>
          {note && <span className="text-[10px] text-text-secondary/50">{note}</span>}
        </span>
      </span>
      <span className={cn("w-8 h-4.5 rounded-full p-0.5 transition-colors flex-shrink-0", on ? "bg-accent-cyan/80" : "bg-cosmic-border")}>
        <span className={cn("block w-3.5 h-3.5 rounded-full bg-white transition-transform", on && "translate-x-3.5")} />
      </span>
    </button>
  );
}

export function VideoParamBar(p: Props) {
  const selected = p.models.find((m) => m.id === p.selectedModel);
  return (
    <>
      <Chip icon={Sparkles} label="模型" value={selected?.name || "Auto"}>
        <div className="max-h-72 overflow-y-auto space-y-0.5">
          {p.models.map((m) => (
            <Row key={m.id} active={p.selectedModel === m.id} onClick={() => p.onModelSelect(m.id)}>
              <span className="flex flex-col items-start gap-0.5 min-w-0">
                <span className="flex items-center gap-1.5">
                  <span className="font-medium truncate">{m.name}</span>
                  {m.badge && <span className="px-1 py-0.5 rounded text-[9px] bg-accent-cyan/[0.1] text-accent-cyan">{m.badge}</span>}
                </span>
                {m.desc && <span className="text-[10px] text-text-secondary/60 truncate">{m.desc}</span>}
              </span>
            </Row>
          ))}
        </div>
      </Chip>

      <Chip icon={Ratio} label="比例" value={p.aspectRatio}>
        <div className="grid grid-cols-3 gap-1.5">
          {ASPECTS.map((a) => (
            <button
              key={a.label}
              onClick={() => p.onAspectChange(a.label)}
              className={cn(
                "flex flex-col items-center gap-1 py-2 rounded-md text-[11px] border transition-colors",
                p.aspectRatio === a.label ? "border-accent-cyan/40 bg-accent-cyan/[0.08] text-accent-cyan" : "border-cosmic-border/50 text-text-secondary hover:border-cosmic-border",
              )}
            >
              <span className="border border-current opacity-70 rounded-[2px]" style={{ width: 18 * (a.w >= a.h ? 1 : a.w / a.h), height: 18 * (a.h >= a.w ? 1 : a.h / a.w) }} />
              {a.label}
            </button>
          ))}
        </div>
      </Chip>

      <Chip icon={Monitor} label="分辨率" value={p.resolution}>
        <div className="grid grid-cols-2 gap-1.5">
          {RESOLUTIONS.map((r) => (
            <Row key={r} active={p.resolution === r} onClick={() => p.onResolutionChange(r)}>{r}</Row>
          ))}
        </div>
      </Chip>

      <Chip icon={Gauge} label="质量" value={QUALITIES.find((q) => q.id === p.quality)?.label}>
        <div className="grid grid-cols-3 gap-1.5">
          {QUALITIES.map((q) => (
            <Row key={q.id} active={p.quality === q.id} onClick={() => p.onQualityChange(q.id)}>{q.label}</Row>
          ))}
        </div>
      </Chip>

      <Chip icon={Timer} label="时长" value={`${p.duration}s`}>
        <div className="grid grid-cols-3 gap-1.5">
          {DURATIONS.map((d) => (
            <Row key={d} active={p.duration === d} onClick={() => p.onDurationChange(d)}>{d}s</Row>
          ))}
        </div>
      </Chip>

      <Chip icon={Hash} label="数量" value={String(p.count)}>
        <div className="grid grid-cols-3 gap-1.5">
          {COUNTS.map((n) => (
            <Row key={n} active={p.count === n} onClick={() => p.onCountChange(n)}>{n} 个</Row>
          ))}
        </div>
      </Chip>

      <Chip icon={SlidersHorizontal} label="更多">
        <div className="space-y-0.5">
          <Toggle label="生成配音" icon={Music} on={p.generateAudio} onChange={p.onGenerateAudioChange} note="Seedance Omni 同时生成音轨" />
          <Toggle label="多镜头分镜" icon={SlidersHorizontal} on={p.multiShot} onChange={p.onMultiShotChange} note="每镜独立生成后合成" />
          <Toggle label="后续唇形同步" icon={Mic} on={p.postLipsync} onChange={p.onPostLipsyncChange} note="成片后带入 Kling 口型" />
        </div>
      </Chip>
    </>
  );
}
