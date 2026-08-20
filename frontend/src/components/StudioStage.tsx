"use client";

import { Play, ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";

/** Cinematic empty canvas — Yapper create stage, not a help paragraph. */
export function StudioStage({
  title,
  hint,
  kind = "video",
  className,
}: {
  title: string;
  hint: string;
  kind?: "video" | "image";
  className?: string;
}) {
  const Icon = kind === "image" ? ImageIcon : Play;
  return (
    <div
      data-testid="studio-stage"
      className={cn(
        "mt-6 rounded-2xl border border-dashed border-cosmic-border/80 bg-black/25 overflow-hidden",
        className,
      )}
    >
      <div
        className={cn(
          "relative flex flex-col items-center justify-center px-6",
          kind === "image" ? "py-14 min-h-[220px]" : "py-16 min-h-[260px]",
        )}
      >
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,hsl(var(--accent-blue)/0.12),transparent_68%)]" />
        <Icon className="relative w-10 h-10 text-text-tertiary mb-3" />
        <p className="relative text-sm font-medium text-text-primary">{title}</p>
        <p className="relative text-xs text-text-tertiary mt-1.5 max-w-md text-center leading-relaxed">{hint}</p>
      </div>
    </div>
  );
}
