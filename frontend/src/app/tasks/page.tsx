"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { listTasks, getTaskStatus } from "@/lib/api";
import { TaskCard } from "@/components/TaskCard";

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  const fetchTasks = useCallback(async () => {
    try {
      const statusFilter = filter === "all" ? undefined : filter;
      const data = await listTasks(undefined, statusFilter, 50);
      setTasks(data.tasks);
    } catch {}
    finally { setLoading(false); }
  }, [filter]);

  useEffect(() => { fetchTasks(); }, [fetchTasks]);

  useEffect(() => {
    const interval = setInterval(async () => {
      const active = tasks.filter((t) => !["completed", "failed", "cancelled"].includes(t.status));
      if (active.length === 0) return;
      for (const task of active) {
        try {
          const status = await getTaskStatus(task.task_id);
          if (status.status !== task.status || status.progress !== task.progress) {
            setTasks((prev) => prev.map((t) => t.task_id === task.task_id ? { ...t, ...status } : t));
          }
        } catch {}
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [tasks]);

  if (loading) {
    return (
      <main className="max-w-4xl mx-auto px-4 py-8 text-center text-dark-500">
        <div className="spinner mx-auto mb-4" />加载任务中...
      </main>
    );
  }

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">我的生成任务</h1>
        <span className="text-sm text-dark-500">{tasks.length} 个</span>
      </div>

      <div className="flex gap-2 mb-6">
        {[
          { key: "all", label: "全部" },
          { key: "queued", label: "排队" },
          { key: "generating", label: "生成中" },
          { key: "completed", label: "已完成" },
          { key: "failed", label: "失败" },
        ].map((f) => (
          <button key={f.key} onClick={() => setFilter(f.key)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${filter === f.key ? "bg-accent-cyan600 text-text-accent-cyan" : "bg-dark-800 text-dark-400 hover:bg-dark-700"}`}>
            {f.label}
          </button>
        ))}
      </div>

      {tasks.length === 0 ? (
        <div className="text-center py-20 text-dark-500">
          <div className="text-5xl mb-4">🎬</div>
          <p>还没有任务，去创作一个吧！</p>
        </div>
      ) : (
        <div className="space-y-4">
          {tasks.map((task) => (
            <div key={task.task_id} onClick={() => router.push(`/tasks/${task.task_id}`)}
              className="cursor-pointer hover:opacity-90 transition">
              <TaskCard task={task} onStatusChange={fetchTasks} />
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
