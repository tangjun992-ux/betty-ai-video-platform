"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Rss,
  CheckCircle2,
  Loader2,
  Clock,
  XCircle,
  Image as ImageIcon,
  Video,
} from "lucide-react";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

/* ═══════════════════════════════════════════════════════
   Feed Page — 最近创作活动时间线
   ═══════════════════════════════════════════════════════ */

interface TaskItem {
  task_id: string;
  prompt: string;
  media_type: string;
  status: string;
  model: string | null;
  results: string | null;
  created_at: string | null;
}

// Parse the results field (Python stringified list) to extract first URL
function parseResultsUrl(results: string | null): string | null {
  if (!results) return null;
  try {
    // Handle Python dict format: [{'url': 'https://...'}]
    const urlMatch = results.match(/'url':\s*'([^']+)'/);
    if (urlMatch) return urlMatch[1];
    // Handle JSON format: [{"url": "https://..."}]
    const parsed = JSON.parse(results.replace(/'/g, '"'));
    if (Array.isArray(parsed) && parsed[0]?.url) return parsed[0].url;
  } catch {}
  return null;
}

function timeAgo(iso: string | null): string {
  if (!iso) return "—";
  const s = Math.max(1, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  if (s < 60) return "刚刚";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} 分钟前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} 小时前`;
  return `${Math.floor(h / 24)} 天前`;
}

const statusConfig: Record<string, { icon: typeof CheckCircle2; color: string; label: string }> = {
  succeeded: { icon: CheckCircle2, color: "text-emerald-500", label: "完成" },
  completed: { icon: CheckCircle2, color: "text-emerald-500", label: "完成" },
  running: { icon: Loader2, color: "text-sky-500", label: "生成中" },
  processing: { icon: Loader2, color: "text-sky-500", label: "处理中" },
  queued: { icon: Clock, color: "text-amber-500", label: "排队中" },
  pending: { icon: Clock, color: "text-amber-500", label: "等待中" },
  failed: { icon: XCircle, color: "text-red-500", label: "失败" },
};

export default function FeedPage() {
  const router = useRouter();

  const { data, isLoading, error } = useQuery({
    queryKey: ["feed-tasks"],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/tasks/?limit=50`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    },
    staleTime: 30_000,
    refetchInterval: 15_000,
  });

  const tasks: TaskItem[] = Array.isArray(data?.tasks)
    ? data.tasks
    : Array.isArray(data) ? data : [];

  return (
    <div className="min-h-screen bg-cosmic-deep">
      <div className="max-w-3xl mx-auto px-4 py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-3 mb-1">
            <div className="w-9 h-9 rounded-xl bg-brand/[0.08] flex items-center justify-center">
              <Rss className="w-5 h-5 text-brand" />
            </div>
            <h1 className="text-2xl font-semibold text-text-primary tracking-[-0.02em]">动态</h1>
          </div>
          <p className="text-text-secondary text-sm ml-12">最近的创作活动</p>
        </motion.div>

        {/* Loading */}
        {isLoading && (
          <div className="space-y-4">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex gap-4 animate-pulse">
                <div className="w-3 shrink-0 flex flex-col items-center">
                  <div className="w-3 h-3 rounded-full bg-cosmic-border" />
                </div>
                <div className="flex-1 p-4 rounded-xl bg-cosmic-surface border border-cosmic-border space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-cosmic-subtle" />
                    <div className="flex-1 space-y-2">
                      <div className="h-3 bg-cosmic-subtle rounded w-3/4" />
                      <div className="h-3 bg-cosmic-subtle rounded w-1/2" />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="text-center py-16">
            <XCircle className="w-10 h-10 text-text-tertiary mx-auto mb-3" />
            <p className="text-text-secondary">加载失败，请稍后重试</p>
          </div>
        )}

        {/* Empty */}
        {!isLoading && !error && tasks.length === 0 && (
          <div className="text-center py-16">
            <Rss className="w-12 h-12 text-text-tertiary/40 mx-auto mb-4" />
            <p className="text-text-secondary font-medium">暂无动态</p>
            <p className="text-text-tertiary text-sm mt-1">创作内容后将在这里显示</p>
          </div>
        )}

        {/* Timeline */}
        {!isLoading && !error && tasks.length > 0 && (
          <div className="relative">
            {/* Timeline vertical line */}
            <div className="absolute left-[5px] top-3 bottom-3 w-[2px] bg-gradient-to-b from-brand/20 via-cosmic-border to-brand/10" />

            <div className="space-y-1">
              {tasks.map((task, idx) => {
                const cfg = statusConfig[task.status] ?? statusConfig.queued;
                const Icon = cfg.icon;

                return (
                  <motion.div
                    key={task.task_id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.03 }}
                    className="flex gap-4 group cursor-pointer"
                    onClick={() => router.push(`/tasks/${task.task_id}`)}
                  >
                    {/* Status dot */}
                    <div className="w-3 shrink-0 flex flex-col items-center pt-3">
                      <div className={cn(
                        "w-3 h-3 rounded-full border-2 border-cosmic-deep z-10",
                        task.status === "running" && "animate-spin"
                      )}>
                        <Icon className={cn("w-3 h-3", cfg.color)} />
                      </div>
                    </div>

                    {/* Card */}
                    <div className="flex-1 p-3.5 rounded-xl bg-cosmic-surface border border-cosmic-border hover:border-brand/20 hover:shadow-elevation-sm transition-all duration-200">
                      <div className="flex items-start gap-3">
                        {/* Thumbnail */}
                        <div className="w-12 h-12 rounded-lg bg-cosmic-subtle shrink-0 overflow-hidden">
                          {(() => {
                            const url = parseResultsUrl(task.results);
                            return url ? (
                            <img
                              src={url}
                              alt=""
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              {task.media_type === "video" ? (
                                <Video className="w-5 h-5 text-text-tertiary" />
                              ) : (
                                <ImageIcon className="w-5 h-5 text-text-tertiary" />
                              )}
                            </div>
                          );
                          })()}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-text-primary line-clamp-2 leading-relaxed">
                            {task.prompt?.length > 60
                              ? task.prompt.slice(0, 60) + "…"
                              : task.prompt || "无提示词"}
                          </p>
                          <div className="flex items-center gap-2 mt-1.5">
                            {task.model && (
                              <span className="text-[11px] text-text-tertiary bg-cosmic-subtle px-1.5 py-0.5 rounded">
                                {task.model}
                              </span>
                            )}
                            <span className={cn(
                              "text-[11px] font-medium px-1.5 py-0.5 rounded flex items-center gap-1",
                              cfg.color === "text-emerald-500" && "bg-emerald-50 text-emerald-600",
                              cfg.color === "text-sky-500" && "bg-sky-50 text-sky-600",
                              cfg.color === "text-amber-500" && "bg-amber-50 text-amber-600",
                              cfg.color === "text-red-500" && "bg-red-50 text-red-600",
                            )}>
                              <Icon className="w-3 h-3" />
                              {cfg.label}
                            </span>
                          </div>
                          <span className="text-[11px] text-text-tertiary mt-1 block">
                            {timeAgo(task.created_at)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
