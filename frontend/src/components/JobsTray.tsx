"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  ListTodo,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronRight,
} from "lucide-react";
import { API_BASE } from "@/lib/api";
import { useAuthStore } from "@/lib/stores";
import { cn, truncate } from "@/lib/utils";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";

/* ═══════════════════════════════════════════════════════
   JobsTray — AURORA 亮色主题实时作业队列面板
   ═══════════════════════════════════════════════════════ */

// ─── Types ────────────────────────────────────────────────

export type TaskStatus = "queued" | "running" | "succeeded" | "failed";

export interface TaskItem {
  task_id: string;
  prompt: string;
  media_type: "image" | "video";
  status: TaskStatus;
  model: string;
  results: string | null;
  created_at: string;
}

// Parse Python-stringified results list to get URL
function parseTaskUrl(results: string | null): string | null {
  if (!results) return null;
  try {
    const m = results.match(/'url':\s*'([^']+)'/);
    if (m) return m[1];
  } catch {}
  return null;
}

interface TasksResponse {
  tasks: TaskItem[];
}

// ─── Status config ─────────────────────────────────────────

const STATUS_CONFIG: Record<
  TaskStatus,
  {
    icon: typeof Clock;
    iconColor: string;
    badgeColor: string;
    badgeBg: string;
    label: string;
  }
> = {
  queued: {
    icon: Clock,
    iconColor: "text-amber-500",
    badgeColor: "text-amber-700",
    badgeBg: "bg-amber-100",
    label: "排队中",
  },
  running: {
    icon: Loader2,
    iconColor: "text-sky-500",
    badgeColor: "text-sky-700",
    badgeBg: "bg-sky-100",
    label: "运行中",
  },
  succeeded: {
    icon: CheckCircle2,
    iconColor: "text-emerald-500",
    badgeColor: "text-emerald-700",
    badgeBg: "bg-emerald-100",
    label: "已完成",
  },
  failed: {
    icon: XCircle,
    iconColor: "text-red-500",
    badgeColor: "text-red-700",
    badgeBg: "bg-red-100",
    label: "失败",
  },
};

const MEDIA_TYPE_LABELS: Record<string, string> = {
  image: "图片",
  video: "视频",
};

// ─── Helpers ───────────────────────────────────────────────

function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSec = Math.floor((now - then) / 1000);

  if (diffSec < 60) return "刚刚";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} 分钟前`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} 小时前`;
  return `${Math.floor(diffSec / 86400)} 天前`;
}

function hasActiveTasks(tasks: TaskItem[]): boolean {
  return tasks.some((t) => t.status === "queued" || t.status === "running");
}

// ─── Fetch wrapper ─────────────────────────────────────────

async function fetchTasks(token: string | null): Promise<TasksResponse> {
  const params = new URLSearchParams({ limit: "20" });
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}/tasks?${params}`, { headers });
  if (!res.ok) throw new Error(`获取任务列表失败: ${res.status}`);
  return res.json();
}

// ─── Component ─────────────────────────────────────────────

export function JobsTray() {
  const token = useAuthStore((s) => s.token);

  const {
    data,
    isLoading,
    isError,
  } = useQuery<TasksResponse>({
    queryKey: ["jobs-tray", token],
    queryFn: () => fetchTasks(token),
    refetchInterval: (query) => {
      const tasks = query.state.data?.tasks ?? [];
      return hasActiveTasks(tasks) ? 5_000 : false;
    },
    staleTime: 4_000,
    retry: 2,
  });

  const tasks = data?.tasks ?? [];
  const activeCount = useMemo(
    () => tasks.filter((t) => t.status === "queued" || t.status === "running").length,
    [tasks]
  );

  // ── Status icon + badge for trigger button ──
  const TriggerIcon = activeCount > 0 ? Loader2 : ListTodo;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className={cn(
            "relative inline-flex items-center justify-center w-9 h-9 rounded-lg",
            "text-text-tertiary hover:text-text-primary hover:bg-cosmic-subtle",
            "transition-all duration-200"
          )}
          aria-label="作业队列"
        >
          <TriggerIcon
            className={cn(
              "w-5 h-5",
              activeCount > 0 && "animate-spin text-sky-500"
            )}
          />

          {/* Active count badge */}
          {activeCount > 0 && (
            <span
              className={cn(
                "absolute -top-0.5 -right-0.5 inline-flex items-center justify-center",
                "min-w-[16px] h-4 px-1 rounded-full",
                "bg-brand text-white text-[10px] font-bold leading-none",
                "shadow-sm"
              )}
            >
              {activeCount > 99 ? "99+" : activeCount}
            </span>
          )}
        </button>
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={8}
        className={cn(
          "w-80 p-0",
          "bg-cosmic-surface border border-cosmic-border",
          "shadow-lg rounded-xl overflow-hidden"
        )}
      >
        {/* ── Header ── */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-cosmic-border">
          <h3 className="text-sm font-semibold text-text-primary">作业队列</h3>
          {activeCount > 0 && (
            <span className="text-[11px] text-text-tertiary">
              {activeCount} 个进行中
            </span>
          )}
        </div>

        {/* ── Content ── */}
        <div className="max-h-[360px] overflow-y-auto">
          {isLoading && tasks.length === 0 && (
            <div className="flex items-center justify-center py-10">
              <Loader2 className="w-5 h-5 animate-spin text-text-tertiary" />
            </div>
          )}

          {isError && (
            <div className="flex flex-col items-center justify-center py-10 gap-2">
              <XCircle className="w-5 h-5 text-red-400" />
              <p className="text-sm text-text-tertiary">加载失败</p>
            </div>
          )}

          {!isLoading && !isError && tasks.length === 0 && (
            <div className="flex flex-col items-center justify-center py-10 gap-2">
              <ListTodo className="w-6 h-6 text-text-tertiary/50" />
              <p className="text-sm text-text-tertiary">暂无任务</p>
            </div>
          )}

          {tasks.map((task) => {
            const cfg = STATUS_CONFIG[task.status] ?? STATUS_CONFIG.queued;
            const StatusIcon = cfg.icon;

            return (
              <Link
                key={task.task_id}
                href={`/tasks/${task.task_id}`}
                className={cn(
                  "flex items-center gap-3 px-4 py-3",
                  "hover:bg-cosmic-subtle transition-colors",
                  "border-b border-cosmic-border/50 last:border-b-0"
                )}
              >
                {/* Thumbnail */}
                <div className="w-6 h-6 rounded-md bg-cosmic-subtle overflow-hidden shrink-0 flex items-center justify-center">
                  {(() => {
                    const url = parseTaskUrl(task.results);
                    return url ? (
                    <img
                      src={url}
                      alt=""
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full bg-cosmic-subtle" />
                  );
                  })()}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    {/* Media type tag */}
                    <span className="text-[10px] font-medium text-text-tertiary bg-cosmic-subtle px-1.5 py-px rounded">
                      {MEDIA_TYPE_LABELS[task.media_type] ?? task.media_type}
                    </span>
                    {/* Prompt (truncated) */}
                    <span className="text-xs text-text-primary truncate">
                      {truncate(task.prompt, 40)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {/* Relative time */}
                    <span className="text-[11px] text-text-tertiary">
                      {relativeTime(task.created_at)}
                    </span>
                    {/* Status badge */}
                    <span
                      className={cn(
                        "inline-flex items-center gap-0.5 text-[10px] font-medium px-1.5 py-px rounded-full",
                        cfg.badgeColor,
                        cfg.badgeBg
                      )}
                    >
                      <StatusIcon className={cn("w-3 h-3", cfg.iconColor)} />
                      {cfg.label}
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>

        {/* ── Footer: "查看全部" ── */}
        {tasks.length > 0 && (
          <Link
            href="/tasks"
            className={cn(
              "flex items-center justify-center gap-1 px-4 py-2.5",
              "border-t border-cosmic-border",
              "text-xs font-medium text-text-secondary hover:text-brand",
              "hover:bg-cosmic-subtle transition-colors"
            )}
          >
            查看全部
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        )}
      </PopoverContent>
    </Popover>
  );
}

export default JobsTray;
