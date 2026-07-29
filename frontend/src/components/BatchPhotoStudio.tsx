"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { Upload, Loader2, Download, RefreshCw, Sparkles, ImageIcon } from "lucide-react";
import { submitGeneration, getTaskStatus, uploadImage, type TaskResult } from "@/lib/api";
import { API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

// Shared studio for Yapper-style batch photo tools:
// Product Shots · Professional Headshots · AI Photo Packs.
// Composes the real /generate backend (count 1-4 batch) + task polling → result grid.

export interface PhotoPack {
  id: string;
  name: string;
  desc: string;
  /** Prompt fragment appended after the subject to steer the pack style. */
  promptSuffix: string;
  style?: string;
}

export interface BatchPhotoStudioProps {
  emoji: string;
  title: string;
  subtitle: string;
  /** Label for the free-text subject field (e.g. "产品描述" / "人物特征"). */
  subjectLabel: string;
  subjectPlaceholder: string;
  packs: PhotoPack[];
  /** When true, shows a reference-image uploader (subject photo for headshots/product). */
  allowReference?: boolean;
  cta: string;
}

function resolveMedia(url: string): string {
  if (!url) return url;
  if (url.startsWith("http")) return url;
  const origin = API_BASE.replace(/\/api\/v1$/, "");
  return `${origin}${url}`;
}

const COUNT_OPTIONS = [1, 2, 4];

export default function BatchPhotoStudio({
  emoji, title, subtitle, subjectLabel, subjectPlaceholder, packs, allowReference = false, cta,
}: BatchPhotoStudioProps) {
  const toast = useToast();
  const [subject, setSubject] = useState("");
  const [packId, setPackId] = useState(packs[0]?.id ?? "");
  const [count, setCount] = useState(4);
  const [refFile, setRefFile] = useState<File | null>(null);
  const [refPreview, setRefPreview] = useState("");
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [results, setResults] = useState<Array<{ url: string; model?: string }>>([]);

  const pack = packs.find((p) => p.id === packId) ?? packs[0];

  const onRefUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setRefFile(f);
    setRefPreview(URL.createObjectURL(f));
  }, []);

  const run = async () => {
    if (!subject.trim()) {
      toast.error("请填写内容", subjectLabel);
      return;
    }
    setLoading(true);
    setResults([]);
    setTaskId(null);
    try {
      let imageUrl: string | undefined;
      if (allowReference && refFile) {
        const up = await uploadImage(refFile);
        imageUrl = up.url;
      }

      const prompt = `${subject.trim()}，${pack.promptSuffix}`;
      const res = await submitGeneration({
        prompt,
        media_type: "image",
        model: "auto",
        quality: "high",
        count,
        style: pack.style,
        image_url: imageUrl,
      });
      setTaskId(res.task_id);

      const maxPolls = 90;
      let polls = 0;
      const poll = async (): Promise<TaskResult> => {
        if (polls++ > maxPolls) throw new Error("生成超时，请重试");
        const status = await getTaskStatus(res.task_id);
        if (status.status === "completed" || status.status === "failed") return status as TaskResult;
        await new Promise((r) => setTimeout(r, 2000));
        return poll();
      };
      const result = await poll();
      if (result.status === "failed") throw new Error(result.error_message || "生成失败");

      const imgs = (result.results ?? [])
        .filter((r) => r.type === "image" || !r.type)
        .map((r) => ({ url: resolveMedia(r.url), model: r.model }));
      if (imgs.length === 0) throw new Error("未返回结果");
      setResults(imgs);
      toast.success("生成完成", `已生成 ${imgs.length} 张`);
    } catch (e: any) {
      toast.error("生成失败", e.message || "请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-8">
        <span className="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-brand-50 border border-cosmic-border text-2xl">{emoji}</span>
        <div>
          <h1 className="text-2xl font-bold gradient-text-static">{title}</h1>
          <p className="text-text-secondary text-sm">{subtitle}</p>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: config */}
        <div className="space-y-4">
          {allowReference && (
            <label className="block">
              <span className="text-sm font-medium text-text-primary mb-2 block">参考照片（可选）</span>
              <div className="relative aspect-[4/3] rounded-2xl border-2 border-dashed border-cosmic-border hover:border-brand/40 bg-cosmic-subtle flex items-center justify-center cursor-pointer overflow-hidden transition-all group">
                {refPreview ? (
                  <>
                    <img src={refPreview} alt="参考" className="w-full h-full object-contain" />
                    <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                      <RefreshCw className="w-8 h-8 text-white" />
                    </div>
                  </>
                ) : (
                  <div className="text-center p-6">
                    <Upload className="w-9 h-9 text-text-secondary mx-auto mb-2 group-hover:text-brand transition-colors" />
                    <p className="text-sm text-text-secondary">上传参考照片</p>
                    <p className="text-xs text-text-tertiary/60 mt-1">用于保持人物 / 产品一致性</p>
                  </div>
                )}
                <input type="file" accept="image/*" onChange={onRefUpload} className="absolute inset-0 opacity-0 cursor-pointer" />
              </div>
            </label>
          )}

          <div>
            <span className="text-sm font-medium text-text-primary mb-2 block">{subjectLabel}</span>
            <textarea
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder={subjectPlaceholder}
              rows={3}
              className="w-full px-4 py-3 rounded-2xl bg-cosmic-subtle border border-cosmic-border text-sm text-text-primary placeholder:text-text-tertiary/50 focus:outline-none focus:ring-2 focus:ring-brand/25 focus:border-brand/30 resize-none transition-all"
            />
          </div>

          <div>
            <span className="text-sm font-medium text-text-primary mb-2 block">选择风格包</span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {packs.map((p) => (
                <button key={p.id} onClick={() => setPackId(p.id)}
                  className={cn("text-left p-3 rounded-xl border transition-all",
                    packId === p.id ? "bg-brand/[0.08] border-brand/25" : "bg-cosmic-subtle border-cosmic-border hover:border-cosmic-border-hover")}>
                  <p className={cn("text-sm font-semibold", packId === p.id ? "text-brand" : "text-text-primary")}>{p.name}</p>
                  <p className="text-xs text-text-tertiary mt-0.5">{p.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <div>
            <span className="text-sm font-medium text-text-primary mb-2 block">生成数量</span>
            <div className="flex gap-2">
              {COUNT_OPTIONS.map((n) => (
                <button key={n} onClick={() => setCount(n)}
                  className={cn("flex-1 py-2 rounded-xl text-sm font-semibold border transition-all",
                    count === n ? "bg-brand/[0.08] text-brand border-brand/25" : "bg-cosmic-subtle border-cosmic-border text-text-secondary hover:text-text-primary")}>
                  {n} 张
                </button>
              ))}
            </div>
          </div>

          <button onClick={run} disabled={loading || !subject.trim()} className="btn-primary w-full">
            {loading ? (
              <><Loader2 className="w-5 h-5 animate-spin" />生成中... {taskId ? `(${taskId.slice(0, 8)}...)` : ""}</>
            ) : (
              <><Sparkles className="w-5 h-5" />{cta}</>
            )}
          </button>
        </div>

        {/* Right: result grid */}
        <div className="space-y-3">
          <span className="text-sm font-medium text-text-primary block">生成结果</span>
          <div className="grid grid-cols-2 gap-3">
            {loading && results.length === 0 ? (
              Array.from({ length: count }).map((_, i) => (
                <div key={i} className="aspect-square rounded-2xl border border-cosmic-border bg-cosmic-subtle animate-pulse flex items-center justify-center">
                  <Loader2 className="w-6 h-6 text-brand animate-spin" />
                </div>
              ))
            ) : results.length > 0 ? (
              results.map((r, i) => (
                <div key={i} className="relative group aspect-square rounded-2xl border border-cosmic-border bg-cosmic-subtle overflow-hidden">
                  <img src={r.url} alt={`结果 ${i + 1}`} className="w-full h-full object-cover" />
                  <a href={r.url} download
                    className="absolute bottom-2 right-2 inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-black/60 text-white text-xs opacity-0 group-hover:opacity-100 transition-opacity">
                    <Download className="w-3.5 h-3.5" />下载
                  </a>
                </div>
              ))
            ) : (
              <div className="col-span-2 aspect-[2/1] rounded-2xl border border-dashed border-cosmic-border bg-cosmic-subtle flex items-center justify-center text-text-tertiary/50">
                <div className="text-center">
                  <ImageIcon className="w-8 h-8 mx-auto mb-2" />
                  <p className="text-sm">结果将以网格显示在这里</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
