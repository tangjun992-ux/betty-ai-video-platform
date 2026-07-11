"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus, Trash2, ChevronLeft, ChevronRight, Film, Loader2,
  Sparkles, Download, Music, ImageIcon, Video as VideoIcon,
} from "lucide-react";
import { listLibrary, composeTimeline, API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

interface LibItem { id: string; url: string; thumbnail?: string | null; title: string; media_type: string; }
interface Clip { key: string; url: string; thumbnail?: string | null; title: string; }

function resolveMedia(url: string): string {
  if (!url) return url;
  if (url.startsWith("http")) return url;
  return `${API_BASE.replace(/\/api\/v1$/, "")}${url}`;
}

export default function TimelinePage() {
  const toast = useToast();
  const [videos, setVideos] = useState<LibItem[]>([]);
  const [audios, setAudios] = useState<LibItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [track, setTrack] = useState<Clip[]>([]);
  const [narration, setNarration] = useState<LibItem | null>(null);
  const [withAudio, setWithAudio] = useState(true);
  const [composing, setComposing] = useState(false);
  const [result, setResult] = useState<{ url: string; thumbnail: string } | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [v, a] = await Promise.all([
          listLibrary({ media_type: "video", limit: 60 }),
          listLibrary({ media_type: "audio", limit: 30 }),
        ]);
        setVideos((v.items || []).filter((i: LibItem) => i.url));
        setAudios((a.items || []).filter((i: LibItem) => i.url));
      } catch (e: any) {
        toast.error("加载素材库失败", e.message || "");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const addClip = useCallback((item: LibItem) => {
    setTrack((t) => [...t, { key: `${item.id}-${Date.now()}`, url: item.url, thumbnail: item.thumbnail, title: item.title }]);
    setResult(null);
  }, []);
  const removeClip = (key: string) => { setTrack((t) => t.filter((c) => c.key !== key)); setResult(null); };
  const move = (idx: number, dir: -1 | 1) => {
    setTrack((t) => {
      const n = [...t]; const j = idx + dir;
      if (j < 0 || j >= n.length) return t;
      [n[idx], n[j]] = [n[j], n[idx]];
      return n;
    });
    setResult(null);
  };

  const compose = async () => {
    if (track.length < 1) { toast.error("请先添加片段", "从下方素材库添加视频到时间线"); return; }
    setComposing(true);
    setResult(null);
    try {
      const res = await composeTimeline(
        track.map((c) => ({ url: c.url })),
        { with_audio: withAudio, narration_url: narration?.url },
      );
      setResult({ url: resolveMedia(res.url), thumbnail: resolveMedia(res.thumbnail) });
      toast.success("合成完成", `${res.clip_count} 个片段已合成为一条成片`);
    } catch (e: any) {
      toast.error("合成失败", e.message || "请稍后重试");
    } finally {
      setComposing(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-6">
        <span className="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-brand-50 border border-cosmic-border text-2xl">🎞️</span>
        <div>
          <h1 className="text-2xl font-bold gradient-text-static">时间线编辑器</h1>
          <p className="text-text-secondary text-sm">把多个片段按顺序排列，一键合成为成片（真实 ffmpeg 拼接）</p>
        </div>
      </motion.div>

      {/* Preview / result */}
      <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface overflow-hidden mb-5">
        <div className="aspect-video bg-black flex items-center justify-center">
          {composing ? (
            <div className="text-center text-white/80"><Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />正在合成成片…</div>
          ) : result ? (
            <video src={result.url} poster={result.thumbnail} controls autoPlay className="w-full h-full object-contain" />
          ) : (
            <div className="text-center text-text-tertiary/60">
              <Film className="w-10 h-10 mx-auto mb-2" />
              <p className="text-sm">成片预览将显示在这里</p>
            </div>
          )}
        </div>
        {result && (
          <div className="flex items-center justify-between px-4 py-2.5 border-t border-cosmic-border">
            <span className="text-xs text-text-secondary">成片已生成 · {track.length} 镜</span>
            <a href={result.url} download className="btn-secondary text-sm"><Download className="w-4 h-4" /> 下载成片</a>
          </div>
        )}
      </div>

      {/* Timeline track */}
      <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-4 mb-5">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-text-primary flex items-center gap-2"><Film className="w-4 h-4 text-brand" /> 时间线 · {track.length} 镜</span>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-xs text-text-secondary cursor-pointer">
              <input type="checkbox" checked={withAudio} onChange={(e) => setWithAudio(e.target.checked)} className="accent-brand" /> 混入音轨
            </label>
            <button onClick={compose} disabled={composing || track.length < 1} className="btn-primary h-9 px-4 text-sm">
              {composing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} 合成成片
            </button>
          </div>
        </div>

        {track.length === 0 ? (
          <div className="h-24 rounded-xl border border-dashed border-cosmic-border flex items-center justify-center text-sm text-text-tertiary">
            从下方素材库点击视频，加入时间线
          </div>
        ) : (
          <div className="flex gap-2 overflow-x-auto pb-2">
            {track.map((c, i) => (
              <div key={c.key} className="relative flex-shrink-0 w-40 group">
                <div className="aspect-video rounded-lg overflow-hidden ring-1 ring-cosmic-border bg-black">
                  {c.thumbnail ? <img src={resolveMedia(c.thumbnail)} alt="" className="w-full h-full object-cover" />
                    : <video src={resolveMedia(c.url)} muted className="w-full h-full object-cover" />}
                </div>
                <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded bg-black/60 text-[10px] text-white font-semibold">#{i + 1}</div>
                <div className="absolute inset-x-0 bottom-1 flex items-center justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => move(i, -1)} disabled={i === 0} className="w-6 h-6 rounded bg-black/70 text-white flex items-center justify-center disabled:opacity-30"><ChevronLeft className="w-3.5 h-3.5" /></button>
                  <button onClick={() => removeClip(c.key)} className="w-6 h-6 rounded bg-black/70 text-white hover:bg-red-500 flex items-center justify-center"><Trash2 className="w-3.5 h-3.5" /></button>
                  <button onClick={() => move(i, 1)} disabled={i === track.length - 1} className="w-6 h-6 rounded bg-black/70 text-white flex items-center justify-center disabled:opacity-30"><ChevronRight className="w-3.5 h-3.5" /></button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Narration picker */}
        {audios.length > 0 && (
          <div className="mt-3 pt-3 border-t border-cosmic-border">
            <div className="flex items-center gap-2 mb-2 text-xs text-text-secondary"><Music className="w-3.5 h-3.5" /> 旁白 / 配乐（可选，替换默认环境音）</div>
            <div className="flex gap-2 flex-wrap">
              <button onClick={() => setNarration(null)} className={cn("px-3 py-1.5 rounded-lg text-xs border transition-all", !narration ? "bg-brand/[0.08] text-brand border-brand/25" : "bg-cosmic-subtle border-cosmic-border text-text-secondary")}>无</button>
              {audios.map((a) => (
                <button key={a.id} onClick={() => setNarration(a)} className={cn("px-3 py-1.5 rounded-lg text-xs border transition-all max-w-[160px] truncate", narration?.id === a.id ? "bg-brand/[0.08] text-brand border-brand/25" : "bg-cosmic-subtle border-cosmic-border text-text-secondary hover:text-text-primary")}>{a.title}</button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Media library picker */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <VideoIcon className="w-4 h-4 text-brand" />
          <span className="text-sm font-semibold text-text-primary">素材库 · 视频（{videos.length}）</span>
          <span className="text-xs text-text-tertiary">点击加入时间线</span>
        </div>
        {loading ? (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
            {[...Array(6)].map((_, i) => <div key={i} className="aspect-video rounded-lg skeleton" />)}
          </div>
        ) : videos.length === 0 ? (
          <div className="h-28 rounded-xl border border-dashed border-cosmic-border flex flex-col items-center justify-center text-sm text-text-tertiary gap-2">
            <ImageIcon className="w-6 h-6" />
            素材库暂无视频。先去 <a href="/create/video" className="text-brand underline">视频创作</a> 或 <a href="/agent" className="text-brand underline">Agent</a> 生成一些片段。
          </div>
        ) : (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3">
            {videos.map((v) => (
              <button key={v.id} onClick={() => addClip(v)} title={v.title}
                className="group relative aspect-video rounded-lg overflow-hidden ring-1 ring-cosmic-border hover:ring-brand/50 transition-all">
                {v.thumbnail ? <img src={resolveMedia(v.thumbnail)} alt="" className="w-full h-full object-cover" />
                  : <video src={resolveMedia(v.url)} muted className="w-full h-full object-cover" />}
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-white text-black text-xs font-semibold"><Plus className="w-3.5 h-3.5" /> 加入</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
