"use client";

import { useEffect, useState, useCallback } from "react";
import { AlertTriangle, X } from "lucide-react";
import { API_BASE } from "@/lib/api";

const STORAGE_KEY = "betty-demo-dismissed";

/** Subtle indicator when the platform is in demo/preview mode. Dismissible. */
export function DemoModeBanner() {
  const [show, setShow] = useState(false);
  const [label, setLabel] = useState("");
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === "1") setDismissed(true);
  }, []);

  useEffect(() => {
    if (dismissed) return;
    fetch(`${API_BASE}/system/capabilities`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        const demo = !!d.demo_mode || !d.real_generation_available;
        if (demo) {
          setShow(true);
          setLabel(
            d.label ||
              "预览模式：未配置模型 API Key，生成结果为本地演示媒体"
          );
        }
      })
      .catch(() => {});
  }, [dismissed]);

  const dismiss = useCallback(() => {
    setShow(false);
    setDismissed(true);
    localStorage.setItem(STORAGE_KEY, "1");
  }, []);

  if (dismissed) return null;
  if (!show) return null;

  return (
    <div className="flex items-center justify-center gap-2 border-b border-warning/15 bg-warning/[0.06] px-4 py-1.5 text-[11px] text-warning">
      <AlertTriangle className="w-3 h-3 shrink-0" />
      <span className="truncate min-w-0">
        <span className="font-semibold">演示模式</span>
        <span className="opacity-75"> — {label}</span>
      </span>
      <button
        onClick={dismiss}
        title="关闭提示"
        className="shrink-0 p-0.5 rounded hover:bg-warning/15 transition-colors"
      >
        <X className="w-3 h-3" />
      </button>
    </div>
  );
}
