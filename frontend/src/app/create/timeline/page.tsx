"use client";

import { Suspense, useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus, Trash2, ChevronLeft, ChevronRight, Film, Loader2,
  Sparkles, Download, Music, ImageIcon, Video as VideoIcon, Type as TypeIcon,
  Save, FolderOpen,
} from "lucide-react";
import {
  listLibrary,
  composeTimeline,
  listTimelineProjects,
  getTimelineProject,
  saveTimelineProject,
  API_BASE,
  type TimelineProject,
} from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

interface LibItem { id: string; url: string; thumbnail?: string | null; title: string; media_type: string; }
interface Clip {
  key: string;
  url: string;
  thumbnail?: string | null;
  title: string;
  start: number;
  end: number;
  volume: number;
}

type Transition = "cut" | "fade" | "dissolve";
type ExportPreset = "landscape_16_9" | "portrait_9_16" | "square_1_1";

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

const EXPORT_PRESETS: { id: ExportPreset; label: string; hint: string }[] = [
  { id: "landscape_16_9", label: "横屏 16:9", hint: "YouTube / B站" },
  { id: "portrait_9_16", label: "竖屏 9:16", hint: "抖音 / Reels" },
  { id: "square_1_1", label: "方屏 1:1", hint: "小红书 / 信息流" },
];

function clipFromUrl(
  url: string,
  lib: LibItem[],
  idx: number,
  label?: string,
  saved?: { start?: number; end?: number; volume?: number },
): Clip {
  const hit = lib.find((v) => v.url === url);
  return {
    key: `clip-${idx}-${url.slice(-12)}`,
    url,
    thumbnail: hit?.thumbnail,
    title: label || hit?.title || `片段 ${idx + 1}`,
    start: saved?.start ?? 0,
    end: saved?.end ?? 5,
    volume: saved?.volume ?? 1,
  };
}

function TimelineEditorContent() {
  const toast = useToast();
  const router = useRouter();
  const searchParams = useSearchParams();
  const deepLinkProject = searchParams.get("project");

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
  const [exportPreset, setExportPreset] = useState<ExportPreset>("landscape_16_9");
  const [selectedClipKey, setSelectedClipKey] = useState<string | null>(null);

  const [projects, setProjects] = useState<TimelineProject[]>([]);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [projectName, setProjectName] = useState("未命名项目");
  const [saving, setSaving] = useState(false);
  const [loadingProject, setLoadingProject] = useState(false);
  const loadedProjectRef = useRef<string | null>(null);

  const applyProject = useCallback((
    proj: TimelineProject,
    libVideos: LibItem[],
    libAudios: LibItem[],
  ) => {
    const settings = proj.settings || {};
    const tr = (settings.transition as Transition) || "fade";
    setProjectId(proj.id);
    setProjectName(proj.name || "未命名项目");
    setTransition(tr);
    setWithAudio(settings.with_audio ?? true);
    setExportPreset((settings.export_preset as ExportPreset) || "landscape_16_9");
    setTrack(
      (proj.clips || []).map((c, i) =>
        clipFromUrl(c.url, libVideos, i, c.label || undefined, {
          start: c.start,
          end: c.end,
          volume: (c as { volume?: number }).volume,
        }),
      ),
    );
    const narrUrl = settings.narration_url;
    setNarration(narrUrl ? libAudios.find((a) => a.url === narrUrl) || null : null);
    const subs = settings.subtitle_track;
    setSubtitleText(subs?.[0]?.text?.trim() || "");
    setResult(null);
  }, []);

  const refreshProjects = useCallback(async () => {
    try {
      const { projects: list } = await listTimelineProjects();
      setProjects(list || []);
    } catch {
      /* non-fatal */
    }
  }, []);

  const loadProjectById = useCallback(async (
    id: string,
    libVideos: LibItem[],
    libAudios: LibItem[],
    pushUrl = true,
  ) => {
    if (loadedProjectRef.current === id) return;
    setLoadingProject(true);
    try {
      const proj = await getTimelineProject(id);
      applyProject(proj, libVideos, libAudios);
      loadedProjectRef.current = id;
      if (pushUrl) {
        router.replace(`/create/timeline?project=${encodeURIComponent(id)}`, { scroll: false });
      }
    } catch (e: any) {
      toast.error("加载项目失败", e.message || "");
    } finally {
      setLoadingProject(false);
    }
  }, [applyProject, router, toast]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const [v, a] = await Promise.all([
          listLibrary({ media_type: "video", limit: 60 }),
          listLibrary({ media_type: "audio", limit: 30 }),
        ]);
        if (cancelled) return;
        const vItems = (v.items || []).filter((i: LibItem) => i.url);
        const aItems = (a.items || []).filter((i: LibItem) => i.url);
        setVideos(vItems);
        setAudios(aItems);
        await refreshProjects();
        if (deepLinkProject) {
          await loadProjectById(deepLinkProject, vItems, aItems, false);
        }
      } catch (e: any) {
        if (!cancelled) toast.error("加载素材库失败", e.message || "");
      } finally {
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [deepLinkProject, loadProjectById, refreshProjects, toast]);

  useEffect(() => {
    if (!deepLinkProject || loading || loadedProjectRef.current === deepLinkProject) return;
    loadProjectById(deepLinkProject, videos, audios, false);
  }, [deepLinkProject, loading, videos, audios, loadProjectById]);

  useEffect(() => {
    if (track.length === 0) {
      setSelectedClipKey(null);
      return;
    }
    if (!selectedClipKey || !track.some((c) => c.key === selectedClipKey)) {
      setSelectedClipKey(track[0].key);
    }
  }, [track, selectedClipKey]);

  const addClip = useCallback((item: LibItem) => {
    setTrack((t) => [...t, {
      key: `${item.id}-${Date.now()}`,
      url: item.url,
      thumbnail: item.thumbnail,
      title: item.title,
      start: 0,
      end: 5,
      volume: 1,
    }]);
    setResult(null);
  }, []);

  const updateClip = useCallback((key: string, patch: Partial<Pick<Clip, "start" | "end" | "volume">>) => {
    setTrack((t) => t.map((c) => (c.key === key ? { ...c, ...patch } : c)));
    setResult(null);
  }, []);

  const trackDuration = useCallback(
    () => track.reduce((sum, c) => sum + Math.max(0.5, c.end - c.start), 0),
    [track],
  );
  const removeClip = (key: string) => {
    setTrack((t) => t.filter((c) => c.key !== key));
    setSelectedClipKey((k) => (k === key ? null : k));
    setResult(null);
  };
  const move = (idx: number, dir: -1 | 1) => {
    setTrack((t) => {
      const n = [...t]; const j = idx + dir;
      if (j < 0 || j >= n.length) return t;
      [n[idx], n[j]] = [n[j], n[idx]];
      return n;
    });
    setResult(null);
  };

  const buildSubtitleTrack = () => {
    if (!subtitleText.trim()) return [];
    return [{ text: subtitleText.trim(), start: 0, end: Math.max(trackDuration(), 5) }];
  };

  const buildSavePayload = () => ({
    id: projectId || undefined,
    name: projectName.trim() || "未命名项目",
    clips: track.map((c) => ({
      url: c.url,
      start: c.start,
      end: c.end,
      volume: c.volume,
      transition,
      label: c.title,
    })),
    settings: {
      narration_url: narration?.url ?? null,
      with_audio: withAudio,
      transition,
      export_preset: exportPreset,
      subtitle_track: buildSubtitleTrack(),
    },
  });

  const saveProject = async () => {
    if (track.length < 1) {
      toast.error("无法保存", "请至少添加一个视频片段");
      return;
    }
    setSaving(true);
    try {
      const saved = await saveTimelineProject(buildSavePayload());
      const id = saved.id;
      setProjectId(id);
      loadedProjectRef.current = id;
      await refreshProjects();
      router.replace(`/create/timeline?project=${encodeURIComponent(id)}`, { scroll: false });
      toast.success("项目已保存", `${saved.name || projectName} · ${saved.clip_count ?? track.length} 镜`);
    } catch (e: any) {
      toast.error("保存失败", e.message || "请稍后重试");
    } finally {
      setSaving(false);
    }
  };

  const compose = async () => {
    if (track.length < 1) { toast.error("请先添加片段", "从下方素材库添加视频到时间线"); return; }
    setComposing(true);
    setResult(null);
    try {
      const subtitle_track = buildSubtitleTrack();
      const res = await composeTimeline(
        track.map((c) => ({
          url: c.url,
          start: c.start,
          end: c.end,
          volume: c.volume,
          transition,
        })),
        {
          with_audio: withAudio,
          narration_url: narration?.url,
          transition,
          subtitle_track,
          export_preset: exportPreset,
        },
      );
      setResult({ url: resolveMedia(res.url), thumbnail: resolveMedia(res.thumbnail) });
      const presetLabel = EXPORT_PRESETS.find((p) => p.id === exportPreset)?.label || exportPreset;
      toast.success("合成完成", `${res.clip_count} 个片段 · ${presetLabel}${subtitle_track.length ? " · 已烧录字幕" : ""}`);
    } catch (e: any) {
      toast.error("合成失败", e.message || "请稍后重试");
    } finally {
      setComposing(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8" data-testid="timeline-page">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3 mb-6">
        <span className="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-brand-soft border border-cosmic-border text-brand">
          <Film className="w-5 h-5" />
        </span>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl font-display font-bold">时间线编辑器</h1>
          <p className="text-text-secondary text-sm">多轨编排 · 项目持久化 · 字幕烧录合成</p>
        </div>
      </motion.div>

      {/* Project bar */}
      <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-4 mb-5 flex flex-wrap items-center gap-3" data-testid="timeline-project-bar">
        <div className="flex items-center gap-2 flex-1 min-w-[200px]">
          <FolderOpen className="w-4 h-4 text-brand shrink-0" />
          <input
            data-testid="timeline-project-name"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            className="flex-1 min-w-0 bg-cosmic-subtle border border-cosmic-border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-brand/40"
            placeholder="项目名称"
          />
        </div>
        <select
          data-testid="timeline-project-select"
          value={projectId || ""}
          onChange={(e) => {
            const id = e.target.value;
            if (id) {
              loadedProjectRef.current = null;
              loadProjectById(id, videos, audios);
            } else {
              loadedProjectRef.current = null;
              setProjectId(null);
              setProjectName("未命名项目");
              router.replace("/create/timeline", { scroll: false });
            }
          }}
          disabled={loadingProject}
          className="bg-cosmic-subtle border border-cosmic-border rounded-lg px-3 py-1.5 text-sm min-w-[160px] max-w-[220px]"
        >
          <option value="">新建项目…</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name} ({p.clips?.length ?? 0}镜)</option>
          ))}
        </select>
        <button
          data-testid="timeline-save-project"
          onClick={saveProject}
          disabled={saving || track.length < 1}
          className="btn-secondary h-9 px-4 text-sm"
        >
          {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          保存项目
        </button>
        {loadingProject && (
          <span className="text-xs text-text-tertiary flex items-center gap-1">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> 加载项目…
          </span>
        )}
      </div>

      {/* Preview / result */}
      <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface overflow-hidden mb-5">
        <div className="aspect-video bg-black flex items-center justify-center" data-testid="timeline-preview">
          {composing ? (
            <div className="text-center text-white/80"><Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />正在合成成片…</div>
          ) : result ? (
            <video data-testid="timeline-result-video" src={result.url} poster={result.thumbnail} controls autoPlay className="w-full h-full object-contain" />
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

      {/* Export preset — social platforms */}
      <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-4 mb-5" data-testid="timeline-export-preset">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <span className="text-sm font-semibold text-text-primary">导出画幅 · 社交预设</span>
          <div className="flex gap-2 flex-wrap">
            {EXPORT_PRESETS.map((p) => (
              <button
                key={p.id}
                type="button"
                data-testid={`timeline-preset-${p.id}`}
                onClick={() => { setExportPreset(p.id); setResult(null); }}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-medium border transition-all text-left",
                  exportPreset === p.id
                    ? "bg-brand/10 text-brand border-brand/30"
                    : "bg-cosmic-subtle border-cosmic-border text-text-secondary hover:text-text-primary",
                )}
              >
                <span className="block">{p.label}</span>
                <span className="block text-[10px] opacity-70">{p.hint}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Transition selector */}
      <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-4 mb-5">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
          <span className="text-sm font-semibold text-text-primary">转场 Transition</span>
          <div className="flex gap-2" data-testid="timeline-transitions">
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
              <button data-testid="timeline-compose" onClick={compose} disabled={composing || track.length < 1} className="btn-primary h-9 px-4 text-sm">
                {composing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} 合成成片
              </button>
            </div>
          </div>
          {track.length === 0 ? (
            <div data-testid="timeline-empty-track" className="h-24 rounded-xl border border-dashed border-cosmic-border flex items-center justify-center text-sm text-text-tertiary">
              从下方素材库点击视频，加入时间线
            </div>
          ) : (
            <div className="flex gap-2 overflow-x-auto pb-2" data-testid="timeline-track">
              {track.map((c, i) => (
                <div
                  key={c.key}
                  className={cn(
                    "relative flex-shrink-0 w-40 group cursor-pointer rounded-lg",
                    selectedClipKey === c.key && "ring-2 ring-brand/50",
                  )}
                  data-testid="timeline-clip"
                  onClick={() => setSelectedClipKey(c.key)}
                >
                  <div className="aspect-video rounded-lg overflow-hidden ring-1 ring-cosmic-border bg-black">
                    {c.thumbnail ? <img src={resolveMedia(c.thumbnail)} alt="" className="w-full h-full object-cover" />
                      : <video src={resolveMedia(c.url)} muted className="w-full h-full object-cover" />}
                  </div>
                  <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded bg-black/60 text-[10px] text-white font-semibold">#{i + 1}</div>
                  <div className="absolute top-1 right-1 px-1 py-0.5 rounded bg-black/60 text-[9px] text-white">
                    {c.start.toFixed(1)}–{c.end.toFixed(1)}s
                  </div>
                  {i < track.length - 1 && (
                    <div className="absolute -right-1 top-1/2 -translate-y-1/2 z-10 px-1 py-0.5 rounded bg-brand text-[9px] text-white font-medium">
                      {transition}
                    </div>
                  )}
                  <div className="absolute inset-x-0 bottom-1 flex items-center justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button type="button" onClick={(e) => { e.stopPropagation(); move(i, -1); }} disabled={i === 0} className="w-6 h-6 rounded bg-black/70 text-white flex items-center justify-center disabled:opacity-30"><ChevronLeft className="w-3.5 h-3.5" /></button>
                    <button type="button" onClick={(e) => { e.stopPropagation(); removeClip(c.key); }} className="w-6 h-6 rounded bg-black/70 text-white hover:bg-red-500 flex items-center justify-center"><Trash2 className="w-3.5 h-3.5" /></button>
                    <button type="button" onClick={(e) => { e.stopPropagation(); move(i, 1); }} disabled={i === track.length - 1} className="w-6 h-6 rounded bg-black/70 text-white flex items-center justify-center disabled:opacity-30"><ChevronRight className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {track.length > 0 && selectedClipKey && (() => {
            const clip = track.find((c) => c.key === selectedClipKey);
            if (!clip) return null;
            const idx = track.findIndex((c) => c.key === selectedClipKey);
            return (
              <div className="mt-3 p-3 rounded-xl border border-cosmic-border bg-cosmic-subtle/40" data-testid="timeline-clip-trim">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-text-secondary">片段 #{idx + 1} · 入出点 & 音量</span>
                  <span className="text-[11px] text-text-tertiary">{clip.title}</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <label className="text-xs text-text-secondary">
                    入点 In ({clip.start.toFixed(1)}s)
                    <input
                      type="range"
                      min={0}
                      max={Math.max(0, clip.end - 0.5)}
                      step={0.1}
                      value={clip.start}
                      data-testid="timeline-clip-in"
                      onChange={(e) => updateClip(clip.key, { start: Math.min(+e.target.value, clip.end - 0.5) })}
                      className="w-full accent-brand mt-1"
                    />
                  </label>
                  <label className="text-xs text-text-secondary">
                    出点 Out ({clip.end.toFixed(1)}s)
                    <input
                      type="range"
                      min={clip.start + 0.5}
                      max={15}
                      step={0.1}
                      value={clip.end}
                      data-testid="timeline-clip-out"
                      onChange={(e) => updateClip(clip.key, { end: Math.max(+e.target.value, clip.start + 0.5) })}
                      className="w-full accent-brand mt-1"
                    />
                  </label>
                  <label className="text-xs text-text-secondary">
                    音量 ({Math.round(clip.volume * 100)}%)
                    <input
                      type="range"
                      min={0}
                      max={2}
                      step={0.05}
                      value={clip.volume}
                      data-testid="timeline-clip-volume"
                      onChange={(e) => updateClip(clip.key, { volume: +e.target.value })}
                      className="w-full accent-brand mt-1"
                    />
                  </label>
                </div>
              </div>
            );
          })()}
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
                    data-testid="timeline-subtitle-input"
                    value={subtitleText}
                    onChange={(e) => setSubtitleText(e.target.value)}
                    rows={2}
                    placeholder="输入成片字幕文案（合成时将烧录进视频）"
                    className="w-full bg-transparent text-sm resize-none focus:outline-none placeholder:text-text-tertiary"
                  />
                  {subtitleText.trim() && (
                    <div className="mt-2 h-8 rounded-lg bg-black/80 text-white text-xs flex items-center justify-center px-3 truncate" data-testid="timeline-subtitle-preview">
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
          <div data-testid="timeline-library-empty" className="h-28 rounded-xl border border-dashed border-cosmic-border flex flex-col items-center justify-center text-sm text-text-tertiary gap-2">
            <ImageIcon className="w-6 h-6" />
            素材库暂无视频。先去 <a href="/create/video" className="text-brand underline">视频创作</a> 或 <a href="/agent" className="text-brand underline">Agent</a> 生成一些片段。
          </div>
        ) : (
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-3" data-testid="timeline-library-grid">
            {videos.map((v) => (
              <button key={v.id} data-testid="timeline-library-item" onClick={() => addClip(v)} title={v.title}
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

export default function TimelinePage() {
  return (
    <Suspense fallback={
      <div className="max-w-6xl mx-auto px-4 py-16 text-center text-text-secondary">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3 text-brand" />
        加载时间线编辑器…
      </div>
    }>
      <TimelineEditorContent />
    </Suspense>
  );
}
