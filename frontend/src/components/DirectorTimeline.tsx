"use client";

import { useEffect, useRef } from "react";
import { Check, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";

/** Running shot counter — 步, not 镜, because DAG includes audio/subtitle. */
export function timelineProgressLabel(
  phase: string,
  steps: { status: string }[],
): string | undefined {
  if (phase !== "running" || steps.length === 0) return undefined;
  const i = steps.findIndex((s) => s.status === "running");
  const n = steps.length;
  if (i >= 0) return `执行中 · 第 ${i + 1}/${n} 步`;
  const done = steps.filter((s) => s.status === "done").length;
  return `执行中 · 已完成 ${done}/${n} 步`;
}

export function DirectorTimeline({
  children,
  progressLabel,
}: {
  children: React.ReactNode;
  progressLabel?: string;
}) {
  return (
    <div>
      {progressLabel && (
        <p data-testid="agent-timeline-progress" className="text-xs font-medium text-brand mb-3">
          {progressLabel}
        </p>
      )}
      <ol data-testid="agent-timeline" className="relative m-0 list-none p-0">
        {children}
      </ol>
    </div>
  );
}

export function TimelineShot({
  index,
  total,
  status,
  skipped,
  children,
}: {
  index: number;
  total: number;
  status: string;
  skipped?: boolean;
  children: React.ReactNode;
}) {
  const done = status === "done";
  const running = status === "running";
  const failed = status === "failed";
  const last = index === total - 1;
  const label = String(index + 1).padStart(2, "0");
  const nodeRef = useRef<HTMLLIElement>(null);

  useEffect(() => {
    if (running) nodeRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [running]);

  return (
    <li
      ref={nodeRef}
      data-current-step={running ? "true" : undefined}
      data-testid={running ? "agent-timeline-current" : undefined}
      className={cn("relative flex gap-3", skipped && "opacity-50")}
    >
      <div className="flex w-8 shrink-0 flex-col items-center" aria-hidden>
        <div
          data-testid="agent-shot-index"
          className={cn(
            "relative z-10 flex h-8 w-8 items-center justify-center rounded-full border text-[10px] font-mono font-semibold",
            running && "border-brand bg-brand text-white ring-2 ring-brand/40 shadow-[0_0_12px_hsl(var(--brand)/0.45)]",
            done && "border-emerald-500/40 bg-emerald-500/15 text-emerald-500",
            failed && "border-red-500/40 bg-red-500/15 text-red-500",
            !running && !done && !failed && "border-cosmic-border bg-cosmic-surface text-text-secondary",
          )}
        >
          {done ? (
            <Check className="h-3.5 w-3.5" />
          ) : running ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : failed ? (
            <X className="h-3.5 w-3.5" />
          ) : (
            label
          )}
        </div>
        {!last && (
          <div
            className={cn(
              "w-px min-h-[16px] flex-1",
              done ? "bg-emerald-500/35" : running ? "bg-brand/50" : "bg-cosmic-border/70",
            )}
          />
        )}
      </div>
      <div className="min-w-0 flex-1 pb-3">{children}</div>
    </li>
  );
}
