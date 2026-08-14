"use client";

import Link from "next/link";
import { CircleDollarSign, Clock, Layers, Users, Info } from "lucide-react";
import type { GenerationQuote } from "@/lib/api";
import { useLocale } from "@/i18n/LocaleProvider";
import { cn } from "@/lib/utils";

function formatEta(seconds: number): string {
  if (!seconds || seconds < 5) return "<5s";
  if (seconds < 60) return `~${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return s ? `~${m}m${s}s` : `~${m}m`;
}

export function QuoteBar({
  quote,
  fallbackCredits,
  className,
}: {
  quote: GenerationQuote | null;
  fallbackCredits?: number | null;
  className?: string;
}) {
  const { t, locale } = useLocale();
  const en = locale === "en";
  const credits = quote?.estimated_cost_credits ?? fallbackCredits ?? null;
  const eta = quote?.estimated_time_seconds;
  const queue = quote?.queue_ahead ?? 0;
  const used = quote?.concurrent_used;
  const limit = quote?.concurrent_limit;

  return (
    <div
      data-testid="quote-bar"
      className={cn("ml-auto flex flex-wrap items-center justify-end gap-x-3 gap-y-1 text-[11px] text-text-secondary/80 pr-1", className)}
      title={quote?.honesty || (en ? "Catalog ETA — not a live SLA" : "目录均时，不是实时 SLA")}
    >
      <span className="inline-flex items-center gap-1" title={t("quote.credits")}>
        <CircleDollarSign className="w-3.5 h-3.5 text-accent-cyan/90" />
        <span className="font-medium text-text-primary/90">{credits != null ? credits : "—"}</span>
      </span>
      <span className="inline-flex items-center gap-1" title={t("quote.eta")}>
        <Clock className="w-3.5 h-3.5" />
        {eta != null ? formatEta(eta) : "—"}
      </span>
      <span className="inline-flex items-center gap-1" title={t("quote.queue")}>
        <Layers className="w-3.5 h-3.5" />
        {queue}
      </span>
      {used != null && limit != null && (
        <span className="inline-flex items-center gap-1" title={t("quote.concurrent")}>
          <Users className="w-3.5 h-3.5" />
          {used}/{limit}
        </span>
      )}
      <span className="inline-flex items-center gap-0.5 text-text-tertiary" title={t("quote.refund")}>
        <Info className="w-3 h-3 opacity-45" />
        {quote?.demo_mode ? t("quote.demo") : t("quote.refund")}
      </span>
      {quote?.upgrade_hint && quote.concurrent_remaining != null && quote.concurrent_remaining <= 1 && (
        <Link href="/pricing" className="text-brand hover:underline">{en ? "Upgrade" : "升级"}</Link>
      )}
    </div>
  );
}
