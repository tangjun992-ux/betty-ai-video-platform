"use client";

import Link from "next/link";
import { Heart, Repeat2, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

/* ═══════════════════════════════════════════════════════
   MediaCard — AURORA 亮色
   探索/Feed 内容卡片 · hover overlay · author chip · stats
   Lovable 风格: 干净克制 · border-first · 品牌紫点缀
   ═══════════════════════════════════════════════════════ */

export interface MediaAuthor {
  name: string;
  handle: string;
  avatar?: string;
}

export interface MediaStats {
  likes?: number;
  remixes?: number;
}

export interface MediaCardProps {
  image: string;
  tag: string;
  title: string;
  description: string;
  to?: string;
  hasExamples?: boolean;
  examplesTo?: string;
  author?: MediaAuthor;
  stats?: MediaStats;
}

function formatCount(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

/* ── Author chip (shown on hover overlay, top-left) ── */
function AuthorChip({ author }: { author: MediaAuthor }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-cosmic-surface/90 backdrop-blur-md border border-cosmic-border/40 shadow-elevation-sm">
      <div className="w-6 h-6 rounded-full bg-gradient-to-br from-brand to-accent-violet flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0 overflow-hidden">
        {author.avatar ? (
          <img src={author.avatar} alt={author.name} className="w-full h-full object-cover" />
        ) : (
          author.name[0]?.toUpperCase() || "U"
        )}
      </div>
      <div className="min-w-0">
        <div className="text-xs font-semibold text-text-primary truncate leading-tight">
          {author.name}
        </div>
        <div className="text-[10px] text-text-tertiary truncate leading-tight">
          @{author.handle}
        </div>
      </div>
    </div>
  );
}

/* ── Stats bar (shown on hover overlay, bottom) ── */
function StatsBar({ stats }: { stats: MediaStats }) {
  return (
    <div className="flex items-center gap-3">
      {stats.likes != null && (
        <div className="flex items-center gap-1 text-text-primary/90 text-xs font-medium">
          <Heart className="w-3.5 h-3.5 fill-current text-brand/80" />
          {formatCount(stats.likes)}
        </div>
      )}
      {stats.remixes != null && (
        <div className="flex items-center gap-1 text-text-primary/90 text-xs font-medium">
          <Repeat2 className="w-3.5 h-3.5 text-text-primary/70" />
          {formatCount(stats.remixes)}
        </div>
      )}
    </div>
  );
}

/* ── Main Component ── */

export function MediaCard({
  image,
  tag,
  title,
  description,
  to,
  hasExamples,
  examplesTo,
  author,
  stats,
}: MediaCardProps) {
  const hasOverlay = !!(author || stats);

  const cardContent = (
    <div
      className={cn(
        "group relative flex flex-col rounded-xl overflow-hidden",
        "bg-cosmic-surface border border-cosmic-border",
        "transition-all duration-300 ease-out-expo",
        "hover:scale-[1.02] hover:shadow-elevation-md hover:border-brand/15",
        to && "cursor-pointer"
      )}
    >
      {/* ── Image area (16:9) ── */}
      <div className="relative aspect-video overflow-hidden bg-cosmic-subtle">
        <img
          src={image}
          alt={title}
          className="w-full h-full object-cover transition-transform duration-500 ease-out-expo group-hover:scale-105"
          loading="lazy"
        />

        {/* ── Hover overlay ── */}
        {hasOverlay && (
          <div className="absolute inset-0 bg-gradient-to-t from-black/55 via-black/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 ease-out-expo">
            {/* Author chip — top-left */}
            {author && (
              <div className="absolute top-3 left-3">
                <AuthorChip author={author} />
              </div>
            )}

            {/* Stats — bottom */}
            {stats && (
              <div className="absolute bottom-3 left-3 right-3 flex items-end justify-between">
                <StatsBar stats={stats} />
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Content below image ── */}
      <div className="flex flex-col gap-2 p-4 flex-1">
        {/* Tag badge */}
        <span className="self-start inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-brand/[0.08] text-brand text-[11px] font-semibold tracking-tight">
          {tag}
        </span>

        {/* Title */}
        <h3 className="text-sm font-semibold text-text-primary leading-snug line-clamp-2">
          {title}
        </h3>

        {/* Description */}
        <p className="text-xs text-text-secondary leading-relaxed line-clamp-2 mt-auto">
          {description}
        </p>

        {/* Author row at bottom (always shown when author exists) */}
        {author && (
          <div className="flex items-center gap-2 pt-1 border-t border-cosmic-border/60">
            <div className="w-5 h-5 rounded-full bg-gradient-to-br from-brand to-accent-violet flex items-center justify-center text-white text-[9px] font-bold flex-shrink-0 overflow-hidden">
              {author.avatar ? (
                <img src={author.avatar} alt={author.name} className="w-full h-full object-cover" />
              ) : (
                author.name[0]?.toUpperCase() || "U"
              )}
            </div>
            <span className="text-[11px] text-text-tertiary truncate">
              @{author.handle}
            </span>
          </div>
        )}

        {/* Examples link */}
        {examplesTo && (
          <Link
            href={examplesTo}
            className="inline-flex items-center gap-1 mt-1 text-[11px] font-medium text-brand/70 hover:text-brand transition-colors group/link"
            onClick={(e) => e.stopPropagation()}
          >
            示例
            <ArrowUpRight className="w-3 h-3 transition-transform group-hover/link:translate-x-0.5 group-hover/link:-translate-y-0.5" />
          </Link>
        )}
      </div>
    </div>
  );

  if (to) {
    return <Link href={to} className="contents">{cardContent}</Link>;
  }

  return cardContent;
}
