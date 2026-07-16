"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, Copy, Check, Heart, Play, Share2 } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { Loading, ErrorState } from "@/components/StatusStates";
import { cn } from "@/lib/utils";

interface ShareItem {
  id: string;
  task_id: string;
  share_path: string;
  prompt: string;
  media_type: string;
  model_used: string;
  url: string;
  thumbnail: string;
  resolution?: string;
  duration?: number;
  created_at?: string;
  username: string;
  display_name: string;
  avatar?: string;
  likes: number;
  views: number;
  create_path: string;
}

export default function ExploreSharePage() {
  const params = useParams();
  const router = useRouter();
  const taskId = String(params?.id || "");
  const [item, setItem] = useState<ShareItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    if (!taskId) return;
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE}/gallery/share/${encodeURIComponent(taskId)}`);
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d.detail || "作品不存在或未公开（需作者显式发布）");
      }
      setItem(await r.json());
    } catch (e: any) {
      setError(e.message || "加载失败");
      setItem(null);
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    load();
  }, [load]);

  const shareUrl =
    typeof window !== "undefined"
      ? `${window.location.origin}/explore/${taskId}`
      : `/explore/${taskId}`;

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  };

  const remix = () => {
    if (!item) return;
    const p = encodeURIComponent(item.prompt || "");
    const m = encodeURIComponent(item.model_used || "");
    router.push(`${item.create_path}?prompt=${p}&model=${m}`);
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loading />
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16">
        <ErrorState message={error || "作品不存在"} onRetry={load} />
        <button
          type="button"
          onClick={() => router.push("/explore")}
          className="mt-6 mx-auto flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft className="w-4 h-4" /> 返回探索
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-[70vh] max-w-5xl mx-auto px-4 py-8">
      <button
        type="button"
        onClick={() => router.push("/explore")}
        className="mb-6 inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary"
      >
        <ArrowLeft className="w-4 h-4" /> 探索
      </button>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid md:grid-cols-2 gap-8 items-start"
      >
        <div className="rounded-2xl overflow-hidden bg-cosmic-deep ring-1 ring-cosmic-border">
          {item.media_type === "video" ? (
            <video
              src={item.url}
              poster={item.thumbnail}
              controls
              playsInline
              className="w-full aspect-video object-contain bg-black"
            />
          ) : (
            <img
              src={item.url}
              alt={item.prompt}
              className="w-full object-contain max-h-[70vh] bg-black"
            />
          )}
        </div>

        <div>
          <div className="flex items-center gap-2 text-xs text-text-tertiary mb-3">
            <span className="px-2 py-0.5 rounded-full bg-cosmic-surface border border-cosmic-border">
              {item.model_used}
            </span>
            {item.media_type === "video" && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-cosmic-surface border border-cosmic-border">
                <Play className="w-3 h-3" /> 视频
              </span>
            )}
          </div>
          <h1 className="text-xl font-semibold text-text-primary leading-snug mb-4">
            {item.prompt || "未命名作品"}
          </h1>
          <p className="text-sm text-text-secondary mb-6">
            {item.display_name || item.username}
            {item.created_at ? ` · ${(item.created_at || "").slice(0, 10)}` : ""}
          </p>
          <div className="flex items-center gap-4 text-sm text-text-tertiary mb-8">
            <span className="inline-flex items-center gap-1.5">
              <Heart className="w-4 h-4" /> {item.likes}
            </span>
            <span>{item.views} 次浏览</span>
          </div>

          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={remix} className="btn-primary">
              Remix 同款
            </button>
            <button
              type="button"
              onClick={copyLink}
              className={cn("btn-secondary inline-flex items-center gap-2")}
            >
              {copied ? <Check className="w-4 h-4 text-success" /> : <Share2 className="w-4 h-4" />}
              {copied ? "已复制链接" : "复制分享链接"}
            </button>
            <button
              type="button"
              onClick={() => {
                navigator.clipboard.writeText(item.prompt || "");
              }}
              className="btn-secondary inline-flex items-center gap-2"
            >
              <Copy className="w-4 h-4" /> 复制提示词
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
