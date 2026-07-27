"use client";

interface TaskCardProps {
  task: any;
  onStatusChange?: () => void;
}

const STATUS_MAP: Record<string, { icon: string; color: string; label: string }> = {
  queued: { icon: "⏳", color: "text-yellow-400", label: "排队中" },
  analyzing: { icon: "🔍", color: "text-blue-400", label: "分析中" },
  routing: { icon: "🔀", color: "text-blue-400", label: "路由中" },
  generating: { icon: "⚙️", color: "text-blue-400", label: "生成中" },
  uploading: { icon: "📤", color: "text-teal-400", label: "上传中" },
  completed: { icon: "✅", color: "text-green-400", label: "已完成" },
  failed: { icon: "❌", color: "text-red-400", label: "失败" },
  cancelled: { icon: "🚫", color: "text-dark-500", label: "已取消" },
};

export function TaskCard({ task, onStatusChange }: TaskCardProps) {
  const status = task.status || "queued";
  const { icon, color, label } = STATUS_MAP[status] || STATUS_MAP.queued;

  const results = task.results || [];
  const mediaResult = results.find((r: any) => !r.error);

  const handleRetry = () => {
    if (onStatusChange) onStatusChange();
  };

  return (
    <div className="bg-dark-900/50 border border-dark-800 rounded-xl p-4 transition hover:border-dark-700">
      <div className="flex items-start gap-4">
        {/* Media preview */}
        {status === "completed" && mediaResult?.url ? (
          <div className="w-32 h-32 rounded-lg overflow-hidden bg-dark-800 flex-shrink-0">
            {mediaResult.type === "video" ? (
              <video
                src={mediaResult.url}
                className="w-full h-full object-cover"
                controls
              />
            ) : (
              <img
                src={mediaResult.url}
                alt={task.prompt}
                className="w-full h-full object-cover"
              />
            )}
          </div>
        ) : (
          <div className="w-32 h-32 rounded-lg bg-dark-800 flex-shrink-0 flex items-center justify-center">
            <span className="text-3xl">{icon}</span>
          </div>
        )}

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-sm font-medium ${color}`}>
              {icon} {label}
            </span>
            {task.model && (
              <span className="text-xs text-dark-500 bg-dark-800 px-2 py-0.5 rounded">
                {task.model}
              </span>
            )}
            {task.progress > 0 && status === "generating" && (
              <span className="text-xs text-accent-cyan">
                {task.progress}%
              </span>
            )}
          </div>

          <p className="text-dark-300 text-sm leading-relaxed line-clamp-2">
            {task.prompt}
          </p>

          {/* Progress bar for active tasks */}
          {status === "generating" && task.progress > 0 && (
            <div className="mt-2 w-full bg-dark-700 rounded-full h-1.5">
              <div
                className="bg-gradient-to-r from-accent-cyan to-teal-400 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(task.progress, 100)}%` }}
              />
            </div>
          )}

          <div className="text-xs text-dark-500 mt-2 flex items-center gap-3">
            <span>📐 {task.resolution || "1080x1080"}</span>
            <span>
              {status === "completed"
                ? "✅ 完成"
                : status === "failed"
                ? `❌ ${task.error_message || "未知错误"}`
                : task.current_stage
                ? `⚙️ ${task.current_stage}...`
                : "处理中..."}
            </span>
            {task.created_at && (
              <span>
                🕐{" "}
                {new Date(task.created_at).toLocaleString("zh-CN", {
                  month: "numeric",
                  day: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            )}
          </div>

          {/* Actions */}
          <div className="mt-3 flex gap-2">
            {status === "completed" && mediaResult?.url ? (
              <>
                <button
                  onClick={() => {
                    const a = document.createElement("a");
                    a.href = mediaResult.url;
                    a.download = "";
                    a.target = "_blank";
                    a.click();
                  }}
                  className="px-3 py-1.5 bg-dark-800 text-dark-300 rounded text-xs hover:bg-dark-700 transition"
                >
                  💾 下载
                </button>
                <button
                  onClick={() => navigator.clipboard.writeText(mediaResult.url)}
                  className="px-3 py-1.5 bg-dark-800 text-dark-300 rounded text-xs hover:bg-dark-700 transition"
                >
                  📋 复制链接
                </button>
                {results.length > 1 && (
                  <span className="text-xs text-dark-500 self-center">
                    {results.length} 个结果
                  </span>
                )}
              </>
            ) : status === "failed" ? (
              <button
                onClick={handleRetry}
                className="px-3 py-1.5 bg-red-900/30 text-red-400 border border-red-800 rounded text-xs hover:bg-red-900/50 transition"
              >
                🔄 刷新状态
              </button>
            ) : status === "generating" ? (
              <div className="flex items-center gap-2 text-xs text-accent-cyan">
                <div className="w-3 h-3 border-2 border-accent-cyan border-t-transparent rounded-full animate-spin" />
                <span>正在生成，请稍候...</span>
              </div>
            ) : (
              <div className="text-xs text-dark-500">等待处理...</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
