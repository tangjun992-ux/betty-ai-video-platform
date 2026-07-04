import { cn } from "@/lib/utils";

/* ═══════════════════════════════════════════════════════
   BrandLogo — betty 品牌标识（内联 SVG，透明背景，任意缩放）
   BrandMark:  图形 Logo（品牌紫渐变圆角方块 + 白色四角星芒）
   BrandLogo:  图形 + 文字组合
   ═══════════════════════════════════════════════════════ */

export function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("shrink-0", className)}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="betty-mark-bg" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#8B7CF6" />
          <stop offset="55%" stopColor="#6C5CE7" />
          <stop offset="100%" stopColor="#5847D6" />
        </linearGradient>
      </defs>
      {/* Rounded-square base */}
      <rect x="2" y="2" width="60" height="60" rx="16" fill="url(#betty-mark-bg)" />
      {/* Primary four-point spark */}
      <path
        d="M30 12c1.7 9.6 7.1 15 16.7 16.7.4.07.4.6 0 .66C37.1 31 31.7 36.4 30 46c-.07.4-.6.4-.66 0C27.6 36.4 22.2 31 12.6 29.36c-.4-.07-.4-.6 0-.66C22.2 27 27.6 21.6 29.34 12c.07-.4.6-.4.66 0Z"
        fill="white"
      />
      {/* Secondary small spark */}
      <path
        d="M45.5 38c.8 4.4 3.3 6.9 7.7 7.7.2.03.2.27 0 .3-4.4.8-6.9 3.3-7.7 7.7-.03.2-.27.2-.3 0-.8-4.4-3.3-6.9-7.7-7.7-.2-.03-.2-.27 0-.3 4.4-.8 6.9-3.3 7.7-7.7.03-.2.27-.2.3 0Z"
        fill="white"
        fillOpacity="0.85"
      />
    </svg>
  );
}

export function BrandLogo({
  className,
  markClassName = "w-7 h-7",
  textClassName,
}: {
  className?: string;
  markClassName?: string;
  textClassName?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <BrandMark className={markClassName} />
      <span
        className={cn(
          "font-semibold text-base tracking-[-0.02em] text-text-primary",
          textClassName
        )}
      >
        betty
      </span>
    </span>
  );
}
