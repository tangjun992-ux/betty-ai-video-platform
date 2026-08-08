"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Activity, AlertTriangle, CheckCircle2, Cloud, CreditCard, Loader2,
  RefreshCw, Shield, Sparkles, XCircle,
} from "lucide-react";
import { useAuthStore } from "@/lib/stores";
import {
  getLastModelSmoke,
  getPromotableModels,
  getSystemReadiness,
  getWebhookFailures,
  getWebhookFailuresDigest,
  sendWebhookFailuresDigest,
  promoteModel,
  retryAllWebhookFailures,
  retryWebhookDelivery,
  type PromotableResponse,
  type SystemReadiness,
  type WebhookFailure,
  type WebhookFailureDigest,
} from "@/lib/api";
import { cn } from "@/lib/utils";

export default function AdminOpsPage() {
  const token = useAuthStore((s) => s.token);
  const [readiness, setReadiness] = useState<SystemReadiness | null>(null);
  const [promotable, setPromotable] = useState<PromotableResponse | null>(null);
  const [lastSmoke, setLastSmoke] = useState<{ available: boolean; report?: Record<string, unknown> } | null>(null);
  const [webhookFailures, setWebhookFailures] = useState<WebhookFailure[]>([]);
  const [webhookDigest, setWebhookDigest] = useState<WebhookFailureDigest | null>(null);
  const [whBusy, setWhBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const rd = await getSystemReadiness();
      setReadiness(rd);
      if (token) {
        const [pm, ls, wh, digest] = await Promise.all([
          getPromotableModels(token),
          getLastModelSmoke(token),
          getWebhookFailures(token),
          getWebhookFailuresDigest(token),
        ]);
        setPromotable(pm);
        setLastSmoke(ls);
        setWebhookFailures(wh.failures);
        setWebhookDigest(digest);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const handlePromote = async (modelId: string) => {
    if (!token) return;
    setBusy(modelId);
    try {
      await promoteModel(token, modelId, "admin ops promote");
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "晋升失败");
    } finally {
      setBusy(null);
    }
  };

  if (!token) {
    return (
      <div className="p-8 text-center text-text-secondary">
        请登录管理员账户后访问运维控制台。
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            <Shield className="w-6 h-6 text-brand" />
            生产运维
          </h1>
          <p className="text-sm text-text-secondary mt-1">
            Stripe / CDN / SSO 就绪 · 模型货架 · Smoke 自动晋升
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

      {loading && !readiness ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-brand" />
        </div>
      ) : readiness ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <ReadinessCard
              title="Stripe 收款"
              icon={CreditCard}
              ok={readiness.stripe.production_ok || readiness.env !== "production"}
              blockers={readiness.stripe.blockers}
              details={[
                { k: "API Key", v: readiness.stripe.api_key_configured ? "已配置" : "未配置" },
                { k: "Webhook", v: readiness.stripe.webhook_secret_configured ? "已配置" : "未配置" },
                { k: "订阅 Checkout", v: readiness.stripe.subscription_ready ? "就绪" : "未就绪" },
                ...(readiness.stripe.bootstrap ? [{
                  k: "Price 环境变量",
                  v: `${readiness.stripe.bootstrap.price_envs_configured}/${readiness.stripe.bootstrap.price_envs_total}`,
                }] : []),
                ...(readiness.stripe.checkout ? [{
                  k: "Checkout 模式",
                  v: readiness.stripe.checkout.mode === "stripe" ? "Stripe" : readiness.stripe.checkout.dev_grant ? "dev-grant" : "blocked",
                }] : []),
              ]}
            />
            <ReadinessCard
              title="CDN / 存储"
              icon={Cloud}
              ok={readiness.storage.production_ok || readiness.env !== "production"}
              blockers={readiness.storage.blockers}
              details={[
                { k: "类型", v: readiness.storage.storage_type },
                { k: "CDN", v: readiness.storage.cdn_configured ? "已配置" : "未配置" },
                { k: "S3 Public", v: readiness.storage.s3_public_configured ? "已配置" : "未配置" },
              ]}
            />
            <ReadinessCard
              title="OIDC / SSO"
              icon={Shield}
              ok={readiness.sso.production_ok}
              blockers={readiness.sso.blockers}
              details={[
                { k: "OIDC", v: readiness.sso.configured ? "已配置" : "未配置" },
              ]}
            />
          </div>

          {readiness.stripe.staging && (
            <section className="rounded-xl border border-cosmic-border bg-cosmic-elevated p-4">
              <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
                <CreditCard className="w-4 h-4 text-brand" />
                Stripe Staging 验收
                <span className={cn(
                  "text-xs font-normal px-2 py-0.5 rounded-full",
                  readiness.stripe.staging.staging_ready
                    ? "bg-success/15 text-success"
                    : "bg-amber-500/15 text-amber-600",
                )}>
                  {readiness.stripe.staging.staging_ready ? "可测收款" : "待配置"}
                </span>
              </h2>
              <ul className="space-y-1.5 text-xs text-text-secondary mb-3">
                {readiness.stripe.staging.checklist.map((item) => (
                  <li key={item.id} className="flex items-center gap-2">
                    {item.ok ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-success shrink-0" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                    )}
                    <span>{item.label}{item.required ? " *" : ""}</span>
                  </li>
                ))}
              </ul>
              <p className="text-[11px] text-text-tertiary">
                Webhook: {readiness.stripe.staging.webhook_events.join(" · ")} · 成功页 {readiness.stripe.staging.success_page_path}
              </p>
            </section>
          )}

          {readiness.storage.staging && (
            <section className="rounded-xl border border-cosmic-border bg-cosmic-elevated p-4">
              <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Cloud className="w-4 h-4 text-brand" />
                CDN / 存储 Staging
                <span className={cn(
                  "text-xs font-normal px-2 py-0.5 rounded-full",
                  readiness.storage.staging.staging_ready
                    ? "bg-success/15 text-success"
                    : "bg-amber-500/15 text-amber-600",
                )}>
                  {readiness.storage.staging.staging_ready ? "就绪" : "待配置"}
                </span>
              </h2>
              <ul className="space-y-1.5 text-xs text-text-secondary mb-2">
                {readiness.storage.staging.checklist.map((item) => (
                  <li key={item.id} className="flex items-center gap-2">
                    {item.ok ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-success shrink-0" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                    )}
                    <span>{item.label}{item.required ? " *" : ""}</span>
                  </li>
                ))}
              </ul>
              <p className="text-[11px] text-text-tertiary font-mono truncate">
                public base: {readiness.storage.staging.public_media_base}
              </p>
            </section>
          )}

          {readiness.go_live && (
            <section className="rounded-xl border border-cosmic-border bg-cosmic-elevated p-4">
              <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Activity className="w-4 h-4 text-brand" />
                Go-Live 总览
                <span className={cn(
                  "text-xs font-normal px-2 py-0.5 rounded-full",
                  readiness.go_live.go_live_ok
                    ? "bg-success/15 text-success"
                    : "bg-amber-500/15 text-amber-600",
                )}>
                  {readiness.go_live.go_live_ok ? "可上线" : "未达标"}
                </span>
              </h2>
              <div className="flex flex-wrap gap-3 text-xs text-text-secondary mb-3">
                <span>收款: {readiness.go_live.revenue_ready ? "✓" : "✗"}</span>
                <span>CDN: {readiness.go_live.media_ready ? "✓" : "✗"}</span>
                <span>
                  Live KPI: {readiness.go_live.live_kpi_ready === null ? "—" : readiness.go_live.live_kpi_ready ? "✓" : "✗"}
                </span>
              </div>
              {readiness.live_kpi && (
                <p className="text-[11px] text-text-tertiary mb-2">
                  出片 KPI · video {readiness.live_kpi.video_outframe_ok}/{readiness.live_kpi.targets.video_outframe_min}
                  {" · "}image {readiness.live_kpi.image_outframe_ok}/{readiness.live_kpi.targets.image_outframe_min}
                  {readiness.live_kpi.note ? ` · ${readiness.live_kpi.note}` : ""}
                </p>
              )}
              {readiness.go_live.blockers.length > 0 && (
                <ul className="text-[11px] text-amber-600/90 space-y-0.5">
                  {readiness.go_live.blockers.slice(0, 6).map((b) => (
                    <li key={b}>· {b}</li>
                  ))}
                </ul>
              )}
            </section>
          )}

          <section className="rounded-xl border border-cosmic-border bg-cosmic-elevated p-4">
            <h2 className="text-sm font-medium mb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand" />
              模型货架 · {readiness.catalog.active_count} / {readiness.catalog.active_target} active
            </h2>
            <div className="flex flex-wrap gap-4 text-sm text-text-secondary mb-4">
              <span>beta: {readiness.catalog.beta_count}</span>
              <span>Smoke 自动晋升: {readiness.smoke.auto_promote_enabled ? "开启" : "关闭"}</span>
              <span>Mapping 晋升: {readiness.smoke.mapping_promote_enabled ? "开启" : "关闭"}</span>
              {readiness.smoke.last_ts && (
                <span>最近 smoke: {readiness.smoke.last_ts} · outframe {readiness.smoke.outframe_ok ?? 0}</span>
              )}
              {readiness.smoke.last_auto_promote && readiness.smoke.last_auto_promote.count > 0 && (
                <span>最近 auto-promote: {readiness.smoke.last_auto_promote.promoted.join(", ")}</span>
              )}
              {readiness.ops_alerts && (
                <span>Webhook 告警: {readiness.ops_alerts.webhook_failure_alerts ? "已配置" : "未配置"}</span>
              )}
              {readiness.ops_alerts?.digest_enabled && (
                <span>Digest 聚合: 开启</span>
              )}
              {readiness.ops_alerts?.digest_beat_hourly && (
                <span>Digest Beat: 小时</span>
              )}
            </div>
            {promotable && promotable.promotable.length > 0 ? (
              <div className="space-y-2">
                {promotable.promotable.map((m) => (
                  <div key={m.model_id} className="flex flex-wrap items-center justify-between gap-2 py-2 border-t border-cosmic-border/50 first:border-t-0">
                    <div>
                      <p className="text-sm font-medium">{m.display_name}</p>
                      <p className="text-xs text-text-tertiary font-mono">{m.model_id} · {m.media_types.join(", ")}</p>
                      {m.last_smoke && (
                        <p className="text-[11px] text-text-secondary mt-0.5">
                          smoke: {m.last_smoke.ok ? "ok" : "fail"} · {m.last_smoke.path || "—"}
                        </p>
                      )}
                    </div>
                    <button
                      type="button"
                      disabled={busy === m.model_id}
                      onClick={() => handlePromote(m.model_id)}
                      className="px-3 py-1.5 rounded-lg text-xs bg-brand text-white hover:bg-brand-strong disabled:opacity-50"
                    >
                      {busy === m.model_id ? "晋升中…" : "晋升 active"}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-tertiary">暂无可晋升 beta 模型（需 KIE 映射白名单）</p>
            )}
          </section>

          <section className="rounded-xl border border-cosmic-border bg-cosmic-elevated p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
              <h2 className="text-sm font-medium flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                Webhook 投递失败
                <span className="text-text-tertiary font-normal">({webhookFailures.length})</span>
              </h2>
              <div className="flex flex-wrap gap-2">
                {token && (
                  <button
                    type="button"
                    disabled={whBusy === "digest"}
                    onClick={async () => {
                      setWhBusy("digest");
                      try {
                        await sendWebhookFailuresDigest(token);
                        const digest = await getWebhookFailuresDigest(token);
                        setWebhookDigest(digest);
                      } catch (e: unknown) {
                        setError(e instanceof Error ? e.message : "Digest 发送失败");
                      } finally {
                        setWhBusy(null);
                      }
                    }}
                    className="px-2 py-1 rounded text-xs border border-cosmic-border hover:bg-cosmic-subtle disabled:opacity-50"
                  >
                    {whBusy === "digest" ? "发送中…" : "发送 Digest"}
                  </button>
                )}
                {webhookFailures.length > 0 && (
                <button
                  type="button"
                  disabled={whBusy === "all"}
                  onClick={async () => {
                    if (!token) return;
                    setWhBusy("all");
                    try {
                      await retryAllWebhookFailures(token);
                      const wh = await getWebhookFailures(token);
                      setWebhookFailures(wh.failures);
                    } catch (e: unknown) {
                      setError(e instanceof Error ? e.message : "批量重试失败");
                    } finally {
                      setWhBusy(null);
                    }
                  }}
                  className="px-2 py-1 rounded text-xs border border-cosmic-border hover:bg-cosmic-subtle disabled:opacity-50"
                >
                  {whBusy === "all" ? "重试中…" : "全部重试"}
                </button>
                )}
              </div>
            </div>
            {webhookDigest && webhookDigest.total > 0 && (
              <div className="mb-3 p-2 rounded-lg bg-amber-500/5 border border-amber-500/20 text-xs space-y-1">
                <p className="text-text-secondary">
                  聚合摘要 · {webhookDigest.total} 失败 · 已告警 {webhookDigest.alert_sent_count} · 待告警 {webhookDigest.pending_alert}
                </p>
                {webhookDigest.top_reasons.length > 0 && (
                  <p className="text-text-tertiary truncate">
                    主因: {webhookDigest.top_reasons.map((r) => `${r.reason} (${r.count})`).join(" · ")}
                  </p>
                )}
              </div>
            )}
            {webhookFailures.length > 0 ? (
              <div className="space-y-2 max-h-56 overflow-y-auto">
                {webhookFailures.map((f) => (
                  <div key={f.task_id} className="text-xs border-t border-cosmic-border/50 pt-2 first:border-t-0 first:pt-0 flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-mono text-text-primary">{f.task_id.slice(0, 12)}… · {f.status}</p>
                      <p className="text-text-secondary truncate">{f.webhook_url}</p>
                      <p className="text-amber-600/90">
                        {f.status_code ? `HTTP ${f.status_code}` : "—"} · {f.attempts ?? "?"} 次 · {f.reason || "未知错误"}
                      </p>
                    </div>
                    <button
                      type="button"
                      disabled={whBusy === f.task_id}
                      onClick={async () => {
                        if (!token) return;
                        setWhBusy(f.task_id);
                        try {
                          await retryWebhookDelivery(token, f.task_id);
                          const wh = await getWebhookFailures(token);
                          setWebhookFailures(wh.failures);
                        } catch (e: unknown) {
                          setError(e instanceof Error ? e.message : "重试失败");
                        } finally {
                          setWhBusy(null);
                        }
                      }}
                      className="shrink-0 px-2 py-1 rounded text-xs bg-brand/90 text-white hover:bg-brand disabled:opacity-50"
                    >
                      {whBusy === f.task_id ? "…" : "重试"}
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-tertiary">暂无失败记录</p>
            )}
          </section>

          {lastSmoke?.available && lastSmoke.report && (
            <section className="rounded-xl border border-cosmic-border bg-cosmic-elevated p-4">
              <h2 className="text-sm font-medium mb-2 flex items-center gap-2">
                <Activity className="w-4 h-4" />
                最近 Smoke 报告
              </h2>
              <pre className="text-[11px] text-text-secondary overflow-x-auto max-h-48">
                {JSON.stringify(lastSmoke.report, null, 2)}
              </pre>
            </section>
          )}
        </>
      ) : null}
    </div>
  );
}

function ReadinessCard({
  title, icon: Icon, ok, blockers, details,
}: {
  title: string;
  icon: typeof CreditCard;
  ok: boolean;
  blockers: string[];
  details: { k: string; v: string }[];
}) {
  return (
    <div className={cn(
      "rounded-xl border p-4",
      ok ? "border-emerald-500/30 bg-emerald-500/5" : "border-amber-500/30 bg-amber-500/5",
    )}>
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-4 h-4 text-brand" />
        <h3 className="text-sm font-medium">{title}</h3>
        {ok ? (
          <CheckCircle2 className="w-4 h-4 text-emerald-500 ml-auto" />
        ) : (
          <XCircle className="w-4 h-4 text-amber-500 ml-auto" />
        )}
      </div>
      <dl className="text-xs space-y-1 text-text-secondary">
        {details.map((d) => (
          <div key={d.k} className="flex justify-between gap-2">
            <dt>{d.k}</dt>
            <dd className="font-mono text-text-primary">{d.v}</dd>
          </div>
        ))}
      </dl>
      {blockers.length > 0 && (
        <ul className="mt-2 text-[11px] text-amber-600 space-y-0.5">
          {blockers.map((b) => <li key={b}>· {b}</li>)}
        </ul>
      )}
    </div>
  );
}
