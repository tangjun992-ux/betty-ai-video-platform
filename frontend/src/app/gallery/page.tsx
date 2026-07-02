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

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

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
      if (!resp.ok) throw new Error("加载失败");
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
        <h1 className="text-3xl font-bold mb-2 gradient-text-static">灵感画廊</h1>
        <p className="text-text-secondary">探索社区优质创作，获取灵感</p>
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
            {[{ key: "all", label: "全部风格" } as StyleOption, ...styleOptions.slice(0, 15)].map((s) => (
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
            className="columns-1 sm:columns-2 lg:columns-3 xl:columns-4 gap-4 space-y-4"
          >
            {filtered.map((item) => (
              <div
                key={item.id}
                className="group relative bg-cosmic-surface border border-cosmic-border rounded-2xl overflow-hidden break-inside-avoid hover:border-cosmic-border-hover hover:shadow-card hover:-translate-y-0.5 transition-all duration-300"
                onMouseEnter={() => setHoveredId(item.id)}
                onMouseLeave={() => setHoveredId(null)}
              >
                {/* Media */}
                <div className="relative bg-cosmic-deep overflow-hidden">
                  {item.media_type === "video" ? (
                    <div className="relative">
                      <video
                        src={item.url}
                        className="w-full object-cover"
                        muted loop playsInline
                        autoPlay={hoveredId === item.id}
                        poster={item.thumbnail}
                      />
                      {hoveredId !== item.id && (
                        <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/30 transition-colors">
                          <div className="w-12 h-12 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center group-hover:scale-110 transition-transform">
                            <svg className="w-6 h-6 text-text-accent-cyan ml-1" fill="currentColor" viewBox="0 0 24 24">
                              <path d="M8 5v14l11-7z"/>
                            </svg>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <img
                      src={item.url}
                      alt={item.prompt}
                      className="w-full object-cover group-hover:scale-105 transition-transform duration-500"
                      loading="lazy"
                    />
                  )}

                  {/* Top badges */}
                  <div className="absolute top-3 left-3 flex gap-2">
                    <span className="px-2 py-1 bg-black/60 backdrop-blur-md rounded-full text-[11px] text-white font-medium">
                      {item.model_used}
                    </span>
                  </div>
                  <div className="absolute top-3 right-3">
                    <span className="px-2 py-1 bg-warning-muted backdrop-blur-md rounded-full text-[11px] text-warning border border-warning/20">
                      ⚡ {item.credits_cost}cr
                    </span>
                  </div>
                </div>

                {/* Info */}
                <div className="p-4">
                  <p className="text-sm text-text-accent-cyan/80 line-clamp-2 leading-relaxed mb-2">
                    {item.prompt}
                  </p>

                  {item.styles.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {item.styles.slice(0, 3).map((s) => (
                        <span key={s} className="px-2 py-0.5 rounded-full text-[10px] bg-cosmic-subtle text-text-secondary border border-cosmic-border">
                          {s}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-base">{item.avatar}</span>
                      <span className="text-xs text-text-secondary">{item.username}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-secondary">
                      <span>❤️ {item.likes}</span>
                      <span>👁 {item.views}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => navigator.clipboard.writeText(item.prompt)}
                      className="flex-1 py-1.5 rounded-lg text-xs bg-cosmic-subtle hover:bg-cosmic-border text-text-secondary hover:text-brand transition-all flex items-center justify-center gap-1 border border-cosmic-border hover:border-cosmic-border-hover"
                    >
                      📋 复制 Prompt
                    </button>
                    <a
                      href={(() => {
                        const p = encodeURIComponent(item.prompt || "");
                        const m = encodeURIComponent(item.model_used || "");
                        return item.media_type === "video"
                          ? `/create/video?prompt=${p}&model=${m}`
                          : `/create/image?prompt=${p}&model=${m}`;
                      })()}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand/[0.08] text-brand text-xs font-medium border border-brand/20 hover:bg-brand/[0.15] transition-colors"
                    >
                      🔄 复用创作
                    </a>
                  </div>
                </div>
              </div>
            ))}
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
