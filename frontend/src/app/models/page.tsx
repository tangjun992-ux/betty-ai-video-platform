"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Cpu, Zap, Clock, Search, Film, Image as ImageIcon, Sparkles, Activity } from "lucide-react";

import { API_BASE } from "@/lib/api";
import { cn } from "@/lib/utils";

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
interface HealthRow {
  model_id: string;
  score: number;
  circuit_open: boolean;
  avg_latency_ms: number;
  successes: number;
  failures: number;
}

type Tab = "active" | "lab" | "all" | "image" | "video";

const isVideo = (m: ModelInfo) => m.capabilities.media_types.includes("video");

export default function ModelsPage() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [healthMap, setHealthMap] = useState<Record<string, HealthRow>>({});
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("active");
  const [q, setQ] = useState("");
  const [activeModels, setActiveModels] = useState<ModelInfo[]>([]);
  const [betaModels, setBetaModels] = useState<ModelInfo[]>([]);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [res, hr] = await Promise.all([
          fetch(`${API_BASE}/models/`),
          fetch(`${API_BASE}/models/health`),
        ]);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const all: ModelInfo[] = Array.isArray(data?.models) ? data.models : [];
        const active = Array.isArray(data?.active) ? data.active : all.filter((m) => m.status === "active");
        const beta = Array.isArray(data?.beta) ? data.beta : all.filter((m) => m.status !== "active");
        if (alive) {
          setModels(all);
          setActiveModels(active);
          setBetaModels(beta);
        }
        if (hr.ok) {
          const hd = await hr.json();
          const map: Record<string, HealthRow> = {};
          for (const row of hd.models || []) map[row.model_id] = row;
          if (alive) setHealthMap(map);
        }
      } catch (e: any) {
        if (alive) setErr(e?.message || "加载失败");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  const imgCount = activeModels.filter((m) => !isVideo(m)).length;
  const vidCount = activeModels.filter(isVideo).length;
  const labCount = betaModels.length;

  const source = tab === "lab" ? betaModels : activeModels;

  const filtered = useMemo(() => {
    const kw = q.trim().toLowerCase();
    return source.filter((m) => {
      if (tab === "image" && isVideo(m)) return false;
      if (tab === "video" && !isVideo(m)) return false;
      if (!kw) return true;
      return (
        m.display_name.toLowerCase().includes(kw) ||
        m.provider.toLowerCase().includes(kw) ||
        m.capabilities.styles.some((s) => s.toLowerCase().includes(kw))
      );
    });
  }, [source, tab, q]);

  const tabs: { key: Tab; label: string; count: number; icon: any }[] = [
    { key: "active", label: "已验证", count: activeModels.length, icon: Sparkles },
    { key: "lab", label: "实验室", count: labCount, icon: Activity },
    { key: "image", label: "图片", count: imgCount, icon: ImageIcon },
    { key: "video", label: "视频", count: vidCount, icon: Film },
  ];

  return (
    <div className="max-w-6xl mx-auto px-4 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mb-8 text-center">
        <h1 className="text-3xl font-display font-bold mb-2">模型库</h1>
        <p className="text-sm text-text-secondary">
          已验证可用模型 ·{" "}
          <span className="text-brand font-semibold">{imgCount} 图片</span>
          {" · "}
          <span className="text-brand font-semibold">{vidCount} 视频</span>
          {labCount > 0 && (
            <>
              {" · "}
              <span className="text-text-tertiary">{labCount} 个实验室模型</span>
            </>
          )}
        </p>
      </motion.div>

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
                  active ? "bg-brand/15 text-brand" : "text-text-secondary hover:text-text-primary"
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
            className="w-full h-10 pl-10 pr-3 rounded-xl bg-cosmic-surface/50 border border-cosmic-border/40 text-sm placeholder:text-text-secondary/50 focus:outline-none focus:ring-2 focus:ring-brand/20 focus:border-brand/30"
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
            <ModelCard key={m.id} model={m} i={i} health={healthMap[m.id]} />
          ))}
          {filtered.length === 0 && (
            <p className="col-span-full text-center text-sm text-text-secondary py-16">没有匹配的模型</p>
          )}
        </div>
      )}
    </div>
  );
}

function ModelCard({ model, i, health }: { model: ModelInfo; i: number; health?: HealthRow }) {
  const video = isVideo(model);
  const c = model.capabilities;
  const credits = video ? c.cost_per_5s_video_credits : c.cost_per_image_credits;
  const active = model.status === "active";
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(i * 0.03, 0.4) }}
      className="p-5 rounded-2xl bg-cosmic-surface/20 border border-cosmic-border/40 hover:border-brand/40 hover:bg-cosmic-surface/30 transition-all duration-200 flex flex-col"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {video ? <Film className="w-5 h-5 text-brand" /> : <ImageIcon className="w-5 h-5 text-brand" />}
          <h3 className="font-semibold leading-tight">{model.display_name}</h3>
        </div>
        <div className="flex items-center gap-1.5">
          {health?.circuit_open && <span className="badge-destructive">熔断</span>}
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
              active ? "bg-emerald-500/10 text-emerald-600" : "bg-brand/10 text-brand"
            }`}
          >
            {active ? "可用" : "Beta"}
          </span>
        </div>
      </div>
      <p className="text-[11px] text-text-secondary/70 mb-2">{model.provider}</p>
      <p className="text-sm text-text-secondary mb-4 flex-1">{model.description}</p>

      {health && (health.successes + health.failures > 0 || health.circuit_open) && (
        <div className="flex items-center gap-2 mb-3 text-[11px] text-text-tertiary">
          <Activity className="w-3 h-3 text-brand" />
          <span className={cn("font-mono font-semibold", health.score >= 80 ? "text-success" : health.score >= 50 ? "text-warning" : "text-destructive")}>
            SLA {health.score}
          </span>
          <span>· {health.avg_latency_ms || "—"}ms</span>
          <span>· {health.successes}/{health.successes + health.failures}</span>
        </div>
      )}

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
      <Icon className="w-3.5 h-3.5 text-brand/70 shrink-0" />
      <span className="text-[11px] text-text-secondary truncate">{label}</span>
    </div>
  );
}
