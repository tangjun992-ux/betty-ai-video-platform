"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Compass, PackageOpen } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";
import { MediaCard } from "@/components/dashboard/MediaCard";

/* ═══════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════ */

interface GalleryItem {
  id: string;
  task_id: string;
  prompt: string;
  media_type: "image" | "video";
  model_used: string;
  thumbnail?: string;
  thumbnail_url?: string;
  url?: string;
  created_at: string;
  username?: string;
  likes?: number;
}

interface GalleryResponse {
  items: GalleryItem[];
  total?: number;
}

/* ═══════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════ */

function truncatePrompt(p: string, max = 30): string {
  if (p.length <= max) return p;
  return p.slice(0, max) + "…";
}

function typeLabel(t: string): string {
  return t === "video" ? "视频" : "图片";
}

/* ═══════════════════════════════════════════════════════
   Skeleton
   ═══════════════════════════════════════════════════════ */

function SkeletonCard() {
  return (
    <div className="rounded-xl overflow-hidden border border-cosmic-border bg-cosmic-surface animate-pulse">
      <div className="aspect-video bg-cosmic-subtle" />
      <div className="p-4 space-y-2.5">
        <div className="h-3.5 w-10 rounded-full bg-cosmic-subtle" />
        <div className="h-4 w-3/4 rounded bg-cosmic-subtle" />
        <div className="h-3 w-1/2 rounded bg-cosmic-subtle" />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Explore Page
   ═══════════════════════════════════════════════════════ */

export default function ExplorePage() {
  const {
    data,
    isLoading,
    error,
  } = useQuery<GalleryResponse>({
    queryKey: ["explore-gallery"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/gallery?limit=24`);
      if (!res.ok) throw new Error("加载失败");
      return res.json();
    },
    staleTime: 60_000,
  });

  const items = data?.items ?? [];

  /* ── Loading ── */
  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header skeleton */}
        <div className="mb-8">
          <div className="h-8 w-40 rounded-lg bg-cosmic-subtle animate-pulse mb-2" />
          <div className="h-4 w-64 rounded bg-cosmic-subtle animate-pulse" />
        </div>
        {/* Card grid skeleton */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      </div>
    );
  }

  /* ── Error ── */
  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-20 text-center">
        <div className="text-destructive mb-3 text-lg font-semibold">
          加载失败
        </div>
        <div className="text-text-tertiary text-sm">
          {(error as Error).message || "无法获取探索内容"}
        </div>
      </div>
    );
  }

  /* ── Stagger animation config ── */
  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.06,
        delayChildren: 0.1,
      },
    },
  };

  const itemAnim = {
    hidden: { opacity: 0, y: 20 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.4, ease: [0.25, 0.1, 0.25, 1] as const },
    },
  };

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* ═══ Header ═══ */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.25, 0.1, 0.25, 1] as const }}
        className="mb-8"
      >
        <div className="flex items-center gap-3 mb-1">
          <div className="w-9 h-9 rounded-xl bg-brand/10 flex items-center justify-center">
            <Compass className="w-5 h-5 text-brand" />
          </div>
          <h1 className="text-2xl font-semibold text-text-primary">探索</h1>
        </div>
        <p className="text-text-secondary text-sm mt-1">
          发现社区创作的精彩内容
        </p>
      </motion.div>

      {/* ═══ Empty State ═══ */}
      {items.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.35, ease: [0.25, 0.1, 0.25, 1] as const }}
          className="flex flex-col items-center justify-center py-24 text-center"
        >
          <div className="w-16 h-16 rounded-2xl bg-cosmic-subtle border border-cosmic-border flex items-center justify-center mb-4">
            <PackageOpen className="w-8 h-8 text-text-disabled" />
          </div>
          <p className="text-text-tertiary text-sm font-medium">暂无内容</p>
          <p className="text-text-disabled text-xs mt-1">
            还没有社区作品，快来创作第一个吧
          </p>
        </motion.div>
      ) : (
        /* ═══ Gallery Grid ═══ */
        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
        >
          {items.map((item) => (
            <motion.div key={item.id} variants={itemAnim}>
              <MediaCard
                image={item.thumbnail || item.url || "/brand/logo-icon.png"}
                tag={typeLabel(item.media_type)}
                title={truncatePrompt(item.prompt)}
                description={item.model_used || "AI 模型"}
                to={`/tasks/${item.task_id}`}
                stats={item.likes != null ? { likes: item.likes } : undefined}
              />
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
