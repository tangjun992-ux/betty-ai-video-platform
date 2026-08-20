"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Loader2, Upload, Sparkles, FolderOpen } from "lucide-react";
import { CapabilityNotice } from "@/components/CapabilityNotice";
import { API_BASE, listLibrary } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

/**
 * Face Swap — verified i2i edit (google/nano-banana-edit).
 * Honesty: not InsightFace/Roop pixel identity swap.
 */

const FALLBACK_TEMPLATES = [
  { id: "poster", label: "电影海报", hint: "戏剧光影", text: "cinematic movie poster lighting, dramatic contrast, keep face identity from source, match target scene" },
  { id: "linkedin", label: "职场证件", hint: "干净背景", text: "professional headshot lighting, clean background blend, natural skin tone, keep source face identity" },
  { id: "cyber", label: "赛博朋克", hint: "霓虹轮廓", text: "cyberpunk neon rim light, futuristic atmosphere, keep source face identity on target body" },
  { id: "comic", label: "漫画风", hint: "描边合成", text: "stylized comic illustration blend, bold ink edges, keep recognizable source face on target" },
  { id: "vintage", label: "复古胶片", hint: "颗粒暖调", text: "vintage film grain, warm color grade, soft vignette, preserve source facial features" },
  { id: "magazine", label: "杂志封面", hint: "时尚大片", text: "fashion magazine cover, studio key light, editorial retouch look, keep source face identity" },
  { id: "shortcover", label: "短视频封面", hint: "高对比钩子", text: "viral short-video thumbnail, high contrast, punchy color, keep source face recognizable on target" },
  { id: "holiday", label: "节日贺卡", hint: "氛围光", text: "festive greeting card lighting, warm bokeh, seasonal atmosphere, preserve source facial features" },
];

type Slot = "face" | "target";

export default function FaceSwapPage() {
  const router = useRouter();
  const toast = useToast();
  const [faceFile, setFaceFile] = useState<File | null>(null);
  const [targetFile, setTargetFile] = useState<File | null>(null);
  const [faceUrl, setFaceUrl] = useState("");
  const [targetUrl, setTargetUrl] = useState("");
  const [facePreview, setFacePreview] = useState("");
  const [targetPreview, setTargetPreview] = useState("");
  const [prompt, setPrompt] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [templates, setTemplates] = useState(FALLBACK_TEMPLATES);
  const [picker, setPicker] = useState<Slot | null>(null);
  const [libItems, setLibItems] = useState<Array<{ id: string; url: string; thumbnail?: string; title?: string }>>([]);

  useEffect(() => {
    fetch(`${API_BASE}/face-swap/templates`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (Array.isArray(d?.templates) && d.templates.length) setTemplates(d.templates);
      })
      .catch(() => {});
  }, []);

  const onFace = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFaceFile(f);
    setFaceUrl("");
    setFacePreview(URL.createObjectURL(f));
  }, []);

  const onTarget = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setTargetFile(f);
    setTargetUrl("");
    setTargetPreview(URL.createObjectURL(f));
  }, []);

  const openPicker = async (slot: Slot) => {
    setPicker(slot);
    try {
      const data = await listLibrary({ media_type: "image", limit: 48 });
      setLibItems((data.items || []).filter((it: any) => it.media_type === "image" && it.url));
    } catch {
      setLibItems([]);
    }
  };

  const pickFromLibrary = (url: string) => {
    if (picker === "face") {
      setFaceFile(null);
      setFaceUrl(url);
      setFacePreview(url);
    } else if (picker === "target") {
      setTargetFile(null);
      setTargetUrl(url);
      setTargetPreview(url);
    }
    setPicker(null);
  };

  const ready = Boolean((faceFile || faceUrl) && (targetFile || targetUrl));

  const resolveUrl = async (file: File | null, url: string) => {
    if (url) return url;
    if (!file) throw new Error("缺少图片");
    const fd = new FormData();
    fd.append("file", file);
    const up = await fetch(`${API_BASE}/library/upload`, { method: "POST", body: fd });
    if (!up.ok) throw new Error("上传失败");
    const item = await up.json();
    if (!item?.url) throw new Error("上传未返回 URL");
    return item.url as string;
  };

  const submit = async () => {
    if (!ready) {
      toast.error("请选择两张图", "源人脸 + 目标场景（上传或从内容库）");
      return;
    }
    setSubmitting(true);
    try {
      let res: Response;
      if (faceFile && targetFile) {
        const fd = new FormData();
        fd.append("face_file", faceFile);
        fd.append("target_file", targetFile);
        if (prompt.trim()) fd.append("prompt", prompt.trim());
        res = await fetch(`${API_BASE}/face-swap/upload`, { method: "POST", body: fd });
      } else {
        const fu = await resolveUrl(faceFile, faceUrl);
        const tu = await resolveUrl(targetFile, targetUrl);
        res = await fetch(`${API_BASE}/face-swap`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            face_url: fu,
            target_url: tu,
            prompt: prompt.trim() || undefined,
          }),
        });
      }
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
        {([
          { key: "face" as Slot, label: "1. 源人脸", preview: facePreview, onChange: onFace },
          { key: "target" as Slot, label: "2. 目标图", preview: targetPreview, onChange: onTarget },
        ]).map((slot) => (
          <div key={slot.key}>
            <span className="text-sm font-medium mb-2 block">{slot.label}</span>
            <label className="block cursor-pointer">
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
            <button
              type="button"
              data-testid={`face-swap-from-library-${slot.key}`}
              onClick={() => openPicker(slot.key)}
              className="mt-2 w-full inline-flex items-center justify-center gap-1.5 text-xs text-text-secondary hover:text-text-primary"
            >
              <FolderOpen className="w-3.5 h-3.5" /> 从内容库选择
            </button>
          </div>
        ))}
      </div>

      {picker && (
        <div className="mb-6 rounded-2xl border border-cosmic-border p-3" data-testid="face-swap-library-picker">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-text-secondary">从内容库选择{picker === "face" ? "源人脸" : "目标图"}</p>
            <button type="button" className="text-xs text-text-secondary" onClick={() => setPicker(null)}>关闭</button>
          </div>
          {libItems.length === 0 ? (
            <p className="text-xs text-text-tertiary py-4 text-center">内容库暂无图片</p>
          ) : (
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
              {libItems.map((it) => (
                <button
                  key={it.id}
                  type="button"
                  onClick={() => pickFromLibrary(it.url)}
                  className="aspect-square rounded-lg overflow-hidden border border-cosmic-border hover:border-accent-cyan"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={it.thumbnail || it.url} alt={it.title || ""} className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="mb-4" data-testid="face-swap-templates">
        <p className="text-xs text-text-secondary mb-2">玩法模板（写入提示词漏斗，非 InsightFace / Roop 像素换脸）</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {templates.map((t) => (
            <button
              key={t.id}
              type="button"
              data-testid={`face-swap-template-${t.id}`}
              onClick={() => setPrompt(t.text)}
              className={cn(
                "text-left px-3 py-2.5 rounded-xl text-xs border transition-colors overflow-hidden",
                prompt === t.text
                  ? "border-brand bg-brand/10 text-brand"
                  : "border-cosmic-border text-text-secondary hover:border-brand/40",
              )}
              style={{
                backgroundImage: (t as { color?: string }).color
                  ? `linear-gradient(135deg, ${(t as { color?: string }).color}22, transparent)`
                  : undefined,
              }}
            >
              <span className="block text-base mb-0.5">{(t as { icon?: string }).icon || "🎭"}</span>
              <span className="block font-semibold text-text-primary">{t.label}</span>
              <span className="block text-[10px] text-text-secondary/80 mt-0.5">{t.hint}</span>
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
        disabled={submitting || !ready}
        onClick={submit}
        className="w-full py-3.5 rounded-2xl bg-brand text-white font-semibold disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {submitting ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
        开始换脸
      </button>
    </div>
  );
}
