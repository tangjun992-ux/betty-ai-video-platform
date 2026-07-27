"use client";

import { cn } from "@/lib/utils";
import { type ReactNode, useRef, useCallback } from "react";

/* ─────────────────────────────────────────────────────
   CosmicGradientCard
   渐变边框卡片 — 鼠标追踪辉光 · Glassmorphism 内部
   ───────────────────────────────────────────────────── */

interface CosmicGradientCardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  /** 是否启用 hover 辉光增强 */
  hover?: boolean;
  /** 是否启用鼠标追踪辉光 (需 hover=true) */
  mouseTracking?: boolean;
  /** 渐变方向 */
  gradientFrom?: string;
  gradientVia?: string;
  gradientTo?: string;
}

export function CosmicGradientCard({
  children,
  className,
  onClick,
  hover = true,
  mouseTracking = false,
  gradientFrom = "from-accent-cyan/20",
  gradientVia = "via-accent-blue/15",
  gradientTo = "to-accent-violet/20",
}: CosmicGradientCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!mouseTracking || !cardRef.current) return;
      const rect = cardRef.current.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      cardRef.current.style.setProperty("--mouse-x", `${x}%`);
      cardRef.current.style.setProperty("--mouse-y", `${y}%`);
    },
    [mouseTracking]
  );

  const handleMouseLeave = useCallback(() => {
    if (!mouseTracking || !cardRef.current) return;
    cardRef.current.style.setProperty("--mouse-x", "50%");
    cardRef.current.style.setProperty("--mouse-y", "50%");
  }, [mouseTracking]);

  return (
    <div
      ref={cardRef}
      onClick={onClick}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={cn(
        // Outer gradient border
        "relative rounded-2xl p-px",
        "bg-gradient-to-br",
        gradientFrom,
        gradientVia,
        gradientTo,
        // Hover enhancement
        hover && [
          "hover:from-accent-cyan/35 hover:via-accent-blue/25 hover:to-accent-violet/35",
          "transition-all duration-500",
        ],
        // Clickable
        onClick && "cursor-pointer active:scale-[0.985]",
        // Mouse tracking glow
        mouseTracking && "overflow-hidden",
        className
      )}
    >
      {/* Inner glass card */}
      <div
        className={cn(
          "relative rounded-xl",
          "bg-cosmic-surface/60 backdrop-blur-xl",
          "p-6 h-full",
          "overflow-hidden"
        )}
      >
        {/* ── Top inner glow ── */}
        <div className="absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-white/8 to-transparent" />

        {/* ── Mouse tracking radial glow ── */}
        {mouseTracking && (
          <div
            className="absolute inset-0 opacity-0 hover:opacity-100 transition-opacity duration-500 pointer-events-none"
            style={{
              background:
                "radial-gradient(500px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), hsl(189 94% 48% / 0.07), transparent 60%)",
            }}
          />
        )}

        {/* ── Children ── */}
        <div className="relative z-10 h-full">{children}</div>

        {/* ── Bottom ambient gradient ── */}
        <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-accent-cyan/[0.02] to-transparent pointer-events-none" />
      </div>
    </div>
  );
}
