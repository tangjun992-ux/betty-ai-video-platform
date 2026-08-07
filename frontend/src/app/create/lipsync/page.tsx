"use client";

import { useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Mic, Music, Upload, Info, Loader2, RefreshCw, Play, Sparkles } from "lucide-react";
import { ErrorState, Empty } from "@/components/StatusStates";
import { useToast } from "@/components/Toast";
import { CapabilityNotice } from "@/components/CapabilityNotice";
import { cn } from "@/lib/utils";

import { API_BASE, apiAuthHeaders, estimateTool } from "@/lib/api";

const SAMPLE_VOICES = [
  { id: "zh-CN-XiaoxiaoNeural", name: "晓晓", gender: "女", desc: "温柔自然" },
  { id: "zh-CN-YunxiNeural", name: "云希", gender: "男", desc: "沉稳大气" },
  { id: "zh-CN-XiaoyiNeural", name: "晓伊", gender: "女", desc: "活泼可爱" },
  { id: "en-US-JennyNeural", name: "Jenny", gender: "女", desc: "Friendly" },
  { id: "en-US-GuyNeural", name: "Guy", gender: "男", desc: "Professional" },
];

export default function LipsyncPage() {
  const router = useRouter();
  const toast = useToast();
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>("");
  const [remoteImageUrl, setRemoteImageUrl] = useState<string>("");
  const [text, setText] = useState("");
  const [voiceId, setVoiceId] = useState("zh-CN-XiaoxiaoNeural");
  const [submitting, setSubmitting] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<"text" | "audio">("text");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioName, setAudioName] = useState("");
  const [tier, setTier] = useState<"demo" | "studio">("demo");
  const [offlineDemo, setOfflineDemo] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [stage, setStage] = useState("");
  const [estimatedCredits, setEstimatedCredits] = useState<number | null>(null);
  const [estimatedSeconds, setEstimatedSeconds] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    estimateTool({ tool: "lipsync", tier })
      .then((e) => {
        if (!cancelled) {
          setEstimatedCredits(e.estimated_cost_credits);
          setEstimatedSeconds(e.estimated_time_seconds);
        }
      })
      .catch(() => { if (!cancelled) { setEstimatedCredits(null); setEstimatedSeconds(null); } });
    return () => { cancelled = true; };
  }, [tier]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const q = new URLSearchParams(window.location.search);
    const u = q.get("image_url") || q.get("ref") || "";
    if (u && (u.startsWith("http") || u.startsWith("/"))) {
      setRemoteImageUrl(u);
      setImagePreview(u);
    }
  }, []);

  const handleAudioUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAudioFile(file);
    setAudioName(file.name);
  }, []);

  const handleImageUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    setError(null);
  }, []);

  const handleSubmit = async () => {
    if (!imageFile && !remoteImageUrl) { setError("请上传一张图片"); return; }
    if (inputMode === "text" && !text.trim()) { setError("请输入要说的文字"); return; }
    if (inputMode === "audio" && !audioFile) { setError("请上传音频文件"); return; }

    setSubmitting(true);
    setError(null);
    setElapsed(0);
    setStage("提交中");

    try {
      const formData = new FormData();
      if (imageFile) formData.append("image_file", imageFile);
      else if (remoteImageUrl) formData.append("image_url", remoteImageUrl);
      if (inputMode === "text") {
        formData.append("text", text);
      } else if (audioFile) {
        formData.append("audio_file", audioFile);
      }
      formData.append("voice_id", voiceId);
      formData.append("tier", tier);

      const res = await fetch(`${API_BASE}/lipsync`, { method: "POST", body: formData, headers: apiAuthHeaders() });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "唇形同步请求失败");
      }

      const data = await res.json();
      setTaskId(data.task_id);
      setStage("生成中");

      // Kling AI-Avatar 数字人生成通常需要 2-5 分钟，给足轮询窗口（最长 ~9 分钟），
      // 与后端任务时限对齐，避免前端提前判定"超时"。
      const started = Date.now();
      const maxMs = 9 * 60 * 1000;
      const poll = async (): Promise<any> => {
        const el = Math.floor((Date.now() - started) / 1000);
        setElapsed(el);
        if (Date.now() - started > maxMs) throw new Error("生成超时，请稍后重试或改用 Studio 档位");
        const status = await fetch(`${API_BASE}/tasks/${data.task_id}`, {
          headers: apiAuthHeaders(),
        }).then(r => r.json()).catch(() => ({}));
        if (status.current_stage) setStage(status.current_stage);
        if (status.status === "completed" || status.status === "failed") return status;
        await new Promise(r => setTimeout(r, 3000));
        return poll();
      };

      const result = await poll();
      if (result.status === "failed") throw new Error(result.error_message || "生成失败");

      toast.success("唇形同步完成", "视频已生成，正在跳转...");
      router.push(`/tasks/${data.task_id}`);
    } catch (err: any) {
      const msg = err.message || "生成失败";
      setError(msg);
      toast.error("生成失败", msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold mb-2 gradient-text-static">唇形同步</h1>
        <p className="text-text-secondary text-sm mb-4">
          上传清晰正面人物照 + 文字/语音，生成口型同步视频。建议嘴巴自然、台词 8–20 秒；卡通图或蜂鸣音会出现「成功但口型不动」。
        </p>
        <CapabilityNotice feature="lipsync" className="mb-4" onDemoChange={setOfflineDemo} />
        <div className="grid grid-cols-2 gap-2 mb-6 max-w-md">
          {([
            {
              id: "demo" as const,
              label: "Demo",
              desc: offlineDemo
                ? "4 积分 · 离线预览动效（非口型）"
                : "4 积分 · Kling 口型 · 音量均衡",
            },
            {
              id: "studio" as const,
              label: "Studio",
              desc: offlineDemo
                ? "10 积分 · 仍需模型 Key · Personal+"
                : "10 积分 · InfiniTalk 优先 · Personal+",
            },
          ]).map((t) => (
            <button key={t.id} type="button" onClick={() => setTier(t.id)}
              className={cn("p-3 rounded-xl border text-left transition-all",
                tier === t.id ? "border-brand/40 bg-brand/[0.06]" : "border-cosmic-border bg-cosmic-subtle")}>
              <div className="text-sm font-semibold">{t.label}</div>
              <div className="text-[10px] text-text-secondary mt-0.5">{t.desc}</div>
            </button>
          ))}
        </div>
      </motion.div>

      {error && !submitting && (
        <ErrorState message={error} onRetry={handleSubmit} onDismiss={() => setError(null)} />
      )}

      {!error && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Image + Voice */}
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="space-y-4"
          >
            {/* Image Upload */}
            <label className="block">
              <span className="text-sm font-medium text-text-accent-cyan mb-2 block">1. 上传人物图片</span>
              <div className="relative aspect-square rounded-2xl border-2 border-dashed border-cosmic-border hover:border-accent-cyan/40 bg-cosmic-subtle flex items-center justify-center cursor-pointer overflow-hidden transition-all group">
                {imagePreview ? (
                  <>
                    <img src={imagePreview} alt="Preview" className="w-full h-full object-cover" />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                      <RefreshCw className="w-8 h-8 text-text-accent-cyan" />
                    </div>
                  </>
                ) : (
                  <div className="text-center p-8">
                    <Upload className="w-10 h-10 text-text-secondary mx-auto mb-3 group-hover:text-accent-cyan transition-colors" />
                    <p className="text-sm text-text-secondary">点击上传人物照片</p>
                    <p className="text-xs text-text-secondary/40 mt-1">支持 JPG、PNG，建议正面照</p>
                  </div>
                )}
                <input type="file" accept="image/*" onChange={handleImageUpload} className="absolute inset-0 opacity-0 cursor-pointer" />
              </div>
            </label>

            {/* Voice Selector */}
            <div>
              <span className="text-sm font-medium text-text-accent-cyan mb-2 block">3. 选择音色</span>
              <div className="grid grid-cols-2 gap-2">
                {SAMPLE_VOICES.map((v) => (
                  <button
                    key={v.id}
                    onClick={() => setVoiceId(v.id)}
                    className={cn(
                      "flex items-center gap-2 p-2.5 rounded-xl text-left transition-all duration-200 border",
                      voiceId === v.id
                        ? "bg-accent-cyan/[0.08] text-accent-cyan border-accent-cyan/20"
                        : "bg-cosmic-subtle border-cosmic-border text-text-secondary hover:text-text-accent-cyan hover:border-cosmic-border-hover"
                    )}
                  >
                    <div className={cn(
                      "w-8 h-8 rounded-lg flex items-center justify-center text-xs font-semibold",
                      v.gender === "女" ? "bg-pink-500/20 text-pink-400" : "bg-blue-500/20 text-blue-400"
                    )}>
                      {v.name[0]}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium truncate">{v.name} · {v.gender}</p>
                      <p className="text-[10px] text-text-secondary/50">{v.desc}</p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Right: Text + Submit */}
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="space-y-4 flex flex-col"
          >
            <div className="flex-1 flex flex-col">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-text-accent-cyan">2. 输入方式</span>
                <div className="flex rounded-full bg-cosmic-subtle border border-cosmic-border p-0.5">
                  <button
                    onClick={() => setInputMode("text")}
                    className={cn(
                      "px-3 py-1 rounded-full text-xs font-semibold transition-all duration-200",
                      inputMode === "text" ? "bg-cosmic-surface text-text-primary shadow-elevation-sm" : "text-text-secondary hover:text-text-accent-cyan"
                    )}
                  >
                    文字
                  </button>
                  <button
                    onClick={() => setInputMode("audio")}
                    className={cn(
                      "px-3 py-1 rounded-full text-xs font-semibold transition-all duration-200",
                      inputMode === "audio" ? "bg-cosmic-surface text-text-primary shadow-elevation-sm" : "text-text-secondary hover:text-text-accent-cyan"
                    )}
                  >
                    音频
                  </button>
                </div>
              </div>

              {inputMode === "text" ? (
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="输入要让角色说的话...&#10;&#10;例如：你好，欢迎来到 betty AI 创作平台！"
                  rows={8}
                  className="flex-1 w-full px-4 py-3 rounded-2xl bg-cosmic-subtle border border-cosmic-border text-sm text-text-accent-cyan placeholder:text-text-accent-cyan/20 focus:outline-none focus:ring-2 focus:ring-accent-cyan/20 focus:border-accent-cyan/30 resize-none transition-all"
                />
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-cosmic-border hover:border-accent-cyan/40 bg-cosmic-subtle cursor-pointer transition-all group relative">
                  {audioFile ? (
                    <div className="text-center p-8">
                      <Music className="w-10 h-10 text-accent-cyan mx-auto mb-3" />
                      <p className="text-sm text-text-accent-cyan font-medium">{audioName}</p>
                      <p className="text-xs text-text-secondary mt-1">{(audioFile.size / 1024 / 1024).toFixed(1)} MB</p>
                      <button
                        onClick={(e) => { e.preventDefault(); setAudioFile(null); setAudioName(""); }}
                        className="mt-3 text-xs text-destructive hover:underline"
                      >
                        移除
                      </button>
                    </div>
                  ) : (
                    <div className="text-center p-8">
                      <Upload className="w-10 h-10 text-text-secondary mx-auto mb-3 group-hover:text-accent-cyan transition-colors" />
                      <p className="text-sm text-text-secondary">点击上传音频文件</p>
                      <p className="text-xs text-text-secondary/40 mt-1">支持 MP3、WAV、M4A</p>
                    </div>
                  )}
                  <input type="file" accept="audio/*" onChange={handleAudioUpload} className="absolute inset-0 opacity-0 cursor-pointer" />
                </div>
              )}

              <p className="text-xs text-text-secondary mt-1.5 flex items-center gap-1">
                <Info className="w-3 h-3" />
                {inputMode === "text" ? "建议 10-100 字，支持中文/英文" : "音频时长建议 5-30 秒"}
              </p>
            </div>

            {/* Submit */}
            <button
              onClick={handleSubmit}
              disabled={submitting || !imagePreview || (inputMode === "text" ? !text.trim() : !audioFile)}
              className="btn-primary w-full"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  生成中... {taskId ? `(${taskId.slice(0, 8)}...)` : ""}
                </>
              ) : (
                <>
                  <Mic className="w-5 h-5" />
                  生成唇形同步
                  {estimatedCredits != null && (
                    <span className="ml-1 opacity-80">· {estimatedCredits} 积分</span>
                  )}
                </>
              )}
            </button>
            {estimatedSeconds != null && !submitting && (
              <p className="text-[11px] text-text-tertiary text-center mt-1.5">
                预计 {Math.ceil(estimatedSeconds / 60)}–5 分钟 · Kling 数字人出片
              </p>
            )}

            {/* Generating status — Kling 数字人约需 2-5 分钟，展示阶段与已用时长 */}
            {submitting && taskId && (
              <div className="p-3 rounded-xl bg-cosmic-subtle border border-cosmic-border space-y-2">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 text-accent-cyan animate-spin flex-shrink-0" />
                  <div className="flex-1">
                    <p className="text-sm text-text-accent-cyan">
                      AI 正在生成唇形同步视频 · {stage || "生成中"}
                    </p>
                    <p className="text-xs text-text-secondary">
                      已用 {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, "0")} · 数字人通常需 2-5 分钟，请耐心等待
                    </p>
                  </div>
                </div>
                <div className="h-1.5 rounded-full bg-cosmic-border/50 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-accent-cyan to-teal-400 transition-all duration-500"
                    style={{ width: `${Math.min(95, 10 + (elapsed / 300) * 85)}%` }}
                  />
                </div>
              </div>
            )}
          </motion.div>
        </div>
      )}

      {/* Tips */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="mt-8 p-4 rounded-2xl surface-raised"
      >
        <h3 className="text-sm font-semibold text-text-accent-cyan mb-2 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-accent-cyan" />
          使用技巧
        </h3>
        <ul className="space-y-1.5 text-xs text-text-secondary">
          <li>• 上传清晰的正面照效果最佳</li>
          <li>• 文字建议 10-100 字，过长会自动分段</li>
          <li>• 支持中英文混合输入</li>
          <li>• 生成时间约 30-60 秒</li>
        </ul>
      </motion.div>
    </div>
  );
}
