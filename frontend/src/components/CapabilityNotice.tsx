"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, Sparkles } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

type Feature = "lipsync" | "motion" | "audio" | "video" | "image";

interface Caps {
  demo_mode?: boolean;
  real_generation_available?: boolean;
  features?: Record<string, { available?: boolean; mode?: string; note?: string }>;
}

/** Per-feature honest disclosure of what actually runs in the current mode.
 *  Demo output for lipsync/motion is NOT true sync/transfer — say so plainly. */
const DEMO_TEXT: Record<Feature, string> = {
  lipsync:
    "演示模式下唇形同步为 Ken Burns 动效预览，并非真实口型对齐。配置 KIE_API_KEY 后启用真实唇形同步。",
  motion:
    "运动控制需要真实模型能力，演示模式无法模拟。请配置 KIE_API_KEY 后使用原生 Kling Motion Control。",
  audio:
    "演示模式为本地合成音（非真实 ElevenLabs/TTS）。配置 TTS Key 后启用真实配音。",
  video:
    "演示模式生成的是本地 Ken Burns 演示视频（带 DEMO 水印）。配置模型 Key 后启用真实视频生成。",
  image:
    "演示模式生成的是本地占位图。配置模型 Key 后启用真实图片生成。",
};

const REAL_TEXT: Record<Feature, string> = {
  lipsync: "真实唇形同步可用（已配置模型凭证）。",
  motion:
    "原生 Kling Motion Control 可用（input_urls + video_urls）。非 Runway Act-One；失败时任务层可回退。",
  audio: "真实 TTS 配音可用（已配置模型凭证）。",
  video: "真实视频生成可用（已配置模型凭证）。",
  image: "真实图片生成可用（已配置模型凭证）。",
};

function resolveCapsUrl(): string {
  // Prefer same-origin rewrite in the browser to avoid cross-origin hangs.
  if (typeof window !== "undefined") {
    return "/api/v1/system/capabilities";
  }
  return `${API_BASE}/system/capabilities`;
}

export function CapabilityNotice({
  feature,
  className,
  onDemoChange,
}: {
  feature: Feature;
  className?: string;
  onDemoChange?: (isDemo: boolean) => void;
}) {
  const [caps, setCaps] = useState<Caps | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => ctrl.abort(), 8_000);

    fetch(resolveCapsUrl(), { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!alive) return;
        const next = d || { demo_mode: true, real_generation_available: false };
        setCaps(next);
        onDemoChange?.(!!next.demo_mode || !next.real_generation_available);
      })
      .catch(() => {
        if (!alive) return;
        const fallback = { demo_mode: true, real_generation_available: false };
        setCaps(fallback);
        onDemoChange?.(true);
      })
      .finally(() => {
        if (!alive) return;
        window.clearTimeout(timer);
        setLoading(false);
      });

    return () => {
      alive = false;
      window.clearTimeout(timer);
      ctrl.abort();
    };
  }, [feature, onDemoChange]);

  const isDemo = caps ? !!caps.demo_mode || !caps.real_generation_available : false;
  const motionBlocked = isDemo && feature === "motion";
  const motionNative =
    feature === "motion" &&
    !isDemo &&
    (caps?.features?.motion_transfer?.mode === "native" ||
      caps?.features?.motion_transfer?.available === true);

  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-xl border px-3 py-2 text-xs",
        loading
          ? "border-cosmic-border bg-cosmic-subtle text-text-secondary"
          : isDemo
            ? "border-amber-400/40 bg-amber-500/10 text-amber-800 dark:text-amber-200"
            : "border-emerald-400/40 bg-emerald-500/10 text-emerald-800 dark:text-emerald-200",
        className,
      )}
      data-testid={`capability-notice-${feature}`}
      data-demo={loading ? "pending" : isDemo ? "true" : "false"}
      data-loading={loading ? "true" : "false"}
    >
      {loading ? (
        <Loader2 className="w-3.5 h-3.5 shrink-0 mt-0.5 animate-spin" />
      ) : isDemo ? (
        <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
      ) : (
        <CheckCircle2 className="w-3.5 h-3.5 shrink-0 mt-0.5" />
      )}
      <div>
        <span className="font-semibold inline-flex items-center gap-1">
          {loading ? (
            "检测能力中"
          ) : isDemo ? (
            motionBlocked ? "此功能需要模型 Key" : "演示模式"
          ) : (
            <>
              <Sparkles className="w-3 h-3" /> 真实生成
            </>
          )}
        </span>
        <span className="opacity-90">
          {" "}
          —{" "}
          {loading
            ? "正在确认当前环境的模型凭证与能力探针…"
            : isDemo
              ? DEMO_TEXT[feature]
              : motionNative
                ? REAL_TEXT.motion
                : REAL_TEXT[feature]}
        </span>
      </div>
    </div>
  );
}
