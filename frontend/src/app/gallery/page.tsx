"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { Loading, Empty, ErrorState } from "@/components/StatusStates";

// ─── Types ─────────────────────────────────────────────

interface GalleryItem {
  id: string;
  task_id: string;
  prompt: string;
  media_type: "image" | "video";
  model_used: string;
  style: string;
  styles: string[];
  resolution: string;
  duration?: number;
  url: string;
  thumbnail: string;
  credits_cost: number;
  created_at: string;
  username: string;
  avatar: string;
  likes: number;
  views: number;
}

interface StyleOption {
  key: string;
  label: string;
}

import { API_BASE } from "@/lib/api";

// ─── Page ──────────────────────────────────────────────

export default function GalleryPage() {
  const [items, setItems] = useState<GalleryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [style, setStyle] = useState("all");
  const [mediaFilter, setMediaFilter] = useState("all");
  const [sort, setSort] = useState("popular");
  const [stats, setStats] = useState<any>(null);
  const [styleOptions, setStyleOptions] = useState<StyleOption[]>([]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [query, setQuery] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [resFilter, setResFilter] = useState("all");
  const [durFilter, setDurFilter] = useState("all");

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(
        `${API_BASE}/gallery/?style=${style}&media_type=${mediaFilter}&sort=${sort}&limit=36`
      );
      if (!resp.ok) {
        throw new Error(
          resp.status === 404
            ? "接口不存在 (HTTP 404)——后端版本过旧，请重启后端服务"
            : `加载失败 (HTTP ${resp.status})`
        );
      }
      const data = await resp.json();
      setItems(data.items || []);
      if (data.styles) setStyleOptions(data.styles);

      try {
        const statsResp = await fetch(`${API_BASE}/gallery/stats`);
        if (statsResp.ok) setStats(await statsResp.json());
      } catch {}
    } catch (err: any) {
      setError(err.message || "加载画廊失败");
    } finally {
      setLoading(false);
    }
  }, [style, mediaFilter, sort]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  useEffect(() => {
    const onScroll = () => setShowScrollTop(window.scrollY > 600);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // ─── Render ───────────────────────────────────────────

  const kw = query.trim().toLowerCase();
  const matchRes = (it: GalleryItem) =>
    resFilter === "all" ||
    (resFilter === "4k" && /4k|2160|3840/i.test(it.resolution || "")) ||
    (resFilter === "1080p" && /1080|1920/i.test(it.resolution || ""));
  const matchDur = (it: GalleryItem) =>
    durFilter === "all" ||
    (durFilter === "short" && (it.duration || 0) > 0 && (it.duration || 0) <= 5) ||
    (durFilter === "long" && (it.duration || 0) > 5);
  const filtered = items.filter((it) => {
    if (kw && !(
      it.prompt.toLowerCase().includes(kw) ||
      (it.model_used || "").toLowerCase().includes(kw) ||
      (it.styles || []).some((s) => s.toLowerCase().includes(kw))
    )) return false;
    return matchRes(it) && matchDur(it);
  });

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-8"
      >
        <h1 className="text-3xl font-bold mb-2 gradient-text-static">探索</h1>
        <p className="text-text-secondary">发现社区优质创作，一键做同款</p>
        {stats && (
          <div className="flex justify-center gap-6 mt-4 text-sm text-text-secondary">
            <span className="inline-flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-fuchsia" />
              {stats.total_images || 0} 图片
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-violet" />
              {stats.total_videos || 0} 视频
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-accent-cyan" />
              {(stats.total_credits_consumed || 0).toLocaleString()} 积分
            </span>
          </div>
        )}
      </motion.div>

      {/* Filters */}
      <div className="flex flex-col items-center gap-4 mb-8">
        {/* Search */}
        <div className="relative w-full max-w-md">
          <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary/50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z" /></svg>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索案例：prompt、模型或风格..."
            className="w-full h-11 pl-10 pr-4 rounded-full bg-cosmic-subtle border border-cosmic-border text-sm placeholder:text-text-secondary/50 focus:outline-none focus:border-accent-cyan/30 focus:ring-2 focus:ring-accent-cyan/10 transition-all"
          />
        </div>
        {/* Media type */}
        <div className="flex bg-cosmic-subtle rounded-full p-1 border border-cosmic-border">
          {[
            { key: "all", label: "全部" },
            { key: "image", label: "图片" },
            { key: "video", label: "视频" },
          ].map((f) => (
            <button
              key={f.key}
              onClick={() => setMediaFilter(f.key)}
              className={cn(
                "px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200",
                mediaFilter === f.key
                  ? "bg-brand text-white shadow-button-glow"
                  : "text-text-secondary hover:text-text-accent-cyan"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Style chips */}
        {styleOptions.length > 0 && (
          <div className="flex flex-wrap justify-center gap-2">
            {[{ key: "all", label: "全部风格" } as StyleOption, ...styleOptions.filter((s) => s.key !== "all").slice(0, 15)].map((s) => (
              <button
                key={s.key}
                onClick={() => setStyle(s.key)}
                className={cn(
                  "px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200",
                  style === s.key
                    ? "bg-accent-cyan/[0.08] text-accent-cyan border border-accent-cyan/20"
                    : "bg-cosmic-subtle border border-cosmic-border text-text-secondary hover:text-brand hover:border-cosmic-border-hover"
                )}
              >
                {s.label}
              </button>
            ))}
          </div>
        )}

        {/* Sort + All Filters */}
        <div className="flex gap-2 items-center">
          {[
            { key: "popular", label: "最热" },
            { key: "recent", label: "最新" },
            { key: "credits", label: "积分高" },
          ].map((s) => (
            <button
              key={s.key}
              onClick={() => setSort(s.key)}
              className={cn(
                "px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200",
                sort === s.key
                  ? "bg-brand-soft text-brand border border-brand/20"
                  : "bg-cosmic-surface text-text-secondary border border-cosmic-border hover:border-cosmic-border-hover"
              )}
            >
              {s.label}
            </button>
          ))}
          <button
            onClick={() => setShowFilters((v) => !v)}
            className={cn(
              "px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 inline-flex items-center gap-1.5",
              showFilters || resFilter !== "all" || durFilter !== "all"
                ? "bg-accent-cyan/[0.08] text-accent-cyan border border-accent-cyan/20"
                : "bg-cosmic-surface text-text-secondary border border-cosmic-border hover:border-cosmic-border-hover"
            )}
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h18M6 12h12M10 20h4" /></svg>
            全部筛选
          </button>
        </div>

        {/* Advanced filters panel */}
        {showFilters && (
          <div className="flex flex-wrap justify-center gap-4 p-4 rounded-2xl bg-cosmic-surface border border-cosmic-border">
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">分辨率</span>
              {[{ k: "all", l: "全部" }, { k: "1080p", l: "1080p" }, { k: "4k", l: "4K" }].map((o) => (
                <button key={o.k} onClick={() => setResFilter(o.k)}
                  className={cn("px-3 py-1 rounded-full text-xs transition-all", resFilter === o.k ? "bg-accent-cyan/[0.1] text-accent-cyan border border-accent-cyan/20" : "bg-cosmic-subtle text-text-secondary border border-cosmic-border")}>{o.l}</button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">视频时长</span>
              {[{ k: "all", l: "全部" }, { k: "short", l: "≤5s" }, { k: "long", l: ">5s" }].map((o) => (
                <button key={o.k} onClick={() => setDurFilter(o.k)}
                  className={cn("px-3 py-1 rounded-full text-xs transition-all", durFilter === o.k ? "bg-accent-cyan/[0.1] text-accent-cyan border border-accent-cyan/20" : "bg-cosmic-subtle text-text-secondary border border-cosmic-border")}>{o.l}</button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <AnimatePresence mode="wait">
        {loading ? (
          <Loading variant="skeleton" skeletonCount={8} />
        ) : error ? (
          <ErrorState message={error} onRetry={fetchItems} />
        ) : filtered.length === 0 ? (
          <Empty
            title="还没有作品"
            description="快去创作第一个吧！"
            action={{ label: "开始创作", onClick: () => window.location.href = "/create/image" }}
          />
        ) : (
          <motion.div
            key={`${mediaFilter}-${style}-${sort}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="columns-2 md:columns-3 xl:columns-4 2xl:columns-5 gap-3 space-y-3"
          >
            {filtered.map((item) => {
              const remixHref = (() => {
                const p = encodeURIComponent(item.prompt || "");
                const m = encodeURIComponent(item.model_used || "");
                return item.media_type === "video"
                  ? `/create/video?prompt=${p}&model=${m}`
                  : `/create/image?prompt=${p}&model=${m}`;
              })();
              return (
                <div
                  key={item.id}
                  className="group relative rounded-xl overflow-hidden break-inside-avoid bg-cosmic-deep ring-1 ring-cosmic-border hover:ring-brand/40 hover:shadow-card transition-all duration-300"
                  onMouseEnter={() => setHoveredId(item.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  {/* Media — fills the card, yapper-style media-forward layout */}
                  {item.media_type === "video" ? (
                    <video
                      src={item.url}
                      className="w-full object-cover align-middle"
                      muted loop playsInline
                      autoPlay={hoveredId === item.id}
                      poster={item.thumbnail}
                    />
                  ) : (
                    <img
                      src={item.url}
                      alt={item.prompt}
                      className="w-full object-cover align-middle group-hover:scale-[1.03] transition-transform duration-500"
                      loading="lazy"
                    />
                  )}

                  {/* Top badges */}
                  <div className="absolute top-2.5 left-2.5 flex gap-1.5">
                    {item.media_type === "video" && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-black/60 backdrop-blur-md rounded-full text-[10px] text-white font-medium">
                        <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                        视频
                      </span>
                    )}
                    <span className="px-2 py-0.5 bg-black/55 backdrop-blur-md rounded-full text-[10px] text-white/90 font-medium">
                      {item.model_used}
                    </span>
                  </div>
                  <div className="absolute top-2.5 right-2.5">
                    <span className="px-2 py-0.5 bg-black/55 backdrop-blur-md rounded-full text-[10px] text-warning font-medium">
                      ⚡{item.credits_cost}
                    </span>
                  </div>

                  {/* Hover overlay — prompt + actions rise from the bottom */}
                  <div className="absolute inset-0 flex flex-col justify-end opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-gradient-to-t from-black/85 via-black/25 to-transparent pointer-events-none">
                    <div className="p-3 pointer-events-auto">
                      <p className="text-[13px] text-white/95 line-clamp-2 leading-snug mb-2.5">
                        {item.prompt}
                      </p>
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2.5 text-[11px] text-white/70">
                          <span className="inline-flex items-center gap-1">❤️ {item.likes}</span>
                          <span className="inline-flex items-center gap-1">👁 {item.views}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => navigator.clipboard.writeText(item.prompt)}
                            title="复制 Prompt"
                            className="w-7 h-7 rounded-lg bg-white/15 hover:bg-white/25 backdrop-blur-md flex items-center justify-center text-white transition-colors"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                          </button>
                          <a
                            href={remixHref}
                            className="inline-flex items-center gap-1 px-2.5 h-7 rounded-lg bg-white text-black text-[11px] font-semibold hover:bg-white/90 transition-colors"
                          >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                            做同款
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>

      {/* CTA */}
      {!loading && !error && items.length > 0 && (
        <div className="text-center mt-12">
          <a href="/create/image" className="btn-primary">
            ✨ 开始创作你自己的作品
          </a>
        </div>
      )}

      {/* Scroll to top */}
      {showScrollTop && (
        <button
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          className="fixed bottom-8 right-8 w-10 h-10 rounded-full bg-cosmic-surface border border-cosmic-border shadow-elevation-md backdrop-blur-xl flex items-center justify-center hover:bg-cosmic-subtle transition-all z-40"
          aria-label="返回顶部"
        >
          <svg className="w-5 h-5 text-text-accent-cyan" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
          </svg>
        </button>
      )}
    </main>
  );
}
