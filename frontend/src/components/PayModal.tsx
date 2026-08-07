"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Loader2, CheckCircle2, ScanLine, CreditCard } from "lucide-react";
import { createPayOrder, getPayStatus, mockConfirmPay, getPayMethods, getBillingSummary, checkout } from "@/lib/api";
import { cn } from "@/lib/utils";

type Method = "wechat" | "alipay" | "stripe";

export interface PayTarget { kind: "plan" | "pack"; id: string; cycle?: "monthly" | "yearly"; }

const METHOD_META: Record<Exclude<Method, "stripe">, { label: string; color: string; icon: string }> = {
  wechat: { label: "微信支付", color: "text-[#07C160]", icon: "💬" },
  alipay: { label: "支付宝", color: "text-[#1677FF]", icon: "🅰️" },
};

export function PayModal({ target, onClose, onPaid }: { target: PayTarget | null; onClose: () => void; onPaid?: (balance: number) => void; }) {
  const [method, setMethod] = useState<Method>("wechat");
  const [order, setOrder] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [paid, setPaid] = useState(false);
  const [live, setLive] = useState<Record<string, boolean>>({});
  const [stripeEnabled, setStripeEnabled] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getPayMethods().then((m) => setLive({ wechat: m.methods.wechat?.live, alipay: m.methods.alipay?.live })).catch(() => {});
    getBillingSummary().then((s) => setStripeEnabled(!!s.stripe_enabled)).catch(() => {});
  }, []);

  const stopPoll = () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; } };

  const openOrder = useCallback(async (m: Method) => {
    if (!target) return;
    if (m === "stripe") {
      setLoading(true);
      try {
        await checkout(target.kind, target.id, target.cycle || "monthly");
      } catch {
        /* redirect or dev-grant handled in checkout() */
      } finally {
        setLoading(false);
      }
      return;
    }
    setLoading(true); setPaid(false); setOrder(null); stopPoll();
    try {
      const o = await createPayOrder(target.kind, target.id, m, target.cycle || "monthly");
      setOrder(o);
      pollRef.current = setInterval(async () => {
        try {
          const s = await getPayStatus(o.order_no);
          if (s.status === "paid") {
            stopPoll(); setPaid(true);
            try { window.dispatchEvent(new Event("betty:credits")); } catch {}
            onPaid?.(s.balance);
          }
        } catch {}
      }, 2000);
    } catch (e) { /* surfaced by caller toast normally */ }
    finally { setLoading(false); }
  }, [target, onPaid]);

  useEffect(() => {
    if (target) {
      if (stripeEnabled && method === "stripe") openOrder("stripe");
      else if (method !== "stripe") openOrder(method);
    }
    return stopPoll;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, stripeEnabled]);

  const switchMethod = (m: Method) => { setMethod(m); openOrder(m); };

  const simulate = async () => {
    if (!order) return;
    try { const r = await mockConfirmPay(order.order_no); stopPoll(); setPaid(true); try { window.dispatchEvent(new Event("betty:credits")); } catch {} onPaid?.(r.balance); } catch {}
  };

  const qrMethods: Exclude<Method, "stripe">[] = ["wechat", "alipay"];

  return (
    <AnimatePresence>
      {target && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={onClose}>
          <motion.div initial={{ scale: 0.96, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.98, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-sm rounded-2xl bg-cosmic-surface border border-cosmic-border overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b border-cosmic-border">
              <span className="font-semibold text-text-primary">{method === "stripe" ? "Stripe 结算" : "扫码支付"}</span>
              <button onClick={onClose} className="btn-icon"><X className="w-4 h-4" /></button>
            </div>

            {/* Method tabs */}
            <div className="flex gap-2 p-4 pb-0 flex-wrap">
              {qrMethods.map((m) => (
                <button key={m} onClick={() => switchMethod(m)}
                  className={cn("flex-1 min-w-[40%] flex items-center justify-center gap-1.5 py-2 rounded-xl text-sm font-medium border transition-all",
                    method === m ? "bg-brand/[0.08] text-brand border-brand/30" : "bg-cosmic-subtle border-cosmic-border text-text-secondary hover:text-text-primary")}>
                  <span>{METHOD_META[m].icon}</span> {METHOD_META[m].label}
                </button>
              ))}
              {stripeEnabled && (
                <button onClick={() => switchMethod("stripe")}
                  className={cn("flex-1 min-w-[40%] flex items-center justify-center gap-1.5 py-2 rounded-xl text-sm font-medium border transition-all",
                    method === "stripe" ? "bg-brand/[0.08] text-brand border-brand/30" : "bg-cosmic-subtle border-cosmic-border text-text-secondary hover:text-text-primary")}>
                  <CreditCard className="w-4 h-4" /> Stripe
                </button>
              )}
            </div>

            <div className="p-5 flex flex-col items-center">
              {method === "stripe" ? (
                <div className="py-10 flex flex-col items-center gap-3 text-center">
                  {loading ? (
                    <Loader2 className="w-10 h-10 animate-spin text-brand" />
                  ) : (
                    <>
                      <CreditCard className="w-12 h-12 text-brand" />
                      <p className="text-sm text-text-secondary">正在跳转 Stripe Checkout…</p>
                      <button onClick={() => openOrder("stripe")} className="btn-primary mt-2 text-sm">重新打开结算页</button>
                    </>
                  )}
                </div>
              ) : paid ? (
                <div className="py-10 flex flex-col items-center gap-3">
                  <CheckCircle2 className="w-14 h-14 text-success" />
                  <p className="text-lg font-semibold text-text-primary">支付成功</p>
                  <p className="text-sm text-text-secondary">+{order?.credits} 积分已到账</p>
                  <button onClick={onClose} className="btn-primary mt-2">完成</button>
                </div>
              ) : loading || !order ? (
                <div className="py-16"><Loader2 className="w-8 h-8 animate-spin text-brand" /></div>
              ) : (
                <>
                  <div className="relative w-48 h-48 rounded-xl overflow-hidden ring-1 ring-cosmic-border bg-white p-2">
                    <img src={order.qr_image} alt="支付二维码" className="w-full h-full object-contain" />
                  </div>
                  <p className={cn("mt-3 text-sm flex items-center gap-1.5", METHOD_META[method as Exclude<Method, "stripe">].color)}>
                    <ScanLine className="w-4 h-4" /> 请用{METHOD_META[method as Exclude<Method, "stripe">].label}扫码支付
                  </p>
                  <div className="mt-2 text-center">
                    <div className="text-2xl font-bold text-text-primary">¥{order.amount_cny}</div>
                    <div className="text-xs text-text-tertiary">{order.label} · {order.credits} 积分</div>
                  </div>
                  <div className="mt-3 flex items-center gap-1.5 text-xs text-text-tertiary">
                    <Loader2 className="w-3 h-3 animate-spin" /> 等待支付…
                  </div>
                  {live[method as Exclude<Method, "stripe">] === false && (
                    <div className="mt-4 w-full">
                      <button onClick={simulate} className="btn-secondary w-full text-sm">模拟已支付（开发环境）</button>
                      <p className="text-[11px] text-text-tertiary text-center mt-2">
                        沙箱模式：未接入{METHOD_META[method as Exclude<Method, "stripe">].label}商户号。配置商户凭据 + 公网回调后自动切换真实收款。
                      </p>
                    </div>
                  )}
                </>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
