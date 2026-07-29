"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { ImagePlus, X, Download, Maximize2, Sparkles, Loader2, CheckCircle2, Globe } from "lucide-react";
import { listPhotoPacks, generatePack, getTaskStatus, uploadImage, publishShare, type PhotoPack, type TaskResult } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

/* ─────────────────────────────────────────────────────────────
   BatchPackStudio — real batch SKU pipeline (Yapper Product Shots /
   Headshots / Photo Packs). One input → a BATCH of professional
   variations generated in one job, filling a gallery as they finish.
   ───────────────────────────────────────────────────────────── */

interface ResultCell { label: string; taskId: string; status: string; url?: string; error?: string; published?: boolean }

export function BatchPackStudio({
  defaultPack, category, title, subtitle, subjectPlaceholder,
}: {
  defaultPack?: string;
  category?: string;         // filter pack picker to a category
  title: string;
  subtitle: string;
  subjectPlaceholder?: string;
}) {
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [packs, setPacks] = useState<PhotoPack[]>([]);
  const [packId, setPackId] = useState<string>(defaultPack || "");
  const [subject, setSubject] = useState("");
  const [refFile, setRefFile] = useState<File | null>(null);
  const [refPreview, setRefPreview] = useState<string | null>(null);
  const [count, setCount] = useState(4);
  const [busy, setBusy] = useState(false);
  const [cells, setCells] = useState<ResultCell[]>([]);
  const [lightbox, setLightbox] = useState<string | null>(null);

  useEffect(() => {
    listPhotoPacks().then((ps) => {
      const filtered = category ? ps.filter((p) => p.category === category) : ps;
      setPacks(filtered);
      if (!packId && filtered.length) setPackId(defaultPack && filtered.some((p) => p.id === defaultPack) ? defaultPack : filtered[0].id);
    }).catch(() => {});
  }, [category, defaultPack]); // eslint-disable-line

  const pack = packs.find((p) => p.id === packId);
  const maxCount = pack?.variation_count ?? 4;
  const effCount = Math.min(count, maxCount);

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) { setRefFile(f); setRefPreview(URL.createObjectURL(f)); }
    e.target.value = "";
  };

  const pollOne = useCallback(async (taskId: string, label: string) => {
    for (let i = 0; i < 80; i++) {
      try {
        const s = await getTaskStatus(taskId);
        if (s.status === "completed" || s.status === "failed") {
          const r = (s as TaskResult).results?.[0];
          setCells((prev) => prev.map((c) => c.taskId === taskId
            ? { ...c, status: s.status, url: r?.url, error: (s as TaskResult).error_message }
            : c));
          return;
        }
      } catch { /* keep polling */ }
      await new Promise((r) => setTimeout(r, 3000));
    }
    setCells((prev) => prev.map((c) => c.taskId === taskId ? { ...c, status: "failed", error: "超时" } : c));
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!pack || busy) return;
    setBusy(true);
    setCells([]);
    try {
      let image_url: string | undefined;
      if (pack.i2i && refFile) {
        const up = await uploadImage(refFile);
        image_url = up.url;
      }
      const batch = await generatePack({ pack_id: pack.id, subject: subject || undefined, image_url, count: effCount });
      const initial = batch.items.map((it) => ({ label: it.label, taskId: it.task_id, status: it.status, error: it.error }));
      setCells(initial);
      const failedSubmit = batch.items.filter((it) => it.status === "failed");
      if (failedSubmit.length === batch.items.length) {
        toast.error("生成失败", batch.items[0]?.error || "请检查积分");
      } else {
        toast.success("已开始批量生成", `${batch.dispatched} 张 · 预估 ${batch.estimated_cost_credits} 积分`);
      }
      await Promise.all(batch.items.filter((it) => it.status !== "failed").map((it) => pollOne(it.task_id, it.label)));
    } catch (e: any) {
      toast.error("生成失败", e.message || "");
    } finally {
      setBusy(false);
    }
  }, [pack, busy, refFile, subject, effCount, pollOne, toast]);

  const downloadAll = () => {
    cells.filter((c) => c.url).forEach((c, i) => setTimeout(() => {
      const a = document.createElement("a"); a.href = c.url!; a.download = ""; a.target = "_blank"; a.rel = "noopener";
      document.body.appendChild(a); a.click(); a.remove();
    }, i * 350));
  };

  // Growth flywheel: publish finished pack results to Explore (create → explore → remix).
  const publishAll = useCallback(async () => {
    const done = cells.filter((c) => c.status === "completed" && !c.published);
    if (!done.length) return;
    let ok = 0;
    await Promise.all(done.map(async (c) => {
      try { await publishShare(c.taskId); ok++; setCells((prev) => prev.map((x) => x.taskId === c.taskId ? { ...x, published: true } : x)); }
      catch { /* skip */ }
    }));
    if (ok) toast.success("已发布到 Explore", `${ok} 张作品已进入探索画廊`);
  }, [cells, toast]);

  const doneCount = cells.filter((c) => c.status === "completed").length;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">{title}</h1>
        <p className="text-sm text-text-secondary/80 mt-1">{subtitle}</p>
      </div>

      {/* Config card */}
      <div className="rounded-2xl bg-cosmic-elevated border border-cosmic-border shadow-lg p-4 space-y-4">
        {/* Pack picker */}
        <div>
          <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider mb-2">套系</p>
          <div className="flex flex-wrap gap-2">
            {packs.map((p) => (
              <button key={p.id} onClick={() => setPackId(p.id)}
                className={cn("px-3 py-1.5 rounded-lg text-xs border transition-colors",
                  packId === p.id ? "border-accent-cyan/40 bg-accent-cyan/[0.08] text-accent-cyan" : "border-cosmic-border/50 text-text-secondary hover:border-cosmic-border")}>
                {p.label} · {p.variation_count} 图
              </button>
            ))}
          </div>
          {pack && <p className="text-[11px] text-text-secondary/60 mt-1.5">{pack.desc}</p>}
        </div>

        <div className="flex flex-col sm:flex-row gap-4">
          {/* Reference image (i2i packs) */}
          {pack?.i2i && (
            <div className="flex-shrink-0">
              <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider mb-2">参考图（可选）</p>
              <input ref={fileRef} type="file" accept="image/*" onChange={onFile} className="hidden" />
              {refPreview ? (
                <div className="relative w-24 h-24 rounded-xl overflow-hidden border border-cosmic-border">
                  <img src={refPreview} alt="ref" className="w-full h-full object-cover" />
                  <button onClick={() => { setRefFile(null); setRefPreview(null); }} className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/70 flex items-center justify-center"><X className="w-3 h-3 text-white" /></button>
                </div>
              ) : (
                <button onClick={() => fileRef.current?.click()} className="w-24 h-24 rounded-xl border border-dashed border-cosmic-border/60 flex flex-col items-center justify-center gap-1 text-text-secondary/60 hover:border-accent-cyan/40 hover:text-accent-cyan transition-colors">
                  <ImagePlus className="w-5 h-5" /><span className="text-[10px]">上传</span>
                </button>
              )}
            </div>
          )}

          {/* Subject */}
          <div className="flex-1">
            <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider mb-2">主体描述</p>
            <textarea value={subject} onChange={(e) => setSubject(e.target.value)} rows={3}
              placeholder={subjectPlaceholder || "例如：一瓶蓝色渐变的香水 / 一位年轻的亚洲女性"}
              className="w-full resize-none px-3 py-2 rounded-lg text-sm bg-cosmic-surface/50 border border-cosmic-border/50 text-text-primary placeholder:text-text-tertiary/45 focus:outline-none focus:border-accent-cyan/40" />
          </div>
        </div>

        {/* Count + generate */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-secondary/60">数量</span>
            {[2, 4, maxCount].filter((v, i, a) => a.indexOf(v) === i && v <= maxCount).map((n) => (
              <button key={n} onClick={() => setCount(n)}
                className={cn("px-2.5 py-1 rounded-md text-xs border", effCount === n ? "border-accent-cyan/40 bg-accent-cyan/[0.08] text-accent-cyan" : "border-cosmic-border/50 text-text-secondary")}>
                {n}
              </button>
            ))}
          </div>
          <button onClick={handleGenerate} disabled={busy || !pack}
            className={cn("inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-medium transition-all",
              busy || !pack ? "bg-cosmic-subtle text-text-tertiary/50 cursor-not-allowed" : "bg-gradient-to-r from-accent-cyan to-accent-violet text-white hover:brightness-110 active:scale-95")}>
            {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {busy ? "批量生成中…" : `生成 ${effCount} 张套系`}
          </button>
        </div>
      </div>

      {/* Results gallery */}
      {cells.length > 0 && (
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">
              套系结果 {doneCount}/{cells.length}
            </p>
            {doneCount > 0 && (
              <div className="flex items-center gap-2">
                <button onClick={publishAll} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] border border-cosmic-border/60 text-text-secondary hover:text-accent-cyan hover:border-accent-cyan/40 transition-colors">
                  <Globe className="w-3.5 h-3.5" /> 发布到 Explore
                </button>
                <button onClick={downloadAll} className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] bg-accent-cyan/[0.1] text-accent-cyan hover:bg-accent-cyan/20">
                  <Download className="w-3.5 h-3.5" /> 下载全部
                </button>
              </div>
            )}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {cells.map((c) => (
              <motion.div key={c.taskId} initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
                className="group relative rounded-xl overflow-hidden border border-cosmic-border bg-cosmic-subtle aspect-square">
                {c.url ? (
                  <>
                    <img src={c.url} alt={c.label} onClick={() => setLightbox(c.url!)} className="w-full h-full object-cover cursor-zoom-in" />
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-t from-black/70 to-transparent flex items-end justify-end p-2 gap-1.5 pointer-events-none">
                      <button onClick={() => setLightbox(c.url!)} className="btn-icon bg-white/15 text-white pointer-events-auto"><Maximize2 className="w-4 h-4" /></button>
                      <a href={c.url} download target="_blank" rel="noopener noreferrer" className="btn-icon bg-white/15 text-white pointer-events-auto"><Download className="w-4 h-4" /></a>
                    </div>
                  </>
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center gap-2 text-text-secondary/50">
                    {c.status === "failed" ? <span className="text-[11px] text-destructive px-2 text-center">{c.error || "失败"}</span>
                      : <Loader2 className="w-5 h-5 animate-spin" />}
                  </div>
                )}
                <div className="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded bg-black/55 text-[10px] text-white/90 flex items-center gap-1">
                  {c.status === "completed" && <CheckCircle2 className="w-3 h-3 text-accent-cyan" />}
                  {c.label}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {lightbox && (
        <div onClick={() => setLightbox(null)} className="fixed inset-0 z-[100] bg-black/85 backdrop-blur-sm flex items-center justify-center p-6">
          <button onClick={() => setLightbox(null)} className="absolute top-5 right-5 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white"><X className="w-5 h-5" /></button>
          <img src={lightbox} alt="预览" onClick={(e) => e.stopPropagation()} className="max-w-full max-h-full rounded-lg object-contain" />
        </div>
      )}
    </div>
  );
}
