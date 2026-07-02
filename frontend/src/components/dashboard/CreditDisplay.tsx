"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Coins, Plus } from "lucide-react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { cn } from "@/lib/utils";

/* ═══════════════════════════════════════════════════════
   CreditDisplay — Lovable 风格积分显示
   带数字滚动动画 · AURORA 亮色
   ═══════════════════════════════════════════════════════ */

export function CreditDisplay({
  credits,
  to = "/pricing",
}: {
  credits: number;
  to?: string;
}) {
  const mv = useMotionValue(0);
  const rounded = useTransform(mv, (v) => Math.round(v).toLocaleString());

  useEffect(() => {
    const controls = animate(mv, credits, { duration: 0.6, ease: "easeOut" });
    return () => controls.stop();
  }, [credits, mv]);

  return (
    <Link
      href={to}
      className={cn(
        "inline-flex items-center gap-1.5 h-8 px-3 rounded-full",
        "bg-brand/[0.08] text-brand text-xs font-semibold",
        "hover:bg-brand/[0.14] transition-colors",
        "border border-brand/10"
      )}
    >
      <Coins className="w-3.5 h-3.5" />
      <motion.span>{rounded}</motion.span>
      <Plus className="w-3 h-3 opacity-50" />
    </Link>
  );
}

export default CreditDisplay;
