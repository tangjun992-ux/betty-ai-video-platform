"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import { Upload, Loader2, Download, RefreshCw, Sparkles, ArrowRight } from "lucide-react";
import { editImageTool, API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { useLocale, type TranslationKey } from "@/i18n/LocaleProvider";
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
  // Optional i18n keys — when provided, title/subtitle/cta/placeholder are
  // translated via the active locale; the literal props remain the fallback.
  titleKey?: TranslationKey;
  subtitleKey?: TranslationKey;
  ctaKey?: TranslationKey;
  promptKey?: TranslationKey;
}

export default function ImageToolStudio({
  operation, emoji, title, subtitle, cta,
  needsPrompt = false, promptPlaceholder = "", factors, ratios,
  titleKey, subtitleKey, ctaKey, promptKey,
}: ImageToolStudioProps) {
  const toast = useToast();
  const { t } = useLocale();
  const tt = (k: TranslationKey | undefined, fallback: string) => (k ? t(k) : fallback);
  const L = {
    title: tt(titleKey, title),
    subtitle: tt(subtitleKey, subtitle),
    cta: tt(ctaKey, cta),
    placeholder: tt(promptKey, promptPlaceholder),
  };
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
    if (!file) { toast.error(t("tool.needImage"), t("tool.needImageDesc")); return; }
    if (needsPrompt && !prompt.trim()) { toast.error(t("tool.needPrompt"), t("tool.needPromptDesc")); return; }
    setLoading(true);
    setResult(null);
    try {
      const res = await editImageTool({ operation, file, prompt, factor, ratio });
      setResult({ url: resolveMedia(res.url), model: res.model });
      toast.success(t("tool.done"), t("tool.doneDesc"));
    } catch (e: any) {
      toast.error(t("tool.failed"), e.message || t("tool.failedDesc"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-8">
        <span className="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-brand-50 border border-cosmic-border text-2xl">{emoji}</span>
        <div>
          <h1 className="text-2xl font-bold gradient-text-static">{L.title}</h1>
          <p className="text-text-secondary text-sm">{L.subtitle}</p>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: input */}
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-text-primary mb-2 block">{t("tool.upload")}</span>
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
                  <p className="text-sm text-text-secondary">{t("tool.clickUpload")}</p>
                  <p className="text-xs text-text-tertiary/60 mt-1">{t("tool.supported")}</p>
                </div>
              )}
              <input type="file" accept="image/*" onChange={onUpload} className="absolute inset-0 opacity-0 cursor-pointer" />
            </div>
          </label>

          {needsPrompt && (
            <div>
              <span className="text-sm font-medium text-text-primary mb-2 block">{t("tool.instruction")}</span>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder={L.placeholder}
                rows={3}
                className="w-full px-4 py-3 rounded-2xl bg-cosmic-subtle border border-cosmic-border text-sm text-text-primary placeholder:text-text-tertiary/50 focus:outline-none focus:ring-2 focus:ring-brand/25 focus:border-brand/30 resize-none transition-all"
              />
            </div>
          )}

          {factors && (
            <div>
              <span className="text-sm font-medium text-text-primary mb-2 block">{t("tool.factor")}</span>
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
              <span className="text-sm font-medium text-text-primary mb-2 block">{t("tool.ratio")}</span>
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
            {loading ? (<><Loader2 className="w-5 h-5 animate-spin" />{t("tool.processing")}</>) : (<><Sparkles className="w-5 h-5" />{L.cta}</>)}
          </button>
        </div>

        {/* Right: result */}
        <div className="space-y-3">
          <span className="text-sm font-medium text-text-primary block">{t("tool.result")}</span>
          <div className="relative aspect-square rounded-2xl border border-cosmic-border bg-cosmic-subtle overflow-hidden flex items-center justify-center"
            style={{ backgroundImage: "repeating-conic-gradient(#2a2a35 0% 25%, #1e1e28 0% 50%)", backgroundSize: "24px 24px" }}>
            {loading ? (
              <div className="text-center">
                <Loader2 className="w-8 h-8 text-brand animate-spin mx-auto mb-2" />
                <p className="text-sm text-text-secondary">{t("tool.processing")}</p>
              </div>
            ) : result ? (
              <img src={result.url} alt={L.title} className="w-full h-full object-contain" />
            ) : (
              <div className="text-center text-text-tertiary/50">
                <ArrowRight className="w-8 h-8 mx-auto mb-2" />
                <p className="text-sm">{t("tool.resultHere")}</p>
              </div>
            )}
          </div>
          {result && (
            <div className="flex items-center justify-between gap-2">
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-cosmic-surface border border-cosmic-border text-text-tertiary truncate">{result.model}</span>
              <a href={result.url} download className="btn-secondary text-sm"><Download className="w-4 h-4" />{t("tool.download")}</a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
