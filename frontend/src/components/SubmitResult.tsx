"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { getTaskStatus } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";

interface SubmitResultProps {
  result: any;
  onReset: () => void;
}

// ─── Progress stages definitions ────────────────────────

interface ProgressStage {
  range: [number, number]; // [start%, end%)
  label: string;
  icon: string;
  color: string;
}

const STAGES: ProgressStage[] = [
  { range: [0, 15],   label: "验证提示词",   icon: "🔍", color: "from-slate-500 to-slate-400" },
  { range: [15, 35],  label: "调度队列中",   icon: "⏳", color: "from-blue-500 to-cyan-400" },
  { range: [35, 60],  label: "模型生成中",   icon: "🎨", color: "from-accent-cyan to-purple-500" },
  { range: [60, 85],  label: "后处理优化",   icon: "✨", color: "from-purple-500 to-pink-400" },
  { range: [85, 100], label: "即将完成",    icon: "🚀", color: "from-teal-400 to-emerald-400" },
];

function getStage(progress: number): ProgressStage {
  for (const s of STAGES) {
    if (progress >= s.range[0] && progress < s.range[1]) return s;
  }
  return STAGES[STAGES.length - 1];
}

const WS_BASE = (process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000").replace(/^http/, "ws");

// ─── Preview skeleton shimmer ───────────────────────────

function PreviewSkeleton({ stage, progress }: { stage: ProgressStage; progress: number }) {
  return (
    <div className="relative w-full aspect-square rounded-2xl overflow-hidden bg-gradient-to-br from-cosmic-subtle to-cosmic-elevated border border-cosmic-border/40">
      {/* Animated gradient background */}
      <div 
        className="absolute inset-0 opacity-30"
        style={{
          background: `conic-gradient(from 0deg, transparent ${progress * 3.6}deg, hsl(252 78% 63% / 0.12) ${progress * 3.6}deg)`,
        }}
      />
      
      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
        <motion.div
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-5xl"
        >
          {stage.icon}
        </motion.div>
        <div className="text-center">
          <p className="text-sm font-medium text-text-accent-cyan/80">{stage.label}</p>
          <p className="text-xs text-text-secondary mt-1">{progress}%</p>
        </div>
      </div>

      {/* Pixelated preview hint */}
      <div 
        className="absolute inset-0 bg-gradient-to-t from-cosmic-elevated via-transparent to-transparent"
        style={{ opacity: Math.min(progress / 80, 0.6) }}
      />
    </div>
  );
}

// ─── Main Component ──────────────────────────────────────

export function SubmitResult({ result, onReset }: SubmitResultProps) {
  const taskId = result?.task_id;
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [stageMessage, setStageMessage] = useState("");
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<NodeJS.Timeout | undefined>(undefined);

  // ── WebSocket connection ───────────────────────────────
  useEffect(() => {
    if (!taskId) return;

    const wsUrl = `${WS_BASE}/api/v1/ws/tasks/${taskId}`;
    let ws: WebSocket;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      try {
        ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log(`[WS] connected for task ${taskId}`);
          // Send initial ping
          ws.send("ping");
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "progress") {
              setProgress(data.progress || 0);
              setStageMessage(data.message || data.current_stage || "");
              if (data.preview_url) {
                setPreviewUrls(prev => {
                  if (prev.includes(data.preview_url)) return prev;
                  return [...prev, data.preview_url];
                });
              }
            }
            if (data.type === "completed" || data.status === "completed") {
              setStatus(data);
              setProgress(100);
              ws.close();
            }
            if (data.type === "failed" || data.status === "failed") {
              setStatus(data);
              ws.close();
            }
          } catch {}
        };

        ws.onclose = () => {
          // Reconnect after 3s if still in progress
          if (!status || (status.status !== "completed" && status.status !== "failed")) {
            reconnectTimer = setTimeout(connect, 3000);
          }
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        // WebSocket failed, fall back to polling
      }
    };

    connect();

    return () => {
      if (ws) ws.close();
      clearTimeout(reconnectTimer);
    };
  }, [taskId]);

  // ── Fallback polling ───────────────────────────────────
  useEffect(() => {
    if (!taskId || wsRef.current?.readyState === WebSocket.OPEN) return;

    const MAX_POLL_TIME_MS = 10 * 60 * 1000; // 10 min total (matches KIE adapter 600s timeout)
    const startTime = Date.now();

    const poll = async () => {
      try {
        // Stop polling if exceeded max time
        if (Date.now() - startTime > MAX_POLL_TIME_MS) {
          setStatus({ status: "failed", error_message: "生成超时，请稍后重试或联系支持" });
          if (pollRef.current) clearInterval(pollRef.current);
          return;
        }

        const data = await getTaskStatus(taskId, 8000); // 8s per poll
        setStatus(data);
        setProgress(data.progress || 0);
        setStageMessage((data as any).current_stage || "");
        if (data.status === "completed" || data.status === "failed") {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch {
        // Network error — keep polling
      }
    };

    poll();
    pollRef.current = setInterval(poll, 2000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [taskId]);

  // ── Derived state ──────────────────────────────────────
  const isComplete = status?.status === "completed";
  const isFailed = status?.status === "failed";
  const results = status?.results || [];
  const stage = getStage(progress);
  const progressPct = isComplete ? 100 : isFailed ? 0 : Math.max(progress, 5);

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      {/* ── Header ─────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-8"
      >
        <div className="text-5xl mb-3">
          {isComplete ? "🎉" : isFailed ? "😢" : "🔄"}
        </div>
        <h1 className="text-2xl font-bold mb-2">
          {isComplete
            ? "生成完成！"
            : isFailed
            ? "生成失败"
            : `${stage.label} ${progressPct}%`}
        </h1>
        <p className="text-text-secondary text-sm">
          {isComplete
            ? `使用 ${status?.model || "AI 模型"} 成功生成`
            : isFailed
            ? status?.error_message || "未知错误，请重试"
            : stageMessage || "AI 正在为你创作..."}
        </p>
      </motion.div>

      {/* ── Enhanced Progress Bar ───────────────────────── */}
      <AnimatePresence>
        {!isComplete && !isFailed && (
          <motion.div
            initial={{ opacity: 0, scaleY: 0.8 }}
            animate={{ opacity: 1, scaleY: 1 }}
            exit={{ opacity: 0 }}
            className="mb-8"
          >
            {/* Stage indicators */}
            <div className="flex justify-between mb-2">
              {STAGES.map((s, i) => {
                const stageMid = (s.range[0] + s.range[1]) / 2;
                const active = progressPct >= s.range[1];
                const current = progressPct >= s.range[0] && progressPct < s.range[1];
                return (
                  <div key={i} className="flex flex-col items-center gap-1">
                    <motion.div
                      animate={current ? { scale: [1, 1.2, 1] } : {}}
                      transition={{ duration: 1.5, repeat: Infinity }}
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-sm transition-all duration-500 ${
                        active
                          ? "bg-accent-cyan text-white"
                          : current
                          ? "bg-accent-cyan/[0.12] text-accent-cyan ring-2 ring-accent-cyan/50"
                          : "bg-cosmic-subtle text-text-secondary"
                      }`}
                    >
                      {s.icon}
                    </motion.div>
                    <span className={`text-[10px] hidden sm:block ${
                      active || current ? "text-text-accent-cyan" : "text-text-secondary/50"
                    }`}>
                      {s.label}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Main progress track */}
            <div className="relative w-full h-4 bg-cosmic-subtle rounded-full overflow-hidden">
              {/* Background pulse for current stage */}
              <div
                className="absolute inset-0 opacity-20"
                style={{
                  background: `linear-gradient(90deg, ${stage.color.split(" ")[1]}, ${stage.color.split(" ")[3] || "transparent"})`,
                }}
              />
              
              {/* Progress fill */}
              <motion.div
                className={`absolute inset-y-0 left-0 bg-gradient-to-r ${stage.color} rounded-full`}
                initial={{ width: "0%" }}
                animate={{ width: `${progressPct}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
              >
                {/* Shimmer effect */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
              </motion.div>

              {/* Percentage label */}
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xs font-bold text-text-accent-cyan drop-shadow-md">
                  {progressPct}%
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Preview Stream ──────────────────────────────── */}
      {!isComplete && !isFailed && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
          <PreviewSkeleton stage={stage} progress={progressPct} />
          
          {/* Show intermediate previews if any */}
          {previewUrls.slice(-1).map((url, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="relative rounded-2xl overflow-hidden border border-cosmic-border/40"
            >
              <img
                src={url}
                alt="Preview"
                className="w-full aspect-square object-cover"
                style={{ filter: `blur(${Math.max(10 - progressPct / 10, 0)}px)` }}
              />
              <div className="absolute bottom-0 inset-x-0 p-3 bg-gradient-to-t from-black/70 to-transparent">
                <p className="text-xs text-white/80">预览 · 生成中...</p>
              </div>
            </motion.div>
          ))}

          {/* If no previews, show loading placeholder */}
          {previewUrls.length === 0 && (
            <div className="flex flex-col items-center justify-center gap-3 rounded-2xl bg-cosmic-subtle border border-cosmic-border/40 p-8">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
              >
                <svg className="w-10 h-10 text-accent-cyan/50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                </svg>
              </motion.div>
              <p className="text-sm text-text-secondary">等待模型响应...</p>
              <p className="text-xs text-text-secondary/60">
                任务 ID: {taskId?.slice(0, 8)}...
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── Results Grid ─────────────────────────────────── */}
      <AnimatePresence>
        {isComplete && results.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6"
          >
            {results.map((r: any, idx: number) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.1 * idx }}
                className="group bg-cosmic-surface border border-cosmic-border rounded-xl overflow-hidden hover:border-accent-cyan/30 hover:shadow-elevation-md transition-all duration-300"
              >
                {r.url ? (
                  r.type === "video" ? (
                    <video src={r.url} controls className="w-full" />
                  ) : (
                    <div className="relative">
                      <img src={r.url} alt="result" className="w-full h-64 object-cover" />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
                    </div>
                  )
                ) : (
                  <div className="w-full h-40 flex items-center justify-center text-text-secondary">
                    无预览
                  </div>
                )}
                <div className="p-3">
                  <div className="text-sm text-text-accent-cyan">
                    {r.type === "video" ? "🎬 视频" : "🖼️ 图片"} — {r.model}
                  </div>
                  <div className="flex gap-2 mt-2">
                    {r.url && (
                      <button
                        onClick={() => {
                          const a = document.createElement("a");
                          a.href = r.url;
                          a.download = "";
                          a.target = "_blank";
                          a.click();
                        }}
                        className="px-3 py-1.5 bg-accent-cyan text-white rounded text-xs hover:bg-accent-cyan/90 transition"
                      >
                        💾 下载
                      </button>
                    )}
                    {r.url && (
                      <button
                        onClick={() => navigator.clipboard.writeText(r.url)}
                        className="px-3 py-1.5 bg-cosmic-subtle text-text-secondary rounded text-xs hover:bg-cosmic-border transition"
                      >
                        📋 复制
                      </button>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Failed State ─────────────────────────────────── */}
      {isFailed && (
        <div className="text-center py-8">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-destructive-muted border border-destructive/20 text-destructive text-sm mb-6">
            ⚠️ {status?.error_message || "生成过程中发生错误"}
          </div>
        </div>
      )}

      {/* ── Action Buttons ───────────────────────────────── */}
      <div className="flex gap-3">
        <button
          onClick={onReset}
          className="flex-1 py-3 rounded-xl text-lg font-bold transition-all bg-gradient-to-r from-accent-cyan to-accent-violet hover:brightness-110 text-white shadow-button-glow active:scale-[0.98]"
        >
          ✨ 继续创作
        </button>
        <a
          href="/tasks"
          className="px-6 py-3 rounded-xl text-lg font-medium bg-cosmic-subtle text-text-secondary hover:bg-cosmic-border hover:text-text-primary transition text-center"
        >
          查看任务 →
        </a>
      </div>
    </main>
  );
}
