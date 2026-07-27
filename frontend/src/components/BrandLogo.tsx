import { cn } from "@/lib/utils";

/* ═══════════════════════════════════════════════════════
   BrandLogo — betty 品牌标识（内联 SVG，透明背景，任意缩放）
   BrandMark:  几何字母标「b」— 深靛蓝方角容器 + 白色字母，
               专业、克制、去 AI 星芒化（对标 Notion/Linear/Vercel 字母标）
   BrandLogo:  图形 + 文字组合
   ═══════════════════════════════════════════════════════ */

// The "b" glyph geometry, shared by all variants.
//   stem = vertical ascender bar; bowl = filled disc that OVERLAPS the stem so
//   the two merge into one solid shape; counter (hole) is offset to the RIGHT of
//   the stem so the stem↔bowl junction stays solid (fixes the old "detached ring
//   reads as o/io" craft issue). Rendered with fillRule=evenodd (disc minus hole).
const B_STEM = { x: 19, y: 11, w: 8, h: 40, rx: 4 };
const B_BOWL =
  "M21.8 38a13.2 13.2 0 1 0 26.4 0a13.2 13.2 0 1 0 -26.4 0Z" +   // outer bowl disc (cx35 cy38 r13.2)
  "M29.8 38a6.2 6.2 0 1 0 12.4 0a6.2 6.2 0 1 0 -12.4 0Z";        // counter hole (cx36 cy38 r6.2, right of stem)

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
            <stop offset="0%" stopColor="#14B8A6" />
            <stop offset="100%" stopColor="#0F766E" />
          </linearGradient>
        </defs>
      )}
      {/* Squircle container */}
      <rect x="3" y="3" width="58" height="58" rx="16"
        fill={variant === "gradient" ? `url(#${gradId})` : "#0F766E"} />
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
