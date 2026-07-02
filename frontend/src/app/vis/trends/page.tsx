"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { Loader2, ChevronDown, ArrowLeft, Video, Lightbulb, Timer, Smartphone, ThumbsUp, MessageCircle, Share2, Eye } from "lucide-react";
import { cn } from "@/lib/utils";

const API = "http://localhost:8000/api/v1";

const PLATFORM_ICONS = {
  reddit: "🟠", youtube: "🔴", tiktok: "⚫", x: "🐦",
};

const CONTENT_TYPE_ICONS = {
  news_break: "📰", reaction: "🎭", tutorial: "📖", explainer: "🎬",
  commentary: "💬", entertainment: "🎪", challenge: "🏆",
};

const PLATFORM_COLORS = {
  tiktok: "text-pink-600 bg-pink-50",
  youtube_shorts: "text-red-600 bg-red-50",
  instagram_reels: "text-purple-600 bg-purple-50",
};

function formatCount(n) {
  if (n >= 1000000) return (n / 1000000).toFixed(1) + "M";
  if (n >= 1000) return (n / 1000).toFixed(1) + "K";
  return String(n);
}

const CONTENT_TYPES = [
  { value: "", label: "All Types" },
  { value: "news_break", label: "📰 News Break" },
  { value: "reaction", label: "🎭 Reaction" },
  { value: "tutorial", label: "📖 Tutorial" },
  { value: "explainer", label: "🎬 Explainer" },
  { value: "commentary", label: "💬 Commentary" },
  { value: "entertainment", label: "🎪 Entertainment" },
];

const SOURCE_OPTIONS = [
  { value: "", label: "All Sources" },
  { value: "reddit", label: "🟠 Reddit" },
  { value: "youtube", label: "🔴 YouTube" },
  { value: "tiktok", label: "⚫ TikTok" },
  { value: "x", label: "🐦 X" },
];

export default function VisTrendsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [source, setSource] = useState("");
  const [contentType, setContentType] = useState("");
  const [expanded, setExpanded] = useState(null);

  const fetchTrends = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams({ limit: "30" });
      if (source) params.set("source", source);
      if (contentType) params.set("content_type", contentType);
      const res = await fetch(`${API}/trends/curated?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setItems(data.items || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [source, contentType]);

  useEffect(() => { fetchTrends(); }, [fetchTrends]);

  useEffect(() => {
    const interval = setInterval(fetchTrends, 60000);
    return () => clearInterval(interval);
  }, [fetchTrends]);

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link href="/vis" className="text-sm text-purple-500 hover:text-purple-600 flex items-center gap-1 mb-2">
            <ArrowLeft className="w-3 h-3" /> Back to Dashboard
          </Link>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Video className="w-6 h-6 text-purple-500" />
            Video-Ready Trends
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Curated for short-form video production
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative">
          <select value={source} onChange={(e) => setSource(e.target.value)}
            className="appearance-none pl-3 pr-8 py-2 bg-white border border-slate-200 rounded-lg text-sm cursor-pointer">
            {SOURCE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        </div>
        <div className="relative">
          <select value={contentType} onChange={(e) => setContentType(e.target.value)}
            className="appearance-none pl-3 pr-8 py-2 bg-white border border-slate-200 rounded-lg text-sm cursor-pointer">
            {CONTENT_TYPES.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        </div>
        <div className="h-8 w-px bg-slate-200" />
        <span className="text-xs text-slate-400 flex items-center gap-1">
          <Lightbulb className="w-3 h-3" />
          {items.length} video-ready topics
        </span>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
        </div>
      )}

      {error && (
        <div className="text-center py-20 text-slate-400">
          <p>Failed to load trends: {error}</p>
        </div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="text-center py-20 text-slate-400">
          <Video className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p>No video-ready trends found</p>
        </div>
      )}

      {!loading && !error && items.length > 0 && (
        <div className="space-y-3">
          {items.map(({ topic, curation }) => (
            <motion.div
              key={topic.topic_id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className={cn(
                "bg-white rounded-xl border p-4 cursor-pointer transition-all",
                expanded === topic.topic_id
                  ? "border-purple-300 shadow-sm"
                  : "border-slate-200 hover:border-slate-300"
              )}
              onClick={() => setExpanded(expanded === topic.topic_id ? null : topic.topic_id)}
            >
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-16 h-16 rounded-xl flex flex-col items-center justify-center border bg-purple-50 border-purple-200">
                  <span className="text-xl font-bold text-purple-700">
                    {(curation.video_worthiness * 100).toFixed(0)}
                  </span>
                  <span className="text-[9px] text-purple-400">video-fit</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <span>{PLATFORM_ICONS[topic.source_platform]}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded border font-medium bg-purple-50 text-purple-600 border-purple-200">
                      {CONTENT_TYPE_ICONS[curation.content_type]} {curation.content_type}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-50 text-green-600 border border-green-100 flex items-center gap-1">
                      <Timer className="w-3 h-3" /> {curation.suggested_duration}s
                    </span>
                  </div>
                  <p className="text-sm font-medium text-slate-800 line-clamp-2">{topic.title}</p>
                  <div className="flex items-center gap-3 mt-1.5 text-[10px] text-slate-400">
                    <span>Visual: {(curation.visual_potential * 100).toFixed(0)}%</span>
                    <span>Narrative: {(curation.narrative_score * 100).toFixed(0)}%</span>
                    <span>Feasibility: {(curation.production_feasibility * 100).toFixed(0)}%</span>
                    <span className="text-purple-500 font-medium">
                      Viral: {(topic.viral_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <ChevronDown className={cn(
                  "w-4 h-4 text-slate-300 flex-shrink-0 mt-1 transition-transform",
                  expanded === topic.topic_id && "rotate-180"
                )} />
              </div>

              {expanded === topic.topic_id && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="mt-4 pt-4 border-t border-slate-100 space-y-4"
                >
                  <div className="bg-purple-50 rounded-lg p-4">
                    <p className="text-xs font-medium text-purple-700 flex items-center gap-1 mb-1">
                      <Lightbulb className="w-3 h-3" /> Production Guidance
                    </p>
                    <p className="text-sm text-purple-600">{curation.production_notes}</p>
                  </div>

                  <div className="grid grid-cols-5 gap-3">
                    {[
                      { label: "Video Fit", value: curation.video_worthiness },
                      { label: "Visual", value: curation.visual_potential },
                      { label: "Narrative", value: curation.narrative_score },
                      { label: "Feasibility", value: curation.production_feasibility },
                      { label: "Timeliness", value: curation.timeliness_score },
                    ].map(({ label, value }) => (
                      <div key={label} className="bg-slate-50 rounded-lg p-3 text-center">
                        <p className="text-[10px] text-slate-400">{label}</p>
                        <p className="text-sm font-bold text-slate-700">{(value * 100).toFixed(0)}%</p>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center gap-2">
                    <Smartphone className="w-3 h-3 text-slate-400" />
                    <span className="text-xs text-slate-500">Best for:</span>
                    {curation.target_platforms.map(p => (
                      <span key={p} className={cn("text-xs px-2 py-0.5 rounded font-medium", PLATFORM_COLORS[p] || "")}>
                        {p.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>

                  <div>
                    <p className="text-xs text-slate-500 mb-2">Audience Sentiment</p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden flex">
                        <div className="h-full bg-green-400" style={{ width: `${topic.sentiment.positive * 100}%` }} />
                        <div className="h-full bg-slate-300" style={{ width: `${topic.sentiment.neutral * 100}%` }} />
                        <div className="h-full bg-red-400" style={{ width: `${topic.sentiment.negative * 100}%` }} />
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    <span className="flex items-center gap-1"><ThumbsUp className="w-3 h-3" /> {formatCount(topic.engagement.upvotes)}</span>
                    <span className="flex items-center gap-1"><MessageCircle className="w-3 h-3" /> {formatCount(topic.engagement.comments)}</span>
                    <span className="flex items-center gap-1"><Share2 className="w-3 h-3" /> {formatCount(topic.engagement.shares)}</span>
                    <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> {formatCount(topic.engagement.views)}</span>
                  </div>

                  {topic.hooks && topic.hooks.length > 0 && (
                    <div>
                      <p className="text-xs text-slate-500 mb-2">Viral Hooks</p>
                      <div className="flex flex-wrap gap-1.5">
                        {topic.hooks.map((hook, i) => (
                          <span key={i} className="text-[11px] px-2 py-1 rounded-md bg-purple-50 text-purple-600 border border-purple-100">
                            {hook.pattern} ({(hook.strength * 100).toFixed(0)}%)
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </motion.div>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
