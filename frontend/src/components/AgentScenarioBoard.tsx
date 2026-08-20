"use client";

import { ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export type AgentScenarioCard = {
  id: string;
  icon: React.ElementType;
  cat: "视频" | "图片" | "工具";
  title: string;
  desc: string;
};

const GRADIENT: Record<AgentScenarioCard["cat"], string> = {
  视频: "from-accent-violet to-accent-blue",
  图片: "from-accent-blue to-accent-fuchsia",
  工具: "from-brand to-accent-violet",
};

function ScenarioSection({
  testId,
  label,
  list,
  onSelect,
  titleOf,
  descOf,
  catOf,
}: {
  testId: string;
  label: string;
  list: AgentScenarioCard[];
  onSelect: (id: string) => void;
  titleOf: (s: AgentScenarioCard) => string;
  descOf: (s: AgentScenarioCard) => string;
  catOf: (cat: string) => string;
}) {
  if (!list.length) return null;
  return (
    <section data-testid={testId} className="mb-6 last:mb-0">
      <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-tertiary">
        {label}
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {list.map((sc) => (
          <button
            key={sc.id}
            type="button"
            onClick={() => onSelect(sc.id)}
            className="group relative flex items-start gap-3 rounded-2xl border border-cosmic-border/50 bg-cosmic-surface/50 p-4 text-left transition-all hover:border-brand/40 hover:shadow-card"
            data-testid={`agent-scenario-${sc.id}`}
          >
            <div
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br",
                GRADIENT[sc.cat],
              )}
            >
              <sc.icon className="h-5 w-5 text-white" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="mb-0.5 flex items-center gap-2">
                <span className="text-sm font-semibold text-text-primary">{titleOf(sc)}</span>
                <span className="rounded bg-cosmic-subtle px-1.5 py-0.5 text-[10px] text-text-tertiary">
                  {catOf(sc.cat)}
                </span>
              </div>
              <p className="line-clamp-2 text-[11px] leading-snug text-text-secondary">{descOf(sc)}</p>
            </div>
            <span className="absolute right-3 top-1/2 inline-flex -translate-y-1/2 items-center gap-1 text-[11px] font-medium text-brand opacity-0 transition-opacity group-hover:opacity-100">
              试用 <ArrowRight className="h-3 w-3" />
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

/** Idle "Try Feature" board — Video / Image groups, studio-token gradients. */
export function AgentScenarioBoard({
  items,
  onSelect,
  titleOf,
  descOf,
  catOf,
  videoLabel = "视频",
  imageLabel = "图片",
  utilityLabel = "工具",
}: {
  items: AgentScenarioCard[];
  onSelect: (id: string) => void;
  titleOf: (s: AgentScenarioCard) => string;
  descOf: (s: AgentScenarioCard) => string;
  catOf: (cat: string) => string;
  videoLabel?: string;
  imageLabel?: string;
  utilityLabel?: string;
}) {
  const video = items.filter((s) => s.cat === "视频");
  const image = items.filter((s) => s.cat === "图片");
  const other = items.filter((s) => s.cat === "工具");

  return (
    <div className="mt-5" data-testid="agent-try-features">
      <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-text-tertiary">
        试试这些能力 · 或直接描述你的创意
      </p>
      <ScenarioSection
        testId="agent-try-video"
        label={videoLabel}
        list={video}
        onSelect={onSelect}
        titleOf={titleOf}
        descOf={descOf}
        catOf={catOf}
      />
      <ScenarioSection
        testId="agent-try-image"
        label={imageLabel}
        list={image}
        onSelect={onSelect}
        titleOf={titleOf}
        descOf={descOf}
        catOf={catOf}
      />
      {other.length > 0 && (
        <ScenarioSection
          testId="agent-try-utility"
          label={utilityLabel}
          list={other}
          onSelect={onSelect}
          titleOf={titleOf}
          descOf={descOf}
          catOf={catOf}
        />
      )}
    </div>
  );
}
