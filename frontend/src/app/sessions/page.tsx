"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  PlayCircle,
  Clock,
  Bot,
  Image,
  Video,
  Music,
  ChevronRight,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api";

/* ═══════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════ */

interface SessionAsset {
  step: string;
  model: string;
  type?: string;
  media_url?: string;
  dry_run?: boolean;
}

interface DirectorSession {
  session_uid: string;
  title: string;
  brief: string;
  intent: string;
  status: string;
  created_at: string;
  assets: SessionAsset[];
}

/* ═══════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════ */

const intentLabel: Record<string, string> = {
  image: "图像",
  image_series: "系列图",
  video_from_text: "文生视频",
  video_from_image: "图生视频",
  campaign: "营销宣传片",
  talking: "数字人口播",
  audio: "音频",
  video: "视频",
};

const intentIcon = (intent: string) => {
  if (intent.includes("video")) return Video;
  if (intent.includes("image")) return Image;
  if (intent.includes("audio") || intent === "talking") return Music;
  return PlayCircle;
};

function relativeTime(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  const diff = now - then;
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const weeks = Math.floor(days / 7);

  if (seconds < 60) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  if (hours < 24) return `${hours} 小时前`;
  if (days < 7) return `${days} 天前`;
  if (weeks < 4) return `${weeks} 周前`;
  return new Date(iso).toLocaleDateString("zh-CN", {
    month: "short",
    day: "numeric",
  });
}

/* ═══════════════════════════════════════════════════════
   Status Badge
   ═══════════════════════════════════════════════════════ */

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
    completed: {
      label: "已完成",
      className: "bg-success/10 text-success border-success/20",
    },
    done: {
      label: "已完成",
      className: "bg-success/10 text-success border-success/20",
    },
    running: {
      label: "运行中",
      className: "bg-info/10 text-info border-info/20",
    },
    planned: {
      label: "已规划",
      className: "bg-info/10 text-info border-info/20",
    },
    failed: {
      label: "失败",
      className: "bg-destructive/10 text-destructive border-destructive/20",
    },
  };

  const c = config[status] || {
    label: status,
    className: "bg-cosmic-subtle text-text-tertiary border-cosmic-border",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border",
        c.className
      )}
    >
      {status === "running" && (
        <span className="w-1.5 h-1.5 rounded-full bg-info animate-pulse" />
      )}
      {status === "completed" || status === "done" ? (
        <span className="w-1.5 h-1.5 rounded-full bg-success" />
      ) : null}
      {status === "failed" && (
        <span className="w-1.5 h-1.5 rounded-full bg-destructive" />
      )}
      {c.label}
    </span>
  );
}

/* ═══════════════════════════════════════════════════════
   Skeleton
   ═══════════════════════════════════════════════════════ */

function SessionSkeleton() {
  return (
    <div className="animate-pulse rounded-2xl border border-cosmic-border bg-cosmic-surface p-5">
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-cosmic-subtle" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-48 rounded-md bg-cosmic-subtle" />
          <div className="h-3 w-64 rounded-md bg-cosmic-subtle" />
        </div>
        <div className="w-16 h-5 rounded-full bg-cosmic-subtle" />
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════
   Sessions Page
   ═══════════════════════════════════════════════════════ */

export default function SessionsPage() {
  const router = useRouter();

  const {
    data: sessions,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<DirectorSession[]>({
    queryKey: ["director-sessions"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/director/sessions`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      // Handle both { sessions: [...] } and [...] response shapes
      const arr = Array.isArray(json) ? json : json.sessions ?? [];
      return arr;
    },
    staleTime: 30_000,
    retry: 2,
  });

  const hasSessions = sessions && sessions.length > 0;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 md:py-12">
      {/* ═══ Header ═══ */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand/10 text-brand text-xs font-medium mb-3">
          <Bot className="w-3.5 h-3.5" /> DIRECTOR AGENT
        </div>
        <h1 className="text-2xl font-semibold text-text-primary mb-1">
          创作会话
        </h1>
        <p className="text-sm text-text-secondary">
          Director Agent 创作历史
        </p>
      </motion.div>

      {/* ═══ Loading ═══ */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <SessionSkeleton key={i} />
          ))}
        </div>
      )}

      {/* ═══ Error ═══ */}
      {isError && !isLoading && (
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          className="rounded-2xl border border-destructive/20 bg-destructive/5 p-8 text-center"
        >
          <AlertCircle className="w-10 h-10 text-destructive/60 mx-auto mb-3" />
          <div className="text-text-primary font-medium mb-1">
            加载失败
          </div>
          <div className="text-text-tertiary text-sm mb-4">
            {error instanceof Error ? error.message : "无法获取会话列表"}
          </div>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-cosmic-surface border border-cosmic-border text-sm font-medium text-text-secondary hover:text-text-primary hover:border-cosmic-border-hover transition-all"
          >
            <RefreshCw className="w-4 h-4" />
            重试
          </button>
        </motion.div>
      )}

      {/* ═══ Empty ═══ */}
      {!isLoading && !isError && !hasSessions && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-12 text-center"
        >
          <Bot className="w-12 h-12 text-text-disabled mx-auto mb-4" />
          <div className="text-text-primary font-medium mb-1">
            暂无会话
          </div>
          <div className="text-text-tertiary text-sm">
            前往 Director Agent 开始你的第一个创作吧
          </div>
        </motion.div>
      )}

      {/* ═══ Session List ═══ */}
      {hasSessions && (
        <div className="space-y-3">
          {sessions.map((session, i) => {
            const Icon = intentIcon(session.intent);
            const label = intentLabel[session.intent] || session.intent || "会话";
            const displayTitle =
              session.title || (session.brief ? session.brief.slice(0, 40) : "未命名会话");
            const assetCount = Array.isArray(session.assets)
              ? session.assets.length
              : 0;

            return (
              <motion.button
                key={session.session_uid}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                onClick={() =>
                  router.push(`/agent?session=${session.session_uid}`)
                }
                className={cn(
                  "w-full text-left rounded-2xl border border-cosmic-border bg-cosmic-surface p-5",
                  "hover:border-brand/25 hover:shadow-md transition-all",
                  "active:scale-[0.99] cursor-pointer group"
                )}
              >
                <div className="flex items-center gap-4">
                  {/* Icon */}
                  <div className="w-10 h-10 rounded-xl bg-brand/8 flex items-center justify-center flex-shrink-0 text-brand">
                    <Icon className="w-5 h-5" />
                  </div>

                  {/* Main content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <h3 className="text-sm font-semibold text-text-primary truncate">
                        {displayTitle}
                      </h3>
                      <StatusBadge status={session.status} />
                    </div>
                    <div className="flex items-center gap-3 text-xs text-text-tertiary">
                      <span className="inline-flex items-center gap-1">
                        <PlayCircle className="w-3 h-3" />
                        {label}
                      </span>
                      <span className="inline-flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {relativeTime(session.created_at)}
                      </span>
                      <span>
                        {assetCount > 0 ? `${assetCount} 个资产` : "无资产"}
                      </span>
                    </div>
                  </div>

                  {/* Chevron */}
                  <ChevronRight className="w-4 h-4 text-text-disabled group-hover:text-brand transition-colors flex-shrink-0" />
                  <button
                    type="button"
                    title="复制深链"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigator.clipboard.writeText(`${window.location.origin}/agent?session=${session.session_uid}`);
                    }}
                    className="opacity-0 group-hover:opacity-100 text-[10px] px-2 py-1 rounded-md border border-cosmic-border text-text-tertiary hover:text-brand transition-all flex-shrink-0"
                  >
                    复制链接
                  </button>
                </div>
              </motion.button>
            );
          })}
        </div>
      )}
    </div>
  );
}
