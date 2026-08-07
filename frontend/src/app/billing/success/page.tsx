"use client";

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { CheckCircle2, Loader2, Zap, ArrowRight } from "lucide-react";
import { getBillingSummary } from "@/lib/api";

function SuccessContent() {
  const params = useSearchParams();
  const sessionId = params.get("session_id");
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBillingSummary()
      .then((s) => {
        setSummary(s);
        try { window.dispatchEvent(new Event("betty:credits")); } catch {}
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-lg mx-auto px-4 py-16 text-center">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <CheckCircle2 className="w-16 h-16 text-success mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-text-primary mb-2">支付成功</h1>
        <p className="text-text-secondary text-sm mb-6">
          {sessionId
            ? "Stripe 结算已完成，积分与套餐权益将在数秒内同步到账。"
            : "您的充值或订阅已处理，积分已更新。"}
        </p>

        {loading ? (
          <Loader2 className="w-6 h-6 animate-spin text-brand mx-auto" />
        ) : summary ? (
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
