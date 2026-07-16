"use client";

import { useEffect, useState, useCallback } from "react";
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw, Activity, Cpu } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

const ORIGIN = API_BASE.replace(/\/api\/v1$/, "");

type Health = { status: string; version?: string; checks?: any };
type ModelHealth = {
  model_id: string;
  successes: number;
  failures: number;
  avg_latency_ms: number;
  circuit_open: boolean;
  score: number;
  success_rate: number;
  last_error?: string;
};

function Dot({ ok }: { ok: boolean | null }) {
  return <span className={cn("inline-block w-2.5 h-2.5 rounded-full", ok === null ? "bg-text-tertiary/40" : ok ? "bg-success" : "bg-destructive")} />;
}

export default function StatusPage() {
  const [data, setData] = useState<Health | null>(null);
  const [err, setErr] = useState(false);
  const [latency, setLatency] = useState<number | null>(null);
  const [updated, setUpdated] = useState<string>("");
  const [modelHealth, setModelHealth] = useState<ModelHealth[]>([]);
  const [circuitsOpen, setCircuitsOpen] = useState(0);
  const [lastSmoke, setLastSmoke] = useState<{
    ts?: string; mode?: string; probed?: number; ok?: number;
    failed_count?: number; quarantined_count?: number;
  } | null>(null);

  const load = useCallback(async () => {
    const t0 = performance.now();
    try {
      const res = await fetch(`${ORIGIN}/health/ready`, { cache: "no-store" });
      setLatency(Math.round(performance.now() - t0));
      const j = await res.json();
      setData(j); setErr(false);
    } catch { setErr(true); setData(null); }
    try {
      const mh = await fetch(`${API_BASE}/models/health`, { cache: "no-store" });
      if (mh.ok) {
        const j = await mh.json();
        setModelHealth(j.models || []);
        setCircuitsOpen(j.circuits_open || 0);
        setLastSmoke(j.last_smoke || null);
      }
    } catch { /* ignore */ }
    setUpdated(new Date().toLocaleTimeString());
  }, []);

  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t); }, [load]);

  const checks = data?.checks || {};
  const dbOk = checks.database === "ok";
  const redisOk = checks.redis === "ok";
  const workers = typeof checks.celery_workers === "number" ? checks.celery_workers : null;
  const apiOk = !err && !!data;
  const allOk = apiOk && dbOk && redisOk && (workers ?? 0) > 0 && circuitsOpen === 0;
  const overall = err ? "major" : allOk ? "operational" : "degraded";

  const items = [
    { name: "API 服务", ok: apiOk, note: apiOk ? `延迟 ${latency ?? "?"}ms` : "无法连接" },
    { name: "数据库", ok: apiOk ? dbOk : null, note: dbOk ? "正常" : (checks.database || "—") },
    { name: "Redis / 队列", ok: apiOk ? redisOk : null, note: redisOk ? "正常" : (checks.redis || "—") },
    { name: "生成 Worker", ok: apiOk ? (workers ?? 0) > 0 : null, note: workers != null ? `${workers} 个在线` : "—" },
    { name: "模型熔断", ok: circuitsOpen === 0, note: circuitsOpen ? `${circuitsOpen} 个熔断中` : "全部畅通" },
    {
      name: "上次冒烟",
      ok: lastSmoke ? (lastSmoke.failed_count || 0) === 0 : null,
      note: lastSmoke
        ? `${lastSmoke.mode || "?"} · ${lastSmoke.ok ?? 0}/${lastSmoke.probed ?? 0} 通过` +
          ((lastSmoke.failed_count || 0) > 0 ? ` · 失败 ${lastSmoke.failed_count}` : "") +
          (lastSmoke.ts ? ` · ${String(lastSmoke.ts).replace("T", " ").replace("Z", " UTC")}` : "")
        : "尚未运行",
    },
  ];

  const hotModels = modelHealth
    .filter((m) => m.successes + m.failures > 0 || m.circuit_open)
    .slice(0, 12);

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2.5">
          <Activity className="w-6 h-6 text-brand" />
          <h1 className="text-2xl font-display font-bold text-text-primary">系统状态</h1>
        </div>
        <button onClick={load} className="btn-icon" title="刷新"><RefreshCw className="w-4 h-4" /></button>
      </div>

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

      <div className="mt-6">
        <div className="flex items-center gap-2 mb-2">
          <Cpu className="w-4 h-4 text-brand" />
          <h2 className="text-sm font-semibold text-text-primary">模型健康 / SLA</h2>
          <span className="text-[11px] text-text-tertiary">GET /models/health</span>
        </div>
        {hotModels.length === 0 ? (
          <div className="rounded-xl border border-cosmic-border bg-cosmic-surface p-4 text-xs text-text-tertiary">
            暂无运行时反馈（尚未产生成功/失败记录）。模型 registry 已就绪，共 {modelHealth.length} 个。
          </div>
        ) : (
          <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface divide-y divide-cosmic-border overflow-hidden">
            {hotModels.map((m) => (
              <div key={m.model_id} className="flex items-center justify-between px-4 py-2.5 gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-medium text-text-primary truncate">{m.model_id}</div>
                  <div className="text-[11px] text-text-tertiary">
                    成功 {m.successes} · 失败 {m.failures} · 延迟 {m.avg_latency_ms || "—"}ms
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {m.circuit_open && <span className="badge-destructive">熔断</span>}
                  <span className={cn(
                    "text-xs font-mono font-semibold",
                    m.score >= 80 ? "text-success" : m.score >= 50 ? "text-warning" : "text-destructive"
                  )}>{m.score}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

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
        实时读取 <code>/health/ready</code> 与 <code>/models/health</code>。生产环境建议接入 Prometheus 抓取 <code>/metrics</code> + 告警。
      </p>
    </div>
  );
}
