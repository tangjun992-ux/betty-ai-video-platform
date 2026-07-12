"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus, Trash2, ChevronLeft, ChevronRight, Film, Loader2,
  Sparkles, Download, Music, ImageIcon, Video as VideoIcon, Type as TypeIcon,
} from "lucide-react";
import { listLibrary, composeTimeline, API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

interface LibItem { id: string; url: string; thumbnail?: string | null; title: string; media_type: string; }
interface Clip { key: string; url: string; thumbnail?: string | null; title: string; }
type Transition = "cut" | "fade" | "dissolve";

function resolveMedia(url: string): string {
  if (!url) return url;
  if (url.startsWith("http")) return url;
  return `${API_BASE.replace(/\/api\/v1$/, "")}${url}`;
}

const TRANSITIONS: { id: Transition; label: string }[] = [
  { id: "cut", label: "硬切 Cut" },
  { id: "fade", label: "淡入淡出 Fade" },
  { id: "dissolve", label: "叠化 Dissolve" },
];

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
  const [transition, setTransition] = useState<Transition>("fade");
  const [subtitleText, setSubtitleText] = useState("");
  const [showSubtitleTrack, setShowSubtitleTrack] = useState(true);

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
      const subtitle_track = subtitleText.trim()
        ? [{ text: subtitleText.trim(), start: 0, end: Math.max(track.length * 5, 5) }]
        : [];
      const res = await composeTimeline(
        track.map((c) => ({ url: c.url, transition })),
        {
          with_audio: withAudio,
          narration_url: narration?.url,
          transition,
          subtitle_track,
        },
      );
      setResult({ url: resolveMedia(res.url), thumbnail: resolveMedia(res.thumbnail) });
      toast.success("合成完成", `${res.clip_count} 个片段 · 转场 ${transition}`);
    } catch (e: any) {
      toast.error("合成失败", e.message || "请稍后重试");
    } finally {
      setComposing(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-6">
        <span className="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-brand-soft border border-cosmic-border text-brand">
          <Film className="w-5 h-5" />
        </span>
        <div>
          <h1 className="text-2xl font-display font-bold">时间线编辑器</h1>
          <p className="text-text-secondary text-sm">多轨编排：视频轨 · 旁白轨 · 字幕轨，提交时携带转场字段</p>
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
            <span className="text-xs text-text-secondary">成片已生成 · {track.length} 镜 · {transition}</span>
            <a href={result.url} download className="btn-secondary text-sm"><Download className="w-4 h-4" /> 下载成片</a>
          </div>
        )}
      </div>

      {/* Transition selector */}
      <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-4 mb-5">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
          <span className="text-sm font-semibold text-text-primary">转场 Transition</span>
          <div className="flex gap-2">
            {TRANSITIONS.map((t) => (
              <button key={t.id} onClick={() => { setTransition(t.id); setResult(null); }}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-medium border transition-all",
                  transition === t.id
                    ? "bg-brand/10 text-brand border-brand/30"
                    : "bg-cosmic-subtle border-cosmic-border text-text-secondary hover:text-text-primary"
                )}>
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Video track */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-text-secondary flex items-center gap-1.5">
              <Film className="w-3.5 h-3.5 text-brand" /> 视频轨 · {track.length} 镜
            </span>
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
                  {i < track.length - 1 && (
                    <div className="absolute -right-1 top-1/2 -translate-y-1/2 z-10 px-1 py-0.5 rounded bg-brand text-[9px] text-white font-medium">
                      {transition}
                    </div>
                  )}
                  <div className="absolute inset-x-0 bottom-1 flex items-center justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onClick={() => move(i, -1)} disabled={i === 0} className="w-6 h-6 rounded bg-black/70 text-white flex items-center justify-center disabled:opacity-30"><ChevronLeft className="w-3.5 h-3.5" /></button>
                    <button onClick={() => removeClip(c.key)} className="w-6 h-6 rounded bg-black/70 text-white hover:bg-red-500 flex items-center justify-center"><Trash2 className="w-3.5 h-3.5" /></button>
                    <button onClick={() => move(i, 1)} disabled={i === track.length - 1} className="w-6 h-6 rounded bg-black/70 text-white flex items-center justify-center disabled:opacity-30"><ChevronRight className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Narration track */}
        <div className="pt-3 border-t border-cosmic-border mb-4">
          <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-text-secondary">
            <Music className="w-3.5 h-3.5 text-brand" /> 旁白轨 / 配乐
          </div>
          <div className="min-h-[44px] rounded-xl border border-dashed border-cosmic-border bg-cosmic-subtle/50 px-3 py-2 flex items-center gap-2 flex-wrap">
            <button onClick={() => setNarration(null)} className={cn("px-3 py-1.5 rounded-lg text-xs border transition-all", !narration ? "bg-brand/[0.08] text-brand border-brand/25" : "bg-cosmic-surface border-cosmic-border text-text-secondary")}>无</button>
            {audios.length === 0 ? (
              <span className="text-xs text-text-tertiary">暂无音频素材</span>
            ) : audios.map((a) => (
              <button key={a.id} onClick={() => setNarration(a)} className={cn("px-3 py-1.5 rounded-lg text-xs border transition-all max-w-[160px] truncate", narration?.id === a.id ? "bg-brand/[0.08] text-brand border-brand/25" : "bg-cosmic-surface border-cosmic-border text-text-secondary hover:text-text-primary")}>{a.title}</button>
            ))}
            {narration && (
              <span className="ml-auto text-[11px] text-brand truncate max-w-[180px]">当前：{narration.title}</span>
            )}
          </div>
        </div>

        {/* Subtitle track */}
        <div className="pt-3 border-t border-cosmic-border">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-text-secondary">
              <TypeIcon className="w-3.5 h-3.5 text-brand" /> 字幕轨
            </div>
            <button onClick={() => setShowSubtitleTrack((v) => !v)} className="text-[11px] text-text-tertiary hover:text-brand">
              {showSubtitleTrack ? "收起" : "展开"}
            </button>
          </div>
          <AnimatePresence>
            {showSubtitleTrack && (
              <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                <div className="rounded-xl border border-dashed border-cosmic-border bg-cosmic-subtle/50 p-3">
                  <textarea
                    value={subtitleText}
                    onChange={(e) => setSubtitleText(e.target.value)}
                    rows={2}
                    placeholder="输入成片字幕文案（可选，将随 transition 一并提交给 compose）"
                    className="w-full bg-transparent text-sm resize-none focus:outline-none placeholder:text-text-tertiary"
                  />
                  {subtitleText.trim() && (
                    <div className="mt-2 h-8 rounded-lg bg-black/80 text-white text-xs flex items-center justify-center px-3 truncate">
                      {subtitleText.trim()}
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
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
