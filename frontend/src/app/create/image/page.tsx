"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles, ImagePlus, Upload, X, Clock, RefreshCw,
  Download, Video, ExternalLink, ImageIcon, Wand2, CheckCircle2,
  Copy, Maximize2, XCircle, Plus, Trash2, Coins, CheckSquare, Square,
} from "lucide-react";
import { ImageParamBar } from "@/components/ImageParamBar";
import { ImageAppsRow } from "@/components/ImageAppsRow";
import { BatchPromptInput } from "@/components/BatchPromptInput";
import { CosmicPromptCard } from "@/components/cosmic/CosmicPromptCard";
import type { CreativityLevel } from "@/components/CreativitySlider";
import { Loading, Empty, ErrorState } from "@/components/StatusStates";
import { useAuthStore, useCreationStore, useOnboardingStore } from "@/lib/stores";
import { useToast } from "@/components/Toast";
import {
  submitGeneration, getTaskStatus, uploadImage, trackOnboarding, cancelTask,
  listCreativeSessions, createCreativeSession, getCreativeSession,
  updateCreativeSession, deleteCreativeSession,
  type GenerateResponse, type TaskResult, type CreativeSession, API_BASE,
} from "@/lib/api";
import { cn } from "@/lib/utils";

// Compose a real WxH from an aspect ratio + a resolution tier (long edge px).
function resolveResolution(aspect: string, tier: string): string {
  const longEdge: Record<string, number> = { "720p": 720, "1080p": 1080, "2K": 1440, "4K": 2160 };
  const L = longEdge[tier] ?? 1080;
  const ratios: Record<string, [number, number]> = {
    "1:1": [1, 1], "16:9": [16, 9], "9:16": [9, 16], "4:3": [4, 3], "3:4": [3, 4],
  };
  const [rw, rh] = ratios[aspect] ?? [1, 1];
  const even = (n: number) => Math.max(2, Math.round(n / 2) * 2);
  if (rw >= rh) {
    return `${even(L)}x${even((L * rh) / rw)}`;
  }
  return `${even((L * rw) / rh)}x${even(L)}`;
}

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

// ═══════════════════════════════════════════════════════════
// Page Component
// ═══════════════════════════════════════════════════════════

export default function CreateImagePage() {
  const router = useRouter();
  const toast = useToast();
  const user = useAuthStore((s) => s.user);
  const completeOnboarding = useOnboardingStore((s) => s.completeFor);

  // ── Store ────────────────────────────────────────────
  const {
    prompt, setPrompt, selectedModel, setSelectedModel,
    quality, setQuality, style, setStyle, creativity, setCreativity,
    resolution, setResolution, aspectRatio, setAspectRatio,
    count, setCount, referenceFiles, addReference, removeReference, reorderReference,
    remoteRefs, addRemoteRef, removeRemoteRef,
    negativePrompt, setNegativePrompt, seedInput, setSeedInput,
    addRecentPrompt, addResult, results, setResults,
    activeTab, setActiveTab,
  } = useCreationStore();

  // ── Local State ──────────────────────────────────────
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const [prefillPrompt, setPrefillPrompt] = useState("");
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
  const [imageModels, setImageModels] = useState<Array<{ id: string; name: string; desc: string; badge?: string; credits?: number }>>(IMAGE_MODELS_FALLBACK);

  // Result interactions
  const [lightbox, setLightbox] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [queuePos, setQueuePos] = useState<number | null>(null);
  const cancelledRef = useRef(false);

  // Sessions
  const [sessions, setSessions] = useState<CreativeSession[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);

  const refreshSessions = useCallback(async () => {
    try { setSessions(await listCreativeSessions()); } catch { /* guest/offline ok */ }
  }, []);
  useEffect(() => { refreshSessions(); }, [refreshSessions]);

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
          ...active.map((m: { id: string; display_name: string; description?: string; provider?: string; capabilities?: { cost_per_image_credits?: number } }) => ({
            id: m.id,
            name: m.display_name,
            desc: (m.description || m.provider || "").slice(0, 48),
            badge: "已验证",
            credits: m.capabilities?.cost_per_image_credits,
          })),
        ]);
      })
      .catch(() => {});
  }, []);

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
    // Remix pre-fill (?prompt=&model=&image_url=) from explore/library page
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
      addRemoteRef(remixImage);
    }
  }, [imageModels, setPrompt, setSelectedModel, addRemoteRef]); // remix pre-fill when models load

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

  const handleSubmit = useCallback(async (promptOverride?: string) => {
    // The Cosmic prompt card keeps its text internally and calls setPrompt(p)
    // then handleSubmit() in the same tick — so the store `prompt` may be stale
    // here. Accept an explicit override to avoid the race.
    const effPrompt = (promptOverride ?? prompt).trim();
    if (!effPrompt || submitting) return;

    cancelledRef.current = false;
    setSubmitting(true);
    setError(null);
    setProgress(0);
    setQueuePos(null);
    setProgressStage("正在提交...");
    setEstimatedSeconds(null);
    addRecentPrompt(effPrompt);
    const startedAt = Date.now();

    try {
      // 1) Upload local reference images, then append remote (remix) refs; cap 4.
      let referenceImages: string[] | undefined;
      const urls: string[] = [];
      if (referenceFiles.length > 0) {
        setProgressStage("上传参考图...");
        for (const ref of referenceFiles.slice(0, 4)) {
          const uploaded = await uploadImage(ref.file);
          if (uploaded.url) urls.push(uploaded.url);
        }
      }
      const combined = [...urls, ...remoteRefs].slice(0, 4);
      referenceImages = combined.length ? combined : undefined;

      // 2) Submit generation (real resolution from aspect + tier; seed / negative)
      const seedNum = seedInput.trim() ? Number(seedInput.trim()) : undefined;
      const res: GenerateResponse = await submitGeneration({
        prompt: effPrompt,
        media_type: "image",
        model: selectedModel === "auto" ? undefined : selectedModel,
        quality,
        resolution: resolveResolution(aspectRatio, resolution),
        count,
        style: style || undefined,
        enhance_prompt: creativity !== "wild",
        image_url: referenceImages?.[0],
        reference_images: referenceImages,
        seed: seedNum,
        negative_prompt: negativePrompt.trim() || undefined,
      });

      setTaskId(res.task_id);
      if (user?.id) trackOnboarding("generation_submitted");
      setEstimatedSeconds(res.estimated_time_seconds || 30);
      setProgress(5);
      setProgressStage("模型推理中...");

      // 2) Poll until complete (abortable via cancel button)
      const pollInterval = 2000;
      const maxPolls = 150; // 5 minutes max
      let polls = 0;

      const poll = async (): Promise<TaskResult> => {
        if (cancelledRef.current) throw new Error("__cancelled__");
        if (polls++ > maxPolls) throw new Error("生成超时，请重试");
        const status = await getTaskStatus(res.task_id);

        if ("queue_position" in status && typeof status.queue_position === "number") {
          setQueuePos(status.queue_position);
        }
        if ("progress" in status && typeof status.progress === "number") {
          setProgress(Math.min(status.progress, 99));
        }
        if ("current_stage" in status && status.current_stage) {
          setProgressStage(status.current_stage);
        }

        if (status.status === "completed" || status.status === "failed" || status.status === "cancelled") {
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
      if (result.status === "cancelled") {
        throw new Error("__cancelled__");
      }

      // 3) Add results (with per-image credits + elapsed time)
      const resultCount = result.results?.length || 0;
      const elapsedMs = Date.now() - startedAt;
      const perCredits = resultCount > 0 && result.cost_credits != null
        ? Math.round((result.cost_credits / resultCount) * 100) / 100
        : (res.estimated_cost_credits != null && count > 0 ? res.estimated_cost_credits / count : undefined);
      const newItems: typeof results = [];
      if (result.results && result.results.length > 0) {
        for (const r of result.results) {
          const item = {
            url: r.url,
            type: (r.type || "image") as "image" | "video",
            prompt: effPrompt,
            model: res.estimated_model || selectedModel,
            seed: (r as any).seed ?? seedNum,
            credits: perCredits,
            elapsedMs,
          };
          addResult(item);
          newItems.push(item);
        }
      }

      setHasSubmitted(true);
      toast.success("生成完成", `已生成 ${resultCount} 张图片`);
      if (resultCount > 0 && user?.id) {
        completeOnboarding(String(user.id));
        trackOnboarding("first_work_completed");
      }

      // 4) Persist into the active session (auto-create one if none)
      if (newItems.length > 0) {
        try {
          const merged = [...newItems, ...results].slice(0, 60).map((it) => ({
            url: it.url, type: it.type, prompt: it.prompt, model: it.model,
            seed: it.seed, credits: it.credits,
          }));
          if (!activeSession) {
            // Create the session WITH its assets in one request (avoids a
            // create→patch round-trip race under concurrent dev-DB writes).
            const created = await createCreativeSession(effPrompt.slice(0, 40) || "图片会话", merged);
            setActiveSession(created.session_uid);
          } else {
            await updateCreativeSession(activeSession, { assets: merged });
          }
          await refreshSessions();
        } catch { /* session persistence best-effort */ }
      }

    } catch (err: any) {
      if (err?.message === "__cancelled__") {
        toast.info?.("已取消", "本次生成已取消");
      } else {
        const message = err.message || "生成失败，请重试";
        setError(message);
        toast.error("生成失败", message);
        console.error("Generation error:", err);
      }
    } finally {
      setSubmitting(false);
      setTaskId(null);
      setProgress(0);
      setQueuePos(null);
      setProgressStage("");
      setEstimatedSeconds(null);
    }
  }, [
    prompt, selectedModel, quality, resolution, aspectRatio, count,
    style, creativity, submitting, referenceFiles, remoteRefs, seedInput, negativePrompt,
    addRecentPrompt, addResult, toast, user?.id, completeOnboarding,
    activeSession, results, refreshSessions,
  ]);

  // Cancel the in-flight generation (revokes worker + refunds, stops polling).
  const handleCancel = useCallback(async () => {
    cancelledRef.current = true;
    const id = taskId;
    if (id) {
      try { await cancelTask(id); } catch { /* best-effort */ }
    }
    setSubmitting(false);
    setTaskId(null);
    setProgress(0);
    setQueuePos(null);
    setProgressStage("");
  }, [taskId]);

  // Session actions
  const handleNewSession = useCallback(async () => {
    try {
      const created = await createCreativeSession("新图片会话");
      setActiveSession(created.session_uid);
      setResults([]);
      await refreshSessions();
      toast.success("已新建会话", "");
    } catch { toast.error("新建失败", "请登录后使用会话"); }
  }, [refreshSessions, setResults, toast]);

  const handleSwitchSession = useCallback(async (uid: string) => {
    try {
      const s = await getCreativeSession(uid);
      setActiveSession(uid);
      const items = (s.assets || []).map((a) => ({
        url: a.url, type: (a.type || "image") as "image" | "video",
        prompt: a.prompt || "", model: a.model || "", seed: a.seed, credits: a.credits,
      }));
      setResults(items);
    } catch { toast.error("加载会话失败", ""); }
  }, [setResults, toast]);

  const handleDeleteSession = useCallback(async (uid: string) => {
    try {
      await deleteCreativeSession(uid);
      if (activeSession === uid) { setActiveSession(null); setResults([]); }
      await refreshSessions();
    } catch { toast.error("删除失败", ""); }
  }, [activeSession, refreshSessions, setResults, toast]);

  // 单资产迭代：变体(同 prompt/model，新种子×4) 或 复现(同种子)
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
        addResult({ url: r.url, type: (r.type || "image") as "image" | "video",
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
          resolution: resolveResolution(aspectRatio, resolution),
          count,
          style: style || undefined,
          enhance_prompt: creativity !== "wild",
          negative_prompt: negativePrompt.trim() || undefined,
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
  }, [selectedModel, quality, aspectRatio, resolution, count, style, creativity, negativePrompt, addRecentPrompt, addResult, toast, setPrompt]);

  // ── Reference preview: local uploads first, then remote (remix) URLs ──
  const combinedRefs = [
    ...referenceFiles.map((r) => ({ preview: r.preview, name: r.file?.name })),
    ...remoteRefs.map((u) => ({ preview: u, name: "remix" })),
  ].slice(0, 4);
  const handleRemoveRef = useCallback((i: number) => {
    if (i < referenceFiles.length) removeReference(i);
    else removeRemoteRef(i - referenceFiles.length);
  }, [referenceFiles.length, removeReference, removeRemoteRef]);

  // ── Batch download / selection helpers ──
  const toggleSelect = useCallback((url: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(url)) next.delete(url); else next.add(url);
      return next;
    });
  }, []);
  const downloadUrls = useCallback(async (urls: string[]) => {
    for (const u of urls) {
      try {
        const a = document.createElement("a");
        a.href = u; a.download = ""; a.target = "_blank"; a.rel = "noopener";
        document.body.appendChild(a); a.click(); a.remove();
        await new Promise((r) => setTimeout(r, 350));
      } catch { /* ignore */ }
    }
  }, []);
  const copyPrompt = useCallback((p: string) => {
    navigator.clipboard?.writeText(p).then(
      () => toast.success("已复制提示词", ""),
      () => toast.error("复制失败", ""),
    );
  }, [toast]);

  // ── Credit estimate for the param bar ──
  const selectedModelObj = imageModels.find((m) => m.id === selectedModel);
  const perImageCredits = selectedModelObj?.credits ?? null;
  const estimatedCredits = perImageCredits != null ? perImageCredits * count : null;

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

  const goPill = (href: string) => router.push(href);

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* ── Left: Sessions ──────────────────────────── */}
      <div className="hidden lg:block w-56 p-4 pt-6 border-r border-cosmic-border/40 overflow-y-auto flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">会话</p>
          <button
            onClick={handleNewSession}
            className="inline-flex items-center gap-0.5 text-[11px] text-accent-cyan hover:opacity-80"
            title="新建会话"
          >
            <Plus className="w-3.5 h-3.5" /> 新建
          </button>
        </div>
        {sessions.length === 0 ? (
          <p className="text-[11px] text-text-secondary/50 leading-relaxed">
            生成后自动创建会话，历史作品按会话归档。
          </p>
        ) : (
          <div className="space-y-1">
            {sessions.map((s) => (
              <div
                key={s.session_uid}
                className={cn(
                  "group flex items-center justify-between gap-1 px-2.5 py-1.5 rounded-lg text-xs cursor-pointer transition-colors",
                  activeSession === s.session_uid
                    ? "bg-accent-cyan/[0.08] border border-accent-cyan/20 text-accent-cyan"
                    : "text-text-secondary hover:bg-cosmic-surface/30 border border-transparent"
                )}
                onClick={() => handleSwitchSession(s.session_uid)}
              >
                <span className="truncate flex-1">{s.title || "未命名会话"}</span>
                <span className="text-[9px] text-text-secondary/50">{s.assets?.length ?? 0}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.session_uid); }}
                  className="opacity-0 group-hover:opacity-100 text-text-secondary/60 hover:text-destructive transition-opacity"
                  title="删除会话"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Center: Creation Area ───────────────────────── */}
      <div className="flex-1 flex flex-col p-4 pt-6 overflow-y-auto">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex-1 flex flex-col max-w-3xl mx-auto w-full"
        >
          {/* ═══════════ Title + tool pills (Yapper-style) ═══════════ */}
          <div className="text-center mb-5">
            <h1 className="text-2xl font-bold tracking-tight text-text-primary">
              Prompt · 编辑 · 合成专业图像
            </h1>
            <div className="mt-3 flex items-center justify-center gap-2 flex-wrap">
              {[
                { label: "创意构思", href: "/agent", badge: "App" },
                { label: "图片编辑器", href: "/create/image-editor", badge: "App" },
                { label: "产品图", href: "/create/product", badge: "App" },
              ].map((pill) => (
                <button
                  key={pill.label}
                  onClick={() => goPill(pill.href)}
                  className="group inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium bg-cosmic-surface/50 border border-cosmic-border/60 text-text-secondary hover:text-text-primary hover:border-accent-cyan/40 transition-colors"
                >
                  <Sparkles className="w-3.5 h-3.5 text-accent-cyan/80" />
                  {pill.label}
                  <span className="px-1 py-0.5 rounded text-[8px] font-semibold bg-accent-cyan/[0.12] text-accent-cyan">{pill.badge}</span>
                </button>
              ))}
            </div>
          </div>

          {/* ═══════════ Prompt Area (Cosmic) ═══════════ */}
          <div className="flex flex-col">
            {/* Cosmic Prompt Card */}
            <CosmicPromptCard
              onSubmit={(p: string) => { setPrompt(p); handleSubmit(p); }}
              placeholder="输入提示词，或上传图片进行编辑 / 合成..."
              suggestions={SUGGESTIONS}
              loading={submitting}
              mode="图片创作"
              initialValue={prefillPrompt}
              referenceFiles={combinedRefs}
              onAddReference={handleAddReference}
              onRemoveReference={handleRemoveRef}
              onReorderReference={reorderReference}
              maxReferences={4}
            />

            {/* Consolidated parameter toolbar (all configs via dropdowns) */}
            <div className="mt-2.5 px-1">
              <ImageParamBar
                models={imageModels}
                selectedModel={selectedModel}
                onModelSelect={setSelectedModel}
                aspectRatio={aspectRatio}
                onAspectChange={setAspectRatio}
                resolution={resolution}
                onResolutionChange={setResolution}
                count={count}
                onCountChange={setCount}
                quality={quality}
                onQualityChange={setQuality}
                seedInput={seedInput}
                onSeedChange={setSeedInput}
                negativePrompt={negativePrompt}
                onNegativeChange={setNegativePrompt}
                style={style}
                onStyleChange={setStyle}
                creativity={creativity}
                onCreativityChange={(c: CreativityLevel) => setCreativity(c)}
                estimatedCredits={estimatedCredits}
                perImageCredits={perImageCredits}
              />
            </div>
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

                {/* Time estimate + elapsed + queue position */}
                <div className="flex items-center justify-between px-1">
                  <div className="flex items-center gap-1.5 text-xs text-text-secondary">
                    <Clock className="w-3 h-3" />
                    <span>已耗时 {elapsedSeconds}s</span>
                    {queuePos != null && queuePos > 0 && (
                      <span className="ml-2 px-1.5 py-0.5 rounded bg-cosmic-subtle text-[10px] text-text-secondary/80">
                        队列第 {queuePos + 1} 位
                      </span>
                    )}
                  </div>
                  {remainingDisplay && (
                    <span className="text-xs text-text-secondary/60">
                      预计剩余 {remainingDisplay}
                    </span>
                  )}
                </div>

                {/* Cancel */}
                <button
                  onClick={handleCancel}
                  className="w-full mt-1 inline-flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs border border-cosmic-border/60 text-text-secondary hover:text-destructive hover:border-destructive/40 transition-colors"
                >
                  <XCircle className="w-3.5 h-3.5" /> 取消生成
                </button>
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
                {/* Header + batch toolbar */}
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">
                    生成结果 ({imageResults.length})
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        const all = imageResults.map((r) => r.url);
                        setSelected((prev) => (prev.size === all.length ? new Set() : new Set(all)));
                      }}
                      className="inline-flex items-center gap-1 text-[11px] text-text-secondary hover:text-accent-cyan"
                    >
                      {selected.size === imageResults.length && imageResults.length > 0
                        ? <CheckSquare className="w-3.5 h-3.5" /> : <Square className="w-3.5 h-3.5" />}
                      全选
                    </button>
                    <button
                      onClick={() => downloadUrls(selected.size ? imageResults.filter((r) => selected.has(r.url)).map((r) => r.url) : imageResults.map((r) => r.url))}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] bg-accent-cyan/[0.1] text-accent-cyan hover:bg-accent-cyan/20 transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      {selected.size ? `下载所选 (${selected.size})` : "下载全部"}
                    </button>
                  </div>
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
                      {/* Image (click to open lightbox) */}
                      <img
                        src={item.url}
                        alt={item.prompt}
                        onClick={() => setLightbox(item.url)}
                        className="w-full aspect-square object-cover cursor-zoom-in"
                        loading="lazy"
                      />

                      {/* Selection checkbox */}
                      <button
                        onClick={(e) => { e.stopPropagation(); toggleSelect(item.url); }}
                        className="absolute top-2 left-2 w-6 h-6 rounded-md bg-black/55 backdrop-blur-sm flex items-center justify-center text-white/90"
                        title="选择"
                      >
                        {selected.has(item.url)
                          ? <CheckSquare className="w-4 h-4 text-accent-cyan" /> : <Square className="w-4 h-4" />}
                      </button>

                      {/* Seed Badge */}
                      {item.seed != null && (
                        <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-black/50 backdrop-blur-sm text-[10px] text-white/70 font-mono" title="随机种子">
                          🌱 {item.seed}
                        </div>
                      )}

                      {/* Actions Overlay — container ignores pointer events so a
                          plain image click opens the lightbox; buttons re-enable. */}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-end justify-center gap-1.5 p-3 flex-wrap pointer-events-none">
                        {/* Maximize / lightbox */}
                        <button
                          onClick={() => setLightbox(item.url)}
                          className="btn-icon bg-white/10 hover:bg-white/20 backdrop-blur-sm text-text-accent-cyan pointer-events-auto"
                          title="放大预览"
                        >
                          <Maximize2 className="w-4 h-4" />
                        </button>
                        {/* 变体 (variations) */}
                        <button
                          onClick={() => iterate("vary", { prompt: item.prompt, model: item.model, seed: item.seed })}
                          disabled={submitting}
                          className="btn-icon bg-brand/[0.85] hover:bg-brand backdrop-blur-sm text-white disabled:opacity-50 pointer-events-auto"
                          title="生成变体（同提示词，新随机种子）"
                        >
                          <Wand2 className="w-4 h-4" />
                        </button>
                        {/* 复现 (reproduce same seed) */}
                        <button
                          onClick={() => iterate("reproduce", { prompt: item.prompt, model: item.model, seed: item.seed })}
                          disabled={submitting || item.seed == null}
                          className="btn-icon bg-white/10 hover:bg-white/20 backdrop-blur-sm text-text-accent-cyan disabled:opacity-40 pointer-events-auto"
                          title={item.seed != null ? `按种子复现 (${item.seed})` : "无种子信息"}
                        >
                          <RefreshCw className="w-4 h-4" />
                        </button>
                        {/* Copy prompt */}
                        <button
                          onClick={() => copyPrompt(item.prompt)}
                          className="btn-icon bg-white/10 hover:bg-white/20 backdrop-blur-sm text-text-accent-cyan pointer-events-auto"
                          title="复制提示词"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                        {/* Download */}
                        <a
                          href={item.url}
                          download
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-icon bg-white/10 hover:bg-white/20 backdrop-blur-sm text-text-accent-cyan pointer-events-auto"
                          title="下载"
                        >
                          <Download className="w-4 h-4" />
                        </a>
                        {/* Use in Video */}
                        <button
                          onClick={() => router.push("/create/video")}
                          className="btn-icon bg-accent-cyan/[0.12] hover:bg-accent-cyan/30 backdrop-blur-sm text-accent-cyan pointer-events-auto"
                          title="用于视频"
                        >
                          <Video className="w-4 h-4" />
                        </button>
                      </div>

                      {/* Metadata footer: model · credits · elapsed */}
                      <div className="absolute bottom-0 inset-x-0 px-2.5 py-1.5 bg-gradient-to-t from-black/75 to-transparent flex items-center justify-between text-[10px] text-white/75 pointer-events-none group-hover:opacity-0 transition-opacity">
                        <span className="inline-flex items-center gap-1 truncate max-w-[55%]">
                          <ImageIcon className="w-3 h-3" /> {item.model}
                        </span>
                        <span className="inline-flex items-center gap-2">
                          {item.credits != null && (
                            <span className="inline-flex items-center gap-0.5"><Coins className="w-3 h-3" />{item.credits}</span>
                          )}
                          {item.elapsedMs != null && (
                            <span>{(item.elapsedMs / 1000).toFixed(1)}s</span>
                          )}
                        </span>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ═══════════ Image Apps (all tools grouped, Yapper-style) ═══════════ */}
          <ImageAppsRow className="mt-10 mb-4" />
        </motion.div>
      </div>

      {/* ── Lightbox (放大预览) ─────────────────────────── */}
      <AnimatePresence>
        {lightbox && (
          <motion.div
            key="lightbox"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setLightbox(null)}
            className="fixed inset-0 z-[100] bg-black/85 backdrop-blur-sm flex items-center justify-center p-6"
          >
            <button
              onClick={() => setLightbox(null)}
              className="absolute top-5 right-5 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white"
              title="关闭"
            >
              <X className="w-5 h-5" />
            </button>
            <motion.img
              key={lightbox}
              initial={{ scale: 0.94 }}
              animate={{ scale: 1 }}
              src={lightbox}
              alt="预览"
              onClick={(e) => e.stopPropagation()}
              className="max-w-full max-h-full rounded-lg object-contain shadow-2xl"
            />
            <a
              href={lightbox}
              download
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="absolute bottom-6 inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white text-sm"
            >
              <Download className="w-4 h-4" /> 下载原图
            </a>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
