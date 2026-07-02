"use client";

import { ReactNode, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  SlidersHorizontal,
  ChevronDown,
  Info,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

/* ─────────────────────────────────────────────────────
   CosmicParamPanel
   可折叠参数面板 — Glassmorphism · 渐变装饰 · 动画折叠
   ───────────────────────────────────────────────────── */

interface ParamGroup {
  id: string;
  label: string;
  icon?: ReactNode;
  tooltip?: string;
  children: ReactNode;
  defaultCollapsed?: boolean;
}

interface CosmicParamPanelProps {
  groups: ParamGroup[];
  className?: string;
  title?: string;
}

export function CosmicParamPanel({
  groups,
  className,
  title = "参数设置",
}: CosmicParamPanelProps) {
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
    new Set(groups.filter((g) => g.defaultCollapsed).map((g) => g.id))
  );

  const toggleGroup = (id: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 16 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        // Glass panel
        "relative w-72 flex-shrink-0",
        "bg-cosmic-surface/40 backdrop-blur-2xl backdrop-saturate-150",
        "border border-cosmic-border/50",
        "rounded-2xl",
        "shadow-elevation-md",
        "overflow-hidden",
        className
      )}
    >
      {/* ── Top glow edge ── */}
      <div className="absolute inset-x-4 top-0 h-px bg-gradient-to-r from-transparent via-accent-cyan/20 to-transparent" />

      {/* ── Header ── */}
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-cosmic-border/30">
        <div className="p-1.5 rounded-lg bg-accent-cyan/8">
          <SlidersHorizontal className="w-3.5 h-3.5 text-accent-cyan" />
        </div>
        <span className="text-body-sm font-semibold text-text-primary flex-1">
          {title}
        </span>
        <Sparkles className="w-3.5 h-3.5 text-accent-cyan/50" />
      </div>

      {/* ── Param groups ── */}
      <div className="divide-y divide-cosmic-border/20">
        {groups.map((group) => {
          const isCollapsed = collapsedGroups.has(group.id);
          const Icon = group.icon;

          return (
            <div
              key={group.id}
              className="group/param px-5 py-4"
            >
              {/* ── Group header (clickable) ── */}
              <button
                onClick={() => toggleGroup(group.id)}
                className="flex items-center justify-between w-full mb-3"
              >
                <div className="flex items-center gap-2 min-w-0">
                  {Icon && (
                    <span className="text-text-tertiary">{Icon}</span>
                  )}
                  <span className="text-caption font-medium text-text-secondary truncate">
                    {group.label}
                  </span>
                  {group.tooltip && (
                    <div className="relative group/tip">
                      <Info className="w-3 h-3 text-text-tertiary/60 shrink-0" />
                      <div className="absolute left-full ml-2 bottom-0 w-48 px-2.5 py-1.5 rounded-lg bg-cosmic-elevated border border-cosmic-border/60 text-caption text-text-secondary opacity-0 invisible group-hover/tip:opacity-100 group-hover/tip:visible transition-all duration-200 pointer-events-none z-50 shadow-elevation-lg">
                        {group.tooltip}
                      </div>
                    </div>
                  )}
                </div>
                <ChevronDown
                  className={cn(
                    "w-3.5 h-3.5 text-text-tertiary/60 shrink-0 transition-transform duration-200",
                    isCollapsed && "-rotate-90"
                  )}
                />
              </button>

              {/* ── Group content (animated) ── */}
              <AnimatePresence initial={false}>
                {!isCollapsed && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                    className="overflow-hidden"
                  >
                    <div className="pt-1">{group.children}</div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          );
        })}
      </div>

      {/* ── Bottom glow edge ── */}
      <div className="absolute inset-x-4 bottom-0 h-px bg-gradient-to-r from-transparent via-accent-violet/15 to-transparent" />
    </motion.div>
  );
}

/* ─────────────────────────────────────────────────────
   CosmicSlider — 渐变轨道 · 辉光滑块
   ───────────────────────────────────────────────────── */

interface CosmicSliderProps {
  label?: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
  leftLabel?: string;
  rightLabel?: string;
  showValue?: boolean;
  className?: string;
}

export function CosmicSlider({
  label,
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  leftLabel = "精准",
  rightLabel = "狂野",
  showValue = true,
  className,
}: CosmicSliderProps) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className={cn("space-y-2", className)}>
      {/* Label + Value */}
      {(label || showValue) && (
        <div className="flex items-center justify-between">
          {label && (
            <span className="text-caption text-text-tertiary">{label}</span>
          )}
          {showValue && (
            <span className="text-caption font-mono font-medium text-accent-cyan tabular-nums">
              {value}
            </span>
          )}
        </div>
      )}

      {/* Slider track */}
      <div className="relative h-6 flex items-center">
        {/* Background track */}
        <div className="absolute inset-x-0 h-1.5 rounded-full bg-cosmic-border/50">
          {/* Filled gradient track */}
          <div
            className="h-full rounded-full transition-all duration-150"
            style={{
              width: `${pct}%`,
              background:
                "linear-gradient(90deg, hsl(189 94% 48%), hsl(217 91% 60%), hsl(255 92% 66%))",
            }}
          />
        </div>

        {/* Native range input (invisible, for interaction) */}
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
        />

        {/* Visible thumb */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-[18px] h-[18px] rounded-full bg-white shadow-glow-cyan border-2 border-accent-cyan pointer-events-none transition-all duration-150 z-0"
          style={{ left: `calc(${pct}% - 9px)` }}
        />
      </div>

      {/* Range labels */}
      <div className="flex justify-between text-[10px] text-text-tertiary/70 select-none">
        <span>{leftLabel}</span>
        <span>{rightLabel}</span>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────
   CosmicSelect — 深空下拉选择
   ───────────────────────────────────────────────────── */

interface CosmicSelectOption {
  value: string;
  label: string;
  description?: string;
}

interface CosmicSelectProps {
  label?: string;
  value: string;
  onChange: (v: string) => void;
  options: CosmicSelectOption[];
  className?: string;
}

export function CosmicSelect({
  label,
  value,
  onChange,
  options,
  className,
}: CosmicSelectProps) {
  return (
    <div className={cn("space-y-1.5", className)}>
      {label && (
        <span className="text-caption text-text-tertiary">{label}</span>
      )}
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={cn(
            "w-full appearance-none",
            "h-9 px-3 pr-8 rounded-lg",
            "bg-cosmic-surface/50 border border-cosmic-border/60",
            "text-body-sm text-text-primary",
            "focus:outline-none focus:border-accent-cyan/30 focus:ring-2 focus:ring-accent-cyan/8",
            "transition-all duration-200",
            "cursor-pointer"
          )}
        >
          {options.map((opt) => (
            <option
              key={opt.value}
              value={opt.value}
              className="bg-cosmic-elevated text-text-primary"
            >
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary pointer-events-none" />
      </div>
    </div>
  );
}
