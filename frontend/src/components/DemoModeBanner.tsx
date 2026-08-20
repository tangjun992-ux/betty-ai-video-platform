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
    <div
      data-testid="demo-mode-banner"
      className="border-b border-amber-400/25 bg-amber-500/[0.07] px-4 py-1.5 text-[11px] text-amber-900 dark:text-amber-200 flex items-center justify-center gap-1.5"
    >
      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
      <p className="truncate">
        <span className="font-semibold">演示模式</span>
        <span className="opacity-90"> — {label}。配置模型 Key 后可真实出片。</span>
      </p>
    </div>
  );
}
