import { cn } from "@/lib/utils";

/* ═══════════════════════════════════════════════════════
   BrandLogo — betty 品牌标识（内联 SVG，透明背景，任意缩放）
   BrandMark:  几何字母标「b」— 深靛蓝方角容器 + 白色字母，
               专业、克制、去 AI 星芒化（对标 Notion/Linear/Vercel 字母标）
   BrandLogo:  图形 + 文字组合
   ═══════════════════════════════════════════════════════ */

// The "b" glyph geometry, shared by all variants (stem + bowl ring, counter = hole).
const B_STEM = { x: 20, y: 13, w: 7.5, h: 38, rx: 3.75 };
const B_BOWL =
  "M33.6 24C40.9 24 46.8 29.9 46.8 37.2C46.8 44.5 40.9 50.4 33.6 50.4C26.3 50.4 20.4 44.5 20.4 37.2C20.4 29.9 26.3 24 33.6 24ZM33.6 31.2C30.3 31.2 27.6 33.9 27.6 37.2C27.6 40.5 30.3 43.2 33.6 43.2C36.9 43.2 39.6 40.5 39.6 37.2C39.6 33.9 36.9 31.2 33.6 31.2Z";

type BrandVariant = "gradient" | "solid" | "mono";

/**
 * BrandMark — geometric "b" monogram.
 *  - gradient (default): squircle w/ brand gradient + white glyph. Works on
 *    light *and* dark surfaces (self-contained tile).
 *  - solid: flat single-color brand squircle + white glyph (print / flat UI).
 *  - mono: glyph only (no tile) in `currentColor` — for dark headers, footers,
 *    watermarks; set text color at the call site (e.g. text-white on dark).
 */
export function BrandMark({
  className,
  variant = "gradient",
}: {
  className?: string;
  variant?: BrandVariant;
}) {
  const gradId = `betty-mark-bg-${variant}`;

  if (variant === "mono") {
    // Transparent tile, glyph inherits currentColor.
    return (
      <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg"
        className={cn("shrink-0", className)} role="img" aria-label="betty">
        <g fill="currentColor">
          <rect x={B_STEM.x} y={B_STEM.y} width={B_STEM.w} height={B_STEM.h} rx={B_STEM.rx} />
          <path fillRule="evenodd" clipRule="evenodd" d={B_BOWL} />
        </g>
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg"
      className={cn("shrink-0", className)} role="img" aria-label="betty">
      {variant === "gradient" && (
        <defs>
          <linearGradient id={gradId} x1="8" y1="4" x2="56" y2="60" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#7A6BF0" />
            <stop offset="100%" stopColor="#5A49D6" />
          </linearGradient>
        </defs>
      )}
      {/* Squircle container */}
      <rect x="3" y="3" width="58" height="58" rx="16"
        fill={variant === "gradient" ? `url(#${gradId})` : "#6C5CE7"} />
      {/* Subtle top inner highlight for polished product-icon depth */}
      <rect x="3" y="3" width="58" height="58" rx="16" fill="white" fillOpacity="0.06" />
      {/* Geometric "b" glyph */}
      <g fill="#FFFFFF">
        <rect x={B_STEM.x} y={B_STEM.y} width={B_STEM.w} height={B_STEM.h} rx={B_STEM.rx} />
        <path fillRule="evenodd" clipRule="evenodd" d={B_BOWL} />
      </g>
    </svg>
  );
}

export function BrandLogo({
  className,
  markClassName = "w-7 h-7",
  textClassName,
  variant = "gradient",
}: {
  className?: string;
  markClassName?: string;
  textClassName?: string;
  variant?: BrandVariant;
}) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <BrandMark className={markClassName} variant={variant} />
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
