"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { API_BASE, getTaskStatus, listTasks } from "@/lib/api";



export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params?.id as string;
  const [task, setTask] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [similarTasks, setSimilarTasks] = useState<any[]>([]);

  const fetchTask = useCallback(async () => {
    try {
      const data = await getTaskStatus(taskId);
      setTask(data);

      // Load full task list to get parameters
      const listData = await listTasks(undefined, undefined, 100);
      const fullTask = listData.tasks.find((t: any) => t.task_id === taskId);
      if (fullTask) {
        setTask((prev: any) => ({ ...prev, ...fullTask }));
      }

      // Find similar tasks
      const similar = listData.tasks
        .filter((t: any) => t.status === "completed" && t.task_id !== taskId)
        .slice(0, 4);
      setSimilarTasks(similar);
    } catch (err) {
      console.error("Failed to load task:", err);
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => { fetchTask(); }, [fetchTask]);

  // Auto-refresh active tasks
  useEffect(() => {
    if (!task || ["completed", "failed", "cancelled"].includes(task.status)) return;
    const interval = setInterval(async () => {
      try {
        const data = await getTaskStatus(taskId);
        setTask((prev: any) => ({ ...prev, ...data }));
        if (data.status === "completed" || data.status === "failed") {
          clearInterval(interval);
        }
      } catch {}
    }, 2000);
    return () => clearInterval(interval);
  }, [task, taskId]);

  if (loading) {
    return (
      <main className="max-w-4xl mx-auto px-4 py-8 text-center text-dark-500">
        <div className="spinner mx-auto mb-4" />
        加载任务详情...
      </main>
    );
  }

  if (!task) {
    return (
      <main className="max-w-4xl mx-auto px-4 py-20 text-center">
        <div className="text-5xl mb-4">🔍</div>
        <h1 className="text-xl font-bold mb-2">任务未找到</h1>
        <button onClick={() => router.push("/tasks")}
          className="mt-4 px-6 py-2 bg-accent-cyan600 text-text-accent-cyan rounded-lg hover:bg-accent-cyan transition">
          返回任务列表
        </button>
      </main>
    );
  }

  const results = task.results || [];
  const isComplete = task.status === "completed";
  const paramsData = task.parameters || {};

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      {/* Back button + status */}
      <div className="flex items-center justify-between mb-6">
        <button onClick={() => router.back()}
          className="text-dark-400 hover:text-text-accent-cyan transition text-sm">
          ← 返回
        </button>
        <span className="text-xs text-dark-500 font-mono">{taskId.slice(0, 8)}...</span>
      </div>

      {/* Task info */}
      <div className="bg-dark-900/50 border border-dark-800 rounded-xl p-6 mb-6">
        <h1 className="text-xl font-bold mb-3">{task.current_stage === "completed" ? "✅ 已完成" : task.current_stage === "failed" ? "❌ 失败" : `⚙️ ${task.current_stage || "处理中"}`}</h1>
        <p className="text-dark-300 leading-relaxed mb-4">{task.full_prompt || "无提示词"}</p>

        {/* Progress */}
        {task.status === "generating" && task.progress > 0 && (
          <div className="w-full bg-dark-700 rounded-full h-2 mb-4">
            <div className="bg-gradient-to-r from-accent-cyan to-teal-400 h-2 rounded-full transition-all"
              style={{ width: `${Math.min(task.progress, 100)}%` }} />
          </div>
        )}

        {/* Meta grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <div>
            <div className="text-dark-500 text-xs">模型</div>
            <div className="text-text-accent-cyan">{task.model || "-"}</div>
          </div>
          <div>
            <div className="text-dark-500 text-xs">类型</div>
            <div className="text-text-accent-cyan">{task.media_type === "video" ? "🎬 视频" : "🖼️ 图片"}</div>
          </div>
          <div>
            <div className="text-dark-500 text-xs">分辨率</div>
            <div className="text-text-accent-cyan">{task.resolution || "1080x1080"}</div>
          </div>
          <div>
            <div className="text-dark-500 text-xs">质量</div>
            <div className="text-text-accent-cyan">{paramsData.quality || "balanced"}</div>
          </div>
        </div>

        {/* Routing info */}
        {paramsData.routing_info && (
          <div className="mt-4 p-3 bg-dark-800/50 rounded-lg">
            <div className="text-xs text-accent-cyan font-medium mb-1">🤖 智能路由分析</div>
            <div className="text-xs text-dark-400">
              {paramsData.routing_info}
            </div>
          </div>
        )}

        {/* Enhanced prompt */}
        {paramsData.original_prompt && (
          <details className="mt-3">
            <summary className="text-xs text-yellow-500 cursor-pointer">✨ 原始提示词（已增强）</summary>
            <div className="text-xs text-dark-400 mt-1 p-2 bg-dark-800 rounded">{paramsData.original_prompt}</div>
          </details>
        )}
      </div>

      {/* Results */}
      {isComplete && results.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-bold mb-3">生成结果</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {results.map((r: any, idx: number) => (
              <div key={idx} className="bg-dark-900/50 border border-dark-800 rounded-xl overflow-hidden">
                {r.url ? (
                  r.type === "video" ? (
                    <video src={r.url} controls className="w-full" />
                  ) : (
                    <img src={r.url} alt="result" className="w-full h-64 object-cover" />
                  )
                ) : (
                  <div className="w-full h-40 flex items-center justify-center bg-dark-800 text-dark-500">无预览</div>
                )}
                <div className="p-3 flex items-center justify-between">
                  <div className="text-sm text-text-accent-cyan">
                    {r.type === "video" ? "🎬" : "🖼️"} {r.model}
                  </div>
                  <div className="flex gap-2">
                    {r.url && (
                      <button onClick={() => { const a = document.createElement("a"); a.href = r.url; a.download = ""; a.target = "_blank"; a.click(); }}
                        className="px-3 py-1 bg-accent-cyan600 text-text-accent-cyan rounded text-xs hover:bg-accent-cyan transition">
                        💾 下载
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error */}
      {task.status === "failed" && (
        <div className="bg-red-900/20 border border-red-800 rounded-xl p-4 mb-6">
          <div className="text-red-400 font-medium mb-1">❌ 生成失败</div>
          <div className="text-sm text-red-300">{task.error_message}</div>
        </div>
      )}

      {/* Timestamps */}
      <div className="text-xs text-dark-500 space-y-1">
        {task.created_at && <div>🕐 创建: {new Date(task.created_at).toLocaleString("zh-CN")}</div>}
        {task.completed_at && <div>✅ 完成: {new Date(task.completed_at).toLocaleString("zh-CN")}</div>}
      </div>

      {/* Similar tasks */}
      {similarTasks.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-bold mb-3">相关任务</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {similarTasks.map((t) => (
              <button key={t.task_id} onClick={() => router.push(`/tasks/${t.task_id}`)}
                className="text-left bg-dark-900/50 border border-dark-800 rounded-xl p-3 hover:border-dark-700 transition">
                <p className="text-sm text-dark-300 line-clamp-1">{t.prompt}</p>
                <div className="text-xs text-dark-500 mt-1">
                  {t.model} · {t.media_type}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
