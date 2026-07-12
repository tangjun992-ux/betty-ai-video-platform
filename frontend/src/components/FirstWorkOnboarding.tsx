"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Check, ChevronRight, ImageIcon, Sparkles, X } from "lucide-react";
import {
  useAuthStore,
  useCreationStore,
  useOnboardingStore,
} from "@/lib/stores";
import { API_BASE, trackOnboarding } from "@/lib/api";
import { cn } from "@/lib/utils";

const RECOMMENDED_PROMPT =
  "一杯精品咖啡放在大理石桌面，清晨柔光，商业产品摄影，电影级质感";

/** Lightweight first-work activation checklist, shown only to logged-in users
 * whose server account has no completed generation. */
export function FirstWorkOnboarding() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, token } = useAuthStore();
  const prompt = useCreationStore((s) => s.prompt);
  const setPrompt = useCreationStore((s) => s.setPrompt);
  const records = useOnboardingStore((s) => s.records);
  const startFor = useOnboardingStore((s) => s.startFor);
  const completeFor = useOnboardingStore((s) => s.completeFor);
  const dismissFor = useOnboardingStore((s) => s.dismissFor);
  const [hasFirstWork, setHasFirstWork] = useState<boolean | null>(null);

  const userId = user?.id ? String(user.id) : "";
  const record = userId ? records[userId] : undefined;

  useEffect(() => {
    if (!userId || !token) {
      setHasFirstWork(null);
      return;
    }
    let active = true;
    fetch(`${API_BASE}/dashboard/dashboard?limit=1`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!active || !d) return;
        const done = Number(d?.stats?.assets_generated || 0) > 0;
        setHasFirstWork(done);
        if (done) completeFor(userId);
      })
      .catch(() => setHasFirstWork(false));
    return () => { active = false; };
  }, [userId, token, completeFor]);

  const inCreate = pathname === "/create/image";
  const promptReady = Boolean(prompt.trim());
  const progress = useMemo(
    () => (1 + (inCreate ? 1 : 0)) / 3 * 100,
    [inCreate],
  );

  if (!userId || pathname.startsWith("/auth") || hasFirstWork !== false
      || record?.completed || record?.dismissed) {
    return null;
  }

  const begin = () => {
    startFor(userId);
    if (!prompt.trim()) setPrompt(RECOMMENDED_PROMPT);
    trackOnboarding("prompt_ready");
    router.push(`/create/image?onboard=1&prompt=${encodeURIComponent(RECOMMENDED_PROMPT)}`);
  };

  const steps = [
    { label: "账号已创建", done: true },
    { label: "进入图片创作", done: inCreate },
    { label: "生成第一张作品", done: false },
  ];

  return (
    <aside className="fixed bottom-5 left-[calc(var(--sidebar-width,64px)+20px)] z-50 w-[310px] rounded-2xl border border-brand/20 bg-cosmic-surface/95 p-4 shadow-elevation-lg backdrop-blur-xl">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand/10">
            <Sparkles className="h-4 w-4 text-brand" />
          </span>
          <div>
            <p className="text-sm font-semibold text-text-primary">完成你的第一张作品</p>
            <p className="text-[11px] text-text-tertiary">约 30 秒 · 新用户推荐路径</p>
          </div>
        </div>
        <button
          onClick={() => { dismissFor(userId); trackOnboarding("dismissed"); }}
          className="btn-icon h-7 w-7"
          aria-label="稍后再说"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-cosmic-subtle">
        <div className="h-full rounded-full bg-brand transition-all" style={{ width: `${progress}%` }} />
      </div>

      <div className="mt-3 space-y-1.5">
        {steps.map((step) => (
          <div key={step.label} className="flex items-center gap-2 text-xs">
            <span className={cn(
              "flex h-5 w-5 items-center justify-center rounded-full border",
              step.done
                ? "border-success/30 bg-success/10 text-success"
                : "border-cosmic-border text-text-tertiary",
            )}>
              {step.done ? <Check className="h-3 w-3" /> : <span className="h-1.5 w-1.5 rounded-full bg-current" />}
            </span>
            <span className={step.done ? "text-text-secondary" : "text-text-primary"}>{step.label}</span>
          </div>
        ))}
      </div>

      <button onClick={begin} className="btn-primary mt-4 w-full">
        <ImageIcon className="h-4 w-4" />
        {inCreate ? (promptReady ? "立即生成" : "使用推荐提示词") : "开始创作"}
        <ChevronRight className="h-4 w-4" />
      </button>
    </aside>
  );
}
