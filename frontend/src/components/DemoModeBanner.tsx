"use client";

import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { API_BASE } from "@/lib/api";

/** Honest disclosure when the platform is in demo/preview mode (no provider keys). */
export function DemoModeBanner() {
  const [show, setShow] = useState(false);
  const [label, setLabel] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/system/capabilities`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        const demo = !!d.demo_mode || !d.real_generation_available;
        setShow(demo);
        setLabel(d.label || "预览模式：未配置模型 API Key，生成结果为本地演示媒体");
      })
      .catch(() => {});
  }, []);

  if (!show) return null;

  return (
    <div className="mx-4 mt-3 mb-1 flex items-start gap-2 rounded-xl border border-amber-400/40 bg-amber-500/10 px-4 py-2.5 text-sm text-amber-800 dark:text-amber-200">
      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
      <div>
        <span className="font-semibold">演示模式</span>
        <span className="opacity-90"> — {label}。配置 KIE_API_KEY 等凭证后可启用真实 AI 生成。</span>
      </div>
    </div>
  );
}
