"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Mic, Film, Puzzle, ImageIcon, VideoIcon, Music,
  Lightbulb, RefreshCw, Play, ChevronRight, ChevronLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useCreationStore } from "@/lib/stores";
import { submitGeneration, getTaskStatus, uploadImage, runStoryboard, type TaskResult, API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { Loading, Empty, ErrorState } from "@/components/StatusStates";
import { ResultGrid } from "@/components/ResultGrid";
import { CosmicVideoPromptArea, type ReferenceMedia, type MultiShot } from "@/components/CosmicVideoPromptArea";
import { CosmicVideoParamPanel } from "@/components/CosmicVideoParamPanel";

/* ════════════════════════════════════════════════════════
   Data
   ════════════════════════════════════════════════════════ */

const VIDEO_MODELS_FALLBACK = [
  { id: "auto", name: "Auto", desc: "智能选择最佳模型", icon: "🤖" },
  { id: "bytedance/seedance-2-fast", name: "Seedance 2.0 Fast", desc: "已验证 · 快速生成", icon: "⚡", badge: "Fast" },
  { id: "seedance-2-fast", name: "Seedance Fast", desc: "已验证视频模型", icon: "🎬", badge: "Active" },
];

const SUGGESTIONS = [
  "电影级科幻城市夜景，赛博朋克风格，缓慢推进镜头，霓虹灯光反射在湿润地面上",
  "自然风光延时摄影，从日出金色光线到满天繁星，平滑过渡",
  "产品展示视频：香水瓶360°旋转，柔和聚光灯，白色背景，电影级调色",
  "第一人称视角穿越未来城市，飞行汽车穿梭，全息广告牌，动态运镜",
];

const ASPECT_RATIOS = [
  { value: "16:9", label: "16:9", icon: "▬" },
  { value: "9:16", label: "9:16", icon: "▮" },
  { value: "1:1", label: "1:1", icon: "■" },
  { value: "4:3", label: "4:3", icon: "▯" },
  { value: "21:9", label: "21:9", icon: "▬▬" },
];

const RESOLUTIONS = ["720p", "1080p", "2K", "4K"];

interface LeftTool {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  desc: string;
  href?: string;
  action?: "image" | "video" | "audio";
  color: string;
}

const LEFT_TOOLS: LeftTool[] = [
  { icon: Mic, label: "唇形同步", desc: "Lip Sync", href: "/create/lipsync", color: "text-purple-400" },
  { icon: Film, label: "动态同步", desc: "Motion", href: "/create/motion", color: "text-rose-400" },
  { icon: Puzzle, label: "时间线", desc: "Timeline", href: "/create/timeline", color: "text-sky-400" },
  { icon: ImageIcon, label: "参考图", desc: "Image", action: "image", color: "text-amber-400" },
  { icon: VideoIcon, label: "参考视频", desc: "Video", action: "video", color: "text-blue-400" },
  { icon: Music, label: "参考音频", desc: "Audio", action: "audio", color: "text-emerald-400" },
];

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
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [videoModels, setVideoModels] = useState(VIDEO_MODELS_FALLBACK);

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
          const uploaded = await uploadImage(ref.file);
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

      // True storyboard: each shot → Director video step (not prompt stitch)
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
          async_mode: true,
        });
        if (sb.job_id) setTaskId(sb.job_id);
        toast.success(
          "真分镜已提交",
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
        resolution: aspectRatio === "1:1" ? "1080x1080"
          : aspectRatio === "16:9" ? "1920x1080"
          : aspectRatio === "9:16" ? "1080x1920"
          : aspectRatio === "21:9" ? "2560x1080"
          : "1920x1080",
        duration,
        count,
        enhance_prompt: true,
        image_url: imageUrl,
        reference_images: referenceImages.length ? referenceImages : undefined,
        reference_videos: referenceVideos.length ? referenceVideos : undefined,
        reference_audios: referenceAudios.length ? referenceAudios : undefined,
        omni: omni || undefined,
        generate_audio: referenceAudios.length > 0 || undefined,
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
      }
    } catch (err: any) {
      const msg = err.message || "视频生成失败，请重试";
      setError(msg);
      toast.error("生成失败", msg);
    } finally {
      setSubmitting(false);
      setTaskId(null);
    }
  }, [prompt, multiShotMode, shots, references, submitting, selectedModel, quality, resolution, aspectRatio, duration, count, addRecentPrompt, addResult, toast]);

  // ── Left tool actions ──
  const handleToolClick = useCallback((tool: LeftTool) => {
    setActiveTool(tool.label);
    if (tool.href) {
      router.push(tool.href);
    } else if (tool.action) {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = tool.action === "image" ? "image/*" : tool.action === "video" ? "video/*" : "audio/*";
      input.onchange = (e) => {
        const f = (e.target as HTMLInputElement).files?.[0];
        if (f) handleAddReference(f, tool.action!);
      };
      input.click();
    }
  }, [router, handleAddReference]);

  // ── Filtered results ──
  const videoResults = results.filter((r) => r.type === "video");

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* ═══ LEFT: Tools Panel ═══ */}
      <div
        className={cn(
          "hidden lg:flex flex-col border-r border-cosmic-border bg-cosmic-surface overflow-y-auto flex-shrink-0 transition-all",
          leftCollapsed ? "w-14" : "w-14 xl:w-48"
        )}
      >
        {/* Collapse toggle */}
        <button
          type="button"
          onClick={() => setLeftCollapsed((v) => !v)}
          className="hidden xl:flex items-center gap-2 px-4 py-3 text-caption text-text-tertiary/60 hover:text-text-tertiary transition-colors"
          aria-label={leftCollapsed ? "展开工具栏" : "收起工具栏"}
        >
          <ChevronLeft className={cn("w-3 h-3 transition-transform", leftCollapsed && "rotate-180")} />
          {!leftCollapsed && <span>收起</span>}
        </button>

        {/* Tools */}
        <div className="flex-1 py-3 px-2 space-y-0.5">
          {LEFT_TOOLS.map((tool, i) => (
            <motion.button
              key={tool.label}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              onClick={() => handleToolClick(tool)}
              title={`${tool.label} — ${tool.desc}`}
              className={cn(
                "flex items-center gap-3 w-full px-2.5 py-2 rounded-lg text-left transition-all duration-200",
                "xl:px-3 xl:py-2.5",
                activeTool === tool.label
                  ? "bg-accent-cyan/[0.08] border border-accent-cyan/20"
                  : "text-text-tertiary hover:text-text-secondary hover:bg-cosmic-subtle border border-transparent"
              )}
            >
              <tool.icon className={cn("w-4 h-4 flex-shrink-0", tool.color)} />
              <div className="hidden xl:flex flex-col items-start min-w-0">
                <span className="text-body-sm font-medium truncate">{tool.label}</span>
                <span className="text-[10px] text-text-tertiary/50 truncate">{tool.desc}</span>
              </div>
            </motion.button>
          ))}
        </div>

        {/* Bottom preview toggle */}
        <button
          onClick={() => setShowPreview(!showPreview)}
          className={cn(
            "flex items-center gap-2 px-2.5 py-3 border-t border-cosmic-border/20 text-caption transition-all",
            showPreview ? "text-accent-cyan" : "text-text-tertiary/50 hover:text-text-tertiary"
          )}
        >
          <Play className="w-4 h-4" />
          <span className="hidden xl:inline">预览</span>
        </button>
      </div>

      {/* ═══ CENTER: Prompt + Preview ═══ */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-3xl mx-auto w-full space-y-4"
          >
            {/* ── Video Prompt Area ── */}
            <CosmicVideoPromptArea
              prompt={prompt}
              onPromptChange={setPrompt}
              onSubmit={handleSubmit}
              loading={submitting}
              references={references}
              onAddReference={handleAddReference}
              onRemoveReference={handleRemoveReference}
              multiShotMode={multiShotMode}
              onMultiShotToggle={(v) => { setMultiShotMode(v); if (v && shots.length === 0) handleShotAdd(); }}
              shots={shots}
              onShotAdd={handleShotAdd}
              onShotUpdate={handleShotUpdate}
              onShotRemove={handleShotRemove}
              onOptimizePrompt={handleOptimizePrompt}
              enhancingPrompt={enhancingPrompt}
              suggestions={SUGGESTIONS}
              onSuggestionClick={setPrompt}
            />

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
                    className="h-full rounded-full"
                    style={{
                      background: "linear-gradient(90deg, hsl(189 94% 48%), hsl(217 91% 60%), hsl(255 92% 66%))",
                    }}
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
          </motion.div>
        </div>
      </div>

      {/* ═══ RIGHT: Parameters ═══ */}
      <div className="hidden xl:block w-72 flex-shrink-0 relative">
        <CosmicVideoParamPanel
          models={videoModels}
          selectedModel={selectedModel}
          onModelSelect={setSelectedModel}
          aspectRatio={aspectRatio}
          onAspectChange={setAspectRatio}
          aspectRatios={ASPECT_RATIOS}
          resolution={resolution}
          onResolutionChange={setResolution}
          resolutions={RESOLUTIONS}
          duration={duration}
          onDurationChange={setDuration}
          count={count}
          onCountChange={setCount}
          quality={quality}
          onQualityChange={(v) => setQuality(v as any)}
          loraScale={50}
          onLoraScaleChange={() => {}}
          cfgScale={7}
          onCfgScaleChange={() => {}}
        />
      </div>
    </div>
  );
}
