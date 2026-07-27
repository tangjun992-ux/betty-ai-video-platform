"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Play, Puzzle, ImageIcon, Video as VideoIcon, Music, ArrowUp, X, Plus,
  Lightbulb, Camera, Film, RefreshCw, Mic, Activity, Layers, Maximize2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useCreationStore } from "@/lib/stores";
import { submitGeneration, getTaskStatus, uploadMedia, runStoryboard, type TaskResult, API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { Loading, Empty, ErrorState } from "@/components/StatusStates";
import { ResultGrid } from "@/components/ResultGrid";
import { type ReferenceMedia, type MultiShot } from "@/components/CosmicVideoPromptArea";
import { VideoParamBar } from "@/components/video/VideoParamBar";

/* ════════════════════════════════════════════════════════
   Data
   ════════════════════════════════════════════════════════ */

const VIDEO_MODELS_FALLBACK = [
  { id: "auto", name: "Auto", desc: "智能选择最佳模型", icon: "🤖" },
  { id: "seedance-2.0", name: "Seedance 2.0", desc: "已验证 · Omni 多模态", icon: "🎬", badge: "Omni" },
  { id: "seedance-2.0-fast", name: "Seedance 2.0 Fast", desc: "已验证 · 快速生成", icon: "⚡", badge: "Fast" },
  { id: "kling-2.5-turbo", name: "Kling 2.5 Turbo", desc: "已验证视频模型", icon: "🔥", badge: "Active" },
];

const VIDEO_APPS = [
  { icon: Mic, label: "唇形同步", desc: "Studio Lip-Syncing", href: "/create/lipsync" },
  { icon: Activity, label: "动作同步", desc: "Motion Control", href: "/create/motion" },
  { icon: Layers, label: "时间线", desc: "多镜头编排合成", href: "/create/timeline" },
  { icon: Maximize2, label: "AI 放大", desc: "Media Upscaling", href: "/create/upscale" },
];

/** dzine 尺寸体系：按比例 + 分辨率档计算最终输出尺寸 */
function videoDims(aspect: string, size: string): { w: number; h: number } {
  const longSide = size === "4K" ? 3840 : size === "2K" ? 2560 : size === "720p" ? 1280 : 1920;
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

/** Yapper 式参考素材按钮（卡片顶部四分按钮） */
function RefBtn({
  icon: Icon, label, count = 0, onClick,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  count?: number;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="relative flex flex-col items-center justify-center gap-1 w-[70px] py-2.5 rounded-xl border border-cosmic-border bg-cosmic-elevated/50 text-text-tertiary hover:text-text-primary hover:border-cosmic-border-hover transition-colors"
    >
      <Icon className="w-4 h-4" />
      <span className="text-[10px] leading-none">{label}</span>
      {count > 0 && (
        <span className="absolute -top-1 -right-1 min-w-4 h-4 px-1 rounded-full bg-brand text-brand-foreground text-[9px] font-semibold flex items-center justify-center">
          {count}
        </span>
      )}
    </button>
  );
}

/* ════════════════════════════════════════════════════════
   Helpers
   ════════════════════════════════════════════════════════ */

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

async function pollTask(taskId: string, interval: number, maxPolls: number): Promise<TaskResult> {
  let polls = 0;
  const poll = async (): Promise<TaskResult> => {
    if (polls++ > maxPolls) throw new Error("生成超时，请重试");
    const status = await getTaskStatus(taskId);
    if (status.status === "completed" || status.status === "failed") return status as TaskResult;
    await new Promise((r) => setTimeout(r, interval));
    return poll();
  };
  return poll();
}

function formatTime(s: number) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return m > 0 ? `${m}分${sec}秒` : `${sec}秒`;
}

/* ════════════════════════════════════════════════════════
   Page
   ════════════════════════════════════════════════════════ */

export default function CreateVideoPage() {
  const router = useRouter();
  const toast = useToast();
  const {
    prompt, setPrompt,
    selectedModel, setSelectedModel,
    quality, setQuality,
    resolution, setResolution,
    aspectRatio, setAspectRatio,
    count, setCount,
    duration, setDuration,
    addRecentPrompt, addResult, results,
  } = useCreationStore();

  // ── Local state ──
  const [references, setReferences] = useState<ReferenceMedia[]>([]);
  const [multiShotMode, setMultiShotMode] = useState(false);
  const [shots, setShots] = useState<MultiShot[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [enhancingPrompt, setEnhancingPrompt] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [videoModels, setVideoModels] = useState(VIDEO_MODELS_FALLBACK);
  const [generateAudio, setGenerateAudio] = useState(false);
  const [postLipsync, setPostLipsync] = useState(false);
  const [showMore, setShowMore] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/models/?status=active`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        const active = (d.active || []).filter(
          (m: { capabilities?: { media_types?: string[] } }) =>
            m.capabilities?.media_types?.includes("video")
        );
        if (!active.length) return;
        setVideoModels([
          VIDEO_MODELS_FALLBACK[0],
          ...active.map((m: { id: string; display_name: string; description?: string; provider?: string }) => ({
            id: m.id,
            name: m.display_name,
            desc: (m.description || m.provider || "").slice(0, 48),
            icon: "🎬",
            badge: "已验证",
          })),
        ]);
      })
      .catch(() => {});
  }, []);

  // ── Remix pre-fill from URL (?prompt=&model=&image_url=) ──
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const p = params.get("prompt");
    const m = params.get("model");
    const img = params.get("image_url") || params.get("ref");
    if (p) setPrompt(p);
    if (m) {
      const matched = videoModels.find(
        (v) => v.id === m || v.id.endsWith(`/${m}`)
      );
      if (matched) setSelectedModel(matched.id);
    }
    if (img) {
      // Seed a remote reference image for i2v remix (Yapper Explore → Create)
      setReferences((prev) => {
        if (prev.some((r) => r.preview === img || r.name === "remix-ref")) return prev;
        return [
          ...prev,
          { id: uid(), type: "image", file: null as any, preview: img, name: "remix-ref" },
        ];
      });
    }
  }, [videoModels, setPrompt, setSelectedModel]);

  // ── Elapsed timer ──
  useEffect(() => {
    if (!submitting) { setElapsed(0); return; }
    const t = setInterval(() => setElapsed((p) => p + 1), 1000);
    return () => clearInterval(t);
  }, [submitting]);

  // ── References ──
  const handleAddReference = useCallback((file: File, type: "image" | "video" | "audio") => {
    const preview = URL.createObjectURL(file);
    setReferences((prev) => [
      ...prev,
      { id: uid(), type, file, preview, name: file.name },
    ]);
  }, []);

  const handleRemoveReference = useCallback((id: string) => {
    setReferences((prev) => prev.filter((r) => r.id !== id));
  }, []);

  // ── Multi-shot ──
  const handleShotAdd = useCallback(() => {
    setShots((prev) => [
      ...prev,
      { id: uid(), prompt: "", label: `镜头片段 ${prev.length + 1}` },
    ]);
  }, []);

  const handleShotUpdate = useCallback((id: string, prompt: string) => {
    setShots((prev) => prev.map((s) => (s.id === id ? { ...s, prompt } : s)));
  }, []);

  const handleShotRemove = useCallback((id: string) => {
    setShots((prev) => prev.filter((s) => s.id !== id));
  }, []);

  // ── AI Optimize Prompt ──
  const handleOptimizePrompt = useCallback(async () => {
    if (!prompt.trim() || enhancingPrompt) return;
    setEnhancingPrompt(true);
    try {
      const res = await fetch("/api/optimize-prompt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, type: "video" }),
      });
      if (res.ok) {
        const data = await res.json();
        setPrompt(data.optimized || prompt);
        toast.success("Prompt 已优化", "AI 增强了画面描述和运镜指令");
      } else {
        toast.warning("优化失败", "使用原始 prompt 继续");
      }
    } catch {
      toast.warning("优化请求失败", "请检查网络后重试");
    } finally {
      setEnhancingPrompt(false);
    }
  }, [prompt, enhancingPrompt, setPrompt, toast]);

  // ── dzine 尺寸体系：最终输出分辨率 ──
  const finalDims = videoDims(aspectRatio, resolution);
  const finalResolution = `${finalDims.w}x${finalDims.h}`;

  // ── Submit ──
  const handleSubmit = useCallback(async () => {
    if (!prompt.trim() || submitting) return;
    setSubmitting(true);
    setError(null);
    addRecentPrompt(prompt);

    try {
      const finalPrompt = multiShotMode && shots.length > 0
        ? `${prompt}\n\n[多镜头序列]\n${shots.map((s, i) => `镜头${i + 1}: ${s.prompt}`).join("\n")}`
        : prompt;

      // Upload multimodal references (Seedance Omni: images + videos + audios)
      // Remix may inject a remote URL with file=null (Explore → Create).
      const referenceImages: string[] = [];
      const referenceVideos: string[] = [];
      const referenceAudios: string[] = [];
      const pushUpload = async (ref: ReferenceMedia, into: string[]) => {
        if (ref.file) {
          const uploaded = await uploadMedia(ref.file);
          if (uploaded.url) into.push(uploaded.url);
        } else if (ref.preview && (ref.preview.startsWith("http") || ref.preview.startsWith("/"))) {
          into.push(ref.preview);
        }
      };
      for (const ref of references.filter((r) => r.type === "image").slice(0, 9)) {
        await pushUpload(ref, referenceImages);
      }
      for (const ref of references.filter((r) => r.type === "video").slice(0, 3)) {
        await pushUpload(ref, referenceVideos);
      }
      for (const ref of references.filter((r) => r.type === "audio").slice(0, 3)) {
        await pushUpload(ref, referenceAudios);
      }
      const imageUrl = referenceImages[0];
      const omni = referenceVideos.length > 0 || referenceAudios.length > 0 || referenceImages.length > 1;
      const wantAudio = generateAudio || referenceAudios.length > 0;

      // True storyboard: each shot → Director video step (Omni refs shared)
      if (multiShotMode && shots.length > 0) {
        const filled = shots.filter((s) => s.prompt.trim());
        if (!filled.length) throw new Error("请至少填写一个分镜提示词");
        const sb = await runStoryboard({
          brief: prompt.trim() || "多镜头分镜",
          shots: filled.map((s, i) => ({
            prompt: s.prompt.trim(),
            duration: duration || 5,
            label: s.label || `分镜 ${i + 1}`,
          })),
          ref_image_url: imageUrl,
          reference_images: referenceImages.length ? referenceImages : undefined,
          reference_videos: referenceVideos.length ? referenceVideos : undefined,
          reference_audios: referenceAudios.length ? referenceAudios : undefined,
          omni: omni || undefined,
          generate_audio: wantAudio || undefined,
          async_mode: true,
        });
        if (sb.job_id) setTaskId(sb.job_id);
        toast.success(
          omni ? "Omni 真分镜已提交" : "真分镜已提交",
          `${sb.shot_count || filled.length} 个独立镜头已进入导演队列`,
        );
        if (sb.job_id) {
          router.push(`/agent?job=${encodeURIComponent(sb.job_id)}`);
        }
        return;
      }

      const body: any = {
        prompt: finalPrompt,
        media_type: "video",
        // Omni auto-routes to seedance-2.0 server-side when model=auto
        model: omni && (selectedModel === "auto" || !selectedModel)
          ? "seedance-2.0"
          : selectedModel === "auto"
            ? undefined
            : selectedModel,
        quality,
        resolution: finalResolution,
        duration,
        count,
        enhance_prompt: true,
        image_url: imageUrl,
        reference_images: referenceImages.length ? referenceImages : undefined,
        reference_videos: referenceVideos.length ? referenceVideos : undefined,
        reference_audios: referenceAudios.length ? referenceAudios : undefined,
        omni: omni || undefined,
        generate_audio: wantAudio || undefined,
      };

      const res = await submitGeneration(body);
      setTaskId(res.task_id);
      const result = await pollTask(res.task_id, 3000, 200);

      if (result.status === "failed") throw new Error(result.error_message || "视频生成失败");

      if (result.results?.length) {
        for (const r of result.results) {
          addResult({ url: r.url, type: "video", prompt: finalPrompt, model: res.estimated_model || selectedModel });
        }
        toast.success("视频生成完成", `已生成 ${result.results.length} 个视频`);
        setShowPreview(true);
        // Optional: continue to Studio Lip-Sync (Kling avatar) — not Seedance generate_audio
        if (postLipsync && imageUrl) {
          const q = new URLSearchParams({ image_url: imageUrl });
          toast.info("继续唇形同步", "已带入参考图；口型走 Kling avatar，非 Act-One");
          router.push(`/create/lipsync?${q.toString()}`);
        }
      }
    } catch (err: any) {
      const msg = err.message || "视频生成失败，请重试";
      setError(msg);
      toast.error("生成失败", msg);
    } finally {
      setSubmitting(false);
      setTaskId(null);
    }
  }, [prompt, multiShotMode, shots, references, submitting, selectedModel, quality, resolution, aspectRatio, duration, count, generateAudio, postLipsync, addRecentPrompt, addResult, toast, router, finalResolution]);

  // ── 参考素材分类 + 选文件 ──
  const imgRefs = references.filter((r) => r.type === "image");
  const vidRefs = references.filter((r) => r.type === "video");
  const audRefs = references.filter((r) => r.type === "audio");
  const pickRef = useCallback((type: "image" | "video" | "audio") => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = type === "image" ? "image/*" : type === "video" ? "video/*" : "audio/*";
    input.multiple = true;
    input.onchange = (e) => {
      const files = Array.from((e.target as HTMLInputElement).files || []);
      for (const f of files) handleAddReference(f, type);
    };
    input.click();
  }, [handleAddReference]);

  // ── Filtered results ──
  const videoResults = results.filter((r) => r.type === "video");

  return (
    <div className="flex-1 min-h-0 overflow-y-auto">
      <div className="max-w-3xl mx-auto w-full px-4 md:px-6 py-6 md:py-8">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {/* ── Header ── */}
          <div className="text-center mb-2">
            <h1 className="text-2xl md:text-3xl font-semibold tracking-[-0.02em] text-text-primary">
              视频创作
            </h1>
            <p className="text-sm text-text-secondary mt-1.5">
              描述画面、运镜与氛围，选择模型与参数，一键生成
            </p>
          </div>

          {/* ── Yapper 式工作台：顶部参考素材按钮 + 输入 + 参数条 ── */}
          <div>
            <div className="rounded-t-2xl border border-cosmic-border bg-cosmic-surface shadow-elevation-lg overflow-visible">
              {/* 顶部：参考素材四分按钮 + 圆形提交 */}
              <div className="flex items-start gap-2 px-3 pt-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <RefBtn icon={ImageIcon} label="参考图" count={imgRefs.length} onClick={() => pickRef("image")} />
                  <RefBtn icon={VideoIcon} label="参考视频" count={vidRefs.length} onClick={() => pickRef("video")} />
                  <RefBtn icon={Music} label="参考音频" count={audRefs.length} onClick={() => pickRef("audio")} />
                  <RefBtn icon={Puzzle} label="Elements" onClick={() => {}} />
                </div>
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={!prompt.trim() || submitting}
                  aria-label="生成视频"
                  title="生成视频"
                  data-testid="video-submit"
                  className="ml-auto shrink-0 w-9 h-9 rounded-full bg-brand hover:bg-brand-strong text-brand-foreground flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {submitting ? (
                    <span className="w-4 h-4 border-2 border-brand-foreground/40 border-t-brand-foreground rounded-full animate-spin" />
                  ) : (
                    <ArrowUp className="w-4 h-4" />
                  )}
                </button>
              </div>

              {/* 文本区 */}
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
                }}
                rows={3}
                placeholder="描述你想要的视频画面：场景、运镜、光影、氛围，或添加参考素材…"
                data-testid="video-prompt-input"
                className="w-full bg-transparent border-none px-4 pt-2.5 pb-2 text-[15px] leading-relaxed text-text-primary placeholder:text-text-tertiary focus:outline-none focus:ring-0 resize-none"
              />

              {/* 参考素材预览 */}
              {references.length > 0 && (
                <div className="flex items-center gap-2 px-4 pb-3 flex-wrap">
                  {references.map((ref) => (
                    <div key={ref.id} className="relative group">
                      {ref.type === "image" ? (
                        <img src={ref.preview} alt={ref.name} className="w-14 h-14 rounded-lg object-cover border border-cosmic-border" />
                      ) : (
                        <div className="w-14 h-14 rounded-lg border border-cosmic-border bg-cosmic-subtle flex items-center justify-center">
                          {ref.type === "video" ? (
                            <VideoIcon className="w-5 h-5 text-text-tertiary" />
                          ) : (
                            <Music className="w-5 h-5 text-text-tertiary" />
                          )}
                        </div>
                      )}
                      <button
                        type="button"
                        onClick={() => handleRemoveReference(ref.id)}
                        className="absolute -top-1.5 -right-1.5 w-4.5 h-4.5 rounded-full bg-black/70 border border-cosmic-border text-white/80 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <X className="w-2.5 h-2.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 参数条（贴合） */}
            <VideoParamBar
              models={videoModels}
              selectedModel={selectedModel}
              onModelSelect={setSelectedModel}
              aspectRatio={aspectRatio}
              onAspect={setAspectRatio}
              resolution={resolution}
              onResolution={setResolution}
              quality={quality}
              onQuality={(q) => setQuality(q as any)}
              duration={duration}
              onDuration={setDuration}
              count={count}
              onCount={setCount}
              promptLength={prompt.length}
              moreExpanded={showMore}
              onMoreToggle={setShowMore}
            />
          </div>

          {/* ── More 展开：高级选项 ── */}
          <AnimatePresence>
            {showMore && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-4 space-y-4 mt-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={handleOptimizePrompt}
                      disabled={enhancingPrompt || !prompt.trim()}
                      className="toolbar-btn"
                    >
                      {enhancingPrompt ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Lightbulb className="w-3.5 h-3.5" />}
                      AI 优化
                    </button>
                    <button
                      type="button"
                      onClick={() => setGenerateAudio(!generateAudio)}
                      className={cn("toolbar-btn", generateAudio && "!text-brand-strong !bg-brand/5")}
                    >
                      <Music className="w-3.5 h-3.5" /> 生成音轨
                    </button>
                    <button
                      type="button"
                      onClick={() => setPostLipsync(!postLipsync)}
                      className={cn("toolbar-btn", postLipsync && "!text-brand-strong !bg-brand/5")}
                    >
                      <Camera className="w-3.5 h-3.5" /> 完成后唇形
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setMultiShotMode(!multiShotMode);
                        if (!multiShotMode && shots.length === 0) handleShotAdd();
                      }}
                      className={cn("toolbar-btn", multiShotMode && "!text-brand-strong !bg-brand/5")}
                    >
                      <Film className="w-3.5 h-3.5" /> Multi-Shot
                    </button>
                  </div>

                  {multiShotMode && (
                    <div className="space-y-2">
                      {shots.map((shot, i) => (
                        <div key={shot.id} className="flex items-start gap-2">
                          <span className="shrink-0 w-6 h-6 rounded-full bg-cosmic-subtle border border-cosmic-border flex items-center justify-center text-[11px] text-text-tertiary mt-1.5">
                            {i + 1}
                          </span>
                          <textarea
                            value={shot.prompt}
                            onChange={(e) => handleShotUpdate(shot.id, e.target.value)}
                            placeholder={`镜头 ${i + 1} 的 prompt...`}
                            rows={2}
                            className="flex-1 bg-cosmic-subtle border border-cosmic-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-tertiary/50 resize-none focus:outline-none focus:border-brand/30"
                          />
                          <button
                            type="button"
                            onClick={() => handleShotRemove(shot.id)}
                            className="shrink-0 mt-2 text-text-tertiary hover:text-destructive transition-colors"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                      <button type="button" onClick={handleShotAdd} className="toolbar-btn">
                        <Plus className="w-3.5 h-3.5" /> 添加镜头
                      </button>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── Error ── */}
          {error && !submitting && (
            <ErrorState
              message={error}
              onRetry={handleSubmit}
              onDismiss={() => setError(null)}
            />
          )}

          {/* ── Generating State ── */}
          {submitting && taskId && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="p-6 rounded-2xl bg-cosmic-surface border border-cosmic-border shadow-elevation-md"
            >
              <Loading variant="pulse" text={`AI 正在生成视频... ${formatTime(elapsed)}`} />
              <div className="mt-4 h-1.5 rounded-full bg-cosmic-border/40 overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-brand"
                  initial={{ width: "0%" }}
                  animate={{ width: "100%" }}
                  transition={{ duration: 120, ease: "easeInOut" }}
                />
              </div>
              <div className="flex items-center justify-between mt-3">
                <p className="text-caption text-text-tertiary">
                  任务 ID: {taskId.slice(0, 8)}...
                </p>
                <p className="text-caption text-text-tertiary">
                  视频生成 1-5 分钟
                </p>
              </div>
            </motion.div>
          )}

          {/* ── Preview / Results ── */}
          <AnimatePresence>
            {(showPreview || videoResults.length > 0) && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                {videoResults.length > 0 ? (
                  <ResultGrid
                    results={videoResults}
                    loading={false}
                    onDownload={(item) => window.open(item.url, "_blank")}
                  />
                ) : (
                  <div className="p-8 rounded-2xl bg-cosmic-surface/30 border border-dashed border-cosmic-border/40 text-center">
                    <Play className="w-10 h-10 text-text-tertiary/30 mx-auto mb-3" />
                    <p className="text-body-sm text-text-tertiary">生成完成后视频将出现在此处</p>
                    <p className="text-caption text-text-tertiary/50 mt-1">
                      支持 4K 预览播放
                    </p>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── Empty State ── */}
          {!submitting && !error && videoResults.length === 0 && (
            <Empty
              title="开始创作视频"
              description="输入 prompt 描述你想要的视频画面，AI 将为你生成。支持多镜头编排、参考素材引导、AI 智能优化。"
            />
          )}

          {/* ── Video Apps（Yapper 式工具卡片） ── */}
          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="pt-8"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-text-primary">Video Apps</h2>
              <span className="text-[11px] text-text-tertiary">专业视频工具</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {VIDEO_APPS.map((app) => (
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
        </motion.div>
      </div>
    </div>
  );
}
