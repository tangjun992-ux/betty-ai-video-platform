"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Upload, Loader2, Copy, ArrowRight, Sparkles, Video, Image as ImageIcon } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

type ViralBeat = { key: string; label: string; t: number; prompt: string; reason?: string };

type Viral = {
  platform?: string;
  placement?: string;
  placement_label?: string;
  aspect?: string;
  duration_sec?: number;
  title?: string;
  author?: string;
  hook?: string;
  beats?: ViralBeat[];
  honesty?: string;
  cta_hint?: string;
};

type ExtractResult = {
  prompt: string;
  mode: string;
  style_tags?: string[];
  subjects?: string[];
  camera?: string;
  mood?: string;
  honesty?: string;
  media_type_hint?: string;
  social?: { platform?: string; title?: string; author?: string; source?: string };
  viral?: Viral;
  create_links?: { image?: string; video?: string; agent?: string };
};

/**
 * Prompt Extractor + URL-to-Viral — Yapper parity utility.
 * Reverse-prompts from upload/URL; social pages use official oEmbed where available.
 * Viral beats are placement templates, not frame-by-frame reverse engineering.
 */

function isBestEffortSocialUrl(url: string): boolean {
  const u = url.trim().toLowerCase();
  if (!u) return false;
  return (
    u.includes("instagram.com")
    || u.includes("x.com/")
    || u.includes("twitter.com/")
    || u.includes("facebook.com")
  );
}

export default function ExtractPage() {
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [mediaUrl, setMediaUrl] = useState("");
  const [preview, setPreview] = useState("");
  const [previewKind, setPreviewKind] = useState<"image" | "video">("image");
  const [targetPlatform, setTargetPlatform] = useState("auto");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExtractResult | null>(null);

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
    const url = mediaUrl.trim();
    if (!file && !url) {
      toast.error("请上传媒体或粘贴链接", "YouTube/TikTok 走官方 oEmbed；Instagram 请上传或直链");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const fd = new FormData();
      if (file) {
        fd.append("media_file", file);
      } else {
        fd.append("media_url", url);
      }
      fd.append("media_kind", "auto");
      if (targetPlatform && targetPlatform !== "auto") {
        fd.append("target_platform", targetPlatform);
      }
      const res = await fetch(`${API_BASE}/generate/extract-prompt`, {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        const detail = typeof err.detail === "string" ? err.detail : err.detail?.msg || "提取失败";
        throw new Error(detail);
      }
      const data = await res.json();
      setResult(data);
      const modeLabel =
        data.mode === "vision" ? "Vision 提取完成"
        : data.mode === "metadata" ? "元数据模板完成"
        : "本地启发式提取完成";
      toast.success(
        modeLabel,
        data.mode === "heuristic" || data.mode === "metadata"
          ? "未走付费 vision；分镜来自投放规格，不是原片逐帧反推"
          : "可一键用于生成",
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
  const videoHref = result?.create_links?.video || `/create/${hint}?prompt=${encodeURIComponent(result?.prompt || "")}`;
  const urlOnlyBestEffort = !file && isBestEffortSocialUrl(mediaUrl);
  const canSubmit = !loading && (file || mediaUrl.trim()) && !urlOnlyBestEffort;
  const agentHref = result?.create_links?.agent || `/agent?brief=${encodeURIComponent(result?.prompt || "")}`;

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="text-2xl md:text-3xl font-bold gradient-text-static mb-2">URL-to-Viral</h1>
        <p className="text-sm text-text-secondary max-w-2xl">
          从链接或文件反推提示词，并生成投放规格分镜（钩子 / 展开 / 收束）。
          YouTube、TikTok 走官方 oEmbed（标题+封面）；Instagram 需上传或直链。
          <span className="block mt-1 text-text-tertiary">不是原片下载，不是逐帧结构反推。</span>
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
                data-testid="extract-file"
              />
            </div>
          </label>

          <label className="block">
            <span className="text-sm font-medium mb-2 block">或粘贴社媒 / 直链 URL</span>
            <input
              type="url"
              value={mediaUrl}
              onChange={(e) => {
                setMediaUrl(e.target.value);
                if (e.target.value.trim()) setFile(null);
              }}
              placeholder="YouTube / TikTok 页面，或图片直链"
              className="input-primary w-full"
              data-testid="extract-url"
            />
            <p className="text-[11px] text-text-tertiary mt-1.5" data-testid="extract-url-honesty">
              YouTube / TikTok：官方 oEmbed 封面+标题。Instagram / X：尽力而为，失败请上传文件。非完整视频搬运。
            </p>
            {urlOnlyBestEffort && (
              <p
                className="text-[11px] text-amber-700 dark:text-amber-200 mt-2 px-2.5 py-2 rounded-lg bg-amber-500/10 border border-amber-400/30"
                data-testid="extract-ig-honesty"
              >
                Instagram / X 链接无法稳定免登录解析。请上传媒体文件，或粘贴可直链访问的图片/视频 URL。
              </p>
            )}
          </label>

          <label className="block">
            <span className="text-sm font-medium mb-2 block">投放规格（可选）</span>
            <select
              value={targetPlatform}
              onChange={(e) => setTargetPlatform(e.target.value)}
              className="input-primary w-full"
              data-testid="extract-platform"
            >
              <option value="auto">自动（按链接识别，默认 TikTok 竖屏）</option>
              <option value="tiktok">TikTok / 抖音 · 9:16</option>
              <option value="youtube">YouTube Shorts · 9:16</option>
              <option value="instagram">Instagram Reels · 9:16</option>
              <option value="x">X / 竖屏短视频</option>
            </select>
          </label>

          <button
            type="button"
            onClick={run}
            disabled={!canSubmit}
            data-testid="extract-submit"
            className={cn(
              "w-full h-11 rounded-xl font-semibold inline-flex items-center justify-center gap-2 transition-colors",
              !canSubmit
                ? "bg-white/10 text-text-secondary cursor-not-allowed"
                : "bg-white text-black hover:bg-white/90",
            )}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {loading ? "提取中…" : "提取结构"}
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
                  {result.social?.platform ? ` · ${result.social.platform}` : ""}
                </span>
                <button
                  type="button"
                  onClick={copyPrompt}
                  className="text-xs inline-flex items-center gap-1 text-brand hover:underline"
                >
                  <Copy className="w-3.5 h-3.5" /> 复制
                </button>
              </div>
              {result.social?.title && (
                <p className="text-sm font-medium text-text-primary">{result.social.title}</p>
              )}
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
              {result.viral && (
                <div
                  className="rounded-xl border border-white/[0.08] bg-black/20 p-3 space-y-2"
                  data-testid="extract-viral-panel"
                >
                  <div className="flex flex-wrap items-center gap-2 text-[11px] text-text-tertiary">
                    <span data-testid="extract-viral-placement">
                      {result.viral.placement_label || result.viral.placement} · {result.viral.aspect} · {result.viral.duration_sec}s
                    </span>
                  </div>
                  <ol className="space-y-2">
                    {(result.viral.beats || []).map((b) => (
                      <li key={b.key} className="text-xs leading-relaxed">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <span className="text-text-tertiary mr-1">{b.label}</span>
                            <span className="text-text-secondary">{b.prompt}</span>
                          </div>
                          <Link
                            href={`/create/video?shot=${encodeURIComponent(b.key)}&prompt=${encodeURIComponent(b.prompt)}&aspect=${encodeURIComponent(result.viral?.aspect || "9:16")}`}
                            data-testid={`extract-beat-${b.key}`}
                            className="shrink-0 text-[11px] px-2 py-1 rounded-md border border-cosmic-border hover:border-brand/50 text-brand"
                          >
                            生成此镜
                          </Link>
                        </div>
                      </li>
                    ))}
                  </ol>
                  <p className="text-[11px] text-text-tertiary leading-relaxed" data-testid="extract-viral-honesty">
                    {result.viral.honesty}
                  </p>
                </div>
              )}
              {result.honesty && (
                <p className="text-[11px] text-text-tertiary leading-relaxed" data-testid="extract-honesty">
                  {result.honesty}
                </p>
              )}
              <div className="flex flex-wrap gap-2 pt-2">
                <Link
                  href={videoHref}
                  data-testid="extract-to-video"
                  className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg bg-white text-black text-sm font-medium"
                >
                  <Video className="w-3.5 h-3.5" />
                  一键成片
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <Link
                  href={result.create_links?.image || `/create/image?prompt=${encodeURIComponent(result.prompt)}`}
                  className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border border-cosmic-border text-sm"
                >
                  <ImageIcon className="w-3.5 h-3.5" />
                  用于出图
                </Link>
                <Link
                  href={agentHref}
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
