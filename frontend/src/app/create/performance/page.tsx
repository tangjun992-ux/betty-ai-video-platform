"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Loader2, Upload, Clapperboard } from "lucide-react";
import { CapabilityNotice } from "@/components/CapabilityNotice";
import { API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

/**
 * Performance Drive — Motion + optional Lipsync.
 * Honesty: NOT Runway Act-One.
 */
export default function PerformancePage() {
  const router = useRouter();
  const toast = useToast();
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState("");
  const [videoPreview, setVideoPreview] = useState("");
  const [voiceText, setVoiceText] = useState("");
  const [withTalk, setWithTalk] = useState(true);
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const onImage = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setImageFile(f);
    setImagePreview(URL.createObjectURL(f));
  }, []);

  const onVideo = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setVideoFile(f);
    setVideoPreview(URL.createObjectURL(f));
  }, []);

  const uploadOne = async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: fd });
    if (!res.ok) throw new Error("上传失败");
    const data = await res.json();
    return data.url || data.media_url || data.file_url;
  };

  const submit = async () => {
    if (!imageFile || !videoFile) {
      toast.error("请上传静帧与参考视频", "");
      return;
    }
    if (withTalk && !voiceText.trim()) {
      toast.error("开启口播时请填写台词", "");
      return;
    }
    setSubmitting(true);
    try {
      const image_url = await uploadOne(imageFile);
      const video_url = await uploadOne(videoFile);
      const res = await fetch(`${API_BASE}/performance`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_url,
          video_url,
          prompt: prompt.trim() || undefined,
          with_talk: withTalk,
          voice_text: withTalk ? voiceText.trim() : undefined,
          tier: "demo",
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(typeof err.detail === "string" ? err.detail : "提交失败");
      }
      const data = await res.json();
      toast.success("Performance 已排队", data.honesty || "Motion + 可选口播");
      router.push(`/tasks/${data.task_id}`);
    } catch (e: any) {
      toast.error("提交失败", e?.message || "请稍后重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <h1 className="text-2xl font-bold gradient-text-static mb-2">Performance Drive</h1>
        <p className="text-sm text-text-secondary mb-4">
          原生 Kling Motion Control + 可选 Lipsync 口播分轨。对标「表演驱动」工作流，但不是 Runway Act-One 编码器。
        </p>
        <CapabilityNotice feature="motion" className="mb-4" />
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        <label className="block cursor-pointer">
          <span className="text-sm font-medium mb-2 block">角色静帧</span>
          <div className="aspect-square rounded-2xl border-2 border-dashed border-cosmic-border bg-cosmic-subtle flex items-center justify-center overflow-hidden">
            {imagePreview ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={imagePreview} alt="" className="w-full h-full object-cover" />
            ) : (
              <div className="text-center text-text-secondary p-6">
                <Upload className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">上传图片</p>
              </div>
            )}
            <input type="file" accept="image/*" className="hidden" onChange={onImage} />
          </div>
        </label>
        <label className="block cursor-pointer">
          <span className="text-sm font-medium mb-2 block">参考动作视频</span>
          <div className="aspect-video rounded-2xl border-2 border-dashed border-cosmic-border bg-cosmic-subtle flex items-center justify-center overflow-hidden">
            {videoPreview ? (
              <video src={videoPreview} className="w-full h-full object-cover" muted controls />
            ) : (
              <div className="text-center text-text-secondary p-6">
                <Upload className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">上传视频</p>
              </div>
            )}
            <input type="file" accept="video/*" className="hidden" onChange={onVideo} />
          </div>
        </label>
      </div>

      <label className="flex items-center gap-2 mb-3 text-sm">
        <input
          type="checkbox"
          checked={withTalk}
          onChange={(e) => setWithTalk(e.target.checked)}
          className="rounded border-cosmic-border"
        />
        追加口播 Lipsync（源静帧 + 台词 TTS）
      </label>

      {withTalk && (
        <textarea
          value={voiceText}
          onChange={(e) => setVoiceText(e.target.value)}
          placeholder="口播台词…"
          rows={3}
          className="w-full rounded-xl bg-cosmic-subtle border border-cosmic-border px-4 py-3 text-sm mb-4 resize-none"
        />
      )}

      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="可选：动作迁移提示词"
        rows={2}
        className="w-full rounded-xl bg-cosmic-subtle border border-cosmic-border px-4 py-3 text-sm mb-4 resize-none"
      />

      <button
        type="button"
        disabled={submitting || !imageFile || !videoFile}
        onClick={submit}
        className={cn(
          "w-full py-3.5 rounded-2xl bg-brand text-white font-semibold disabled:opacity-40 flex items-center justify-center gap-2",
        )}
      >
        {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Clapperboard className="w-5 h-5" />}
        开始 Performance Drive
      </button>
    </div>
  );
}
