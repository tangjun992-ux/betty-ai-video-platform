"use client";

import { useRef, useState, type DragEvent } from "react";
import { ImagePlus, X, Coins, ArrowUp, Upload } from "lucide-react";
import { ImageParamBar, type ParamModel } from "@/components/ImageParamBar";
import type { CreativityLevel } from "@/components/CreativitySlider";
import type { Quality } from "@/lib/stores";
import { cn } from "@/lib/utils";

/* ─────────────────────────────────────────────────────────────
   ImageComposer — a single, unified Yapper-style input box.
   Prompt textarea on top; ONE toolbar row underneath holding the
   reference thumbnails + add-ref + all parameter dropdown chips +
   credit estimate + generate button. No nested/stacked frames.
   ───────────────────────────────────────────────────────────── */

interface Ref { preview: string; name?: string }

interface Props {
  prompt: string;
  onPromptChange: (v: string) => void;
  onGenerate: () => void;
  loading?: boolean;
  placeholder?: string;

  referenceFiles: Ref[];
  onAddReference: (file: File) => void;
  onRemoveReference: (i: number) => void;
  onReorderReference?: (from: number, to: number) => void;
  maxReferences?: number;

  // Parameter bar
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

  estimatedCredits: number | null;
  perImageCredits?: number | null;
}

export function ImageComposer(p: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dropping, setDropping] = useState(false);
  const maxRefs = p.maxReferences ?? 4;
  const atCap = p.referenceFiles.length >= maxRefs;
  const canGenerate = !!p.prompt.trim() && !p.loading;

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) p.onAddReference(f);
    e.target.value = "";
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDropping(false);
    const f = e.dataTransfer.files?.[0];
    if (f && !atCap) p.onAddReference(f);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDropping(true); }}
      onDragLeave={(e) => { e.preventDefault(); setDropping(false); }}
      onDrop={onDrop}
      className={cn(
        "relative w-full rounded-2xl bg-cosmic-surface border transition-all duration-200",
        "shadow-elevation-md",
        dropping ? "border-accent-cyan/50 shadow-glow-medium"
          : "border-cosmic-border/60 focus-within:border-accent-cyan/30 focus-within:shadow-glow-subtle",
      )}
    >
      {/* Drag overlay */}
      {dropping && (
        <div className="absolute inset-0 z-20 rounded-2xl bg-accent-cyan/5 backdrop-blur-sm flex items-center justify-center pointer-events-none">
          <span className="inline-flex items-center gap-2 text-sm text-accent-cyan"><Upload className="w-4 h-4" /> 拖放图片到此处</span>
        </div>
      )}

      {/* Prompt textarea */}
      <textarea
        value={p.prompt}
        onChange={(e) => p.onPromptChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canGenerate) p.onGenerate(); }
        }}
        placeholder={p.placeholder || "输入提示词，或上传图片进行编辑 / 合成..."}
        rows={2}
        className="w-full resize-none bg-transparent px-5 pt-4 pb-2 text-[15px] leading-relaxed text-text-primary placeholder:text-text-tertiary/45 focus:outline-none min-h-[64px] max-h-[220px]"
      />

      {/* Single toolbar row: refs + add + params + credit + generate */}
      <div className="flex items-center gap-2 flex-wrap px-3 pb-3 pt-1">
        {/* Reference thumbnails (inline) */}
        {p.referenceFiles.map((ref, i) => (
          <div
            key={`${ref.preview}-${i}`}
            draggable={!!p.onReorderReference}
            onDragStart={() => setDragIndex(i)}
            onDragOver={(e) => { if (p.onReorderReference) e.preventDefault(); }}
            onDrop={(e) => {
              e.preventDefault();
              if (p.onReorderReference && dragIndex !== null && dragIndex !== i) p.onReorderReference(dragIndex, i);
              setDragIndex(null);
            }}
            className={cn(
              "relative group w-8 h-8 rounded-lg overflow-hidden border flex-shrink-0",
              dragIndex === i ? "border-accent-cyan/60 opacity-60" : "border-cosmic-border/60",
              p.onReorderReference && "cursor-grab active:cursor-grabbing",
            )}
            title={ref.name || "参考图"}
          >
            <img src={ref.preview} alt={ref.name || "参考图"} className="w-full h-full object-cover pointer-events-none" />
            <button
              onClick={() => p.onRemoveReference(i)}
              className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity"
            >
              <X className="w-3.5 h-3.5 text-white" />
            </button>
          </div>
        ))}

        {/* Add reference */}
        <input ref={fileRef} type="file" accept="image/*" onChange={onFile} className="hidden" />
        <button
          type="button"
          onClick={() => { if (!atCap) fileRef.current?.click(); }}
          disabled={atCap}
          title={atCap ? `最多 ${maxRefs} 张参考图` : "添加参考图"}
          className={cn(
            "inline-flex items-center justify-center h-8 w-8 rounded-lg border border-cosmic-border/60 bg-cosmic-surface/40 text-text-secondary transition-colors flex-shrink-0",
            atCap ? "opacity-40 cursor-not-allowed" : "hover:border-accent-cyan/40 hover:text-accent-cyan",
          )}
        >
          <ImagePlus className="w-4 h-4" />
        </button>

        {/* Divider */}
        <span className="w-px h-5 bg-cosmic-border/50 mx-0.5" />

        {/* Parameter chips */}
        <ImageParamBar
          models={p.models}
          selectedModel={p.selectedModel}
          onModelSelect={p.onModelSelect}
          aspectRatio={p.aspectRatio}
          onAspectChange={p.onAspectChange}
          resolution={p.resolution}
          onResolutionChange={p.onResolutionChange}
          count={p.count}
          onCountChange={p.onCountChange}
          quality={p.quality}
          onQualityChange={p.onQualityChange}
          seedInput={p.seedInput}
          onSeedChange={p.onSeedChange}
          negativePrompt={p.negativePrompt}
          onNegativeChange={p.onNegativeChange}
          style={p.style}
          onStyleChange={p.onStyleChange}
          creativity={p.creativity}
          onCreativityChange={p.onCreativityChange}
        />

        {/* Right group: credit + generate */}
        <div className="ml-auto flex items-center gap-2 flex-shrink-0">
          <span className="inline-flex items-center gap-1 text-xs text-text-secondary/80" title="预估消耗积分" data-testid="credit-estimate">
            <Coins className="w-3.5 h-3.5 text-accent-cyan" />
            <span className="font-semibold text-accent-cyan">{p.estimatedCredits != null ? p.estimatedCredits : "—"}</span>
            <span className="text-text-secondary/50">积分</span>
          </span>
          <button
            type="button"
            onClick={() => { if (canGenerate) p.onGenerate(); }}
            disabled={!canGenerate}
            title="生成"
            className={cn(
              "inline-flex items-center justify-center h-9 w-9 rounded-xl transition-all",
              canGenerate
                ? "bg-gradient-to-br from-accent-cyan to-accent-violet text-white shadow-button-glow hover:brightness-110 active:scale-95"
                : "bg-cosmic-subtle text-text-tertiary/50 cursor-not-allowed",
            )}
          >
            {p.loading
              ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              : <ArrowUp className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
