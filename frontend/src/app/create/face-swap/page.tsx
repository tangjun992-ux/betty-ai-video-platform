"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Loader2, Upload, Sparkles } from "lucide-react";
import { CapabilityNotice } from "@/components/CapabilityNotice";
import { API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

/**
 * Face Swap — verified i2i edit (google/nano-banana-edit).
 * Honesty: not InsightFace/Roop pixel identity swap.
 */
export default function FaceSwapPage() {
  const router = useRouter();
  const toast = useToast();
  const [faceFile, setFaceFile] = useState<File | null>(null);
  const [targetFile, setTargetFile] = useState<File | null>(null);
  const [facePreview, setFacePreview] = useState("");
  const [targetPreview, setTargetPreview] = useState("");
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const onFace = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFaceFile(f);
    setFacePreview(URL.createObjectURL(f));
  }, []);

  const onTarget = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setTargetFile(f);
    setTargetPreview(URL.createObjectURL(f));
  }, []);

  const submit = async () => {
    if (!faceFile || !targetFile) {
      toast.error("请上传两张图", "源人脸 + 目标场景");
      return;
    }
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("face_file", faceFile);
      fd.append("target_file", targetFile);
      if (prompt.trim()) fd.append("prompt", prompt.trim());
      const res = await fetch(`${API_BASE}/face-swap/upload`, { method: "POST", body: fd });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(typeof err.detail === "string" ? err.detail : "提交失败");
      }
      const data = await res.json();
      toast.success("换脸任务已排队", data.honesty || "i2i edit");
      router.push(`/tasks/${data.task_id}`);
    } catch (e: any) {
      toast.error("换脸失败", e?.message || "请稍后重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <h1 className="text-2xl font-bold gradient-text-static mb-2">AI 换脸</h1>
        <p className="text-sm text-text-secondary mb-4">
          双图换脸（源人脸 → 目标图）。已用 google/nano-banana-edit live 验证出图；属 i2i 指令合成，非 InsightFace 像素级换脸。
        </p>
        <CapabilityNotice feature="image" className="mb-4" />
        <div
          data-testid="capability-notice-face-swap"
          className="rounded-xl border border-emerald-400/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-800 dark:text-emerald-200 mb-6"
        >
          SKU：google/nano-banana-edit · mode=i2i_edit · 5 积分
        </div>
      </motion.div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        {[
          { label: "1. 源人脸", preview: facePreview, onChange: onFace },
          { label: "2. 目标图", preview: targetPreview, onChange: onTarget },
        ].map((slot) => (
          <label key={slot.label} className="block cursor-pointer">
            <span className="text-sm font-medium mb-2 block">{slot.label}</span>
            <div
              className={cn(
                "aspect-square rounded-2xl border-2 border-dashed border-cosmic-border bg-cosmic-subtle flex items-center justify-center overflow-hidden",
              )}
            >
              {slot.preview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={slot.preview} alt="" className="w-full h-full object-cover" />
              ) : (
                <div className="text-center p-6 text-text-secondary">
                  <Upload className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">点击上传</p>
                </div>
              )}
              <input type="file" accept="image/*" className="hidden" onChange={slot.onChange} />
            </div>
          </label>
        ))}
      </div>

      {/* Viral prompt packs — style guidance only; still needs two user photos */}
      <div className="mb-4">
        <p className="text-xs text-text-secondary mb-2">风格模板（写入提示词，非 InsightFace 模板库）</p>
        <div className="flex flex-wrap gap-2">
          {[
            { id: "poster", label: "电影海报", text: "cinematic movie poster lighting, dramatic contrast, keep face identity from source, match target scene" },
            { id: "linkedin", label: "职场证件", text: "professional headshot lighting, clean background blend, natural skin tone, keep source face identity" },
            { id: "cyber", label: "赛博朋克", text: "cyberpunk neon rim light, futuristic atmosphere, keep source face identity on target body" },
            { id: "comic", label: "漫画风", text: "stylized comic illustration blend, bold ink edges, keep recognizable source face on target" },
            { id: "vintage", label: "复古胶片", text: "vintage film grain, warm color grade, soft vignette, preserve source facial features" },
          ].map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setPrompt(t.text)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs border transition-colors",
                prompt === t.text
                  ? "border-brand bg-brand/10 text-brand"
                  : "border-cosmic-border text-text-secondary hover:border-brand/40",
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="可选：补充融合要求（光影、妆造…）或点选上方模板"
        rows={3}
        className="w-full rounded-xl bg-cosmic-subtle border border-cosmic-border px-4 py-3 text-sm mb-4 resize-none"
      />

      <button
        type="button"
        disabled={submitting || !faceFile || !targetFile}
        onClick={submit}
        className="w-full py-3.5 rounded-2xl bg-brand text-white font-semibold disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
        开始换脸
      </button>
    </div>
  );
}
