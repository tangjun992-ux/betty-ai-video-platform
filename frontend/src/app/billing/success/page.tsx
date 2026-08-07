"use client";

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { CheckCircle2, Loader2, Zap, ArrowRight } from "lucide-react";
import { getBillingSummary, syncStripeSession } from "@/lib/api";

function SuccessContent() {
  const params = useSearchParams();
  const sessionId = params.get("session_id");
  const [summary, setSummary] = useState<any>(null);
  const [syncing, setSyncing] = useState(true);
  const [syncNote, setSyncNote] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      let baseline = 0;
      try {
        const initial = await getBillingSummary();
        if (cancelled) return;
        baseline = initial.credits ?? 0;
        setSummary(initial);
      } catch { /* offline */ }

      if (sessionId) {
        try {
          const r = await syncStripeSession(sessionId);
          if (!cancelled && r.summary) setSummary(r.summary);
          else if (!cancelled) {
            const s = await getBillingSummary();
            setSummary(s);
          }
          if (!cancelled) setSyncNote(r.synced ? "Stripe 积分已同步" : "支付已确认，等待入账…");
        } catch {
          if (!cancelled) setSyncNote("正在等待 Stripe 回调…");
        }
      }

      for (let i = 0; i < (sessionId ? 15 : 3); i++) {
        if (cancelled) return;
        await new Promise((r) => setTimeout(r, 2000));
        try {
          const s = await getBillingSummary();
          if (cancelled) return;
          setSummary(s);
          if ((s.credits ?? 0) > baseline) {
            setSyncNote("积分已更新");
            break;
          }
        } catch { /* retry */ }
      }

      if (!cancelled) {
        setSyncing(false);
        try { window.dispatchEvent(new Event("betty:credits")); } catch {}
      }
    })();

    return () => { cancelled = true; };
  }, [sessionId]);

  return (
    <div className="max-w-lg mx-auto px-4 py-16 text-center">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <CheckCircle2 className="w-16 h-16 text-success mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-text-primary mb-2">支付成功</h1>
        <p className="text-text-secondary text-sm mb-2">
          {sessionId ? "Stripe 结算已完成。" : "您的充值或订阅已处理。"}
        </p>
        {syncing && (
          <p className="text-xs text-brand mb-4 inline-flex items-center gap-1.5 justify-center">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> 正在同步积分与套餐…
          </p>
        )}
        {syncNote && !syncing && (
          <p className="text-xs text-text-tertiary mb-4">{syncNote}</p>
        )}

        {summary ? (
          <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-6 mb-8">
            <div className="text-xs text-text-tertiary mb-1">当前可用积分</div>
            <div className="flex items-center justify-center gap-2">
              <Zap className="w-6 h-6 text-brand" />
              <span className="text-3xl font-bold text-text-primary">{(summary.credits ?? 0).toLocaleString()}</span>
            </div>
            {summary.plan && (
              <p className="text-xs text-text-tertiary mt-2">当前套餐：{summary.plan}</p>
            )}
          </div>
        ) : syncing ? (
          <Loader2 className="w-6 h-6 animate-spin text-brand mx-auto mb-8" />
        ) : null}

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href="/create" className="btn-primary inline-flex items-center justify-center gap-2">
            开始创作 <ArrowRight className="w-4 h-4" />
          </Link>
          <Link href="/billing" className="btn-secondary inline-flex items-center justify-center">
            查看账单
          </Link>
        </div>
      </motion.div>
    </div>
  );
}

export default function BillingSuccessPage() {
  return (
    <Suspense fallback={<div className="py-20 text-center"><Loader2 className="w-8 h-8 animate-spin text-brand mx-auto" /></div>}>
      <SuccessContent />
    </Suspense>
  );
}
