"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, ImagePlus, Upload, X, Clock, RefreshCw,
  Download, Video, ExternalLink, ImageIcon, Wand2, CheckCircle2,
} from "lucide-react";
import { ToolSidebar } from "@/components/ToolSidebar";
import { ParameterPanel } from "@/components/ParameterPanel";
import { StyleCardSelector } from "@/components/StyleCardSelector";
import { CreativitySlider } from "@/components/CreativitySlider";
import { BatchPromptInput } from "@/components/BatchPromptInput";
import { CosmicPromptCard } from "@/components/cosmic/CosmicPromptCard";
import { CosmicParamPanel, CosmicSlider, CosmicSelect } from "@/components/cosmic/CosmicParamPanel";
import { Loading, Empty, ErrorState } from "@/components/StatusStates";
import { useCreationStore } from "@/lib/stores";
import { useToast } from "@/components/Toast";
import { submitGeneration, getTaskStatus, type GenerateResponse, type TaskResult } from "@/lib/api";
import { cn } from "@/lib/utils";

// ═══════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════

const IMAGE_MODELS = [
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

// ═══════════════════════════════════════════════════════════
// Page Component
// ═══════════════════════════════════════════════════════════

export default function CreateImagePage() {
  const router = useRouter();
  const toast = useToast();

  // ── Store ────────────────────────────────────────────
  const {
    prompt, setPrompt, selectedModel, setSelectedModel,
    quality, setQuality, style, setStyle, creativity, setCreativity,
    resolution, setResolution, aspectRatio, setAspectRatio,
    count, setCount, referenceFiles, addReference, removeReference,
    addRecentPrompt, addResult, results,
    activeTab, setActiveTab,
  } = useCreationStore();

  // ── Local State ──────────────────────────────────────
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);

  // Progress tracking
  const [progress, setProgress] = useState(0);
  const [progressStage, setProgressStage] = useState<string>("");
  const [estimatedSeconds, setEstimatedSeconds] = useState<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Submission tracking for empty state logic
  const [hasSubmitted, setHasSubmitted] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);
  const elapsedTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Tool pre-fill from URL query param ────────────────
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
  }, []); // Only on mount

  // ── Elapsed timer during generation ──────────────────
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

  // ── Handlers ─────────────────────────────────────────

  const handleAddReference = useCallback((file: File) => {
    const preview = URL.createObjectURL(file);
    addReference(file, preview, "image");
  }, [addReference]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleAddReference(f);
    e.target.value = "";
  }, [handleAddReference]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (prompt.trim() && !submitting) {
        handleSubmit();
      }
    }
  }, [prompt, submitting]);

  const handleSubmit = useCallback(async () => {
    if (!prompt.trim() || submitting) return;

    setSubmitting(true);
    setError(null);
    setProgress(0);
    setProgressStage("正在提交...");
    setEstimatedSeconds(null);
    addRecentPrompt(prompt);

    try {
      // 1) Submit generation
      const res: GenerateResponse = await submitGeneration({
        prompt,
        media_type: "image",
        model: selectedModel === "auto" ? undefined : selectedModel,
        quality,
        resolution: aspectRatio === "1:1" ? "1080x1080"
          : aspectRatio === "16:9" ? "1920x1080"
          : aspectRatio === "9:16" ? "1080x1920"
          : aspectRatio === "4:3" ? "1280x960"
          : "1536x1024",
        count,
        style: style || undefined,
        enhance_prompt: creativity !== "wild",
      });

      setTaskId(res.task_id);
      setEstimatedSeconds(res.estimated_time_seconds || 30);
      setProgress(5);
      setProgressStage("模型推理中...");

      // 2) Poll until complete
      const pollInterval = 2000;
      const maxPolls = 150; // 5 minutes max
      let polls = 0;

      const poll = async (): Promise<TaskResult> => {
        if (polls++ > maxPolls) throw new Error("生成超时，请重试");
        const status = await getTaskStatus(res.task_id);

        // Update progress from server
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
      setProgress(100);

      if (result.status === "failed") {
        throw new Error(result.error_message || "生成失败");
      }

      // 3) Add results
      const resultCount = result.results?.length || 0;
      if (result.results && result.results.length > 0) {
        for (const r of result.results) {
          addResult({
            url: r.url,
            type: (r.type || "image") as "image" | "video",
            prompt: prompt,
            model: res.estimated_model || selectedModel,
          });
        }
      }

      setHasSubmitted(true);

      // Success toast
      toast.success("生成完成", `已生成 ${resultCount} 张图片`);

    } catch (err: any) {
      const message = err.message || "生成失败，请重试";
      setError(message);
      toast.error("生成失败", message);
      console.error("Generation error:", err);
    } finally {
      setSubmitting(false);
      setTaskId(null);
      setProgress(0);
      setProgressStage("");
      setEstimatedSeconds(null);
    }
  }, [
    prompt, selectedModel, quality, resolution, aspectRatio, count,
    style, creativity, submitting, addRecentPrompt, addResult, toast,
  ]);

  const handleRetry = useCallback(() => {
    setError(null);
    handleSubmit();
  }, [handleSubmit]);

  const handleDismissError = useCallback(() => {
    setError(null);
  }, []);

  const handleToolSelect = useCallback((tool: string) => {
    setActiveTool((prev) => (prev === tool ? null : tool));
    if (tool === "产品图") setPrompt("产品摄影，白色背景，专业灯光，高清细节");
    if (tool === "专业头像") setPrompt("专业商务头像，现代办公室背景，柔和光线，高分辨率");
    if (tool === "去背景") setPrompt("移除背景，保留主体，透明背景");
  }, [setPrompt]);

  const handleBatchSubmit = useCallback(async (prompts: string[]) => {
    for (const p of prompts) {
      setPrompt(p);
      await new Promise(r => setTimeout(r, 500));
      // Re-trigger submit with the new prompt value
      // Note: we directly call the async flow since handleSubmit reads from closure
      // For batch mode, we submit synchronously without the debounced callback
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
          resolution: aspectRatio === "1:1" ? "1080x1080"
            : aspectRatio === "16:9" ? "1920x1080"
            : aspectRatio === "9:16" ? "1080x1920"
            : aspectRatio === "4:3" ? "1280x960"
            : "1536x1024",
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
              url: r.url,
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
  }, [selectedModel, quality, aspectRatio, count, style, creativity, addRecentPrompt, addResult, toast, setPrompt]);

  // ── Derived Values ───────────────────────────────────
  const imageResults = results.filter((r) => r.type === "image");
  const showEmpty = !submitting && !error && imageResults.length === 0;
  const showResults = imageResults.length > 0;

  // Remaining time estimate
  const remainingSeconds = estimatedSeconds ? Math.max(0, estimatedSeconds - elapsedSeconds) : null;
  const remainingDisplay = remainingSeconds
    ? remainingSeconds > 60
      ? `约 ${Math.ceil(remainingSeconds / 60)} 分钟`
      : `约 ${remainingSeconds} 秒`
    : null;

  // Progress percentage for display
  const displayProgress = progress > 0 ? progress : (estimatedSeconds && elapsedSeconds > 0
    ? Math.min(95, Math.round((elapsedSeconds / estimatedSeconds) * 100))
    : 0);

  // ═══════════════════════════════════════════════════════
  // Render
  // ═══════════════════════════════════════════════════════

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* ── Left: Tool Sidebar ──────────────────────────── */}
      <div className="hidden lg:block w-56 p-4 pt-6 border-r border-cosmic-border/40 overflow-y-auto flex-shrink-0">
        <ToolSidebar activeTool={activeTool} onToolSelect={handleToolSelect} />
      </div>

      {/* ── Center: Creation Area ───────────────────────── */}
      <div className="flex-1 flex flex-col p-4 pt-6 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex-1 flex flex-col max-w-3xl mx-auto w-full"
        >
          {/* ═══════════ Prompt Area (Cosmic) ═══════════ */}
          <div className="flex-1 flex flex-col">
            {/* Tabs */}
            <div className="flex items-center gap-1 mb-3">
              {PROMPT_TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200",
                    activeTab === tab.id
                      ? "bg-accent-cyan/[0.08] text-accent-cyan"
                      : "text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle"
                  )}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Cosmic Prompt Card */}
            <CosmicPromptCard
              onSubmit={(p: string) => { setPrompt(p); handleSubmit(); }}
              placeholder="描述你想要创作的图像，或上传图片进行编辑..."
              suggestions={SUGGESTIONS}
              loading={submitting}
              mode="图片创作"
              referenceFiles={referenceFiles}
              onAddReference={handleAddReference}
              onRemoveReference={removeReference}
            />
          </div>

          {/* Batch Prompt Input */}
          <BatchPromptInput
            onSubmit={handleBatchSubmit}
            loading={submitting}
            className="mt-4"
          />

          {/* ═══════════ Generation In Progress ═══════════ */}
          <AnimatePresence mode="wait">
            {submitting && (
              <motion.div
                key="generating"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mt-4 space-y-3"
              >
                {/* Loading pulse */}
                <Loading
                  variant="pulse"
                  text={progressStage || "AI 正在生成..."}
                  className="!p-4 rounded-xl bg-cosmic-subtle border border-cosmic-border"
                />

                {/* Task ID */}
                {taskId && (
                  <p className="text-[10px] text-text-secondary/40 px-1 font-mono">
                    任务 {taskId.slice(0, 12)}...
                  </p>
                )}

                {/* Progress bar with shimmer */}
                <div className="relative w-full h-1.5 rounded-full bg-cosmic-subtle overflow-hidden">
                  <motion.div
                    className={cn(
                      "absolute inset-y-0 left-0 rounded-full transition-all duration-500",
                      error ? "bg-destructive" : "bg-gradient-to-r from-primary via-accent-cyan/80 to-primary"
                    )}
                    initial={{ width: "0%" }}
                    animate={{ width: `${displayProgress}%` }}
                    transition={{ type: "spring", stiffness: 100, damping: 20 }}
                  />
                  {/* Shimmer overlay on active progress */}
                  <motion.div
                    className="absolute inset-y-0 w-20 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-progress-shimmer"
                    style={{
                      left: `${Math.max(0, displayProgress - 10)}%`,
                    }}
                  />
                </div>

                {/* Time estimate + elapsed */}
                <div className="flex items-center justify-between px-1">
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
              </motion.div>
            )}
          </AnimatePresence>

          {/* ═══════════ Error State ═══════════ */}
          <AnimatePresence mode="wait">
            {error && !submitting && (
              <motion.div
                key="error"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mt-4"
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

          {/* ═══════════ Empty State ═══════════ */}
          <AnimatePresence mode="wait">
            {showEmpty && (
              <motion.div
                key="empty"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mt-4"
              >
                <Empty
                  icon={<Wand2 className="w-7 h-7 text-text-secondary/40" />}
                  title={hasSubmitted ? "没有生成结果" : "开始创作"}
                  description={
                    hasSubmitted
                      ? "生成已完成但未返回图片，请尝试调整参数后重试"
                      : "输入 prompt 描述你想要的画面，AI 将为你生成精美图片"
                  }
                  action={
                    hasSubmitted
                      ? { label: "重新生成", onClick: handleRetry }
                      : undefined
                  }
                  secondaryAction={
                    !hasSubmitted
                      ? { label: "试试推荐词", onClick: () => setPrompt(SUGGESTIONS[0]) }
                      : undefined
                  }
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* ═══════════ Results Grid (inline, enhanced) ═══════════ */}
          <AnimatePresence mode="wait">
            {showResults && (
              <motion.div
                key="results"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="mt-6"
              >
                {/* Header */}
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">
                    生成结果 ({imageResults.length})
                  </p>
                </div>

                {/* Grid */}
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
                      {/* Image */}
                      <img
                        src={item.url}
                        alt={item.prompt}
                        className="w-full aspect-square object-cover"
                        loading="lazy"
                      />

                      {/* Model Badge */}
                      <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-black/50 backdrop-blur-sm text-[10px] text-text-accent-cyan/80 flex items-center gap-1">
                        <ImageIcon className="w-3 h-3" />
                        <span>{item.model}</span>
                      </div>

                      {/* Actions Overlay */}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-end justify-center gap-2 p-3">
                        {/* Download - btn-icon */}
                        <a
                          href={item.url}
                          download
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-icon bg-white/10 hover:bg-white/20 backdrop-blur-sm text-text-accent-cyan"
                          title="下载"
                        >
                          <Download className="w-4 h-4" />
                        </a>

                        {/* Use in Video */}
                        <button
                          onClick={() => router.push("/create/video")}
                          className="btn-icon bg-accent-cyan/[0.12] hover:bg-accent-cyan/30 backdrop-blur-sm text-accent-cyan"
                          title="用于视频"
                        >
                          <Video className="w-4 h-4" />
                        </button>

                        {/* Open in new tab */}
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-icon bg-white/10 hover:bg-white/20 backdrop-blur-sm text-text-accent-cyan"
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
        </motion.div>
      </div>

      {/* ── Right: Parameter Panel ───────────────────────── */}
      <div className="hidden xl:block w-72 p-4 pt-6 border-l border-cosmic-border/40 overflow-y-auto flex-shrink-0">
        <ParameterPanel
          models={IMAGE_MODELS}
          selectedModel={selectedModel}
          onModelSelect={setSelectedModel}
          aspectRatio={aspectRatio}
          onAspectChange={setAspectRatio}
          resolution={resolution}
          onResolutionChange={setResolution}
          quality={quality}
          onQualityChange={setQuality}
          count={count}
          onCountChange={setCount}
          type="image"
        />
        <StyleCardSelector
          selected={style}
          onChange={setStyle}
          className="mt-4"
        />
        <CreativitySlider
          value={creativity as any}
          onChange={setCreativity}
          className="mt-6"
        />
      </div>
    </div>
  );
}
