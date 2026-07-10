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
import { API_BASE, enhancePrompt } from "@/lib/api";

const MEDIA_ORIGIN = API_BASE.replace(/\/api\/v1$/, "");
const resolveMedia = (u: string | null | undefined) =>
  !u ? "" : u.startsWith("/") ? `${MEDIA_ORIGIN}${u}` : u;

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
  { icon: Video, label: "Seedance 2.0", desc: "电影级视频生成，支持运动控制", badge: "新", color: "from-brand to-accent-violet", href: "/create/video" },
  { icon: Mic, label: "唇形同步工作室", desc: "为图像配音，生成开口说话的数字人", badge: "Pro", color: "from-cyan-500 to-blue-600", href: "/create/lipsync" },
  { icon: Bot, label: "betty Agent", desc: "不写提示词，只做导演 — AI 自动规划创作", badge: "AI", color: "from-amber-500 to-orange-600", href: "/agent" },
  { icon: Image, label: "图片编辑器", desc: "专业级 AI 图像编辑套件", badge: null, color: "from-emerald-500 to-teal-600", href: "/create/image" },
  { icon: Package, label: "产品图批量", desc: "规模化生成专业产品摄影", badge: null, color: "from-rose-500 to-pink-600", href: "/create/image" },
  { icon: Wand2, label: "4K 放大", desc: "2 倍分辨率提升，画质无损", badge: null, color: "from-sky-500 to-indigo-600", href: "/tools" },
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
  const [enhancing, setEnhancing] = useState(false);

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
    const params = new URLSearchParams();
    if (prompt.trim()) params.set("prompt", prompt.trim());
    if (selectedModel && activeTool !== "agent") params.set("model", selectedModel);
    const qs = params.toString();
    window.location.href = qs ? `${path}?${qs}` : path;
  };

  const handleEnhance = async () => {
    if (!prompt.trim() || enhancing) return;
    setEnhancing(true);
    try {
      const r = await enhancePrompt(prompt.trim(), activeTool === "image" ? "image" : "video");
      if (r.enhanced) setPrompt(r.enhanced);
    } catch {
      /* keep original prompt on failure */
    } finally {
      setEnhancing(false);
    }
  };

  /* ── Derived ── */
  const stats = data?.stats ?? null;
  const recentItems = data?.recent_items ?? [];
  const models = data?.models ?? [];

  const statCards = stats ? [
    { label: "剩余积分", value: formatNumber(stats.credits_remaining), icon: Zap, color: "text-brand" },
    { label: "已生成资产", value: formatNumber(stats.assets_generated), icon: Image, color: "text-emerald-500" },
    { label: "近 7 天", value: String(stats.recent_generations), icon: Clock, color: "text-amber-500" },
    { label: "成功率", value: `${stats.success_rate}%`, icon: TrendingUp, color: "text-sky-500" },
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
        <div className="text-destructive mb-3 text-lg font-semibold">控制台加载失败</div>
        <div className="text-text-tertiary text-sm mb-6">{error}</div>
        <button onClick={fetchDashboard} className="px-5 py-2 rounded-xl bg-brand/10 text-brand text-sm font-medium hover:bg-brand/15 transition-colors">
          重试
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
          {(() => { const h = new Date().getHours(); return h < 12 ? "早上好" : h < 18 ? "下午好" : "晚上好"; })()}，创作者 👋
        </motion.h1>
        <motion.p initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="text-text-secondary text-sm">
          今天想创作些什么？
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
            { key: "video", icon: Video, label: "视频" },
            { key: "image", icon: Image, label: "图片" },
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
          <span className="text-[10px] font-semibold text-text-tertiary uppercase tracking-widest mr-1">模型</span>
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
            <span className="text-xs text-text-tertiary">暂无可用模型</span>
          )}
        </div>

        {/* Prompt input */}
        <div className="relative">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleGenerate(); } }}
            placeholder="描述你想创作的内容…（例如：温馨咖啡馆里的电影感产品视频，15 秒）"
            rows={3}
            className="w-full px-4 py-3.5 rounded-2xl bg-cosmic-subtle border border-cosmic-border text-text-primary text-sm placeholder:text-text-disabled resize-none focus:outline-none focus:border-brand/40 focus:bg-cosmic-surface transition-all"
          />
          <div className="flex items-center justify-between mt-3">
            <div className="flex items-center gap-2">
              <Link href="/library" className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-tertiary hover:text-text-secondary hover:bg-cosmic-subtle transition-colors border border-cosmic-border">
                📎 素材库
              </Link>
              <button
                onClick={handleEnhance}
                disabled={!prompt.trim() || enhancing}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-brand/70 hover:text-brand hover:bg-brand/5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {enhancing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                {enhancing ? "优化中…" : "AI 优化提示词"}
              </button>
            </div>
            <button
              onClick={handleGenerate}
              className="flex items-center gap-2 h-10 px-5 rounded-xl bg-brand text-white text-sm font-semibold hover:bg-brand-strong hover:-translate-y-px shadow-button-glow transition-all active:scale-[0.98]"
            >
              <Sparkles className="w-4 h-4" /> 生成
            </button>
          </div>
        </div>
      </Card>

      {/* ═══ Recent + Tools (2-col) ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Creations */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-text-primary">最近创作</h2>
            <Link href="/explore" className="text-xs text-brand hover:text-brand-strong flex items-center gap-1 transition-colors">
              查看全部 <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {hasRecentItems ? (
            <div className="grid grid-cols-2 gap-3">
              {recentItems.slice(0, 4).map((item, i) => {
                const media = resolveMedia(item.media_url);
                const thumb = resolveMedia(item.thumbnail_url);
                const isVideo = item.media_type === "video";
                return (
                <motion.div
                  key={item.task_id || i}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.05 }}
                >
                  <Link href="/library">
                  <Card className="overflow-hidden">
                    <div className="aspect-video bg-cosmic-subtle flex items-center justify-center text-3xl relative group">
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
                        <span>{isVideo ? "🎬" : "🖼️"}</span>
                      )}
                      {isVideo && (
                        <div className="absolute inset-0 bg-text-primary/10 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                          <Play className="w-10 h-10 text-white/80" />
                        </div>
                      )}
                      {isVideo && item.duration != null && (
                        <span className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded-md bg-cosmic-surface/80 backdrop-blur text-[10px] text-text-secondary">
                          {formatDuration(item.duration)}
                        </span>
                      )}
                    </div>
                    <div className="p-3">
                      <div className="text-sm font-medium text-text-primary truncate">{truncatePrompt(item.prompt || "Untitled")}</div>
                      <div className="flex items-center gap-2 mt-1">
                        {item.model && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-brand/8 text-brand truncate max-w-[120px]">{item.model}</span>
                        )}
                        {item.created_at && (
                          <span className="text-[10px] text-text-tertiary">{formatDate(item.created_at)}</span>
                        )}
                      </div>
                    </div>
                  </Card>
                  </Link>
                </motion.div>
                );
              })}
            </div>
          ) : (
            <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-12 text-center">
              <Sparkles className="w-10 h-10 text-text-disabled mx-auto mb-3" />
              <div className="text-text-tertiary text-sm">还没有作品</div>
              <div className="text-text-disabled text-xs mt-1">你生成的资产会显示在这里</div>
            </div>
          )}
        </div>

        {/* Featured Tools */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-text-primary">快捷工具</h2>
            <Link href="/tools" className="text-xs text-brand hover:text-brand-strong flex items-center gap-1 transition-colors">
              全部工具 <ChevronRight className="w-3.5 h-3.5" />
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
                            tool.badge === "新" && "bg-brand/10 text-brand",
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
              不写提示词，<span className="text-brand">只做导演</span>
            </h3>
            <p className="text-text-secondary max-w-md mb-5 text-sm leading-relaxed">
              像导演一样工作。描述你的创意意图，AI Agent 自动规划全流程 — 从解析创意、智能选模型、生成视觉、动态视频到合成，一步到位。
            </p>
            <Link
              href="/agent"
              className="inline-flex items-center gap-2 h-10 px-5 rounded-xl bg-brand text-white text-sm font-semibold hover:bg-brand-strong hover:-translate-y-px shadow-button-glow transition-all"
            >
              试用 Agent <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="flex-shrink-0 grid grid-cols-3 gap-2">
            {["💡 构思", "🧠 规划", "🖼️ 生成", "🎥 转视频", "🎵 配乐", "🎬 合成"].map((s) => (
              <div key={s} className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cosmic-subtle border border-cosmic-border text-xs text-text-secondary">{s}</div>
            ))}
          </div>
        </div>
      </Card>

    </div>
  );
}
