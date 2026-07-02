"use client";

import { forwardRef } from "react";
import { motion, type HTMLMotionProps } from "framer-motion";
import { Sparkles, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/* ─────────────────────────────────────────────────────
   CosmicGenerateButton
   渐变流光按钮 — 多种变体 · 辉光脉冲 · 触感反馈
   ───────────────────────────────────────────────────── */

type ButtonVariant =
  | "primary"
  | "primary-glass"
  | "secondary"
  | "ghost"
  | "destructive"
  | "outline-glow";

type ButtonSize = "sm" | "md" | "lg" | "xl" | "icon";

interface CosmicGenerateButtonProps
  extends Omit<HTMLMotionProps<"button">, "children" | "size"> {
  children?: React.ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
  className?: string;
}

/* ── Style Maps ────────────────────────────────────── */

const variantStyles: Record<ButtonVariant, string> = {
  primary: cn(
    // Gradient background
    "bg-gradient-to-r from-accent-cyan via-accent-blue to-accent-violet",
    "text-white",
    // Glow
    "shadow-button-glow",
    // Hover
    "hover:shadow-button-glow-lg hover:brightness-110",
    // Active
    "active:brightness-95",
    // Disabled
    "disabled:opacity-35 disabled:cursor-not-allowed disabled:hover:shadow-button-glow disabled:hover:brightness-100"
  ),
  "primary-glass": cn(
    "bg-cosmic-surface",
    "border border-cosmic-border",
    "text-text-primary",
    "shadow-elevation-sm",
    "hover:bg-cosmic-subtle hover:border-cosmic-border-hover hover:shadow-elevation-md",
    "active:bg-cosmic-subtle",
    "disabled:opacity-35 disabled:cursor-not-allowed"
  ),
  secondary: cn(
    "bg-cosmic-surface/50",
    "border border-cosmic-border/60",
    "text-text-secondary",
    "hover:bg-cosmic-surface/80 hover:text-text-primary hover:border-cosmic-border-hover",
    "active:bg-cosmic-surface",
    "disabled:opacity-35 disabled:cursor-not-allowed"
  ),
  ghost: cn(
    "text-text-tertiary",
    "hover:text-text-primary hover:bg-cosmic-subtle",
    "active:bg-cosmic-subtle",
    "disabled:opacity-35 disabled:cursor-not-allowed"
  ),
  destructive: cn(
    "bg-destructive/12",
    "border border-destructive/25",
    "text-destructive",
    "hover:bg-destructive/20 hover:border-destructive/40",
    "active:bg-destructive/25",
    "disabled:opacity-35 disabled:cursor-not-allowed"
  ),
  "outline-glow": cn(
    "bg-transparent",
    "border border-accent-cyan/25",
    "text-accent-cyan",
    "shadow-glow-subtle",
    "hover:bg-accent-cyan/[0.06] hover:border-accent-cyan/45 hover:shadow-glow-medium",
    "active:bg-accent-cyan/[0.1]",
    "disabled:opacity-35 disabled:cursor-not-allowed"
  ),
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-caption rounded-lg gap-1.5",
  md: "h-10 px-5 text-body-sm rounded-xl gap-2",
  lg: "h-12 px-6 text-body rounded-xl gap-2",
  xl: "h-14 px-8 text-body rounded-2xl gap-2.5",
  icon: "h-9 w-9 rounded-lg",
};

/* ── Component ─────────────────────────────────────── */

export const CosmicGenerateButton = forwardRef<
  HTMLButtonElement,
  CosmicGenerateButtonProps
>(
  (
    {
      children,
      variant = "primary",
      size = "md",
      loading = false,
      disabled = false,
      icon,
      className,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;
    const isIconOnly = size === "icon";

    return (
      <motion.button
        ref={ref}
        disabled={isDisabled}
        whileTap={{ scale: isDisabled ? 1 : 0.97 }}
        whileHover={{ scale: isDisabled ? 1 : 1.02 }}
        className={cn(
          // Base
          "relative inline-flex items-center justify-center font-semibold",
          "overflow-hidden select-none",
          // Focus ring
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-cyan/40 focus-visible:ring-offset-2 focus-visible:ring-offset-cosmic-surface",
          // Transitions
          "transition-all duration-200 ease-out-expo",
          // Variant
          variantStyles[variant],
          // Size
          sizeStyles[size],
          // Icon-only
          isIconOnly && "p-0",
          // Custom
          className
        )}
        {...props}
      >
        {/* ── Glow pulse overlay (primary only) ── */}
        {variant === "primary" && !isDisabled && (
          <div className="absolute inset-0 rounded-xl opacity-0 hover:opacity-100 transition-opacity duration-500 pointer-events-none">
            <div
              className="absolute inset-0 rounded-xl"
              style={{
                background:
                  "radial-gradient(circle at 50% 0%, hsl(252 78% 63% / 0.18), transparent 70%)",
              }}
            />
          </div>
        )}

        {/* ── Shimmer on hover (primary only) ── */}
        {variant === "primary" && !isDisabled && (
          <div className="absolute inset-0 -translate-x-full hover:translate-x-full transition-transform duration-700 pointer-events-none">
            <div className="h-full w-1/3 bg-gradient-to-r from-transparent via-white/10 to-transparent skew-x-12" />
          </div>
        )}

        {/* ── Content ── */}
        <span className="relative z-10 flex items-center justify-center gap-2">
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : isIconOnly && icon ? (
            icon
          ) : variant === "primary" && !icon ? (
            <Sparkles className="w-4 h-4" />
          ) : icon ? (
            icon
          ) : null}
          {!isIconOnly && children}
        </span>
      </motion.button>
    );
  }
);

CosmicGenerateButton.displayName = "CosmicGenerateButton";
