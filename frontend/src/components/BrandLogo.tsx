import { cn } from "@/lib/utils";

/* ═══════════════════════════════════════════════════════
   BrandLogo — betty 品牌标识（内联 SVG，透明背景，任意缩放）
   BrandMark:  几何字母标「b」— 深靛蓝方角容器 + 白色字母，
               专业、克制、去 AI 星芒化（对标 Notion/Linear/Vercel 字母标）
   BrandLogo:  图形 + 文字组合
   ═══════════════════════════════════════════════════════ */

export function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn("shrink-0", className)}
      role="img"
      aria-label="betty"
    >
      <defs>
        <linearGradient id="betty-mark-bg" x1="8" y1="4" x2="56" y2="60" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#7A6BF0" />
          <stop offset="100%" stopColor="#5A49D6" />
        </linearGradient>
      </defs>
      {/* Squircle container — single-hue restrained gradient */}
      <rect x="3" y="3" width="58" height="58" rx="16" fill="url(#betty-mark-bg)" />
      {/* Subtle top inner highlight for polished product-icon depth */}
      <rect x="3" y="3" width="58" height="58" rx="16" fill="white" fillOpacity="0.06" />
      {/* Geometric lowercase "b" monogram (stem + bowl ring, counter = negative space) */}
      <g fill="#FFFFFF">
        <rect x="20" y="13" width="7.5" height="38" rx="3.75" />
        <path
          fillRule="evenodd"
          clipRule="evenodd"
          d="M33.6 24C40.9 24 46.8 29.9 46.8 37.2C46.8 44.5 40.9 50.4 33.6 50.4C26.3 50.4 20.4 44.5 20.4 37.2C20.4 29.9 26.3 24 33.6 24ZM33.6 31.2C30.3 31.2 27.6 33.9 27.6 37.2C27.6 40.5 30.3 43.2 33.6 43.2C36.9 43.2 39.6 40.5 39.6 37.2C39.6 33.9 36.9 31.2 33.6 31.2Z"
        />
      </g>
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
