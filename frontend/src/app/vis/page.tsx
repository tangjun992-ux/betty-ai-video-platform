"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { TrendingUp, Zap, Flame, Activity, BarChart3, Globe, ArrowRight, Loader2, RefreshCw, ThumbsUp, MessageCircle, Share2, Clock, AlertTriangle, Hash } from "lucide-react";
import { cn } from "@/lib/utils";

const API = "http://localhost:8000/api/v1";

const PLATFORM_ICONS: Record<string, string> = {
  reddit: "🟠", youtube: "🔴", tiktok: "⚫", x: "🐦",
};

const TIER_COLORS: Record<string, string> = {
  tier_1_breakout: "text-red-500 bg-red-500/10 border-red-500/20",
  tier_2_trending: "text-orange-500 bg-orange-500/10 border-orange-500/20",
  tier_3_emerging: "text-yellow-500 bg-yellow-500/10 border-yellow-500/20",
  noise: "text-slate-400 bg-slate-500/5 border-slate-500/10",
};

const TIER_LABELS: Record<string, string> = {
  tier_1_breakout: "Breakout",
  tier_2_trending: "Trending",
  tier_3_emerging: "Emerging",
  noise: "Noise",
};

function formatCount(n: number) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
  if (n >= 1000) return (n / 1000).toFixed(1) + "K";
  return String(n);
}

function formatVelocity(v: number) {
  if (v === null || v === undefined) return "\u2014";
  return (v >= 0 ? "+" : "") + v.toFixed(0) + "/h";
}

export default function VisDashboardPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API}/dashboard/viral`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setStats(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchStats(); }, [fetchStats]);

  useEffect(() => {
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <AlertTriangle className="w-12 h-12 text-red-400" />
        <p className="text-slate-600">Failed to load VIS dashboard</p>
        <p className="text-xs text-slate-400">{error}</p>
        <button onClick={fetchStats} className="px-4 py-2 bg-purple-500 text-white rounded-lg text-sm hover:bg-purple-600">
          Retry
        </button>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-purple-500" />
            Viral Intelligence
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time trending discovery across Reddit, YouTube, TikTok & X
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/vis/trends" className="flex items-center gap-1.5 px-4 py-2 bg-purple-500 text-white rounded-lg text-sm hover:bg-purple-600 transition-colors">
            <Hash className="w-4 h-4" /> Browse Trends <ArrowRight className="w-4 h-4" />
          </Link>
          <button onClick={fetchStats} className="p-2 text-slate-400 hover:text-slate-600 transition-colors" title="Refresh">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<Flame className="w-5 h-5" />} label="Breakouts" value={stats.breakout_topics} color="text-red-500" bgColor="bg-red-500/5" />
        <StatCard icon={<TrendingUp className="w-5 h-5" />} label="Trending" value={stats.trending_topics} color="text-orange-500" bgColor="bg-orange-500/5" />
        <StatCard icon={<Activity className="w-5 h-5" />} label="Signals 24h" value={stats.signals_last_24h} color="text-purple-500" bgColor="bg-purple-500/5" />
        <StatCard icon={<BarChart3 className="w-5 h-5" />} label="Total Topics" value={stats.total_topics_tracked} color="text-blue-500" bgColor="bg-blue-500/5" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <Globe className="w-4 h-4 text-purple-500" /> By Platform
          </h3>
          <div className="space-y-3">
            {Object.entries(stats.platform_breakdown || {}).map(([platform, count]: [string, any]) => (
              <div key={platform} className="flex items-center justify-between">
                <span className="text-sm text-slate-600 capitalize flex items-center gap-2">
                  <span>{PLATFORM_ICONS[platform] || "📊"}</span> {platform}
                </span>
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-purple-500 rounded-full"
                      style={{ width: `${Math.min((count / Math.max(...(Object.values(stats.platform_breakdown) as number[]))) * 100, 100)}%` }} />
                  </div>
                  <span className="text-sm font-mono text-slate-500">{count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-purple-500" /> By Viral Tier
          </h3>
          <div className="space-y-3">
            {Object.entries(stats.viral_score_distribution || {}).map(([tier, count]: [string, any]) => (
              <div key={tier} className="flex items-center justify-between">
                <span className={cn("text-sm px-2 py-0.5 rounded border", TIER_COLORS[tier] || "")}>
                  {TIER_LABELS[tier] || tier}
                </span>
                <span className="text-sm font-mono text-slate-600">{count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {stats.recent_breakouts && stats.recent_breakouts.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <Flame className="w-4 h-4 text-red-500" /> Recent Breakouts
          </h3>
          <div className="grid grid-cols-1 gap-3">
            {stats.recent_breakouts.map((topic: any) => (
              <div key={topic.topic_id} className="bg-white rounded-xl border border-red-200/50 p-4 hover:border-red-300/50 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm">{PLATFORM_ICONS[topic.source_platform] || "📊"}</span>
                      <span className="text-xs text-slate-400 capitalize">{topic.source_platform}</span>
                      <span className={cn("text-xs px-1.5 py-0.5 rounded border", TIER_COLORS[topic.viral_tier])}>
                        {TIER_LABELS[topic.viral_tier]}
                      </span>
                      <span className="text-xs font-mono text-purple-600 font-medium">
                        {(topic.viral_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-sm font-medium text-slate-800 line-clamp-2">{topic.title}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                      <span className="flex items-center gap-1"><ThumbsUp className="w-3 h-3" /> {formatCount(topic.engagement.upvotes)}</span>
                      <span className="flex items-center gap-1"><MessageCircle className="w-3 h-3" /> {formatCount(topic.engagement.comments)}</span>
                      <span className="flex items-center gap-1"><Share2 className="w-3 h-3" /> {formatCount(topic.engagement.shares)}</span>
                      <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {formatVelocity(topic.growth.velocity_1h)}</span>
                    </div>
                    {topic.hooks && topic.hooks.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {topic.hooks.slice(0, 3).map((hook: any, i: number) => (
                          <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-purple-50 text-purple-600 border border-purple-100">
                            {hook.pattern}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex-shrink-0 flex flex-col items-end gap-1">
                    <div className={cn("w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold",
                      topic.viral_tier === "tier_1_breakout" ? "bg-red-100 text-red-600" : "bg-orange-100 text-orange-600"
                    )}>
                      {(topic.viral_score * 100).toFixed(0)}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, color, bgColor }: {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
  bgColor: string;
}) {
  return (
    <div className={cn("rounded-xl border border-slate-200 p-5", bgColor)}>
      <div className="flex items-center gap-2 mb-2">
        <span className={color}>{icon}</span>
        <span className="text-xs text-slate-500">{label}</span>
      </div>
      <p className={cn("text-2xl font-bold", color)}>{formatCount(value)}</p>
    </div>
  );
}
