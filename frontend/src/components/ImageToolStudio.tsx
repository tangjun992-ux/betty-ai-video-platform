"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { Upload, Loader2, Download, RefreshCw, Sparkles, ArrowRight } from "lucide-react";
import { editImageTool, API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

type Op = "edit" | "upscale" | "bg-remove" | "extend";

function resolveMedia(url: string): string {
  if (!url) return url;
  if (url.startsWith("http")) return url;
  const origin = API_BASE.replace(/\/api\/v1$/, "");
  return `${origin}${url}`;
}

export interface ImageToolStudioProps {
  operation: Op;
  emoji: string;
  title: string;
  subtitle: string;
  cta: string;
  needsPrompt?: boolean;
  promptPlaceholder?: string;
  factors?: string[];
  ratios?: string[];
}

export default function ImageToolStudio({
  operation, emoji, title, subtitle, cta,
  needsPrompt = false, promptPlaceholder = "", factors, ratios,
}: ImageToolStudioProps) {
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [prompt, setPrompt] = useState("");
  const [factor, setFactor] = useState(factors?.[0] || "2");
  const [ratio, setRatio] = useState(ratios?.[0] || "16:9");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ url: string; model: string } | null>(null);

  const onUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
  }, []);

  const run = async () => {
    if (!file) { toast.error("请上传图片", "先选择一张要处理的图片"); return; }
    if (needsPrompt && !prompt.trim()) { toast.error("请输入指令", "描述你想要的修改"); return; }
    setLoading(true);
    setResult(null);
    try {
      const res = await editImageTool({ operation, file, prompt, factor, ratio });
      setResult({ url: resolveMedia(res.url), model: res.model });
      toast.success("处理完成", "结果已生成，可对比 / 下载");
    } catch (e: any) {
      toast.error("处理失败", e.message || "请稍后重试");
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
        {/* Left: input */}
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-text-primary mb-2 block">上传图片</span>
            <div className="relative aspect-square rounded-2xl border-2 border-dashed border-cosmic-border hover:border-brand/40 bg-cosmic-subtle flex items-center justify-center cursor-pointer overflow-hidden transition-all group">
              {preview ? (
                <>
                  <img src={preview} alt="源图" className="w-full h-full object-contain" />
                  <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                    <RefreshCw className="w-8 h-8 text-white" />
                  </div>
                </>
              ) : (
                <div className="text-center p-8">
                  <Upload className="w-10 h-10 text-text-secondary mx-auto mb-3 group-hover:text-brand transition-colors" />
                  <p className="text-sm text-text-secondary">点击上传图片</p>
                  <p className="text-xs text-text-tertiary/60 mt-1">支持 JPG / PNG / WEBP，≤10MB</p>
                </div>
              )}
              <input type="file" accept="image/*" onChange={onUpload} className="absolute inset-0 opacity-0 cursor-pointer" />
            </div>
          </label>

          {needsPrompt && (
            <div>
              <span className="text-sm font-medium text-text-primary mb-2 block">编辑指令</span>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={promptPlaceholder}
                rows={3}
                className="w-full px-4 py-3 rounded-2xl bg-cosmic-subtle border border-cosmic-border text-sm text-text-primary placeholder:text-text-tertiary/50 focus:outline-none focus:ring-2 focus:ring-brand/25 focus:border-brand/30 resize-none transition-all"
              />
            </div>
          )}

          {factors && (
            <div>
              <span className="text-sm font-medium text-text-primary mb-2 block">放大倍率</span>
              <div className="flex gap-2">
                {factors.map((f) => (
                  <button key={f} onClick={() => setFactor(f)}
                    className={cn("flex-1 py-2 rounded-xl text-sm font-semibold border transition-all",
                      factor === f ? "bg-brand/[0.08] text-brand border-brand/25" : "bg-cosmic-subtle border-cosmic-border text-text-secondary hover:text-text-primary")}>
                    {f}x
                  </button>
                ))}
              </div>
            </div>
          )}

          {ratios && (
            <div>
              <span className="text-sm font-medium text-text-primary mb-2 block">目标画幅</span>
              <div className="flex flex-wrap gap-2">
                {ratios.map((r) => (
                  <button key={r} onClick={() => setRatio(r)}
                    className={cn("px-3 py-1.5 rounded-xl text-sm font-semibold border transition-all",
                      ratio === r ? "bg-brand/[0.08] text-brand border-brand/25" : "bg-cosmic-subtle border-cosmic-border text-text-secondary hover:text-text-primary")}>
                    {r}
                  </button>
                ))}
              </div>
            </div>
          )}

          <button onClick={run} disabled={loading || !file} className="btn-primary w-full">
            {loading ? (<><Loader2 className="w-5 h-5 animate-spin" />处理中...</>) : (<><Sparkles className="w-5 h-5" />{cta}</>)}
          </button>
        </div>

        {/* Right: result */}
        <div className="space-y-3">
          <span className="text-sm font-medium text-text-primary block">处理结果</span>
          <div className="relative aspect-square rounded-2xl border border-cosmic-border bg-cosmic-subtle overflow-hidden flex items-center justify-center"
            style={{ backgroundImage: "repeating-conic-gradient(#2a2a35 0% 25%, #1e1e28 0% 50%)", backgroundSize: "24px 24px" }}>
            {loading ? (
              <div className="text-center">
                <Loader2 className="w-8 h-8 text-brand animate-spin mx-auto mb-2" />
                <p className="text-sm text-text-secondary">AI 正在处理...</p>
              </div>
            ) : result ? (
              <img src={result.url} alt="结果" className="w-full h-full object-contain" />
            ) : (
              <div className="text-center text-text-tertiary/50">
                <ArrowRight className="w-8 h-8 mx-auto mb-2" />
                <p className="text-sm">结果将显示在这里</p>
              </div>
            )}
          </div>
          {result && (
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-cosmic-surface border border-cosmic-border text-text-tertiary truncate">{result.model}</span>
              <a href={result.url} download className="btn-secondary text-sm"><Download className="w-4 h-4" />下载</a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
