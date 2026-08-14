"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Sparkles, Image, Video, Wand2, Lightbulb, AudioLines,
  Play, Clock, ChevronRight, Loader2, Zap, TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { API_BASE, enhancePrompt } from "@/lib/api";
import { useLocale } from "@/i18n/LocaleProvider";
import { useToast } from "@/components/Toast";

const MEDIA_ORIGIN = API_BASE.replace(/\/api\/v1$/, "");
const resolveMedia = (u: string | null | undefined) =>
  !u ? "" : u.startsWith("/") ? `${MEDIA_ORIGIN}${u}` : u;

interface DashboardStats {
  credits_remaining: number;
  assets_generated: number;
  recent_generations: number;
  success_rate: number;
  total_spent: number;
}

interface RecentItem {
  task_id: string;
  prompt: string;
  media_type: string;
  status: string;
  model: string | null;
  thumbnail_url: string | null;
  media_url: string | null;
  duration: number | null;
  created_at: string | null;
}

interface DashboardResponse {
  stats: DashboardStats;
  recent_items: RecentItem[];
}

function formatNumber(n: number): string {
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 1000) return n.toLocaleString();
  return String(n);
}

function truncatePrompt(p: string): string {
  return p.length > 60 ? p.slice(0, 60) + "…" : p;
}

function formatDuration(secs: number | null | undefined): string {
  if (secs == null) return "—";
  if (secs < 60) return `${Math.round(secs)}s`;
  return `${Math.floor(secs / 60)}m${Math.round(secs % 60)}s`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "Just now";
  if (hours < 24) return `${hours}h ago`;
  if (hours < 48) return "Yesterday";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function looksLikeImage(prompt: string): boolean {
  return /图|海报|头像|产品照|摄影|image|photo|poster|portrait|still/i.test(prompt);
}

export default function DashboardPage() {
  const { t, locale } = useLocale();
  const en = locale === "en";
  const router = useRouter();
  const toast = useToast();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [prompt, setPrompt] = useState("");
  const [enhancing, setEnhancing] = useState(false);

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/dashboard/dashboard`);
      if (!res.ok) return;
      const json: DashboardResponse = await res.json();
      setData(json);
    } catch {
      /* conversation home stays usable without stats */
    }
  }, []);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

  const goCreate = (path: string) => {
    const q = prompt.trim();
    const qs = q ? `?${path.includes("/agent") ? "brief" : path.includes("/audio") ? "text" : "prompt"}=${encodeURIComponent(q)}` : "";
    router.push(`${path}${qs}`);
  };

  const handleHelpPrompt = async () => {
    if (!prompt.trim() || enhancing) return;
    setEnhancing(true);
    try {
      const r = await enhancePrompt(prompt.trim(), looksLikeImage(prompt) ? "image" : "video");
      if (r.enhanced) {
        setPrompt(r.enhanced);
        toast.success(en ? "Prompt enhanced" : "提示词已优化");
      }
    } catch {
      toast.error(en ? "Enhance failed" : "优化失败", en ? "Keep the original prompt" : "已保留原文");
    } finally {
      setEnhancing(false);
    }
  };

  const handleCreateContent = () => {
    if (!prompt.trim()) {
      toast.error(en ? "Describe your idea first" : "先描述你想创作的内容");
      return;
    }
    goCreate(looksLikeImage(prompt) ? "/create/image" : "/create/video");
  };

  const stats = data?.stats ?? null;
  const recentItems = data?.recent_items ?? [];
  const statCards = stats ? [
    { label: en ? "Credits" : "剩余积分", value: formatNumber(stats.credits_remaining), icon: Zap, color: "text-brand" },
    { label: en ? "Assets" : "已生成资产", value: formatNumber(stats.assets_generated), icon: Image, color: "text-emerald-500" },
    { label: en ? "7 days" : "近 7 天", value: String(stats.recent_generations), icon: Clock, color: "text-amber-500" },
    { label: en ? "Success" : "成功率", value: `${stats.success_rate}%`, icon: TrendingUp, color: "text-sky-500" },
  ] : [];

  const ctas = [
    { key: "help-prompt", icon: Sparkles, label: t("dashboard.helpPrompt"), onClick: handleHelpPrompt, testId: "cta-help-prompt" },
    { key: "create", icon: Wand2, label: t("dashboard.createContent"), onClick: handleCreateContent, testId: "cta-create-content" },
    { key: "ideate", icon: Lightbulb, label: t("dashboard.helpIdeate"), onClick: () => goCreate("/agent"), testId: "cta-help-ideate" },
    { key: "audio", icon: AudioLines, label: t("dashboard.generateAudio"), onClick: () => goCreate("/create/audio"), testId: "cta-generate-audio" },
  ] as const;

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 md:py-16 space-y-12">
      {/* ═══ Conversation home — 对标 Yapper /dashboard ═══ */}
      <section className="text-center">
        <motion.p
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-sm text-text-tertiary mb-3"
        >
          {(() => {
            const h = new Date().getHours();
            return h < 12 ? t("dashboard.greetingMorning")
              : h < 18 ? t("dashboard.greetingAfternoon")
              : t("dashboard.greetingEvening");
          })()}，{t("dashboard.creator")}
        </motion.p>
        <motion.h1
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-3xl md:text-4xl font-semibold tracking-tight text-text-primary mb-8"
          data-testid="dashboard-headline"
        >
          {t("dashboard.question")}
        </motion.h1>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="rounded-2xl border border-cosmic-border bg-cosmic-surface shadow-elevation-md p-4 md:p-5 text-left"
        >
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleCreateContent();
              }
            }}
            placeholder={t("dashboard.placeholder")}
            rows={4}
            data-testid="dashboard-prompt"
            className="w-full px-1 py-1 bg-transparent text-[15px] leading-relaxed text-text-primary placeholder:text-text-tertiary/50 resize-none focus:outline-none min-h-[96px]"
          />
          <div className="flex items-center justify-between mt-2 px-0.5">
            <span className="inline-flex items-center gap-1.5 h-7 px-2.5 rounded-lg text-[11px] font-medium bg-brand/8 text-brand border border-brand/15">
              <Sparkles className="w-3 h-3" /> {t("dashboard.promptMode")}
            </span>
            <span className="text-[11px] text-text-tertiary">{prompt.length}/5000</span>
          </div>
        </motion.div>

        <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-2.5">
          {ctas.map((c, i) => (
            <motion.button
              key={c.key}
              type="button"
              data-testid={c.testId}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 + i * 0.04 }}
              onClick={c.onClick}
              disabled={c.key === "help-prompt" && enhancing}
              className={cn(
                "flex flex-col items-center gap-2 rounded-2xl border border-cosmic-border bg-cosmic-surface",
                "px-3 py-4 text-sm font-medium text-text-primary",
                "hover:border-brand/30 hover:bg-brand/[0.04] hover:-translate-y-px transition-all",
                "disabled:opacity-50 disabled:cursor-not-allowed",
              )}
            >
              {c.key === "help-prompt" && enhancing
                ? <Loader2 className="w-5 h-5 animate-spin text-brand" />
                : <c.icon className="w-5 h-5 text-brand" />}
              {c.label}
            </motion.button>
          ))}
        </div>
      </section>

      {/* ═══ Secondary: stats (don't compete with CTAs) ═══ */}
      {statCards.length > 0 && (
        <section>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {statCards.map((s) => (
              <div key={s.label} className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-4">
                <s.icon className={cn("w-4 h-4 mb-2", s.color)} />
                <div className="text-lg font-semibold text-text-primary">{s.value}</div>
                <div className="text-[11px] text-text-tertiary">{s.label}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ═══ Secondary: recent jobs ═══ */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-text-primary">{t("dashboard.recent")}</h2>
          <Link href="/library" className="text-xs text-brand hover:text-brand-strong flex items-center gap-1">
            {t("dashboard.all")} <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>
        {recentItems.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {recentItems.slice(0, 8).map((item, i) => {
              const media = resolveMedia(item.media_url);
              const thumb = resolveMedia(item.thumbnail_url);
              const isVideo = item.media_type === "video";
              return (
                <Link key={item.task_id || i} href="/library">
                  <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface overflow-hidden hover:border-brand/20 transition-all">
                    <div className="aspect-video bg-cosmic-subtle flex items-center justify-center relative group">
                      {isVideo && media ? (
                        <video
                          src={media} muted loop playsInline preload="metadata"
                          className="w-full h-full object-cover"
                          onMouseEnter={(e) => e.currentTarget.play().catch(() => {})}
                          onMouseLeave={(e) => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }}
                        />
                      ) : thumb ? (
                        <img src={thumb} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <span className="text-2xl">{isVideo ? "🎬" : "🖼️"}</span>
                      )}
                      {isVideo && (
                        <div className="absolute inset-0 bg-text-primary/10 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                          <Play className="w-8 h-8 text-white/80" />
                        </div>
                      )}
                      {isVideo && item.duration != null && (
                        <span className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded-md bg-cosmic-surface/80 text-[10px] text-text-secondary">
                          {formatDuration(item.duration)}
                        </span>
                      )}
                    </div>
                    <div className="p-2.5">
                      <div className="text-xs font-medium text-text-primary truncate">{truncatePrompt(item.prompt || "Untitled")}</div>
                      <div className="flex items-center gap-2 mt-1">
                        {item.model && <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-brand/8 text-brand truncate max-w-[100px]">{item.model}</span>}
                        {item.created_at && <span className="text-[10px] text-text-tertiary">{formatDate(item.created_at)}</span>}
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-10 text-center">
            <Sparkles className="w-8 h-8 text-text-disabled mx-auto mb-3" />
            <div className="text-text-tertiary text-sm">{en ? "No creations yet" : "还没有作品"}</div>
            <div className="text-text-disabled text-xs mt-1">{en ? "Describe an idea above — Create Content is one click." : "在上方描述创意，点「开始创作」即可。"}</div>
          </div>
        )}
      </section>
    </div>
  );
}
