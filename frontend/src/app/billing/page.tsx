"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Zap, Loader2, Check, TrendingUp, TrendingDown, Gift, Sparkles, BarChart3, Receipt, RotateCcw, X } from "lucide-react";
import { getBillingSummary, getCreditPacks, getTransactions, getUsage, refundOrder, getReceipt } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { PayModal, type PayTarget } from "@/components/PayModal";
import { cn } from "@/lib/utils";

const TYPE_META: Record<string, { label: string; cls: string }> = {
  purchase: { label: "充值", cls: "text-success" },
  consumption: { label: "消耗", cls: "text-text-secondary" },
  refund: { label: "退款", cls: "text-success" },
  bonus: { label: "赠送", cls: "text-brand" },
  daily_free: { label: "每日免费", cls: "text-brand" },
};

export default function BillingPage() {
  const toast = useToast();
  const [summary, setSummary] = useState<any>(null);
  const [packs, setPacks] = useState<any[]>([]);
  const [txns, setTxns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [payTarget, setPayTarget] = useState<PayTarget | null>(null);
  const [usage, setUsage] = useState<any>(null);
  const [receipt, setReceipt] = useState<any>(null);

  const load = useCallback(async () => {
    try {
      const [s, p, t, u] = await Promise.all([getBillingSummary(), getCreditPacks(), getTransactions(30), getUsage(30)]);
      setSummary(s); setPacks(p.packs || []); setTxns(t.transactions || []); setUsage(u);
    } catch (e: any) { toast.error("加载失败", e.message || ""); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const buy = (packId: string) => setPayTarget({ kind: "pack", id: packId });

  const doRefund = async (orderNo: string) => {
    if (!confirm("确认申请退款？将返还本单积分（已消耗部分不可退）。")) return;
    try { const r = await refundOrder(orderNo); toast.success("退款成功", `已退回 ${r.refunded_credits} 积分`); window.dispatchEvent(new Event("betty:credits")); await load(); }
    catch (e: any) { toast.error("退款失败", e.message || ""); }
  };
  const showReceipt = async (orderNo: string) => {
    try { setReceipt(await getReceipt(orderNo)); } catch (e: any) { toast.error("加载收据失败", e.message || ""); }
  };
  const maxDaily = Math.max(1, ...((usage?.daily || []).map((d: any) => d.credits)));

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold gradient-text-static">积分中心</h1>
        <p className="text-text-secondary text-sm mt-1">管理你的积分余额、充值与消费流水</p>
      </div>

      {/* Balance hero */}
      <div className="rounded-2xl border border-cosmic-border bg-gradient-to-br from-brand/[0.06] via-cosmic-surface to-accent-fuchsia/[0.04] p-6 mb-8">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="text-xs text-text-tertiary mb-1">当前可用积分</div>
            <div className="flex items-center gap-2">
              <Zap className="w-7 h-7 text-brand" />
              <span className="text-4xl font-bold text-text-primary tracking-tight">
                {loading ? "—" : (summary?.credits ?? 0).toLocaleString()}
              </span>
            </div>
            {summary && (
              <div className="flex gap-4 mt-2 text-xs text-text-tertiary">
                <span>充值积分 {summary.purchased_credits?.toLocaleString?.() ?? 0}</span>
                <span>每日免费 {summary.daily_credits}/{summary.daily_credits_max}</span>
                <span>累计消耗 {summary.total_spent?.toLocaleString?.() ?? 0}</span>
              </div>
            )}
          </div>
          <Link href="/pricing" className="btn-secondary"><Sparkles className="w-4 h-4" /> 查看订阅套餐</Link>
        </div>
        {summary && !summary.stripe_enabled && (
          <div className="mt-4 text-[11px] text-text-tertiary bg-cosmic-subtle border border-cosmic-border rounded-lg px-3 py-2">
            开发模式：充值即时到账（未接入支付网关）。配置 <code>STRIPE_API_KEY</code> 后自动切换为真实 Stripe 结算。
          </div>
        )}
      </div>

      {/* Credit packs */}
      <h2 className="text-lg font-semibold text-text-primary mb-4">积分充值</h2>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {(loading ? Array.from({ length: 4 }) : packs).map((pk: any, i: number) => (
          pk ? (
            <div key={pk.id} className={cn("relative rounded-2xl border p-5 flex flex-col gap-3 bg-cosmic-surface", pk.highlighted ? "border-brand/40 shadow-md" : "border-cosmic-border")}>
              {pk.highlighted && <span className="absolute -top-2 left-1/2 -translate-x-1/2 badge-cyan">超值</span>}
              <div className="text-sm font-semibold text-text-primary">{pk.name}</div>
              <div className="flex items-end gap-1">
                <span className="text-3xl font-bold text-text-primary tracking-tight">{pk.credits.toLocaleString()}</span>
                <span className="text-xs text-text-tertiary mb-1">积分</span>
              </div>
              {pk.bonus > 0 && <div className="inline-flex items-center gap-1 text-[11px] text-brand"><Gift className="w-3 h-3" /> 额外赠送 {pk.bonus}</div>}
              <div className="text-sm text-text-secondary">${pk.price_usd}</div>
              <button onClick={() => buy(pk.id)} className="btn-primary w-full mt-auto text-sm">
                <Zap className="w-4 h-4" /> 购买
              </button>
            </div>
          ) : <div key={i} className="aspect-[3/4] rounded-2xl skeleton" />
        ))}
      </div>

      {/* Usage report */}
      {usage && (usage.total_spent > 0 || (usage.by_model || []).length > 0) && (
        <div className="mb-10">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2"><BarChart3 className="w-4.5 h-4.5 text-brand" /> 用量概览 · 近 {usage.period_days} 天</h2>
          <div className="grid md:grid-cols-3 gap-4">
            <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-4">
              <div className="text-xs text-text-tertiary mb-1">消耗积分</div>
              <div className="text-2xl font-bold text-text-primary">{usage.total_spent.toLocaleString()}</div>
              <div className="text-xs text-text-tertiary mt-1">完成任务 {usage.task_count}</div>
            </div>
            <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-4 md:col-span-2">
              <div className="text-xs text-text-tertiary mb-2">按模型</div>
              <div className="space-y-1.5">
                {(usage.by_model || []).slice(0, 5).map((m: any) => {
                  const pct = usage.total_spent ? Math.round((m.credits / usage.total_spent) * 100) : 0;
                  return (
                    <div key={m.model} className="flex items-center gap-2">
                      <span className="text-xs text-text-secondary w-32 truncate">{m.model}</span>
                      <div className="flex-1 h-2 rounded-full bg-cosmic-subtle overflow-hidden">
                        <div className="h-full bg-brand rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-text-tertiary w-14 text-right">{m.credits}</span>
                    </div>
                  );
                })}
                {(usage.by_model || []).length === 0 && <div className="text-xs text-text-tertiary">暂无消耗</div>}
              </div>
            </div>
          </div>
          {(usage.daily || []).length > 1 && (
            <div className="mt-4 rounded-2xl border border-cosmic-border bg-cosmic-surface p-4">
              <div className="text-xs text-text-tertiary mb-2">每日消耗</div>
              <div className="flex items-end gap-1 h-20">
                {usage.daily.map((d: any) => (
                  <div key={d.day} className="flex-1 group relative flex flex-col justify-end" title={`${d.day}: ${d.credits}`}>
                    <div className="w-full bg-brand/70 group-hover:bg-brand rounded-t transition-colors" style={{ height: `${Math.max(4, (d.credits / maxDaily) * 100)}%` }} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Transactions */}
      <h2 className="text-lg font-semibold text-text-primary mb-4">积分流水</h2>
      <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface overflow-hidden">
        {loading ? (
          <div className="p-6 space-y-3">{[...Array(4)].map((_, i) => <div key={i} className="h-6 skeleton rounded" />)}</div>
        ) : txns.length === 0 ? (
          <div className="p-10 text-center text-text-tertiary text-sm">暂无流水记录</div>
        ) : (
          <div className="divide-y divide-cosmic-border">
            {txns.map((t) => {
              const meta = TYPE_META[t.type] || { label: t.type, cls: "text-text-secondary" };
              const positive = t.amount >= 0;
              return (
                <div key={t.id} className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className={cn("w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0", positive ? "bg-success/10 text-success" : "bg-cosmic-subtle text-text-secondary")}>
                      {positive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                    </span>
                    <div className="min-w-0">
                      <div className="text-sm text-text-primary truncate">{t.description || meta.label}</div>
                      <div className="text-[11px] text-text-tertiary">{meta.label} · {(t.created_at || "").slice(0, 19).replace("T", " ")}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    {t.type === "purchase" && t.payment_id && (
                      <div className="flex items-center gap-1">
                        <button onClick={() => showReceipt(t.payment_id)} title="收据" className="btn-icon w-7 h-7 text-text-tertiary hover:text-brand"><Receipt className="w-3.5 h-3.5" /></button>
                        <button onClick={() => doRefund(t.payment_id)} title="退款" className="btn-icon w-7 h-7 text-text-tertiary hover:text-destructive"><RotateCcw className="w-3.5 h-3.5" /></button>
                      </div>
                    )}
                    <div className="text-right">
                      <div className={cn("text-sm font-semibold", positive ? "text-success" : "text-text-primary")}>{positive ? "+" : ""}{t.amount}</div>
                      <div className="text-[11px] text-text-tertiary">余额 {t.balance_after}</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <PayModal target={payTarget} onClose={() => setPayTarget(null)} onPaid={() => load()} />

      {/* Receipt modal */}
      {receipt && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={() => setReceipt(null)}>
          <div className="w-full max-w-sm rounded-2xl bg-cosmic-surface border border-cosmic-border overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-3 border-b border-cosmic-border">
              <span className="font-semibold text-text-primary flex items-center gap-2"><Receipt className="w-4 h-4 text-brand" /> 购买收据</span>
              <button onClick={() => setReceipt(null)} className="btn-icon"><X className="w-4 h-4" /></button>
            </div>
            <div className="p-5 space-y-2.5 text-sm">
              <div className="text-center pb-3 border-b border-dashed border-cosmic-border">
                <div className="font-bold text-text-primary">{receipt.merchant}</div>
                <div className="text-xs text-text-tertiary">收据 · Receipt</div>
              </div>
              {[["商品", receipt.label], ["积分", `${receipt.credits}`], ["金额 (USD)", `$${receipt.amount_usd}`], ["金额 (CNY)", `¥${receipt.amount_cny}`], ["支付方式", receipt.provider], ["状态", receipt.status], ["订单号", receipt.order_no], ["日期", (receipt.created_at || "").slice(0, 19).replace("T", " ")]].map(([k, v]) => (
                <div key={k as string} className="flex justify-between gap-3">
                  <span className="text-text-tertiary">{k}</span>
                  <span className="text-text-primary font-medium text-right break-all">{v as string}</span>
                </div>
              ))}
              <button onClick={() => window.print()} className="btn-secondary w-full mt-3 text-sm">打印 / 保存 PDF</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
