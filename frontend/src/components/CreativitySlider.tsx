"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Sparkles, Target, Wand2 } from "lucide-react";

// ─── Types ──────────────────────────────────────────────

export type CreativityLevel = "precise" | "balanced" | "creative" | "wild";

interface CreativitySliderProps {
  value: CreativityLevel;
  onChange: (level: CreativityLevel) => void;
  className?: string;
}

// ─── Level definitions ──────────────────────────────────

const LEVELS: Array<{
  id: CreativityLevel;
  label: string;
  icon: React.ElementType;
  description: string;
  gradient: string;
  value: number;
}> = [
  {
    id: "precise",
    label: "精准",
    icon: Target,
    description: "严格遵循提示词",
    gradient: "from-blue-500 to-cyan-400",
    value: 25,
  },
  {
    id: "balanced",
    label: "均衡",
    icon: Sparkles,
    description: "平衡创意与精确",
    gradient: "from-accent-cyan to-teal-400",
    value: 50,
  },
  {
    id: "creative",
    label: "创意",
    icon: Wand2,
    description: "AI 自由发挥",
    gradient: "from-purple-500 to-pink-400",
    value: 75,
  },
  {
    id: "wild",
    label: "狂野",
    icon: Sparkles,
    description: "最大化创意惊喜",
    gradient: "from-orange-500 to-red-400",
    value: 95,
  },
];

// ─── Component ──────────────────────────────────────────

export function CreativitySlider({ value, onChange, className }: CreativitySliderProps) {
  const currentLevel = LEVELS.find((l) => l.id === value) || LEVELS[1];
  const currentIndex = LEVELS.indexOf(currentLevel);

  return (
    <div className={cn("space-y-3", className)}>
      {/* Label */}
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-text-secondary/60 uppercase tracking-wider">
          创造力
        </p>
        <span className="text-xs text-text-secondary">
          {currentLevel.label} · {currentLevel.description}
        </span>
      </div>

      {/* Slider track with level markers */}
      <div className="relative">
        {/* Track background */}
        <div className="relative h-2 rounded-full bg-cosmic-subtle overflow-hidden">
          {/* Gradient fill */}
          <motion.div
            className={cn(
              "absolute inset-y-0 left-0 rounded-full bg-gradient-to-r",
              currentLevel.gradient
            )}
            initial={{ width: "50%" }}
            animate={{ width: `${currentLevel.value}%` }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
          />
        </div>

        {/* Clickable level buttons */}
        <div className="absolute inset-0 flex items-center">
          {LEVELS.map((level, index) => {
            const isActive = value === level.id;
            const isPast = index <= currentIndex;
            const Icon = level.icon;

            return (
              <button
                key={level.id}
                onClick={() => onChange(level.id)}
                className={cn(
                  "absolute -translate-x-1/2 flex flex-col items-center gap-1 transition-all duration-200",
                  "focus:outline-none group"
                )}
                style={{ left: `${(index / (LEVELS.length - 1)) * 100}%` }}
              >
                {/* Dot indicator */}
                <motion.div
                  animate={{
                    scale: isActive ? 1.3 : 1,
                    opacity: isPast ? 1 : 0.4,
                  }}
                  className={cn(
                    "w-4 h-4 rounded-full border-2 transition-colors",
                    isActive
                      ? "border-accent-cyan bg-accent-cyan ring-2 ring-accent-cyan/30 shadow-glow-subtle"
                      : isPast
                      ? "border-accent-cyan/60 bg-accent-cyan/60"
                      : "border-text-secondary/30 bg-transparent"
                  )}
                />

                {/* Label below */}
                <span
                  className={cn(
                    "text-[10px] text-center transition-colors mt-2",
                    isActive
                      ? "text-text-primary font-medium"
                      : isPast
                      ? "text-text-secondary"
                      : "text-text-secondary/40"
                  )}
                >
                  {level.label}
                </span>

                {/* Tooltip on hover */}
                <div className="absolute top-8 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                  <div className="bg-card border border-cosmic-border rounded-lg px-2 py-1 shadow-lg">
                    <p className="text-[10px] whitespace-nowrap text-text-accent-cyan">
                      <Icon className="w-3 h-3 inline mr-1" />
                      {level.description}
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Description row */}
      <div className="flex justify-between text-[10px] text-text-secondary/50 px-1">
        <span>精准执行</span>
        <span>自由创意</span>
      </div>

      {/* Active level card */}
      <motion.div
        key={value}
        initial={{ opacity: 0, y: 5 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn(
          "flex items-center gap-3 p-3 rounded-xl border transition-colors",
          "bg-gradient-to-r bg-opacity-10",
          currentLevel.gradient.replace("from-", "from-").replace("to-", "to-") + "/10",
          "border-cosmic-border/40"
        )}
      >
        <div
          className={cn(
            "w-8 h-8 rounded-lg flex items-center justify-center",
            "bg-gradient-to-br",
            currentLevel.gradient
          )}
        >
          {<currentLevel.icon className="w-4 h-4 text-white" />}
        </div>
        <div>
          <p className="text-sm font-medium">{currentLevel.label}模式</p>
          <p className="text-xs text-text-secondary">{currentLevel.description}</p>
        </div>
        <div className="ml-auto text-xs font-mono text-text-secondary">
          {currentLevel.value}%
        </div>
      </motion.div>
    </div>
  );
}
