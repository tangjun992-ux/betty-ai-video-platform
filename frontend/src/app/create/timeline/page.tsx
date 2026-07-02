"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { Plus, Trash2, Play, Save, Layers, GripVertical, Film, CheckCircle, RefreshCw } from "lucide-react";
import { useCreationStore } from "@/lib/stores";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface Clip {
  url: string;
  start: number;
  end: number;
  transition: string;
  label?: string;
}

interface Project {
  id: string;
  name: string;
  clips: Clip[];
  created_at: string;
  updated_at: string;
}

const TRANSITIONS = [
  { id: "cut", label: "剪切" },
  { id: "fade", label: "淡入淡出" },
  { id: "dissolve", label: "溶解" },
  { id: "slide", label: "滑动" },
  { id: "zoom", label: "缩放" },
];

export default function TimelineEditorPage() {
  const router = useRouter();

  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [projectName, setProjectName] = useState("未命名项目");
  const [clips, setClips] = useState<Clip[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [renderResult, setRenderResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Load projects
  useEffect(() => {
    fetch(`${API_BASE}/timeline/projects`)
      .then((r) => r.json())
      .then((data) => {
        setProjects(data.projects || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const selectProject = useCallback((project: Project) => {
    setActiveProject(project);
    setProjectName(project.name);
    setClips([...project.clips]);
    setError(null);
    setRenderResult(null);
  }, []);

  const addClip = useCallback(() => {
    setClips((prev) => [
      ...prev,
      { url: "", start: 0, end: 5, transition: "cut", label: `片段 ${prev.length + 1}` },
    ]);
  }, []);

  const removeClip = useCallback((index: number) => {
    setClips((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const updateClip = useCallback((index: number, field: string, value: any) => {
    setClips((prev) => prev.map((c, i) => (i === index ? { ...c, [field]: value } : c)));
  }, []);

  const moveClip = useCallback((from: number, to: number) => {
    if (to < 0 || to >= clips.length) return;
    setClips((prev) => {
      const next = [...prev];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      return next;
    });
  }, [clips.length]);

  const saveProject = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const body = {
        id: activeProject?.id || undefined,
        name: projectName,
        clips: clips.filter((c) => c.url.trim()),
      };
      const res = await fetch(`${API_BASE}/timeline/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error("保存失败");
      const data = await res.json();

      // Refresh projects
      const projRes = await fetch(`${API_BASE}/timeline/projects`);
      const projData = await projRes.json();
      setProjects(projData.projects || []);
      setActiveProject({ ...body, id: data.id, created_at: data.created_at, updated_at: data.updated_at } as any);
    } catch (err: any) {
      setError(err.message);
    }
    setSubmitting(false);
  };

  const renderTimeline = async () => {
    if (!activeProject) return;
    setSubmitting(true);
    setProgress(0);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/timeline/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: activeProject.id, quality: "balanced", format: "mp4" }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "渲染失败");
      }
      const data = await res.json();

      // Poll progress
      const poll = setInterval(async () => {
        try {
          const tr = await fetch(`${API_BASE}/tasks/${data.task_id}`);
          if (!tr.ok) return;
          const td = await tr.json();
          if (td.status === "completed") {
            clearInterval(poll);
            setProgress(100);
            setRenderResult(td.result_url);
            setSubmitting(false);
          } else if (td.status === "failed") {
            clearInterval(poll);
            setError(td.error_message || "渲染失败");
            setSubmitting(false);
          } else {
            const p = td.parameters?.progress;
            if (p) setProgress(Math.min(99, p));
          }
        } catch {}
      }, 2000);
    } catch (err: any) {
      setError(err.message);
      setSubmitting(false);
    }
  };

  const totalDuration = clips
    .filter((c) => c.url.trim())
    .reduce((sum, c) => sum + Math.max(0, c.end - c.start), 0);

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 w-48 bg-white/[0.05] rounded" />
          <div className="h-96 bg-white/[0.02] rounded-2xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold mb-1 text-text-accent-cyan">时间轴编辑</h1>
        <p className="text-text-secondary text-sm mb-8">
          多片段编排，添加转场效果，渲染合成为完整视频
        </p>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Project List */}
        <motion.div
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-1"
        >
          <div className="rounded-2xl bg-white/[0.02] border border-white/[0.06] p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-text-accent-cyan">项目列表</h3>
              <button
                onClick={() => {
                  setActiveProject(null);
                  setProjectName("未命名项目");
                  setClips([]);
                  setRenderResult(null);
                  setError(null);
                }}
                className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
              >
                <Plus className="w-3 h-3" />
                新建
              </button>
            </div>
            <div className="space-y-1 max-h-96 overflow-y-auto">
              {projects.map((p) => (
                <button
                  key={p.id}
                  onClick={() => selectProject(p)}
                  className={`w-full text-left p-3 rounded-xl transition-all ${
                    activeProject?.id === p.id
                      ? "bg-blue-500/10 border border-blue-500/20"
                      : "hover:bg-white/[0.03] border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Film className="w-4 h-4 text-text-secondary flex-shrink-0" />
                    <span className="text-sm text-text-accent-cyan truncate">{p.name}</span>
                  </div>
                  <div className="text-xs text-text-secondary mt-1">
                    {p.clips?.length || 0} 片段 · {p.clips?.reduce((s, c) => s + Math.max(0, c.end - c.start), 0).toFixed(0) || 0}s
                  </div>
                </button>
              ))}
              {projects.length === 0 && (
                <p className="text-xs text-text-secondary text-center py-4">暂无项目，点击新建</p>
              )}
            </div>
          </div>

          {/* Render Result */}
          {renderResult && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 p-4 rounded-2xl bg-green-500/5 border border-green-500/10"
            >
              <div className="flex items-center gap-2 text-green-400 mb-2">
                <CheckCircle className="w-4 h-4" />
                <span className="text-sm font-medium">渲染完成</span>
              </div>
              <video src={renderResult} controls className="w-full rounded-xl" />
            </motion.div>
          )}
        </motion.div>

        {/* Right: Timeline Editor */}
        <motion.div
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-2"
        >
          <div className="rounded-2xl bg-white/[0.02] border border-white/[0.06] p-4">
            {/* Project Name */}
            <div className="flex items-center gap-3 mb-4">
              <input
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                className="flex-1 bg-transparent text-lg font-semibold text-text-accent-cyan border-b border-white/[0.08] pb-1 focus:outline-none focus:border-blue-500/30"
                placeholder="项目名称"
              />
              <button
                onClick={saveProject}
                disabled={submitting}
                className="px-4 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-sm text-text-accent-cyan flex items-center gap-1.5 transition-all disabled:opacity-30"
              >
                <Save className="w-4 h-4" />
                保存
              </button>
              <button
                onClick={renderTimeline}
                disabled={submitting || clips.filter((c) => c.url.trim()).length === 0}
                className="px-4 py-2 rounded-xl bg-white text-black font-semibold text-sm hover:bg-white/90 flex items-center gap-1.5 transition-all active:scale-[0.98] disabled:opacity-30"
              >
                <Play className="w-4 h-4" />
                渲染
              </button>
            </div>

            {/* Progress */}
            {submitting && progress > 0 && (
              <div className="mb-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-text-secondary">渲染中</span>
                  <span className="text-xs text-text-secondary">{Math.round(progress)}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/[0.05] overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500"
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>
            )}

            {error && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
                {error}
              </div>
            )}

            {/* Clips */}
            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
              {clips.map((clip, index) => (
                <motion.div
                  key={index}
                  layout
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center gap-2 p-3 rounded-xl bg-white/[0.03] border border-white/[0.05] group"
                >
                  <div className="flex flex-col gap-1">
                    <button
                      onClick={() => moveClip(index, index - 1)}
                      disabled={index === 0}
                      className="p-0.5 opacity-0 group-hover:opacity-100 disabled:opacity-20 transition-opacity"
                    >
                      <GripVertical className="w-3 h-3 text-text-secondary" />
                    </button>
                    <button
                      onClick={() => moveClip(index, index + 1)}
                      disabled={index === clips.length - 1}
                      className="p-0.5 opacity-0 group-hover:opacity-100 disabled:opacity-20 transition-opacity"
                    >
                      <GripVertical className="w-3 h-3 text-text-secondary rotate-180" />
                    </button>
                  </div>

                  <div className="flex-1 grid grid-cols-4 gap-2">
                    <input
                      value={clip.url}
                      onChange={(e) => updateClip(index, "url", e.target.value)}
                      placeholder="素材URL"
                      className="col-span-2 bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 text-xs text-text-accent-cyan placeholder:text-text-secondary/40 focus:outline-none focus:border-blue-500/30"
                    />
                    <input
                      type="number"
                      value={clip.start}
                      onChange={(e) => updateClip(index, "start", parseFloat(e.target.value) || 0)}
                      placeholder="开始(s)"
                      className="bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 text-xs text-text-accent-cyan placeholder:text-text-secondary/40 focus:outline-none focus:border-blue-500/30"
                    />
                    <input
                      type="number"
                      value={clip.end}
                      onChange={(e) => updateClip(index, "end", parseFloat(e.target.value) || 5)}
                      placeholder="结束(s)"
                      className="bg-white/[0.03] border border-white/[0.06] rounded-lg px-3 py-2 text-xs text-text-accent-cyan placeholder:text-text-secondary/40 focus:outline-none focus:border-blue-500/30"
                    />
                  </div>

                  <select
                    value={clip.transition}
                    onChange={(e) => updateClip(index, "transition", e.target.value)}
                    className="bg-white/[0.03] border border-white/[0.06] rounded-lg px-2 py-2 text-xs text-text-accent-cyan focus:outline-none"
                  >
                    {TRANSITIONS.map((t) => (
                      <option key={t.id} value={t.id} className="bg-gray-900">{t.label}</option>
                    ))}
                  </select>

                  <button
                    onClick={() => removeClip(index)}
                    className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-500/10 text-red-400 transition-all"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </motion.div>
              ))}
            </div>

            {/* Add Clip */}
            <button
              onClick={addClip}
              className="mt-3 w-full py-3 rounded-xl border-2 border-dashed border-white/[0.06] hover:border-blue-400/20 text-text-secondary hover:text-blue-400 text-sm flex items-center justify-center gap-2 transition-all"
            >
              <Plus className="w-4 h-4" />
              添加片段
            </button>

            {/* Stats */}
            <div className="mt-4 flex items-center gap-4 text-xs text-text-secondary">
              <span>{clips.filter((c) => c.url.trim()).length} 个片段</span>
              <span>总时长 {totalDuration.toFixed(1)}s</span>
            </div>
          </div>

          {/* Tips */}
          <div className="mt-4 p-4 rounded-2xl bg-white/[0.02] border border-white/[0.06]">
            <h3 className="text-sm font-semibold text-text-accent-cyan mb-2">使用技巧</h3>
            <ul className="space-y-1 text-xs text-text-secondary">
              <li>拖拽片段上下可调整顺序</li>
              <li>每个片段可独立设置入点、出点和转场效果</li>
              <li>URL 支持视频和图片素材</li>
              <li>渲染时间 ≈ 总时长 × 3</li>
            </ul>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
