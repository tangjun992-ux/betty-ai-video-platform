"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Mic, Music, Upload, Info, Loader2, RefreshCw, Play, Sparkles } from "lucide-react";
import { ErrorState, Empty } from "@/components/StatusStates";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

import { API_BASE } from "@/lib/api";

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
  const [text, setText] = useState("");
  const [voiceId, setVoiceId] = useState("zh-CN-XiaoxiaoNeural");
  const [submitting, setSubmitting] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<"text" | "audio">("text");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioName, setAudioName] = useState("");
  const [tier, setTier] = useState<"demo" | "studio">("demo");

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
    if (!imageFile && !imagePreview) { setError("请上传一张图片"); return; }
    if (inputMode === "text" && !text.trim()) { setError("请输入要说的文字"); return; }
    if (inputMode === "audio" && !audioFile) { setError("请上传音频文件"); return; }

    setSubmitting(true);
    setError(null);

    try {
      const formData = new FormData();
      if (imageFile) formData.append("image_file", imageFile);
      if (inputMode === "text") {
        formData.append("text", text);
      } else if (audioFile) {
        formData.append("audio_file", audioFile);
      }
      formData.append("voice_id", voiceId);
      formData.append("tier", tier);

      const res = await fetch(`${API_BASE}/lipsync`, { method: "POST", body: formData });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "唇形同步请求失败");
      }

      const data = await res.json();
      setTaskId(data.task_id);

      // Poll
      const maxPolls = 90;
      let polls = 0;
      const poll = async (): Promise<any> => {
        if (polls++ > maxPolls) throw new Error("生成超时");
        const status = await fetch(`${API_BASE}/tasks/${data.task_id}`).then(r => r.json());
        if (status.status === "completed" || status.status === "failed") return status;
        await new Promise(r => setTimeout(r, 2000));
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
          上传图片，输入文字，AI 自动生成口型同步的说话视频
        </p>
        <div className="grid grid-cols-2 gap-2 mb-6 max-w-md">
          {([
            { id: "demo" as const, label: "Demo", desc: "4 积分 · 标准唇形" },
            { id: "studio" as const, label: "Studio", desc: "10 积分 · 高保真 · Personal+" },
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
                  生成唇形同步视频
                </>
              )}
            </button>

            {/* Generating status */}
            {submitting && taskId && (
              <div className="flex items-center gap-3 p-3 rounded-xl bg-cosmic-subtle border border-cosmic-border">
                <div className="relative">
                  <Loader2 className="w-5 h-5 text-accent-cyan animate-spin" />
                </div>
                <div>
                  <p className="text-sm text-text-accent-cyan">AI 正在生成唇形同步视频...</p>
                  <p className="text-xs text-text-secondary">任务 ID: {taskId.slice(0, 8)}...</p>
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
