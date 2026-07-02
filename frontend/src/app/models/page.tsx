"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Cpu, Zap, Clock, Search, Film, Image as ImageIcon, Sparkles } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface Capability {
  media_types: string[];
  max_resolution: string;
  max_duration_s: number;
  avg_latency_s: number;
  styles: string[];
  cost_per_image_credits: number;
  cost_per_5s_video_credits: number;
}
interface ModelInfo {
  id: string;
  provider: string;
  display_name: string;
  description: string;
  capabilities: Capability;
  cost_tier: string;
  status: string;
}

type Tab = "all" | "image" | "video";

const isVideo = (m: ModelInfo) => m.capabilities.media_types.includes("video");

export default function ModelsPage() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("all");
  const [q, setQ] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/models/`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (alive) setModels(Array.isArray(data?.models) ? data.models : []);
      } catch (e: any) {
        if (alive) setErr(e?.message || "加载失败");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  const imgCount = models.filter((m) => !isVideo(m)).length;
  const vidCount = models.filter(isVideo).length;

  const filtered = useMemo(() => {
    const kw = q.trim().toLowerCase();
    return models.filter((m) => {
      if (tab === "image" && isVideo(m)) return false;
      if (tab === "video" && !isVideo(m)) return false;
      if (!kw) return true;
      return (
        m.display_name.toLowerCase().includes(kw) ||
        m.provider.toLowerCase().includes(kw) ||
        m.capabilities.styles.some((s) => s.toLowerCase().includes(kw))
      );
    });
  }, [models, tab, q]);

  const tabs: { key: Tab; label: string; count: number; icon: any }[] = [
    { key: "all", label: "全部", count: models.length, icon: Sparkles },
    { key: "image", label: "图片", count: imgCount, icon: ImageIcon },
    { key: "video", label: "视频", count: vidCount, icon: Film },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-8 text-center">
        <h1 className="text-3xl font-bold mb-2">模型库</h1>
        <p className="text-sm text-text-secondary">
          在一个平台使用所有最新 AI 模型 —— 探索{" "}
          <span className="text-accent-cyan font-semibold">{imgCount || 15}+ 图片模型</span> 与{" "}
          <span className="text-accent-cyan font-semibold">{vidCount || 22}+ 视频模型</span>
        </p>
      </motion.div>

      {/* Controls: tabs + search */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-2 p-1 rounded-xl bg-cosmic-surface/40 border border-cosmic-border/40">
          {tabs.map((t) => {
            const Icon = t.icon;
            const active = tab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  active ? "bg-accent-cyan/15 text-accent-cyan" : "text-text-secondary hover:text-text-primary"
                }`}
              >
                <Icon className="w-4 h-4" />
                {t.label}
                <span className="text-xs opacity-60">{t.count}</span>
              </button>
            );
          })}
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary/50" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="搜索模型、厂商或风格..."
            className="w-full h-10 pl-10 pr-3 rounded-xl bg-cosmic-surface/50 border border-cosmic-border/40 text-sm placeholder:text-text-secondary/50 focus:outline-none focus:ring-2 focus:ring-accent-cyan/20 focus:border-accent-cyan/30"
          />
        </div>
      </div>

      {loading && <p className="text-center text-sm text-text-secondary py-20">加载模型中...</p>}
      {err && !loading && (
        <p className="text-center text-sm text-amber-400 py-20">无法连接后端 ({err}) —— 请确认 API 已启动</p>
      )}
      {!loading && !err && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((m, i) => (
            <ModelCard key={m.id} model={m} i={i} />
          ))}
          {filtered.length === 0 && (
            <p className="col-span-full text-center text-sm text-text-secondary py-16">没有匹配的模型</p>
          )}
        </div>
      )}
    </div>
  );
}

function ModelCard({ model, i }: { model: ModelInfo; i: number }) {
  const video = isVideo(model);
  const c = model.capabilities;
  const credits = video ? c.cost_per_5s_video_credits : c.cost_per_image_credits;
  const active = model.status === "active";
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(i * 0.03, 0.4) }}
      className="p-5 rounded-2xl bg-cosmic-surface/20 border border-cosmic-border/40 hover:border-accent-cyan/40 hover:bg-cosmic-surface/30 transition-all duration-200 flex flex-col"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {video ? <Film className="w-5 h-5 text-accent-cyan" /> : <ImageIcon className="w-5 h-5 text-accent-cyan" />}
          <h3 className="font-semibold leading-tight">{model.display_name}</h3>
        </div>
        <span
          className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
            active ? "bg-emerald-500/10 text-emerald-400" : "bg-accent-cyan/10 text-accent-cyan"
          }`}
        >
          {active ? "可用" : "Beta"}
        </span>
      </div>
      <p className="text-[11px] text-text-secondary/70 mb-2">{model.provider}</p>
      <p className="text-sm text-text-secondary mb-4 flex-1">{model.description}</p>

      <div className="flex flex-wrap gap-1.5 mb-4">
        {c.styles.slice(0, 4).map((s) => (
          <span key={s} className="px-2 py-0.5 rounded-md bg-cosmic-border/30 text-[10px] text-text-secondary">{s}</span>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-2 pt-3 border-t border-cosmic-border/30">
        <Stat icon={Cpu} label={c.max_resolution} />
        <Stat icon={Clock} label={video ? `${c.avg_latency_s}s` : `~${c.avg_latency_s}s`} />
        <Stat icon={Zap} label={`${credits} 积分${video ? "/5s" : ""}`} />
      </div>
    </motion.div>
  );
}

function Stat({ icon: Icon, label }: { icon: any; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <Icon className="w-3.5 h-3.5 text-accent-cyan/70 shrink-0" />
      <span className="text-[11px] text-text-secondary truncate">{label}</span>
    </div>
  );
}
