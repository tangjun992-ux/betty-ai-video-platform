"use client";

import { useRef, useState } from "react";
import { X, ArrowUp, Wand2, Info, CircleDollarSign, Plus, ImageIcon, VideoIcon, Music } from "lucide-react";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { VideoParamBar, type VideoParamModel } from "@/components/VideoParamBar";
import type { Quality } from "@/lib/stores";
import { cn } from "@/lib/utils";

/* Single unified video composer box, modeled on Yapper /create/video. */

type RefType = "image" | "video" | "audio";
interface RefItem { id: string; type: RefType; preview: string; name?: string }

interface Props {
  prompt: string;
  onPromptChange: (v: string) => void;
  onGenerate: () => void;
  loading?: boolean;
  onEnhance?: () => void;
  enhancing?: boolean;

  references: RefItem[];
  onAddReference: (file: File, type: RefType) => void;
  onRemoveReference: (id: string) => void;

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

  estimatedCredits: number | null;
}

const REF_ICON: Record<RefType, React.ElementType> = { image: ImageIcon, video: VideoIcon, audio: Music };

export function VideoComposer(p: Props) {
  const imgRef = useRef<HTMLInputElement>(null);
  const vidRef = useRef<HTMLInputElement>(null);
  const audRef = useRef<HTMLInputElement>(null);
  const [addOpen, setAddOpen] = useState(false);
  const canGenerate = !!p.prompt.trim() && !p.loading;

  const pick = (type: RefType) => {
    setAddOpen(false);
    (type === "image" ? imgRef : type === "video" ? vidRef : audRef).current?.click();
  };
  const onFile = (type: RefType) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) p.onAddReference(f, type);
    e.target.value = "";
  };

  return (
    <div className="relative w-full rounded-[18px] bg-cosmic-elevated border border-cosmic-border shadow-lg">
      {/* Top: textarea + top-right controls */}
      <div className="flex items-start gap-2 px-4 pt-4 pb-1.5">
        <textarea
          value={p.prompt}
          onChange={(e) => p.onPromptChange(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canGenerate) p.onGenerate(); } }}
          placeholder="描述你想要的视频画面、运镜与氛围，或添加参考素材…"
          rows={2}
          className="flex-1 resize-none bg-transparent text-[15px] leading-relaxed text-text-primary placeholder:text-text-tertiary/40 outline-none focus:outline-none focus-visible:outline-none focus:shadow-none focus-visible:shadow-none min-h-[64px] max-h-[220px] py-0.5"
        />
        <div className="flex items-center gap-1.5 flex-shrink-0 pt-0.5">
          {p.onEnhance && (
            <button
              type="button"
              onClick={p.onEnhance}
              disabled={!p.prompt.trim() || p.enhancing}
              title="AI 优化提示词"
              className={cn(
                "inline-flex items-center justify-center h-7 w-7 rounded-lg text-text-secondary transition-colors",
                p.prompt.trim() ? "hover:text-accent-cyan hover:bg-cosmic-subtle/60" : "opacity-40 cursor-not-allowed",
              )}
            >
              {p.enhancing ? <span className="w-3.5 h-3.5 border-2 border-accent-cyan/40 border-t-accent-cyan rounded-full animate-spin" /> : <Wand2 className="w-4 h-4" />}
            </button>
          )}
          <button
            type="button"
            onClick={() => { if (canGenerate) p.onGenerate(); }}
            disabled={!canGenerate}
            title="生成视频"
            className={cn(
              "inline-flex items-center justify-center h-8 w-8 rounded-full transition-all",
              canGenerate ? "bg-accent-cyan text-white hover:brightness-110 active:scale-95" : "bg-cosmic-subtle text-text-tertiary/50 cursor-not-allowed",
            )}
          >
            {p.loading ? <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" /> : <ArrowUp className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Bottom toolbar */}
      <div className="flex items-center gap-1 flex-wrap px-3 pb-3 pt-1">
        {/* Reference thumbnails */}
        {p.references.map((ref) => {
          const Icon = REF_ICON[ref.type];
          return (
            <div key={ref.id} className="relative group w-7 h-7 rounded-md overflow-hidden border border-cosmic-border/60 flex-shrink-0 mr-0.5 bg-cosmic-subtle" title={ref.name || ref.type}>
              {ref.type === "image"
                ? <img src={ref.preview} alt={ref.name || "参考图"} className="w-full h-full object-cover pointer-events-none" />
                : <span className="w-full h-full flex items-center justify-center text-text-secondary"><Icon className="w-3.5 h-3.5" /></span>}
              <button onClick={() => p.onRemoveReference(ref.id)} className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                <X className="w-3 h-3 text-white" />
              </button>
            </div>
          );
        })}

        {/* Add material (image/video/audio) */}
        <input ref={imgRef} type="file" accept="image/*" onChange={onFile("image")} className="hidden" />
        <input ref={vidRef} type="file" accept="video/*" onChange={onFile("video")} className="hidden" />
        <input ref={audRef} type="file" accept="audio/*" onChange={onFile("audio")} className="hidden" />
        <Popover open={addOpen} onOpenChange={setAddOpen}>
          <PopoverTrigger asChild>
            <button type="button" title="添加素材" className="inline-flex items-center justify-center h-7 w-7 rounded-md text-text-secondary hover:text-accent-cyan hover:bg-cosmic-subtle/60 transition-colors flex-shrink-0">
              <Plus className="w-4 h-4" />
            </button>
          </PopoverTrigger>
          <PopoverContent align="start" sideOffset={6} className="w-40 border-cosmic-border bg-cosmic-surface p-1.5">
            {([["image", "参考图", ImageIcon], ["video", "参考视频", VideoIcon], ["audio", "参考音频", Music]] as const).map(([t, label, Icon]) => (
              <button key={t} onClick={() => pick(t)} className="flex items-center gap-2 w-full px-2.5 py-2 rounded-md text-xs text-text-secondary hover:bg-cosmic-subtle hover:text-text-primary transition-colors">
                <Icon className="w-3.5 h-3.5" /> {label}
              </button>
            ))}
          </PopoverContent>
        </Popover>

        <span className="w-px h-5 bg-cosmic-border/50 mx-0.5" />

        {/* Param chips */}
        <VideoParamBar
          models={p.models}
          selectedModel={p.selectedModel}
          onModelSelect={p.onModelSelect}
          aspectRatio={p.aspectRatio}
          onAspectChange={p.onAspectChange}
          resolution={p.resolution}
          onResolutionChange={p.onResolutionChange}
          duration={p.duration}
          onDurationChange={p.onDurationChange}
          count={p.count}
          onCountChange={p.onCountChange}
          quality={p.quality}
          onQualityChange={p.onQualityChange}
          generateAudio={p.generateAudio}
          onGenerateAudioChange={p.onGenerateAudioChange}
          postLipsync={p.postLipsync}
          onPostLipsyncChange={p.onPostLipsyncChange}
          multiShot={p.multiShot}
          onMultiShotChange={p.onMultiShotChange}
        />

        {/* Credits */}
        <div className="ml-auto inline-flex items-center gap-1 text-xs text-text-secondary/80 pr-1" title="预估消耗积分">
          <CircleDollarSign className="w-3.5 h-3.5 text-accent-cyan/90" />
          <span className="font-medium text-text-primary/90">{p.estimatedCredits != null ? p.estimatedCredits : "—"}</span>
          <Info className="w-3 h-3 opacity-45" />
        </div>
      </div>
    </div>
  );
}
