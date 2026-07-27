"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, AlertTriangle, Info, X } from "lucide-react";
import { useToastStore, type ToastType } from "@/lib/stores";
import { cn } from "@/lib/utils";

// ─── Icon + Color Map ──────────────────────────────────

const toastConfig: Record<ToastType, {
  icon: typeof CheckCircle2;
  bg: string;
  border: string;
  iconColor: string;
  progressColor: string;
}> = {
  success: {
    icon: CheckCircle2,
    bg: "bg-success-muted/20",
    border: "border-success/20",
    iconColor: "text-success",
    progressColor: "bg-success",
  },
  error: {
    icon: XCircle,
    bg: "bg-destructive-muted/20",
    border: "border-destructive/20",
    iconColor: "text-destructive",
    progressColor: "bg-destructive",
  },
  warning: {
    icon: AlertTriangle,
    bg: "bg-warning-muted/20",
    border: "border-warning/20",
    iconColor: "text-warning",
    progressColor: "bg-warning",
  },
  info: {
    icon: Info,
    bg: "bg-info-muted/20",
    border: "border-info/20",
    iconColor: "text-info",
    progressColor: "bg-info",
  },
};

// ─── Single Toast ──────────────────────────────────────

function ToastItem({
  id,
  type,
  title,
  description,
  onRemove,
}: {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
  onRemove: () => void;
}) {
  const config = toastConfig[type];
  const Icon = config.icon;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -12, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -8, scale: 0.96 }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className={cn(
        "pointer-events-auto relative flex items-start gap-3 w-full max-w-sm p-4 rounded-2xl border backdrop-blur-2xl shadow-lg",
        config.bg,
        config.border
      )}
    >
      <Icon className={cn("w-5 h-5 flex-shrink-0 mt-0.5", config.iconColor)} />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-text-primary">{title}</p>
        {description && (
          <p className="text-xs text-text-secondary mt-0.5">{description}</p>
        )}
      </div>

      <button
        onClick={onRemove}
        className="flex-shrink-0 p-0.5 rounded-md text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle transition-colors"
        aria-label="关闭通知"
      >
        <X className="w-4 h-4" />
      </button>

      {/* Progress bar */}
      <div className="absolute bottom-0 left-3 right-3 h-0.5 rounded-full overflow-hidden">
        <motion.div
          initial={{ scaleX: 1 }}
          animate={{ scaleX: 0 }}
          transition={{ duration: 4, ease: "linear" }}
          className={cn("h-full rounded-full origin-left", config.progressColor)}
        />
      </div>
    </motion.div>
  );
}

// ─── Toast Container ───────────────────────────────────

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  return (
    <div
      className="fixed top-20 right-4 z-[100] flex flex-col gap-2 pointer-events-none"
      aria-live="polite"
      aria-label="通知"
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            id={toast.id}
            type={toast.type}
            title={toast.title}
            description={toast.description}
            onRemove={() => removeToast(toast.id)}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

// ─── Convenience Hook ──────────────────────────────────

export function useToast() {
  const { addToast } = useToastStore();
  return {
    success: (title: string, description?: string) =>
      addToast({ type: "success", title, description }),
    error: (title: string, description?: string) =>
      addToast({ type: "error", title, description }),
    warning: (title: string, description?: string) =>
      addToast({ type: "warning", title, description }),
    info: (title: string, description?: string) =>
      addToast({ type: "info", title, description }),
  };
}
