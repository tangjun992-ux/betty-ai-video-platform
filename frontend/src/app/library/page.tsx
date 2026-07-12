"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Download, Trash2, ImageIcon, Video, Grid3X3, List,
  Upload, Music, X, Link2, Sparkles, CheckCircle2, Clock, HardDrive, Cpu, FolderOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api";
import { Loading, Empty, ErrorState } from "@/components/StatusStates";
import { useToast } from "@/components/Toast";
import { useLocale } from "@/i18n/LocaleProvider";

// ─── Types ──────────────────────────────────────────────
interface LibraryItem {
  id: string;
  source: "upload" | "generated";
  media_type: "image" | "video" | "audio";
  url: string;
  thumbnail: string | null;
  title: string;
  prompt: string | null;
  model: string | null;
  size_bytes: number | null;
  duration: number | null;
  created_at: string;
}

interface LibraryCounts {
  all: number; image: number; video: number; audio: number;
  upload: number; generated: number;
}

const MEDIA_ORIGIN = API_BASE.replace(/\/api\/v1$/, "");
const resolveUrl = (u: string) => (u.startsWith("/") ? `${MEDIA_ORIGIN}${u}` : u);

const TYPE_TABS = [
  { key: "all", label: "全部", icon: FolderOpen },
  { key: "image", label: "图片", icon: ImageIcon },
  { key: "video", label: "视频", icon: Video },
  { key: "audio", label: "音频", icon: Music },
] as const;

const SOURCE_TABS = [
  { key: "all", label: "全部来源" },
  { key: "upload", label: "已上传" },
  { key: "generated", label: "AI 生成" },
] as const;

const ACCEPT = ".jpg,.jpeg,.png,.webp,.gif,.mp4,.webm,.mov,.mp3,.wav,.m4a,.ogg";

function formatBytes(n: number | null): string {
  if (!n) return "—";
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleDateString("zh-CN", { year: "numeric", month: "short", day: "numeric" });
}

function TypeBadge({ type }: { type: LibraryItem["media_type"] }) {
  const Icon = type === "video" ? Video : type === "audio" ? Music : ImageIcon;
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-black/55 backdrop-blur-sm text-white/85">
      <Icon className="w-3 h-3" />
      {type === "video" ? "视频" : type === "audio" ? "音频" : "图片"}
    </span>
  );
}

function Preview({ item, className, controls = false }: { item: LibraryItem; className?: string; controls?: boolean }) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const src = resolveUrl(item.url);

  if (failed) {
    const Icon = item.media_type === "video" ? Video : item.media_type === "audio" ? Music : ImageIcon;
    return (
      <div className={cn(
        "flex flex-col items-center justify-center gap-1.5 bg-gradient-to-br from-cosmic-subtle/80 to-cosmic-surface/60",
        className
      )}>
        <Icon className="w-7 h-7 text-text-secondary/30" />
        <span className="text-[10px] text-text-secondary/60">预览已失效</span>
        {controls && item.prompt && (
          <span className="text-[10px] text-text-secondary/40 px-6 text-center line-clamp-2">原始链接已过期，可点击"做同款"重新生成</span>
        )}
      </div>
    );
  }
  if (item.media_type === "video") {
    return (
      <video
        src={src} className={className} muted={!controls} loop playsInline controls={controls}
        preload="metadata"
        onError={() => setFailed(true)}
        onMouseEnter={(e) => !controls && e.currentTarget.play().catch(() => {})}
        onMouseLeave={(e) => { if (!controls) { e.currentTarget.pause(); e.currentTarget.currentTime = 0; } }}
      />
    );
  }
  if (item.media_type === "audio") {
    return (
      <div className={cn("flex flex-col items-center justify-center gap-2 bg-cosmic-subtle", className)}>
        <Music className="w-8 h-8 text-text-secondary/60" />
        {controls && <audio src={src} controls className="w-full max-w-xs px-4" onError={() => setFailed(true)} />}
      </div>
    );
  }
  return (
    <img
      src={resolveUrl(item.thumbnail || item.url)} alt="" loading="lazy"
      className={cn(className, "transition-opacity duration-300", loaded ? "opacity-100" : "opacity-0")}
      onLoad={() => setLoaded(true)}
      onError={() => setFailed(true)}
    />
  );
}

export default function LibraryPage() {
  const router = useRouter();
  const toast = useToast();
  const { t } = useLocale();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [items, setItems] = useState<LibraryItem[]>([]);
  const [counts, setCounts] = useState<LibraryCounts | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [tab, setTab] = useState<(typeof TYPE_TABS)[number]["key"]>("all");
  const [source, setSource] = useState<(typeof SOURCE_TABS)[number]["key"]>("all");
  const [search, setSearch] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detail, setDetail] = useState<LibraryItem | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const dragDepth = useRef(0);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(search), 300);
    return () => clearTimeout(t);
  }, [search]);

  const fetchLibrary = useCallback(async () => {
    setError(null);
    try {
      const params = new URLSearchParams({ media_type: tab, source, q: debouncedQ, limit: "96" });
      const res = await fetch(`${API_BASE}/library/?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(data.items || []);
      setCounts(data.counts || null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [tab, source, debouncedQ]);

  useEffect(() => { fetchLibrary(); }, [fetchLibrary]);

  // ─── Upload ───────────────────────────────────────────
  const uploadFiles = useCallback(async (files: FileList | File[]) => {
    const list = Array.from(files);
    if (!list.length) return;
    setUploading(true);
    let ok = 0;
    for (const f of list) {
      try {
        const fd = new FormData();
        fd.append("file", f);
        const res = await fetch(`${API_BASE}/library/upload`, { method: "POST", body: fd });
        if (!res.ok) {
          const d = await res.json().catch(() => null);
          toast.error(`上传失败：${f.name}`, d?.detail || `HTTP ${res.status}`);
          continue;
        }
        ok += 1;
      } catch {
        toast.error(`上传失败：${f.name}`, "网络错误，请重试");
      }
    }
    setUploading(false);
    if (ok > 0) {
      toast.success(`已上传 ${ok} 个文件`);
      fetchLibrary();
    }
  }, [fetchLibrary, toast]);

  // Paste-to-upload (Ctrl/Cmd+V with image in clipboard)
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const files = e.clipboardData?.files;
      if (files?.length) {
        e.preventDefault();
        uploadFiles(files);
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [uploadFiles]);

  // ─── Delete ───────────────────────────────────────────
  const deleteItems = useCallback(async (ids: string[]) => {
    if (!ids.length) return;
    if (!window.confirm(`确定删除 ${ids.length} 项内容吗？此操作不可撤销。`)) return;
    let ok = 0;
    for (const id of ids) {
      try {
        const res = await fetch(`${API_BASE}/library/${encodeURIComponent(id)}`, { method: "DELETE" });
        if (res.ok) ok += 1;
      } catch { /* keep going */ }
    }
    if (ok > 0) toast.success(`已删除 ${ok} 项`);
    if (ok < ids.length) toast.error(`${ids.length - ok} 项删除失败`);
    setSelected(new Set());
    setDetail(null);
    fetchLibrary();
  }, [fetchLibrary, toast]);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const copyLink = async (item: LibraryItem) => {
    try {
      await navigator.clipboard.writeText(resolveUrl(item.url));
      toast.success("链接已复制");
    } catch {
      toast.error("复制失败");
    }
  };

  const remix = (item: LibraryItem) => {
    if (!item.prompt) return;
    const target = item.media_type === "video" ? "/create/video" : "/create/image";
    const params = new URLSearchParams({ prompt: item.prompt });
    if (item.model) params.set("model", item.model);
    router.push(`${target}?${params}`);
  };

  const tabCount = (key: string): number => {
    if (!counts) return 0;
    return (counts as unknown as Record<string, number>)[key] ?? 0;
  };

  const selectionMode = selected.size > 0;

  return (
    <div
      className="max-w-7xl mx-auto px-4 py-6 min-h-[70vh]"
      onDragEnter={(e) => { e.preventDefault(); dragDepth.current += 1; setDragOver(true); }}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={(e) => { e.preventDefault(); dragDepth.current -= 1; if (dragDepth.current <= 0) { dragDepth.current = 0; setDragOver(false); } }}
      onDrop={(e) => {
        e.preventDefault(); dragDepth.current = 0; setDragOver(false);
        if (e.dataTransfer.files?.length) uploadFiles(e.dataTransfer.files);
      }}
    >
      {/* Drag overlay */}
      <AnimatePresence>
        {dragOver && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-cosmic-void/80 backdrop-blur-sm flex items-center justify-center pointer-events-none"
          >
            <div className="border-2 border-dashed border-accent-cyan rounded-2xl px-16 py-12 text-center bg-cosmic-surface/60">
              <Upload className="w-10 h-10 text-accent-cyan mx-auto mb-3" />
              <p className="text-lg font-semibold text-text-primary">松开以上传</p>
              <p className="text-sm text-text-secondary mt-1">支持图片、视频、音频</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <input
        ref={fileInputRef} type="file" accept={ACCEPT} multiple className="hidden"
        onChange={(e) => { if (e.target.files?.length) uploadFiles(e.target.files); e.target.value = ""; }}
      />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-display font-bold">{t("library.title")}</h1>
          <p className="text-sm text-text-secondary mt-0.5">
            {t("library.subtitle")} · 共 {tabCount("all")} 项 · 支持拖拽 / Ctrl+V 粘贴上传
          </p>
        </div>
        <div className="flex items-center gap-2">
          {selectionMode ? (
            <>
              <span className="text-sm text-text-secondary mr-1">{selected.size} 项已选</span>
              <button
                onClick={() => deleteItems(Array.from(selected))}
                className="px-3 py-2 rounded-lg bg-red-500/10 text-red-400 text-sm hover:bg-red-500/20 transition-colors flex items-center gap-1.5"
              >
                <Trash2 className="w-3.5 h-3.5" />
                删除所选
              </button>
              <button
                onClick={() => setSelected(new Set())}
                className="px-3 py-2 rounded-lg border border-cosmic-border text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                取消
              </button>
            </>
          ) : (
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="btn-primary disabled:opacity-60"
            >
              <Upload className="w-4 h-4" />
              {uploading ? "上传中..." : t("library.cta")}
            </button>
          )}
        </div>
      </div>

      {/* Type tabs */}
      <div className="flex items-center gap-1 border-b border-cosmic-border mb-4 overflow-x-auto">
        {TYPE_TABS.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={cn(
              "flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors whitespace-nowrap",
              tab === key
                ? "border-accent-cyan text-text-primary"
                : "border-transparent text-text-secondary hover:text-text-primary"
            )}
          >
            <Icon className="w-4 h-4" />
            {label}
            <span className={cn(
              "ml-0.5 px-1.5 py-0.5 rounded-full text-[10px] leading-none",
              tab === key ? "bg-accent-cyan/15 text-accent-cyan" : "bg-cosmic-subtle text-text-secondary"
            )}>
              {tabCount(key)}
            </span>
          </button>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索文件名、Prompt、模型..."
            className="w-full h-10 pl-10 pr-3 rounded-xl bg-cosmic-surface/50 border border-cosmic-border/40 text-sm placeholder:text-text-secondary/50 focus:outline-none focus:ring-2 focus:ring-accent-cyan/10 focus:border-accent-cyan/30"
          />
        </div>
        <div className="flex items-center gap-1.5 bg-cosmic-surface/30 rounded-lg p-1">
          {SOURCE_TABS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setSource(key)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                source === key ? "bg-cosmic-surface text-text-primary" : "text-text-secondary hover:text-text-primary"
              )}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 bg-cosmic-surface/30 rounded-lg p-1 ml-auto">
          <button
            aria-label="网格视图"
            onClick={() => setViewMode("grid")}
            className={cn("p-1.5 rounded-md", viewMode === "grid" ? "bg-cosmic-surface text-text-primary" : "text-text-secondary")}
          >
            <Grid3X3 className="w-4 h-4" />
          </button>
          <button
            aria-label="列表视图"
            onClick={() => setViewMode("list")}
            className={cn("p-1.5 rounded-md", viewMode === "list" ? "bg-cosmic-surface text-text-primary" : "text-text-secondary")}
          >
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* States */}
      {loading && <Loading text="正在加载内容库..." />}
      {!loading && error && (
        <ErrorState title="内容库加载失败" message={`${error}——请确认后端服务已启动`} onRetry={fetchLibrary} />
      )}
      {!loading && !error && items.length === 0 && (
        <Empty
          icon={<FolderOpen className="w-7 h-7 text-text-secondary/60" />}
          title={debouncedQ ? "没有匹配的内容" : "内容库还是空的"}
          description={debouncedQ ? "换个关键词试试" : "上传素材，或去创作页生成你的第一个作品"}
          action={{ label: "去创作", onClick: () => router.push("/create/video") }}
          secondaryAction={{ label: "上传素材", onClick: () => fileInputRef.current?.click() }}
        />
      )}

      {/* Grid View */}
      {!loading && !error && viewMode === "grid" && items.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {items.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: Math.min(i * 0.02, 0.3) }}
              className={cn(
                "group relative rounded-xl overflow-hidden border bg-cosmic-surface/10 cursor-pointer transition-all",
                selected.has(item.id) ? "border-accent-cyan ring-2 ring-accent-cyan/40" : "border-cosmic-border/40 hover:border-cosmic-border"
              )}
              onClick={() => (selectionMode ? toggleSelect(item.id) : setDetail(item))}
            >
              {/* Media area */}
              <div className="relative aspect-square bg-cosmic-subtle/50 overflow-hidden flex items-center justify-center">
                <Preview item={item} className="w-full h-full object-contain" />

                <div className="absolute top-2 left-2 flex items-center gap-1">
                  {item.media_type !== "image" && <TypeBadge type={item.media_type} />}
                  <span className={cn(
                    "px-1.5 py-0.5 rounded text-[10px] backdrop-blur-sm",
                    item.source === "generated" ? "bg-accent-cyan/20 text-accent-cyan" : "bg-black/50 text-white/80"
                  )}>
                    {item.source === "generated" ? "AI 生成" : "上传"}
                  </span>
                </div>

                {/* Select checkbox */}
                <button
                  aria-label="选择"
                  onClick={(e) => { e.stopPropagation(); toggleSelect(item.id); }}
                  className={cn(
                    "absolute top-2 right-2 w-5 h-5 rounded-full border flex items-center justify-center transition-all",
                    selected.has(item.id)
                      ? "bg-accent-cyan border-accent-cyan opacity-100"
                      : "bg-black/40 border-white/40 opacity-0 group-hover:opacity-100"
                  )}
                >
                  {selected.has(item.id) && <CheckCircle2 className="w-3.5 h-3.5 text-cosmic-void" />}
                </button>
              </div>

              {/* Caption */}
              <div className="px-2.5 py-2 border-t border-cosmic-border/30">
                <p className="text-xs text-text-primary truncate leading-snug">{item.title || "未命名"}</p>
                <p className="text-[10px] text-text-secondary/80 truncate mt-0.5">
                  {item.source === "generated" ? (item.model || "AI 生成") : formatBytes(item.size_bytes)}
                  {" · "}{formatDate(item.created_at)}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* List View */}
      {!loading && !error && viewMode === "list" && items.length > 0 && (
        <div className="space-y-1">
          {items.map((item) => (
            <div
              key={item.id}
              className={cn(
                "group flex items-center gap-4 p-3 rounded-xl transition-all cursor-pointer border",
                selected.has(item.id)
                  ? "bg-accent-cyan/[0.04] border-accent-cyan/30"
                  : "hover:bg-cosmic-surface/30 border-transparent"
              )}
              onClick={() => (selectionMode ? toggleSelect(item.id) : setDetail(item))}
            >
              <button
                aria-label="选择"
                onClick={(e) => { e.stopPropagation(); toggleSelect(item.id); }}
                className={cn(
                  "w-4 h-4 rounded border flex-shrink-0 flex items-center justify-center transition-colors",
                  selected.has(item.id) ? "bg-accent-cyan border-accent-cyan" : "border-cosmic-border"
                )}
              >
                {selected.has(item.id) && <CheckCircle2 className="w-3 h-3 text-cosmic-void" />}
              </button>
              <Preview item={item} className="w-12 h-12 rounded-lg object-cover flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm truncate">{item.title}</p>
                <p className="text-xs text-text-secondary truncate">
                  {item.source === "generated" ? `AI 生成 · ${item.model || "—"}` : `上传 · ${formatBytes(item.size_bytes)}`}
                  {" · "}{formatDate(item.created_at)}
                </p>
              </div>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <a
                  href={resolveUrl(item.url)} download target="_blank" rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="p-1.5 rounded-lg hover:bg-cosmic-surface" aria-label="下载"
                >
                  <Download className="w-4 h-4" />
                </a>
                <button
                  onClick={(e) => { e.stopPropagation(); deleteItems([item.id]); }}
                  className="p-1.5 rounded-lg hover:bg-cosmic-surface text-red-400" aria-label="删除"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Detail modal */}
      <AnimatePresence>
        {detail && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
            onClick={() => setDetail(null)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.96, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 12 }}
              className="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl border border-cosmic-border bg-cosmic-surface"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-5 py-3 border-b border-cosmic-border">
                <div className="flex items-center gap-2 min-w-0">
                  <TypeBadge type={detail.media_type} />
                  <h3 className="text-sm font-semibold truncate">{detail.title}</h3>
                </div>
                <button onClick={() => setDetail(null)} className="p-1.5 rounded-lg hover:bg-cosmic-subtle" aria-label="关闭">
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="bg-black/30 flex items-center justify-center">
                <Preview item={detail} controls className="max-h-[50vh] w-auto max-w-full object-contain mx-auto" />
              </div>

              <div className="p-5 space-y-4">
                {detail.prompt && (
                  <div>
                    <p className="text-xs font-medium text-text-secondary mb-1">Prompt</p>
                    <p className="text-sm text-text-primary bg-cosmic-subtle border border-cosmic-border rounded-lg p-3 leading-relaxed">
                      {detail.prompt}
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="flex items-center gap-1.5 text-text-secondary">
                    <Cpu className="w-3.5 h-3.5" />
                    {detail.source === "generated" ? (detail.model || "AI 生成") : "本地上传"}
                  </div>
                  <div className="flex items-center gap-1.5 text-text-secondary">
                    <HardDrive className="w-3.5 h-3.5" />
                    {formatBytes(detail.size_bytes)}
                  </div>
                  <div className="flex items-center gap-1.5 text-text-secondary">
                    <Clock className="w-3.5 h-3.5" />
                    {formatDate(detail.created_at)}
                  </div>
                  <div className="flex items-center gap-1.5 text-text-secondary">
                    {detail.duration ? `${detail.duration}s` : detail.media_type === "image" ? "静态图片" : "—"}
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-2 pt-1">
                  {detail.source === "generated" && detail.prompt && (
                    <button onClick={() => remix(detail)} className="btn-primary">
                      <Sparkles className="w-4 h-4" />
                      做同款
                    </button>
                  )}
                  <a
                    href={resolveUrl(detail.url)} download target="_blank" rel="noreferrer"
                    className="btn-secondary"
                  >
                    <Download className="w-4 h-4" />
                    下载
                  </a>
                  <button onClick={() => copyLink(detail)} className="btn-secondary">
                    <Link2 className="w-4 h-4" />
                    复制链接
                  </button>
                  <button
                    onClick={() => deleteItems([detail.id])}
                    className="ml-auto px-3 py-2 rounded-lg bg-red-500/10 text-red-400 text-sm hover:bg-red-500/20 transition-colors flex items-center gap-1.5"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    删除
                  </button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
