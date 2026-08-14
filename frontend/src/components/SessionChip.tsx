"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, X } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  createStudioSession,
  listStudioSessions,
  type CreativeSession,
} from "@/lib/api";

/**
 * Compact session picker for create pages — aligns with Yapper Video "Session".
 * Reuses director_sessions; video uses intent=video_create.
 */
export function SessionChip({
  intent,
  value,
  onChange,
  label,
}: {
  intent: string;
  value: string | null;
  onChange: (uid: string | null) => void;
  label?: string;
}) {
  const [sessions, setSessions] = useState<CreativeSession[]>([]);
  const [open, setOpen] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setSessions(await listStudioSessions(intent));
    } catch {
      setSessions([]);
    }
  }, [intent]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const active = sessions.find((s) => s.session_uid === value) || null;

  const handleNew = async () => {
    try {
      const created = await createStudioSession("新视频会话", intent);
      setSessions((prev) => [created, ...prev]);
      onChange(created.session_uid);
      setOpen(false);
    } catch {
      /* guest/offline ok */
    }
  };

  return (
    <div className="relative" data-testid="session-chip">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[11px] uppercase tracking-wider text-text-secondary/70">
          {label || "Session"}
        </span>
        <button
          type="button"
          data-testid="session-chip-toggle"
          onClick={() => setOpen((v) => !v)}
          className={cn(
            "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs border transition-colors",
            active
              ? "border-accent-cyan/40 bg-accent-cyan/10 text-accent-cyan"
              : "border-cosmic-border text-text-secondary hover:text-text-primary",
          )}
        >
          {active ? active.title || "未命名会话" : "未绑定会话"}
        </button>
        {active && (
          <button
            type="button"
            aria-label="清除会话"
            onClick={() => onChange(null)}
            className="text-text-secondary/60 hover:text-text-primary"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
        <button
          type="button"
          data-testid="session-chip-new"
          onClick={handleNew}
          className="inline-flex items-center gap-0.5 text-[11px] text-accent-cyan hover:opacity-80"
        >
          <Plus className="w-3.5 h-3.5" /> 新建
        </button>
        <a href="/sessions" className="text-[11px] text-text-secondary hover:text-text-primary">
          全部会话
        </a>
      </div>
      {open && (
        <div
          data-testid="session-chip-list"
          className="absolute z-20 mt-2 min-w-[220px] rounded-xl border border-cosmic-border bg-cosmic-surface shadow-elevation-md p-1.5"
        >
          {sessions.length === 0 ? (
            <p className="px-2.5 py-2 text-[11px] text-text-secondary">还没有会话，点新建开始归档。</p>
          ) : (
            sessions.map((s) => (
              <button
                key={s.session_uid}
                type="button"
                onClick={() => {
                  onChange(s.session_uid);
                  setOpen(false);
                }}
                className={cn(
                  "w-full text-left px-2.5 py-1.5 rounded-lg text-xs truncate",
                  value === s.session_uid
                    ? "bg-accent-cyan/10 text-accent-cyan"
                    : "text-text-secondary hover:bg-cosmic-subtle hover:text-text-primary",
                )}
              >
                {s.title || "未命名会话"}
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
