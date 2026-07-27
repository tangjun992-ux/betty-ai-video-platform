"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

const KEY = "betty-cookie-consent";

/* ═══════════════════════════════════════════════════════
   CookieConsent — STUDIO v5
   紧凑型底部横条: 不遮挡任何主 CTA, 移动端全宽, 桌面左下
   ═══════════════════════════════════════════════════════ */
export function CookieConsent() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    try { if (!localStorage.getItem(KEY)) setShow(true); } catch {}
  }, []);

  const decide = (value: "all" | "necessary") => {
    try { localStorage.setItem(KEY, JSON.stringify({ value, at: Date.now() })); } catch {}
    setShow(false);
  };

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 16 }}
          transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
          className="fixed bottom-0 inset-x-0 md:inset-x-auto md:bottom-4 md:left-4 md:max-w-sm z-[60]"
          role="dialog" aria-label="Cookie 同意"
        >
          <div className="rounded-t-xl md:rounded-xl bg-cosmic-elevated border border-cosmic-border shadow-elevation-lg px-4 py-3">
            <p className="text-xs text-text-secondary leading-relaxed">
              我们使用必要 Cookie 维持登录与偏好，同意后经分析改进产品。详见
              <Link href="/privacy" className="text-brand-strong hover:underline mx-1">隐私政策</Link>。
            </p>
            <div className="flex items-center gap-2 mt-2.5">
              <button onClick={() => decide("all")} className="btn-primary h-7 px-3.5 text-xs">接受全部</button>
              <button onClick={() => decide("necessary")} className="btn-ghost h-7 px-3 text-xs">仅必要</button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
