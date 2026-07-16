"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Upload, Loader2, Mic, Music, RefreshCw } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { CapabilityNotice } from "@/components/CapabilityNotice";
import { cn } from "@/lib/utils";

/**
 * Talking Avatar — Yapper parity surface.
 * Backend is the lipsync pipeline (image + audio/text → talking video).
 */
const VOICES = [
  { id: "zh-CN-XiaoxiaoNeural", name: "晓晓", desc: "温柔自然" },
  { id: "zh-CN-YunxiNeural", name: "云希", desc: "沉稳大气" },
  { id: "en-US-JennyNeural", name: "Jenny", desc: "Friendly" },
  { id: "en-US-GuyNeural", name: "Guy", desc: "Professional" },
];

export default function TalkingAvatarPage() {
  const router = useRouter();
  const toast = useToast();
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState("");
  const [inputMode, setInputMode] = useState<"audio" | "text">("audio");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioName, setAudioName] = useState("");
  const [text, setText] = useState("");
  const [voiceId, setVoiceId] = useState(VOICES[0].id);
  const [tier, setTier] = useState<"demo" | "studio">("demo");
  const [submitting, setSubmitting] = useState(false);

  const onImage = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setImageFile(f);
    setImagePreview(URL.createObjectURL(f));
  }, []);

  const onAudio = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setAudioFile(f);
    setAudioName(f.name);
  }, []);

  const submit = async () => {
    if (!imageFile) {
      toast.error("需要头像图", "上传一张正面人物照");
      return;
    }
    if (inputMode === "audio" && !audioFile) {
      toast.error("需要音频", "上传一段说话音频，或切换到文本模式");
      return;
    }
    if (inputMode === "text" && !text.trim()) {
      toast.error("需要台词", "输入头像要说的话");
      return;
    }
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("image_file", imageFile);
      fd.append("tier", tier);
      fd.append("voice_id", voiceId);
      if (inputMode === "audio" && audioFile) fd.append("audio_file", audioFile);
      else fd.append("text", text);
      const res = await fetch(`${API_BASE}/lipsync`, { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "提交失败");
      }
      const data = await res.json();
      toast.success("头像任务已提交", "正在生成说话视频…");
      router.push(`/tasks/${data.task_id}`);
    } catch (e: any) {
      toast.error("生成失败", e?.message || "请稍后重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <h1 className="text-2xl font-bold gradient-text-static mb-2">Talking Avatar</h1>
        <p className="text-sm text-text-secondary mb-3">
          图片 + 音频/文本 → 说话头像视频。对标 Yapper Talking Avatar（底层复用唇形同步链路）。
        </p>
        <CapabilityNotice feature="lipsync" className="mb-4" />
        <div className="grid grid-cols-2 gap-2 max-w-md">
          {([
            { id: "demo" as const, label: "Demo", desc: "4 积分 · 标准" },
            { id: "studio" as const, label: "Studio", desc: "10 积分 · Personal+" },
          ]).map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTier(t.id)}
              className={cn(
                "p-3 rounded-xl border text-left",
                tier === t.id ? "border-brand/40 bg-brand/[0.06]" : "border-cosmic-border bg-cosmic-subtle"
              )}
            >
              <div className="text-sm font-semibold">{t.label}</div>
              <div className="text-[10px] text-text-secondary mt-0.5">{t.desc}</div>
            </button>
          ))}
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <label className="block">
          <span className="text-sm font-medium mb-2 block">1. 上传头像照</span>
          <div className="relative aspect-square rounded-2xl border-2 border-dashed border-cosmic-border bg-cosmic-subtle overflow-hidden cursor-pointer group">
            {imagePreview ? (
              <>
                <img src={imagePreview} alt="avatar" className="w-full h-full object-cover" />
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                  <RefreshCw className="w-8 h-8 text-white" />
                </div>
              </>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-text-secondary">
                <Upload className="w-10 h-10 mb-2" />
                <p className="text-sm">正面清晰人物照</p>
              </div>
            )}
            <input type="file" accept="image/*" onChange={onImage} className="absolute inset-0 opacity-0 cursor-pointer" />
          </div>
        </label>

        <div className="space-y-4">
          <div className="flex gap-2">
            {([
              { id: "audio" as const, icon: Music, label: "上传音频" },
              { id: "text" as const, icon: Mic, label: "文本配音" },
            ]).map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setInputMode(m.id)}
                className={cn(
                  "flex-1 h-10 rounded-xl border text-sm inline-flex items-center justify-center gap-2",
                  inputMode === m.id
                    ? "border-brand/40 bg-brand/[0.06]"
                    : "border-cosmic-border text-text-secondary"
                )}
              >
                <m.icon className="w-4 h-4" />
                {m.label}
              </button>
            ))}
          </div>

          {inputMode === "audio" ? (
            <label className="block">
              <span className="text-sm font-medium mb-2 block">2. 说话音频</span>
              <div className="rounded-xl border border-dashed border-cosmic-border p-6 text-center cursor-pointer hover:border-brand/40 relative">
                <Music className="w-8 h-8 mx-auto mb-2 text-text-secondary" />
                <p className="text-sm text-text-secondary">{audioName || "上传 MP3 / WAV / M4A"}</p>
                <input type="file" accept="audio/*" onChange={onAudio} className="absolute inset-0 opacity-0 cursor-pointer" />
              </div>
            </label>
          ) : (
            <>
              <label className="block">
                <span className="text-sm font-medium mb-2 block">2. 台词</span>
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  rows={4}
                  placeholder="头像要说的话…"
                  className="w-full rounded-xl bg-cosmic-subtle border border-cosmic-border px-3 py-2 text-sm"
                />
              </label>
              <div>
                <span className="text-sm font-medium mb-2 block">3. 音色</span>
                <div className="grid grid-cols-2 gap-2">
                  {VOICES.map((v) => (
                    <button
                      key={v.id}
                      type="button"
                      onClick={() => setVoiceId(v.id)}
                      className={cn(
                        "p-2.5 rounded-xl border text-left text-sm",
                        voiceId === v.id
                          ? "border-brand/40 bg-brand/[0.06]"
                          : "border-cosmic-border text-text-secondary"
                      )}
                    >
                      <div className="font-medium">{v.name}</div>
                      <div className="text-[10px] opacity-70">{v.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}

          <button
            type="button"
            onClick={submit}
            disabled={submitting}
            className="w-full h-11 rounded-xl bg-white text-black font-semibold inline-flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {submitting ? "提交中…" : "生成说话头像"}
          </button>
          <p className="text-[11px] text-text-tertiary">
            也可使用完整唇形同步工作室：{" "}
            <a href="/create/lipsync" className="text-brand hover:underline">
              /create/lipsync
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
