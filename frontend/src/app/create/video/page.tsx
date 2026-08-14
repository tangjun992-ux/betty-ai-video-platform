"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { Sparkles, Play, Plus, X, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useCreationStore } from "@/lib/stores";
import { submitGeneration, getTaskStatus, uploadMedia, runStoryboard, enhancePrompt, quoteGeneration, type TaskResult, type GenerationQuote, API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { useLocale } from "@/i18n/LocaleProvider";
import { Loading, Empty, ErrorState } from "@/components/StatusStates";
import { ResultGrid } from "@/components/ResultGrid";
import { VideoComposer } from "@/components/VideoComposer";
import { VideoAppsRow } from "@/components/VideoAppsRow";

/* ════════════════════════════════════════════════════════ Data ═══ */

const VIDEO_MODELS_FALLBACK = [
  { id: "auto", name: "Auto", desc: "智能选择最佳模型", icon: "🤖", credits: undefined as number | undefined },
  { id: "seedance-2.0", name: "Seedance 2.0", desc: "已验证 · Omni 多模态", icon: "🎬", badge: "Omni", credits: 4 },
  { id: "seedance-2.0-fast", name: "Seedance 2.0 Fast", desc: "已验证 · 快速生成", icon: "⚡", badge: "Fast", credits: 3 },
  { id: "kling-2.5-turbo", name: "Kling 2.5 Turbo", desc: "已验证视频模型", icon: "🔥", badge: "Active", credits: 7 },
];

interface RefMedia { id: string; type: "image" | "video" | "audio"; file: File | null; preview: string; name?: string }
interface Shot { id: string; prompt: string; label: string }

function uid() { return Math.random().toString(36).slice(2, 10); }

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

/* ════════════════════════════════════════════════════════ Page ═══ */

export default function CreateVideoPage() {
  const router = useRouter();
  const toast = useToast();
  const { locale } = useLocale();
  const en = locale === "en";
  const {
    prompt, setPrompt, selectedModel, setSelectedModel,
    quality, setQuality, resolution, setResolution,
    aspectRatio, setAspectRatio, count, setCount, duration, setDuration,
    addRecentPrompt, addResult, results,
  } = useCreationStore();

  const [references, setReferences] = useState<RefMedia[]>([]);
  const [multiShotMode, setMultiShotMode] = useState(false);
  const [shots, setShots] = useState<Shot[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [enhancing, setEnhancing] = useState(false);
  const [videoModels, setVideoModels] = useState(VIDEO_MODELS_FALLBACK);
  const [generateAudio, setGenerateAudio] = useState(false);
  const [postLipsync, setPostLipsync] = useState(false);
  const [lipsyncText, setLipsyncText] = useState("");
  const [quote, setQuote] = useState<GenerationQuote | null>(null);

  // Default aspect for video is landscape
  useEffect(() => {
    if (!["16:9", "9:16", "1:1", "4:3", "21:9"].includes(aspectRatio)) setAspectRatio("16:9");
  }, []); // eslint-disable-line

  useEffect(() => {
    fetch(`${API_BASE}/models/?status=active`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        const active = (d.active || []).filter(
          (m: { capabilities?: { media_types?: string[] } }) => m.capabilities?.media_types?.includes("video"),
        );
        if (!active.length) return;
        setVideoModels([
          VIDEO_MODELS_FALLBACK[0],
          ...active.map((m: { id: string; display_name: string; description?: string; provider?: string; capabilities?: { cost_per_5s_video_credits?: number } }) => ({
            id: m.id,
            name: m.display_name,
            desc: (m.description || m.provider || "").slice(0, 48),
            icon: "🎬",
            badge: "已验证",
            credits: m.capabilities?.cost_per_5s_video_credits,
          })),
        ]);
      })
      .catch(() => {});
  }, []);

  // Remix pre-fill
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const p = params.get("prompt");
    const m = params.get("model");
    const img = params.get("image_url") || params.get("ref");
    if (p) setPrompt(p);
    if (m) {
      const matched = videoModels.find((v) => v.id === m || v.id.endsWith(`/${m}`));
      if (matched) setSelectedModel(matched.id);
    }
    if (img) {
      setReferences((prev) => prev.some((r) => r.preview === img)
        ? prev : [...prev, { id: uid(), type: "image", file: null, preview: img, name: "remix-ref" }]);
    }
  }, [videoModels, setPrompt, setSelectedModel]);

  useEffect(() => {
    if (!submitting) { setElapsed(0); return; }
    const t = setInterval(() => setElapsed((p) => p + 1), 1000);
    return () => clearInterval(t);
  }, [submitting]);

  useEffect(() => {
    const q = prompt.trim();
    if (!q) { setQuote(null); return; }
    const t = setTimeout(() => {
      quoteGeneration({
        prompt: q,
        media_type: "video",
        model: selectedModel === "auto" ? "auto" : selectedModel,
        duration,
        count,
        lipsync_text: postLipsync ? (lipsyncText.trim() || q) : undefined,
      }).then(setQuote).catch(() => {});
    }, 400);
    return () => clearTimeout(t);
  }, [prompt, selectedModel, duration, count, postLipsync, lipsyncText]);

  const handleAddReference = useCallback((file: File, type: "image" | "video" | "audio") => {
    const preview = URL.createObjectURL(file);
    setReferences((prev) => [...prev, { id: uid(), type, file, preview, name: file.name }]);
  }, []);
  const handleRemoveReference = useCallback((id: string) => {
    setReferences((prev) => prev.filter((r) => r.id !== id));
  }, []);

  const handleShotAdd = useCallback(() => {
    setShots((prev) => [...prev, { id: uid(), prompt: "", label: `镜头 ${prev.length + 1}` }]);
  }, []);
  const handleShotUpdate = useCallback((id: string, p: string) => {
    setShots((prev) => prev.map((s) => (s.id === id ? { ...s, prompt: p } : s)));
  }, []);
  const handleShotRemove = useCallback((id: string) => {
    setShots((prev) => prev.filter((s) => s.id !== id));
  }, []);

  const handleEnhance = useCallback(async () => {
    if (!prompt.trim() || enhancing) return;
    setEnhancing(true);
    try {
      const res = await enhancePrompt(prompt, "video");
      if (res?.enhanced) { setPrompt(res.enhanced); toast.success("Prompt 已优化", "AI 增强了画面与运镜描述"); }
    } catch { toast.warning("优化失败", "使用原始 prompt 继续"); }
    finally { setEnhancing(false); }
  }, [prompt, enhancing, setPrompt, toast]);

  const handleSubmit = useCallback(async () => {
    if (!prompt.trim() || submitting) return;
    setSubmitting(true);
    setError(null);
    addRecentPrompt(prompt);
    try {
      const referenceImages: string[] = [];
      const referenceVideos: string[] = [];
      const referenceAudios: string[] = [];
      const pushUpload = async (ref: RefMedia, into: string[]) => {
        if (ref.file) { const up = await uploadMedia(ref.file); if (up.url) into.push(up.url); }
        else if (ref.preview && (ref.preview.startsWith("http") || ref.preview.startsWith("/"))) into.push(ref.preview);
      };
      for (const ref of references.filter((r) => r.type === "image").slice(0, 9)) await pushUpload(ref, referenceImages);
      for (const ref of references.filter((r) => r.type === "video").slice(0, 3)) await pushUpload(ref, referenceVideos);
      for (const ref of references.filter((r) => r.type === "audio").slice(0, 3)) await pushUpload(ref, referenceAudios);
      const imageUrl = referenceImages[0];
      const omni = referenceVideos.length > 0 || referenceAudios.length > 0 || referenceImages.length > 1;
      const wantAudio = generateAudio || referenceAudios.length > 0;

      if (multiShotMode && shots.length > 0) {
        const filled = shots.filter((s) => s.prompt.trim());
        if (!filled.length) throw new Error("请至少填写一个分镜提示词");
        const sb = await runStoryboard({
          brief: prompt.trim() || "多镜头分镜",
          shots: filled.map((s, i) => ({ prompt: s.prompt.trim(), duration: duration || 5, label: s.label || `分镜 ${i + 1}` })),
          ref_image_url: imageUrl,
          reference_images: referenceImages.length ? referenceImages : undefined,
          reference_videos: referenceVideos.length ? referenceVideos : undefined,
          reference_audios: referenceAudios.length ? referenceAudios : undefined,
          omni: omni || undefined,
          generate_audio: wantAudio || undefined,
          async_mode: true,
        });
        if (sb.job_id) { setTaskId(sb.job_id); toast.success("真分镜已提交", `${sb.shot_count || filled.length} 个镜头进入导演队列`); router.push(`/agent?job=${encodeURIComponent(sb.job_id)}`); }
        return;
      }

      const body: any = {
        prompt,
        media_type: "video",
        model: omni && (selectedModel === "auto" || !selectedModel) ? "seedance-2.0" : selectedModel === "auto" ? undefined : selectedModel,
        quality,
        resolution: aspectRatio === "1:1" ? "1080x1080" : aspectRatio === "9:16" ? "1080x1920" : aspectRatio === "21:9" ? "2560x1080" : aspectRatio === "4:3" ? "1440x1080" : "1920x1080",
        duration,
        count,
        enhance_prompt: true,
        image_url: imageUrl,
        reference_images: referenceImages.length ? referenceImages : undefined,
        reference_videos: referenceVideos.length ? referenceVideos : undefined,
        reference_audios: referenceAudios.length ? referenceAudios : undefined,
        omni: omni || undefined,
        generate_audio: wantAudio || undefined,
        lipsync_text: postLipsync ? (lipsyncText.trim() || prompt) : undefined,
      };
      const res = await submitGeneration(body);
      setTaskId(res.task_id);
      const result = await pollTask(res.task_id, 3000, 200);
      if (result.status === "failed") throw new Error(result.error_message || "视频生成失败");
      if (result.results?.length) {
        for (const r of result.results) addResult({ url: r.url, type: "video", prompt, model: res.estimated_model || selectedModel });
        toast.success("视频生成完成", postLipsync ? "Omni 一体流已完成（含口播唇形）" : `已生成 ${result.results.length} 个视频`);
      }
    } catch (err: any) {
      const msg = err.message || "视频生成失败，请重试";
      setError(msg);
      toast.error("生成失败", msg);
    } finally {
      setSubmitting(false);
      setTaskId(null);
    }
  }, [prompt, multiShotMode, shots, references, submitting, selectedModel, quality, aspectRatio, duration, count, generateAudio, postLipsync, lipsyncText, addRecentPrompt, addResult, toast, router]);

  const videoResults = results.filter((r) => r.type === "video");
  const selVid = videoModels.find((m) => m.id === selectedModel);
  const per5s = selVid?.credits ?? null;
  const estimatedCredits = per5s != null ? per5s * Math.max(1, Math.ceil((duration || 5) / 5)) * count : null;

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      <div className="flex-1 flex flex-col p-4 pt-6 overflow-y-auto">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex-1 flex flex-col max-w-3xl mx-auto w-full">
          {/* Title + pills */}
          <div className="text-center mb-5">
            <h1 className="text-2xl font-bold tracking-tight text-text-primary">{en ? "Prompt · Edit · Compose pro video" : "Prompt · 编辑 · 混剪专业视频"}</h1>
            <div className="mt-3 flex items-center justify-center gap-2 flex-wrap">
              {[
                { label: en ? "Video ideas" : "视频灵感", href: "/agent" },
                { label: en ? "Lip Sync" : "唇形同步", href: "/create/lipsync" },
                { label: en ? "Motion" : "动态控制", href: "/create/motion" },
              ].map((pill) => (
                <button key={pill.label} onClick={() => router.push(pill.href)} className="group inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium bg-cosmic-surface/50 border border-cosmic-border/60 text-text-secondary hover:text-text-primary hover:border-accent-cyan/40 transition-colors">
                  <Sparkles className="w-3.5 h-3.5 text-accent-cyan/80" />
                  {pill.label}
                  <span className="px-1 py-0.5 rounded text-[8px] font-semibold bg-accent-cyan/[0.12] text-accent-cyan">App</span>
                </button>
              ))}
            </div>
          </div>

          {/* Unified video composer */}
          <VideoComposer
            prompt={prompt}
            onPromptChange={setPrompt}
            onGenerate={handleSubmit}
            loading={submitting}
            onEnhance={handleEnhance}
            enhancing={enhancing}
            references={references}
            onAddReference={handleAddReference}
            onRemoveReference={handleRemoveReference}
            models={videoModels}
            selectedModel={selectedModel}
            onModelSelect={setSelectedModel}
            aspectRatio={aspectRatio}
            onAspectChange={setAspectRatio}
            resolution={resolution}
            onResolutionChange={setResolution}
            duration={duration}
            onDurationChange={setDuration}
            count={count}
            onCountChange={setCount}
            quality={quality}
            onQualityChange={(q) => setQuality(q)}
            generateAudio={generateAudio}
            onGenerateAudioChange={setGenerateAudio}
            postLipsync={postLipsync}
            onPostLipsyncChange={setPostLipsync}
            lipsyncText={lipsyncText}
            onLipsyncTextChange={setLipsyncText}
            multiShot={multiShotMode}
            onMultiShotChange={(v) => { setMultiShotMode(v); if (v && shots.length === 0) handleShotAdd(); }}
            estimatedCredits={estimatedCredits}
            quote={quote}
          />

          {/* Multi-shot editor */}
          <AnimatePresence>
            {multiShotMode && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden mt-3">
                <div className="rounded-xl border border-cosmic-border/60 bg-cosmic-surface/40 p-3 space-y-2">
                  <p className="text-[11px] text-text-secondary/70 mb-1">多镜头分镜（每镜独立生成后合成）</p>
                  {shots.map((s, i) => (
                    <div key={s.id} className="flex items-start gap-2">
                      <span className="mt-2 w-5 h-5 rounded-full bg-cosmic-subtle text-[10px] text-text-secondary flex items-center justify-center flex-shrink-0">{i + 1}</span>
                      <textarea value={s.prompt} onChange={(e) => handleShotUpdate(s.id, e.target.value)} placeholder={`镜头 ${i + 1} 描述…`} rows={1} className="flex-1 resize-none px-2.5 py-1.5 rounded-lg text-xs bg-cosmic-surface/60 border border-cosmic-border/50 text-text-primary placeholder:text-text-tertiary/50 focus:outline-none focus:border-accent-cyan/40" />
                      {shots.length > 1 && (
                        <button onClick={() => handleShotRemove(s.id)} className="mt-1.5 text-text-secondary/60 hover:text-destructive"><X className="w-3.5 h-3.5" /></button>
                      )}
                    </div>
                  ))}
                  <button onClick={handleShotAdd} className="inline-flex items-center gap-1 text-[11px] text-accent-cyan hover:opacity-80"><Plus className="w-3.5 h-3.5" /> 添加镜头</button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Error */}
          {error && !submitting && (
            <div className="mt-4"><ErrorState message={error} onRetry={handleSubmit} onDismiss={() => setError(null)} /></div>
          )}

          {/* Generating */}
          {submitting && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-4 p-5 rounded-2xl bg-cosmic-surface border border-cosmic-border shadow-elevation-md">
              <Loading variant="pulse" text={`AI 正在生成视频... ${formatTime(elapsed)}`} />
              <div className="mt-4 h-1.5 rounded-full bg-cosmic-border/40 overflow-hidden">
                <motion.div className="h-full rounded-full bg-gradient-to-r from-primary via-accent-cyan/80 to-primary" initial={{ width: "0%" }} animate={{ width: "100%" }} transition={{ duration: 120, ease: "easeInOut" }} />
              </div>
              {taskId && <p className="mt-3 text-caption text-text-tertiary">任务 {taskId.slice(0, 8)}… · 视频生成约 1–5 分钟</p>}
            </motion.div>
          )}

          {/* Results */}
          {videoResults.length > 0 && (
            <div className="mt-6"><ResultGrid results={videoResults} loading={false} onDownload={(item) => window.open(item.url, "_blank")} /></div>
          )}

          {/* Empty */}
          {!submitting && !error && videoResults.length === 0 && (
            <div className="mt-4">
              <Empty title={en ? "Start creating video" : "开始创作视频"} description={en ? "Describe the scene and camera moves and AI will generate it — with multi-shot sequencing, reference media (image/video/audio) guidance, and AI enhancement." : "输入 prompt 描述画面与运镜，AI 将为你生成。支持多镜头编排、参考素材（图/视频/音频）引导与 AI 优化。"} />
            </div>
          )}

          {/* Video Apps */}
          <VideoAppsRow className="mt-10 mb-4" />
        </motion.div>
      </div>
    </div>
  );
}
