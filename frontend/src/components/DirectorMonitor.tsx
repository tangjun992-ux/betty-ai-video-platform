"use client";

import { Film, ImageIcon, Star } from "lucide-react";
import { cn } from "@/lib/utils";

export type MonitorAsset = {
  final?: boolean;
  type?: string;
  media_url?: string;
  url?: string;
  thumbnail?: string;
  step?: string;
  honesty?: string;
  mode?: string;
};

/** Prefer the finished cut when done; while running, show the latest produced shot. */
export function pickMonitorAsset<T extends MonitorAsset>(assets: T[], phase: string): T | undefined {
  const finalAsset = assets.find((a) => a.final);
  const shots = assets.filter((a) => !a.final && a.type !== "identity_strip");
  if (phase === "done") return finalAsset || shots[shots.length - 1];
  return shots[shots.length - 1] || finalAsset;
}

export function DirectorMonitor({
  phase,
  progressLabel,
  title,
  mediaUrl,
  posterUrl,
  kind = "video",
  honesty,
}: {
  phase: string;
  progressLabel?: string;
  title?: string;
  mediaUrl?: string;
  posterUrl?: string;
  kind?: "video" | "image";
  honesty?: string;
}) {
  const empty = !mediaUrl;
  const Icon = kind === "image" ? ImageIcon : Film;
  const heading = phase === "done" ? "成片" : phase === "running" ? "当前镜" : "监视器";

  return (
    <aside
      data-testid="agent-monitor"
      className="lg:sticky lg:top-24 rounded-2xl border border-cosmic-border/70 bg-black/40 overflow-hidden"
    >
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-cosmic-border/50">
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-text-primary">
          {phase === "done" && <Star className="w-3.5 h-3.5 text-brand" />}
          {heading}
        </span>
        {progressLabel && (
          <span data-testid="agent-monitor-progress" className="text-[11px] text-brand truncate">
            {progressLabel}
          </span>
        )}
      </div>
      <div className="relative aspect-video bg-black flex items-center justify-center">
        {empty ? (
          <div data-testid="agent-monitor-empty" className="flex flex-col items-center px-4 text-center">
            <Icon className="w-8 h-8 text-text-tertiary mb-2" />
            <p className="text-sm text-text-primary">成片将出现在这里</p>
            <p className="text-[11px] text-text-tertiary mt-1">执行后右侧监视当前镜，完成显示成片。</p>
          </div>
        ) : kind === "video" ? (
          <video
            data-testid="agent-monitor-media"
            src={mediaUrl}
            poster={posterUrl}
            controls
            className="w-full h-full object-contain bg-black"
          />
        ) : (
          <img
            data-testid="agent-monitor-media"
            src={mediaUrl}
            alt={title || "当前镜"}
            className="w-full h-full object-contain bg-black"
          />
        )}
      </div>
      {(title || honesty) && (
        <div className="px-3 py-2 border-t border-cosmic-border/40 space-y-0.5">
          {title && <p className="text-xs font-medium text-text-primary truncate">{title}</p>}
          {honesty && <p className="text-[10px] text-amber-600 truncate">{honesty}</p>}
        </div>
      )}
    </aside>
  );
}
