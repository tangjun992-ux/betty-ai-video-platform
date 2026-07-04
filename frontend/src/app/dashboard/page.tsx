"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Sparkles, Image, Video, Mic, Scissors, Wand2,
  User, Package, Zap, Play, Clock, ChevronRight,
  ArrowRight, TrendingUp, Star, MoreHorizontal, Bot,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api";

/* ═══════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════ */

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

interface DashboardModel {
  name: string;
  type: string;
  provider: string;
  badge: string | null;
}

interface DashboardResponse {
  stats: DashboardStats;
  recent_items: RecentItem[];
  models: DashboardModel[];
}

/* ═══════════════════════════════════════════════════════
   Static data (tools are constant)
   ═══════════════════════════════════════════════════════ */

const FEATURED_TOOLS = [
  { icon: Video, label: "Seedance 2.0", desc: "Cinematic video generation with motion control", badge: "New", color: "from-brand to-accent-violet", href: "/create/video" },
  { icon: Mic, label: "Lip-Sync Studio", desc: "Create talking avatars with voice sync", badge: "Pro", color: "from-cyan-500 to-blue-600", href: "/create/lipsync" },
  { icon: Bot, label: "betty Agent", desc: "Don't prompt, Just Direct — AI plans & creates", badge: "AI", color: "from-amber-500 to-orange-600", href: "/agent" },
  { icon: Image, label: "Image Editor", desc: "Professional AI image editing suite", badge: null, color: "from-emerald-500 to-teal-600", href: "/create/image" },
  { icon: Package, label: "Product Shots", desc: "Batch product photography at scale", badge: null, color: "from-rose-500 to-pink-600", href: "/create/image" },
  { icon: Wand2, label: "Upscaler 4K", desc: "2x resolution boost, no quality loss", badge: null, color: "from-sky-500 to-indigo-600", href: "/tools" },
];

/* ═══════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════ */

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

/* ═══════════════════════════════════════════════════════
   Sub-components
   ═══════════════════════════════════════════════════════ */

function Card({ children, className, hover = true }: {
  children: React.ReactNode; className?: string; hover?: boolean;
}) {
  return (
    <motion.div
      whileHover={hover ? { scale: 1.01, y: -2 } : undefined}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={cn(
        "rounded-2xl border border-cosmic-border bg-cosmic-surface",
        hover && "hover:border-brand/20 hover:shadow-card-hover transition-all cursor-pointer",
        className
      )}
    >
      {children}
    </motion.div>
  );
}

function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-xl bg-cosmic-subtle", className)} />;
}

/* ═══════════════════════════════════════════════════════
   Dashboard Page
   ═══════════════════════════════════════════════════════ */

export default function DashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [prompt, setPrompt] = useState("");
  const [activeTool, setActiveTool] = useState<"video" | "image" | "agent">("video");

  const fetchDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE}/dashboard/dashboard`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: DashboardResponse = await res.json();
      setData(json);
      if (json.models.length > 0) setSelectedModel(json.models[0].name);
    } catch (e: any) {
      setError(e.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

  const handleGenerate = () => {
    const path = activeTool === "agent" ? "/agent" : activeTool === "video" ? "/create/video" : "/create/image";
    window.location.href = prompt.trim() ? `${path}?prompt=${encodeURIComponent(prompt)}` : path;
  };

  /* ── Derived ── */
  const stats = data?.stats ?? null;
  const recentItems = data?.recent_items ?? [];
  const models = data?.models ?? [];

  const statCards = stats ? [
    { label: "Credits Remaining", value: formatNumber(stats.credits_remaining), icon: Zap, color: "text-brand" },
    { label: "Assets Generated", value: formatNumber(stats.assets_generated), icon: Image, color: "text-emerald-500" },
    { label: "Recent (7d)", value: String(stats.recent_generations), icon: Clock, color: "text-amber-500" },
    { label: "Success Rate", value: `${stats.success_rate}%`, icon: TrendingUp, color: "text-sky-500" },
  ] : [];

  /* ── Loading ── */
  if (loading && !data) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-10">
        <div>
          <Skeleton className="h-8 w-64 mb-2" />
          <Skeleton className="h-4 w-40" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
            {[1,2,3,4].map(i => <Skeleton key={i} className="h-24" />)}
          </div>
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  /* ── Error ── */
  if (error && !data) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-20 text-center">
        <div className="text-destructive mb-3 text-lg font-semibold">Failed to load dashboard</div>
        <div className="text-text-tertiary text-sm mb-6">{error}</div>
        <button onClick={fetchDashboard} className="px-5 py-2 rounded-xl bg-brand/10 text-brand text-sm font-medium hover:bg-brand/15 transition-colors">
          Retry
        </button>
      </div>
    );
  }

  const hasRecentItems = recentItems.length > 0;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-10">
      {/* ═══ Welcome + Stats ═══ */}
      <div>
        <motion.h1 initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="text-2xl font-semibold text-text-primary mb-1">
          Good morning, Creator 👋
        </motion.h1>
        <motion.p initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="text-text-secondary text-sm">
          What will you create today?
        </motion.p>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
          {statCards.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.05 }}
              className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-4"
            >
              <s.icon className={cn("w-5 h-5 mb-2", s.color)} />
              <div className="text-xl font-semibold text-text-primary">{s.value}</div>
              <div className="text-xs text-text-tertiary">{s.label}</div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* ═══ Prompt Workspace ═══ */}
      <Card className="p-6 md:p-8 !cursor-default" hover={false}>
        <div className="flex items-center gap-2 mb-5">
          {([
            { key: "video", icon: Video, label: "Video" },
            { key: "image", icon: Image, label: "Image" },
            { key: "agent", icon: Bot, label: "Agent" },
          ] as const).map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTool(t.key)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all",
                activeTool === t.key
                  ? "bg-brand/10 text-brand border border-brand/20"
                  : "text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle border border-transparent"
              )}
            >
              <t.icon className="w-4 h-4" /> {t.label}
            </button>
          ))}
        </div>

        {/* Model selector chips — from API */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-[10px] font-semibold text-text-tertiary uppercase tracking-widest mr-1">Model</span>
          {models.map((m) => (
            <button
              key={m.name}
              onClick={() => setSelectedModel(m.name)}
              className={cn(
                "px-2.5 py-1 rounded-lg text-xs font-medium transition-all border",
                selectedModel === m.name
                  ? "bg-brand/8 text-brand border-brand/20"
                  : "text-text-tertiary border-transparent hover:text-text-secondary hover:bg-cosmic-subtle"
              )}
            >
              {m.name}
            </button>
          ))}
          {models.length === 0 && (
            <span className="text-xs text-text-tertiary">No models available</span>
          )}
        </div>

        {/* Prompt input */}
        <div className="relative">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleGenerate(); } }}
            placeholder="Describe what you want to create... (e.g. Cinematic product video in a warm coffee shop, 15s)"
            rows={3}
            className="w-full px-4 py-3.5 rounded-2xl bg-cosmic-subtle border border-cosmic-border text-text-primary text-sm placeholder:text-text-disabled resize-none focus:outline-none focus:border-brand/40 focus:bg-cosmic-surface transition-all"
          />
          <div className="flex items-center justify-between mt-3">
            <div className="flex items-center gap-2">
              <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-tertiary hover:text-text-secondary hover:bg-cosmic-subtle transition-colors border border-cosmic-border">
                📎 Attach
              </button>
              <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-brand/60 hover:text-brand transition-colors">
                <Sparkles className="w-3.5 h-3.5" /> Ask AI to improve
              </button>
            </div>
            <button
              onClick={handleGenerate}
              className="flex items-center gap-2 h-10 px-5 rounded-xl bg-brand text-white text-sm font-semibold hover:bg-brand-strong hover:-translate-y-px shadow-button-glow transition-all active:scale-[0.98]"
            >
              <Sparkles className="w-4 h-4" /> Generate
            </button>
          </div>
        </div>
      </Card>

      {/* ═══ Recent + Tools (2-col) ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Creations */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-text-primary">Recent</h2>
            <Link href="/explore" className="text-xs text-brand hover:text-brand-strong flex items-center gap-1 transition-colors">
              View all <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {hasRecentItems ? (
            <div className="grid grid-cols-2 gap-3">
              {recentItems.slice(0, 4).map((item, i) => (
                <motion.div
                  key={item.task_id || i}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.05 }}
                >
                  <Card className="overflow-hidden">
                    <div className="aspect-video bg-cosmic-subtle flex items-center justify-center text-3xl relative group">
                      {item.thumbnail_url ? (
                        <img src={item.thumbnail_url} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <span>{item.media_type === "video" ? "🎬" : "🖼️"}</span>
                      )}
                      {item.media_type === "video" && (
                        <div className="absolute inset-0 bg-text-primary/10 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                          <Play className="w-10 h-10 text-text-primary/60" />
                        </div>
                      )}
                      <span className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded-md bg-cosmic-surface/80 backdrop-blur text-[10px] text-text-secondary">
                        {formatDuration(item.duration)}
                      </span>
                    </div>
                    <div className="p-3">
                      <div className="text-sm font-medium text-text-primary truncate">{truncatePrompt(item.prompt || "Untitled")}</div>
                      <div className="flex items-center gap-2 mt-1">
                        {item.model && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-brand/8 text-brand">{item.model}</span>
                        )}
                        {item.created_at && (
                          <span className="text-[10px] text-text-tertiary">{formatDate(item.created_at)}</span>
                        )}
                        <button className="ml-auto p-1 rounded hover:bg-cosmic-subtle">
                          <MoreHorizontal className="w-3.5 h-3.5 text-text-tertiary" />
                        </button>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-12 text-center">
              <Sparkles className="w-10 h-10 text-text-disabled mx-auto mb-3" />
              <div className="text-text-tertiary text-sm">No creations yet</div>
              <div className="text-text-disabled text-xs mt-1">Your generated assets will appear here</div>
            </div>
          )}
        </div>

        {/* Featured Tools */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-text-primary">Quick Tools</h2>
            <Link href="/create/image" className="text-xs text-brand hover:text-brand-strong flex items-center gap-1 transition-colors">
              All tools <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          <div className="space-y-2">
            {FEATURED_TOOLS.map((tool, i) => (
              <motion.div
                key={tool.label}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.04 }}
              >
                <Link href={tool.href}>
                  <Card className="p-3.5 flex items-center gap-3">
                    <div className={cn("w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center flex-shrink-0", tool.color)}>
                      <tool.icon className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-text-primary">{tool.label}</span>
                        {tool.badge && (
                          <span className={cn(
                            "px-1.5 py-0.5 rounded-md text-[9px] font-bold",
                            tool.badge === "New" && "bg-brand/10 text-brand",
                            tool.badge === "Pro" && "bg-amber-500/10 text-amber-600",
                            tool.badge === "AI" && "bg-emerald-500/10 text-emerald-600",
                          )}>{tool.badge}</span>
                        )}
                      </div>
                      <div className="text-[11px] text-text-tertiary mt-0.5 truncate">{tool.desc}</div>
                    </div>
                    <ArrowRight className="w-4 h-4 text-text-disabled flex-shrink-0" />
                  </Card>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* ═══ Agent Showcase ═══ */}
      <Card className="p-8 relative overflow-hidden" hover={false}>
        <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-brand/[0.04] to-transparent rounded-full blur-3xl pointer-events-none" />
        <div className="relative flex flex-col lg:flex-row items-start gap-8">
          <div className="flex-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-brand/6 border border-brand/10 text-[11px] font-semibold text-brand mb-4">
              <Bot className="w-3 h-3" /> betty Agent
            </span>
            <h3 className="text-2xl font-bold text-text-primary mb-2">
              Don&apos;t Prompt, <span className="text-brand">Just Direct</span>
            </h3>
            <p className="text-text-secondary max-w-md mb-5 text-sm leading-relaxed">
              像导演一样工作。描述你的创意意图，AI Agent 自动规划全流程 — 从解析创意、智能选模型、生成视觉、动态视频到合成，一步到位。
            </p>
            <Link
              href="/agent"
              className="inline-flex items-center gap-2 h-10 px-5 rounded-xl bg-brand text-white text-sm font-semibold hover:bg-brand-strong hover:-translate-y-px shadow-button-glow transition-all"
            >
              Try Agent <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="flex-shrink-0 grid grid-cols-3 gap-2">
            {["💡 Describe", "🧠 Plan", "🖼️ Create", "🎥 Animate", "🎵 Audio", "🎬 Compose"].map((s) => (
              <div key={s} className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cosmic-subtle border border-cosmic-border text-xs text-text-secondary">{s}</div>
            ))}
          </div>
        </div>
      </Card>

      {/* ═══ Creator Results (horizontal scroll) ═══ */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">Creator Results</h2>
        </div>
        <div className="flex gap-3 overflow-x-auto pb-2 -mx-6 px-6 scrollbar-hide">
          {[
            { name: "@captainn", role: "Creator", stat: "92M", label: "views", avatar: "C", color: "from-brand to-accent-violet" },
            { name: "@royalty", role: "Creator", stat: "100M", label: "views", avatar: "R", color: "from-cyan-500 to-blue-600" },
            { name: "@funnyfromai", role: "Creator", stat: "$1K+", label: "income", avatar: "F", color: "from-amber-500 to-orange-600" },
            { name: "@deep.seavisitor", role: "Creator", stat: "190M", label: "views", avatar: "D", color: "from-emerald-500 to-teal-600" },
          ].map((t) => (
            <motion.div
              key={t.name}
              whileHover={{ scale: 1.03, y: -4 }}
              className="flex-shrink-0 w-56 p-4 rounded-2xl border border-cosmic-border bg-cosmic-surface hover:border-brand/15 hover:shadow-card-hover transition-all"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className={cn("w-10 h-10 rounded-full bg-gradient-to-br flex items-center justify-center text-white text-sm font-bold", t.color)}>{t.avatar}</div>
                <div>
                  <div className="text-sm font-medium text-text-primary">{t.name}</div>
                  <div className="text-[11px] text-text-tertiary">{t.role}</div>
                </div>
              </div>
              <div className="text-xl font-semibold text-text-primary">{t.stat}</div>
              <div className="text-xs text-text-tertiary">{t.label}</div>
              <div className="flex gap-0.5 mt-2 text-brand text-xs">★★★★★</div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
