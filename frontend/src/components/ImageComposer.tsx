"use client";

import { useRef, useState, type DragEvent } from "react";
import { ImagePlus, X, ArrowUp, Upload, Wand2 } from "lucide-react";
import { ImageParamBar, type ParamModel } from "@/components/ImageParamBar";
import { QuoteBar } from "@/components/QuoteBar";
import type { GenerationQuote } from "@/lib/api";
import type { CreativityLevel } from "@/components/CreativitySlider";
import type { Quality } from "@/lib/stores";
import { enhancePrompt } from "@/lib/api";
import { cn } from "@/lib/utils";

/* ─────────────────────────────────────────────────────────────
   ImageComposer — single unified input box modeled on Yapper.
   • One flat rounded container (no nested frames).
   • Round send button + AI-enhance icon at the TOP-RIGHT.
   • One bottom toolbar row: add-image icon + borderless param
     chips (模型/比例/分辨率/数量/更多) + ◎ credits ⓘ on the right.
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
  quote?: GenerationQuote | null;
}

export function ImageComposer(p: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dropping, setDropping] = useState(false);
  const [enhancing, setEnhancing] = useState(false);
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

  const enhance = async () => {
    if (!p.prompt.trim() || enhancing) return;
    setEnhancing(true);
    try {
      const res = await enhancePrompt(p.prompt, "image");
      if (res?.enhanced) p.onPromptChange(res.enhanced);
    } catch { /* best-effort */ }
    finally { setEnhancing(false); }
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDropping(true); }}
      onDragLeave={(e) => { e.preventDefault(); setDropping(false); }}
      onDrop={onDrop}
      className={cn(
        // One clearly-enclosing card like Yapper: elevated fill + a visible
        // (but soft) border + depth shadow wrapping BOTH the prompt and the
        // params row. Constant — no focus brightening / glow.
        "relative w-full rounded-[18px] bg-cosmic-elevated border border-cosmic-border shadow-lg",
        dropping && "border-accent-cyan/40",
      )}
    >
      {/* Drag overlay */}
      {dropping && (
        <div className="absolute inset-0 z-20 rounded-2xl bg-accent-cyan/5 backdrop-blur-sm flex items-center justify-center pointer-events-none">
          <span className="inline-flex items-center gap-2 text-sm text-accent-cyan"><Upload className="w-4 h-4" /> 拖放图片到此处</span>
        </div>
      )}

      {/* Top: prompt textarea + top-right controls */}
      <div className="flex items-start gap-2 px-4 pt-4 pb-1.5">
        <textarea
          value={p.prompt}
          onChange={(e) => p.onPromptChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canGenerate) p.onGenerate(); }
          }}
          placeholder={p.placeholder || "输入提示词，或添加图片进行编辑 / 合成…"}
          rows={2}
          // Suppress the global :focus-visible brand ring so the textarea is
          // seamless inside the card (no green inner box) — like Yapper.
          className="flex-1 resize-none bg-transparent text-[15px] leading-relaxed text-text-primary placeholder:text-text-tertiary/40 outline-none focus:outline-none focus-visible:outline-none focus:shadow-none focus-visible:shadow-none min-h-[64px] max-h-[220px] py-0.5"
        />
        <div className="flex items-center gap-1.5 flex-shrink-0 pt-0.5">
          {/* AI enhance */}
          <button
            type="button"
            onClick={enhance}
            disabled={!p.prompt.trim() || enhancing}
            title="AI 优化提示词"
            className={cn(
              "inline-flex items-center justify-center h-7 w-7 rounded-lg text-text-secondary transition-colors",
              p.prompt.trim() ? "hover:text-accent-cyan hover:bg-cosmic-subtle/60" : "opacity-40 cursor-not-allowed",
            )}
          >
            {enhancing
              ? <span className="w-3.5 h-3.5 border-2 border-accent-cyan/40 border-t-accent-cyan rounded-full animate-spin" />
              : <Wand2 className="w-4 h-4" />}
          </button>
          {/* Send / generate */}
          <button
            type="button"
            onClick={() => { if (canGenerate) p.onGenerate(); }}
            disabled={!canGenerate}
            title="生成"
            className={cn(
              "inline-flex items-center justify-center h-8 w-8 rounded-full transition-all",
              canGenerate
                ? "bg-accent-cyan text-white hover:brightness-110 active:scale-95"
                : "bg-cosmic-subtle text-text-tertiary/50 cursor-not-allowed",
            )}
          >
            {p.loading
              ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              : <ArrowUp className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Bottom toolbar: add-image + param chips + credits (single row) */}
      <div className="flex items-center gap-1 flex-wrap px-3 pb-3 pt-1">
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
              "relative group w-7 h-7 rounded-md overflow-hidden border flex-shrink-0 mr-0.5",
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
              <X className="w-3 h-3 text-white" />
            </button>
          </div>
        ))}

        {/* Add image (leading icon, borderless) */}
        <input ref={fileRef} type="file" accept="image/*" onChange={onFile} className="hidden" />
        <button
          type="button"
          onClick={() => { if (!atCap) fileRef.current?.click(); }}
          disabled={atCap}
          title={atCap ? `最多 ${maxRefs} 张参考图` : "添加图片"}
          className={cn(
            "inline-flex items-center justify-center h-7 w-7 rounded-md text-text-secondary transition-colors flex-shrink-0",
            atCap ? "opacity-40 cursor-not-allowed" : "hover:text-accent-cyan hover:bg-cosmic-subtle/60",
          )}
        >
          <ImagePlus className="w-4 h-4" />
        </button>

        {/* Parameter chips (borderless) */}
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

        {/* Credits + ETA + queue */}
        <QuoteBar quote={p.quote ?? null} fallbackCredits={p.estimatedCredits} />
      </div>
    </div>
  );
}
