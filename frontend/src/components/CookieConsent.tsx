"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Cookie } from "lucide-react";

const KEY = "betty-cookie-consent";

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
          initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 24 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="fixed bottom-4 inset-x-4 md:inset-x-auto md:right-6 md:max-w-md z-[70]"
          role="dialog" aria-label="Cookie 同意"
        >
          <div className="rounded-2xl bg-cosmic-surface border border-cosmic-border shadow-elevation-lg p-4">
            <div className="flex items-start gap-3">
              <span className="w-9 h-9 rounded-xl bg-brand/[0.08] border border-brand/15 flex items-center justify-center flex-shrink-0">
                <Cookie className="w-4.5 h-4.5 text-brand" />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-text-primary mb-1">我们使用 Cookie</p>
                <p className="text-xs text-text-secondary leading-relaxed">
                  我们使用必要 Cookie 维持登录与偏好，并在您同意后用于分析以改进产品。详见
                  <Link href="/privacy" className="text-brand hover:underline mx-1">隐私政策</Link>。
                </p>
                <div className="flex items-center gap-2 mt-3">
                  <button onClick={() => decide("all")} className="btn-primary h-8 px-4 text-xs">接受全部</button>
                  <button onClick={() => decide("necessary")} className="btn-secondary h-8 px-4 text-xs">仅必要</button>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
