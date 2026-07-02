"use client";

import { motion } from "framer-motion";
import { Download, RefreshCw, Edit3, Video, ImageIcon, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

interface ResultItem {
  url: string;
  type: "image" | "video";
  prompt: string;
  model: string;
}

interface ResultGridProps {
  results: ResultItem[];
  loading?: boolean;
  loadingCount?: number;
  onRegenerate?: (item: ResultItem) => void;
  onEdit?: (item: ResultItem) => void;
  onDownload?: (item: ResultItem) => void;
  onUseInVideo?: (item: ResultItem) => void;
}

function SkeletonCard() {
  return (
    <div className="aspect-square rounded-xl skeleton" />
  );
}

export function ResultGrid({
  results,
  loading,
  loadingCount = 4,
  onRegenerate,
  onEdit,
  onDownload,
  onUseInVideo,
}: ResultGridProps) {
  if (!loading && results.length === 0) return null;

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">
          生成结果 {results.length > 0 && `(${results.length})`}
        </p>
      </div>

      <div className={cn("grid gap-3", results.length <= 1 ? "grid-cols-1" : "grid-cols-2")}>
        {results.map((item, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.1, type: "spring" }}
            className="group relative rounded-xl overflow-hidden border border-cosmic-border/50 bg-cosmic-surface/20"
          >
            {/* Media */}
            {item.type === "image" ? (
              <img
                src={item.url}
                alt={item.prompt}
                className="w-full aspect-square object-cover"
                loading="lazy"
              />
            ) : (
              <video
                src={item.url}
                className="w-full aspect-square object-cover"
                controls
                muted
                loop
                playsInline
              />
            )}

            {/* Type Badge */}
            <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-black/50 backdrop-blur-sm text-[10px] text-text-accent-cyan/80 flex items-center gap-1">
              {item.type === "image" ? <ImageIcon className="w-3 h-3" /> : <Video className="w-3 h-3" />}
              <span>{item.model}</span>
            </div>

            {/* Actions Overlay */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-end justify-center gap-2 p-3">
              {onRegenerate && (
                <button
                  onClick={() => onRegenerate(item)}
                  className="p-2 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm text-text-accent-cyan text-xs transition-all"
                  title="重新生成"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              )}
              {onEdit && (
                <button
                  onClick={() => onEdit(item)}
                  className="p-2 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm text-text-accent-cyan text-xs transition-all"
                  title="编辑"
                >
                  <Edit3 className="w-4 h-4" />
                </button>
              )}
              {onDownload && (
                <a
                  href={item.url}
                  download
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm text-text-accent-cyan text-xs transition-all"
                  title="下载"
                >
                  <Download className="w-4 h-4" />
                </a>
              )}
              {item.type === "image" && onUseInVideo && (
                <button
                  onClick={() => onUseInVideo(item)}
                  className="p-2 rounded-lg bg-accent-cyan/[0.12] hover:bg-accent-cyan/30 backdrop-blur-sm text-accent-cyan text-xs transition-all"
                  title="用于视频"
                >
                  <Video className="w-4 h-4" />
                </button>
              )}
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur-sm text-text-accent-cyan text-xs transition-all"
                title="新窗口打开"
              >
                <ExternalLink className="w-4 h-4" />
              </a>
            </div>
          </motion.div>
        ))}

        {/* Loading skeletons */}
        {loading &&
          Array.from({ length: loadingCount }).map((_, i) => (
            <SkeletonCard key={`skel-${i}`} />
          ))}
      </div>
    </div>
  );
}
