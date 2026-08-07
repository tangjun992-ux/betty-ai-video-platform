"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity, AlertTriangle, Loader2, Power, RefreshCw, Shield, Zap,
} from "lucide-react";
import { useAuthStore } from "@/lib/stores";
import {
  getGatewayStatus,
  gatewayDisableProvider,
  gatewayEnableProvider,
  gatewayResetCircuit,
  gatewayKillSwitch,
  gatewayReloadRoutes,
  type GatewayStatus,
} from "@/lib/api";
import { cn } from "@/lib/utils";

export default function GatewayAdminPage() {
  const token = useAuthStore((s) => s.token);
  const [data, setData] = useState<GatewayStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setData(await getGatewayStatus(token));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const act = async (key: string, fn: () => Promise<unknown>) => {
    setBusy(key);
    try {
      await fn();
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setBusy(null);
    }
  };

  if (!token) {
    return (
      <div className="p-8 text-center text-text-secondary">
        请登录管理员账户后访问 Gateway 控制台。
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Zap className="w-6 h-6 text-brand" />
            Model API Gateway
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            路由、Provider 健康、紧急下线与企业级运维控制
          </p>
        </div>
        <button
          onClick={() => load()}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-cosmic-border text-sm hover:bg-cosmic-subtle"
        >
          <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
          刷新
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {loading && !data ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-brand" />
        </div>
      ) : data ? (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Card label="路由数" value={String(data.routes.route_count)} icon={Activity} />
            <Card
              label="Region"
              value={data.routes.region || "global"}
              icon={Shield}
            />
            <Card
              label="Key 池"
              value={data.kie_key_pool.pool_enabled ? `${data.kie_key_pool.configured} keys` : "单 Key"}
              icon={Zap}
            />
            <Card
              label="Kill Switch"
              value={data.registry.kill_switch ? "已开启" : "关闭"}
              icon={Power}
              danger={data.registry.kill_switch}
            />
          </div>

          {/* Budget + backpressure */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <section className="rounded-xl border border-cosmic-border bg-cosmic-elevated p-4">
              <h2 className="text-sm font-medium mb-2">预算上限（Credits/日）</h2>
              <dl className="text-sm space-y-1 text-text-secondary">
                <div className="flex justify-between">
                  <dt>用户</dt>
                  <dd className="font-mono">
                    {data.budget_caps.user_daily_cap > 0
                      ? data.budget_caps.user_daily_cap
                      : "未限制"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt>团队</dt>
                  <dd className="font-mono">
                    {data.budget_caps.team_daily_cap > 0
                      ? data.budget_caps.team_daily_cap
                      : "未限制"}
                  </dd>
                </div>
              </dl>
            </section>
            <section className="rounded-xl border border-cosmic-border bg-cosmic-elevated p-4">
              <h2 className="text-sm font-medium mb-2">Provider 背压</h2>
              <dl className="text-sm space-y-1 text-text-secondary">
                <div className="flex justify-between">
                  <dt>最大并发</dt>
                  <dd className="font-mono">
                    {data.provider_limits.max_inflight > 0
                      ? data.provider_limits.max_inflight
                      : "未限制"}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt>默认 RPM</dt>
                  <dd className="font-mono">
                    {data.provider_limits.rpm_default > 0
                      ? data.provider_limits.rpm_default
                      : "未限制"}
                  </dd>
                </div>
              </dl>
              {Object.keys(data.provider_limits.inflight).length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {Object.entries(data.provider_limits.inflight).map(([p, n]) => (
                    <span
                      key={p}
                      className="text-xs px-2 py-0.5 rounded-full border border-cosmic-border"
                    >
                      {p}: {n} in-flight
                    </span>
                  ))}
                </div>
              )}
            </section>
          </div>

          {/* Kill switch + reload */}
          <div className="rounded-xl border border-cosmic-border bg-cosmic-elevated p-4 flex flex-wrap gap-3 items-center">
            <span className="text-sm font-medium">紧急控制</span>
            <button
              disabled={!!busy}
              onClick={() => act("kill", () => gatewayKillSwitch(token, !data.registry.kill_switch))}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium",
                data.registry.kill_switch
                  ? "bg-emerald-600/20 text-emerald-400 border border-emerald-500/30"
                  : "bg-red-600/20 text-red-300 border border-red-500/30",
              )}
            >
              {busy === "kill" ? "…" : data.registry.kill_switch ? "关闭 Kill Switch" : "开启 Kill Switch"}
            </button>
            <button
              disabled={!!busy}
              onClick={() => act("reload", () => gatewayReloadRoutes(token))}
              className="px-4 py-2 rounded-lg text-sm border border-cosmic-border hover:bg-cosmic-subtle"
            >
              重载 routes.yaml
            </button>
          </div>

          {/* Backends */}
          <section className="rounded-xl border border-cosmic-border overflow-hidden">
            <div className="px-4 py-3 border-b border-cosmic-border bg-cosmic-subtle/50">
              <h2 className="font-medium text-sm">Provider Backends</h2>
            </div>
            <div className="p-4 flex flex-wrap gap-2">
              {data.backends.map((b) => (
                <span
                  key={b.name}
                  className={cn(
                    "text-xs px-2.5 py-1 rounded-full border",
                    b.configured
                      ? "border-emerald-500/40 text-emerald-400 bg-emerald-500/10"
                      : "border-cosmic-border text-text-tertiary",
                  )}
                >
                  {b.name}{b.configured ? " ✓" : " —"}
                </span>
              ))}
            </div>
          </section>

          {/* Provider health table */}
          <section className="rounded-xl border border-cosmic-border overflow-hidden">
            <div className="px-4 py-3 border-b border-cosmic-border bg-cosmic-subtle/50">
              <h2 className="font-medium text-sm">Provider 健康 / 熔断</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-text-tertiary border-b border-cosmic-border">
                    <th className="px-4 py-2 font-medium">SKU</th>
                    <th className="px-4 py-2">成功</th>
                    <th className="px-4 py-2">失败</th>
                    <th className="px-4 py-2">状态</th>
                    <th className="px-4 py-2">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {data.providers.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-6 text-text-tertiary text-center">
                        暂无 Provider 执行记录
                      </td>
                    </tr>
                  ) : (
                    data.providers.map((p) => {
                      const [provider, remote] = p.key.split(":", 2);
                      return (
                        <tr key={p.key} className="border-b border-cosmic-border/50">
                          <td className="px-4 py-2 font-mono text-xs">{p.key}</td>
                          <td className="px-4 py-2">{p.successes}</td>
                          <td className="px-4 py-2">{p.failures}</td>
                          <td className="px-4 py-2">
                            {p.admin_disabled ? (
                              <span className="text-amber-400">已下线</span>
                            ) : p.circuit_open ? (
                              <span className="text-red-400">熔断</span>
                            ) : (
                              <span className="text-emerald-400">正常</span>
                            )}
                          </td>
                          <td className="px-4 py-2">
                            <div className="flex gap-1 flex-wrap">
                              {p.admin_disabled ? (
                                <MiniBtn
                                  label="恢复"
                                  busy={busy === `en-${p.key}`}
                                  onClick={() => act(`en-${p.key}`, () =>
                                    gatewayEnableProvider(token, provider, remote))}
                                />
                              ) : (
                                <MiniBtn
                                  label="下线"
                                  busy={busy === `dis-${p.key}`}
                                  onClick={() => act(`dis-${p.key}`, () =>
                                    gatewayDisableProvider(token, provider, remote, "admin"))}
                                />
                              )}
                              <MiniBtn
                                label="重置熔断"
                                busy={busy === `rst-${p.key}`}
                                onClick={() => act(`rst-${p.key}`, () =>
                                  gatewayResetCircuit(token, provider, remote))}
                              />
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* Routes preview */}
          <section className="rounded-xl border border-cosmic-border overflow-hidden">
            <div className="px-4 py-3 border-b border-cosmic-border bg-cosmic-subtle/50">
              <h2 className="font-medium text-sm">路由表 ({data.routes.route_count})</h2>
            </div>
            <pre className="p-4 text-xs overflow-x-auto text-text-secondary max-h-80">
              {JSON.stringify(data.routes.routes, null, 2)}
            </pre>
          </section>
        </>
      ) : null}
    </div>
  );
}

function Card({
  label, value, icon: Icon, danger,
}: {
  label: string;
  value: string;
  icon: React.ElementType;
  danger?: boolean;
}) {
  return (
    <div className="rounded-xl border border-cosmic-border bg-cosmic-elevated p-4">
      <div className="flex items-center gap-2 text-text-tertiary text-xs mb-1">
        <Icon className="w-3.5 h-3.5" />
        {label}
      </div>
      <div className={cn("text-lg font-semibold", danger && "text-red-400")}>{value}</div>
    </div>
  );
}

function MiniBtn({
  label, onClick, busy,
}: {
  label: string;
  onClick: () => void;
  busy?: boolean;
}) {
  return (
    <button
      type="button"
      disabled={busy}
      onClick={onClick}
      className="text-[10px] px-2 py-0.5 rounded border border-cosmic-border hover:bg-cosmic-subtle disabled:opacity-50"
    >
      {busy ? "…" : label}
    </button>
  );
}
