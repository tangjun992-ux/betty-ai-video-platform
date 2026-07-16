"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Upload, Loader2, Copy, ArrowRight, Sparkles, Video, Image as ImageIcon } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

/**
 * Prompt Extractor — Yapper parity utility.
 * Reverse-prompts from uploaded image/video via POST /generate/extract-prompt.
 */
export default function ExtractPage() {
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [previewKind, setPreviewKind] = useState<"image" | "video">("image");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    prompt: string;
    mode: string;
    style_tags?: string[];
    subjects?: string[];
    camera?: string;
    mood?: string;
    honesty?: string;
    media_type_hint?: string;
  } | null>(null);

  const onUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setResult(null);
    const isVid = f.type.startsWith("video/");
    setPreviewKind(isVid ? "video" : "image");
    setPreview(URL.createObjectURL(f));
  }, []);

  const run = async () => {
    if (!file) {
      toast.error("请上传媒体", "支持图片或短视频");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("media_file", file);
      fd.append("media_kind", "auto");
      const res = await fetch(`${API_BASE}/generate/extract-prompt`, {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "提取失败");
      }
      const data = await res.json();
      setResult(data);
      toast.success(
        data.mode === "vision" ? "Vision 提取完成" : "本地启发式提取完成",
        data.mode === "heuristic" ? "未走付费 vision，结果供起稿参考" : "可一键用于生成"
      );
    } catch (e: any) {
      toast.error("提取失败", e?.message || "请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const copyPrompt = async () => {
    if (!result?.prompt) return;
    await navigator.clipboard.writeText(result.prompt);
    toast.success("已复制", "提示词已到剪贴板");
  };

  const hint = result?.media_type_hint === "video" ? "video" : "image";

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="text-2xl md:text-3xl font-bold gradient-text-static mb-2">Prompt Extractor</h1>
        <p className="text-sm text-text-secondary max-w-xl">
          从任意图片或视频反推可复用提示词——对标 Yapper Extractor。有 Key 时走 Vision，否则诚实本地启发式。
        </p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium mb-2 block">上传媒体</span>
            <div className="relative aspect-video rounded-2xl border-2 border-dashed border-cosmic-border hover:border-brand/40 bg-cosmic-subtle flex items-center justify-center overflow-hidden cursor-pointer">
              {preview ? (
                previewKind === "video" ? (
                  <video src={preview} className="w-full h-full object-contain" controls muted />
                ) : (
                  <img src={preview} alt="源媒体" className="w-full h-full object-contain" />
                )
              ) : (
                <div className="text-center p-8">
                  <Upload className="w-10 h-10 text-text-secondary mx-auto mb-3" />
                  <p className="text-sm text-text-secondary">点击上传图片或短视频</p>
                  <p className="text-xs text-text-tertiary mt-1">JPG / PNG / WEBP / MP4 · ≤25MB</p>
                </div>
              )}
              <input
                type="file"
                accept="image/*,video/*"
                onChange={onUpload}
                className="absolute inset-0 opacity-0 cursor-pointer"
              />
            </div>
          </label>

          <button
            type="button"
            onClick={run}
            disabled={loading || !file}
            className={cn(
              "w-full h-11 rounded-xl font-semibold inline-flex items-center justify-center gap-2 transition-colors",
              loading || !file
                ? "bg-white/10 text-text-secondary cursor-not-allowed"
                : "bg-white text-black hover:bg-white/90"
            )}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {loading ? "提取中…" : "提取提示词"}
          </button>
        </div>

        <div className="rounded-2xl border border-cosmic-border bg-cosmic-subtle/60 p-5 min-h-[280px]">
          {!result ? (
            <div className="h-full flex flex-col items-center justify-center text-text-secondary text-sm gap-2 py-16">
              <ImageIcon className="w-8 h-8 opacity-40" />
              <p>提取结果将显示在这里</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs uppercase tracking-wide text-text-tertiary">
                  mode · {result.mode}
                </span>
                <button
                  type="button"
                  onClick={copyPrompt}
                  className="text-xs inline-flex items-center gap-1 text-brand hover:underline"
                >
                  <Copy className="w-3.5 h-3.5" /> 复制
                </button>
              </div>
              <p className="text-sm leading-relaxed text-text-primary whitespace-pre-wrap">{result.prompt}</p>
              {(result.style_tags?.length || 0) > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {result.style_tags!.map((t) => (
                    <span key={t} className="text-[11px] px-2 py-0.5 rounded-md bg-white/[0.06] border border-white/[0.08]">
                      {t}
                    </span>
                  ))}
                </div>
              )}
              {result.honesty && (
                <p className="text-[11px] text-text-tertiary leading-relaxed">{result.honesty}</p>
              )}
              <div className="flex flex-wrap gap-2 pt-2">
                <Link
                  href={`/create/${hint}?prompt=${encodeURIComponent(result.prompt)}`}
                  className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg bg-white text-black text-sm font-medium"
                >
                  {hint === "video" ? <Video className="w-3.5 h-3.5" /> : <ImageIcon className="w-3.5 h-3.5" />}
                  用于生成
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <Link
                  href={`/agent?brief=${encodeURIComponent(result.prompt)}`}
                  className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border border-cosmic-border text-sm"
                >
                  交给 Agent
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
