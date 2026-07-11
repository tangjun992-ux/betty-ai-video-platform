"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw, Activity } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

const ORIGIN = API_BASE.replace(/\/api\/v1$/, "");

type Health = { status: string; version?: string; checks?: any };

function Dot({ ok }: { ok: boolean | null }) {
  return <span className={cn("inline-block w-2.5 h-2.5 rounded-full", ok === null ? "bg-text-tertiary/40" : ok ? "bg-success" : "bg-destructive")} />;
}

export default function StatusPage() {
  const [data, setData] = useState<Health | null>(null);
  const [err, setErr] = useState(false);
  const [latency, setLatency] = useState<number | null>(null);
  const [updated, setUpdated] = useState<string>("");

  const load = useCallback(async () => {
    const t0 = performance.now();
    try {
      const res = await fetch(`${ORIGIN}/health/ready`, { cache: "no-store" });
      setLatency(Math.round(performance.now() - t0));
      const j = await res.json();
      setData(j); setErr(false);
    } catch { setErr(true); setData(null); }
    setUpdated(new Date().toLocaleTimeString());
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t); }, [load]);

  const checks = data?.checks || {};
  const dbOk = checks.database === "ok";
  const redisOk = checks.redis === "ok";
  const workers = typeof checks.celery_workers === "number" ? checks.celery_workers : null;
  const apiOk = !err && !!data;
  const allOk = apiOk && dbOk && redisOk && (workers ?? 0) > 0;
  const overall = err ? "major" : allOk ? "operational" : "degraded";

  const items = [
    { name: "API 服务", ok: apiOk, note: apiOk ? `延迟 ${latency ?? "?"}ms` : "无法连接" },
    { name: "数据库", ok: apiOk ? dbOk : null, note: dbOk ? "正常" : (checks.database || "—") },
    { name: "Redis / 队列", ok: apiOk ? redisOk : null, note: redisOk ? "正常" : (checks.redis || "—") },
    { name: "生成 Worker", ok: apiOk ? (workers ?? 0) > 0 : null, note: workers != null ? `${workers} 个在线` : "—" },
  ];

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2.5">
          <Activity className="w-6 h-6 text-brand" />
          <h1 className="text-2xl font-bold text-text-primary">系统状态</h1>
        </div>
        <button onClick={load} className="btn-icon" title="刷新"><RefreshCw className="w-4 h-4" /></button>
      </div>

      {/* Overall banner */}
      <div className={cn("rounded-2xl border p-5 mb-6 flex items-center gap-3",
        overall === "operational" ? "border-success/30 bg-success/[0.06]"
        : overall === "degraded" ? "border-warning/30 bg-warning/[0.06]"
        : "border-destructive/30 bg-destructive/[0.06]")}>
        {overall === "operational" ? <CheckCircle2 className="w-7 h-7 text-success" />
          : overall === "degraded" ? <AlertTriangle className="w-7 h-7 text-warning" />
          : <XCircle className="w-7 h-7 text-destructive" />}
        <div>
          <div className="font-semibold text-text-primary">
            {overall === "operational" ? "所有系统运行正常" : overall === "degraded" ? "部分服务降级" : "服务不可用"}
          </div>
          <div className="text-xs text-text-tertiary">更新于 {updated || "…"} · v{data?.version || "—"} · 每 10 秒自动刷新</div>
        </div>
      </div>

      {/* Components */}
      <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface divide-y divide-cosmic-border">
        {items.map((it) => (
          <div key={it.name} className="flex items-center justify-between px-4 py-3.5">
            <div className="flex items-center gap-3">
              <Dot ok={it.ok} />
              <span className="text-sm font-medium text-text-primary">{it.name}</span>
            </div>
            <span className={cn("text-xs", it.ok === false ? "text-destructive" : "text-text-tertiary")}>{it.note}</span>
          </div>
        ))}
      </div>

      {/* Queue depths */}
      {checks.queue_depth && (
        <div className="mt-6">
          <h2 className="text-sm font-semibold text-text-primary mb-2">队列积压</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {Object.entries(checks.queue_depth).map(([q, n]: any) => (
              <div key={q} className="rounded-xl border border-cosmic-border bg-cosmic-surface p-3 text-center">
                <div className="text-lg font-bold text-text-primary">{n ?? "—"}</div>
                <div className="text-[11px] text-text-tertiary">{q}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-text-tertiary mt-6 text-center">
        实时读取 <code>/health/ready</code> 深度探针。生产环境建议接入 Prometheus 抓取 <code>/metrics</code> + 告警。
      </p>
    </div>
  );
}
