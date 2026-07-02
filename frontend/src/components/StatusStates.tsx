"use client";

import { motion } from "framer-motion";
import { Loader2, AlertTriangle, Inbox, RefreshCw, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

// ═══════════════════════════════════════════════════════════
// Loading State — Professional Skeleton / Spinner
// ═══════════════════════════════════════════════════════════

interface LoadingProps {
  className?: string;
  text?: string;
  variant?: "spinner" | "skeleton" | "pulse";
  skeletonCount?: number;
}

export function Loading({ className, text = "加载中...", variant = "spinner", skeletonCount = 3 }: LoadingProps) {
  if (variant === "skeleton") {
    return (
      <div className={cn("space-y-4", className)}>
        {Array.from({ length: skeletonCount }).map((_, i) => (
          <div key={i} className="skeleton-card h-48" style={{ animationDelay: `${i * 0.15}s` }} />
        ))}
      </div>
    );
  }

  if (variant === "pulse") {
    return (
      <div className={cn("flex items-center gap-3 p-6", className)}>
        <div className="w-3 h-3 rounded-full bg-accent-cyan animate-pulse" />
        <div className="flex-1 space-y-2">
        <div className="h-3 bg-cosmic-subtle rounded-full w-3/4 animate-pulse" />
        <div className="h-2 bg-cosmic-border/60 rounded-full w-1/2 animate-pulse" />
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={cn("flex flex-col items-center justify-center py-16 gap-4", className)}
    >
      <div className="relative">
        <Loader2 className="w-10 h-10 text-accent-cyan animate-spin" />
        <div className="absolute inset-0 blur-xl bg-accent-cyan/[0.12] rounded-full animate-pulse" />
      </div>
      <p className="text-sm text-text-secondary">{text}</p>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════
// Empty State — Professional blank-slate with action
// ═══════════════════════════════════════════════════════════

interface EmptyProps {
  className?: string;
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
}

export function Empty({
  className,
  icon,
  title,
  description,
  action,
  secondaryAction,
}: EmptyProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={cn(
        "flex flex-col items-center justify-center py-20 px-4 text-center",
        className
      )}
    >
      <div className="w-16 h-16 rounded-2xl bg-cosmic-subtle border border-cosmic-border flex items-center justify-center mb-5">
        {icon || <Inbox className="w-7 h-7 text-text-secondary/60" />}
      </div>

      <h3 className="text-lg font-semibold text-text-primary mb-1.5">{title}</h3>
      {description && (
        <p className="text-sm text-text-secondary max-w-sm mb-6">{description}</p>
      )}

      <div className="flex items-center gap-3">
        {action && (
          <button
            onClick={action.onClick}
            className="btn-primary"
          >
            <Sparkles className="w-4 h-4" />
            {action.label}
          </button>
        )}
        {secondaryAction && (
          <button
            onClick={secondaryAction.onClick}
            className="btn-secondary"
          >
            {secondaryAction.label}
          </button>
        )}
      </div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════
// Error State — Professional error boundary with retry
// ═══════════════════════════════════════════════════════════

interface ErrorStateProps {
  className?: string;
  title?: string;
  message?: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export function ErrorState({
  className,
  title = "出错了",
  message = "请稍后重试，或联系支持团队。",
  onRetry,
  onDismiss,
}: ErrorStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "flex flex-col items-center justify-center py-16 px-4 text-center",
        className
      )}
    >
      <div className="w-16 h-16 rounded-2xl bg-destructive-muted border border-destructive/20 flex items-center justify-center mb-5">
        <AlertTriangle className="w-7 h-7 text-destructive" />
      </div>

      <h3 className="text-lg font-semibold text-text-primary mb-1.5">{title}</h3>
      <p className="text-sm text-text-secondary max-w-sm mb-6">{message}</p>

      <div className="flex items-center gap-3">
        {onRetry && (
          <button onClick={onRetry} className="btn-primary">
            <RefreshCw className="w-4 h-4" />
            重试
          </button>
        )}
        {onDismiss && (
          <button onClick={onDismiss} className="btn-ghost">
            关闭
          </button>
        )}
      </div>
    </motion.div>
  );
}

// ═══════════════════════════════════════════════════════════
// Skeleton Card Grid — for gallery/results loading
// ═══════════════════════════════════════════════════════════

interface SkeletonGridProps {
  className?: string;
  count?: number;
  aspectRatio?: "square" | "video" | "wide";
}

export function SkeletonGrid({ className, count = 8, aspectRatio = "square" }: SkeletonGridProps) {
  const aspectClass = aspectRatio === "video"
    ? "aspect-video"
    : aspectRatio === "wide"
    ? "aspect-[21/9]"
    : "aspect-square";

  return (
    <div className={cn("grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4", className)}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="space-y-2">
          <div className={cn("skeleton-card", aspectClass)} style={{ animationDelay: `${i * 0.1}s` }} />
          <div className="skeleton-text w-3/4" style={{ animationDelay: `${i * 0.1 + 0.1}s` }} />
          <div className="skeleton-text w-1/2" style={{ animationDelay: `${i * 0.1 + 0.15}s` }} />
        </div>
      ))}
    </div>
  );
}
