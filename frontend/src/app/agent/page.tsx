"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send, Plus, MessageSquare, ImagePlus, Sparkles, Wand2, Lightbulb, Globe,
  Film, Image as ImageIcon, Mic, Layers, Clapperboard, Check, Loader2, Coins, ArrowRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

import { API_BASE } from "@/lib/api";

interface Step {
  id: string; action: string; title: string; model_id: string; model_name: string;
  reason: string; prompt: string; depends_on: string[]; est_credits: number;
  status: string; result?: any;
}
interface Plan { brief: string; intent: string; summary: string; total_credits: number; steps: Step[]; }
interface Asset { step: string; model: string; type?: string; media_url?: string; url?: string; thumbnail?: string; dry_run?: boolean; }
interface RunResult { plan: Plan; assets: Asset[]; asset_count: number; dry_run: boolean; }

interface Session { id: string; title: string; lastMessage: string; }

const QUICK = [
  { icon: Clapperboard, label: "咖啡产品宣传片", brief: "做一个30秒的咖啡产品宣传片，电影级画质，温暖光线" },
  { icon: Mic, label: "数字人口播", brief: "生成一个数字人口播讲解新品发布的视频" },
  { icon: Layers, label: "国风系列写真", brief: "给我一组国风人像写真，四张，统一风格" },
  { icon: Lightbulb, label: "赛博朋克海报", brief: "画一张赛博朋克城市夜景海报，霓虹质感" },
];

const intentLabel: Record<string, string> = {
  campaign: "营销宣传片", talking: "数字人口播", video_from_text: "文生视频",
  video_from_image: "图生视频", image_series: "系列图", image: "单图创作",
};
const actionIcon = (a: string) =>
  a === "enhance_prompt" ? Wand2 : a === "lipsync" ? Mic : a.includes("video") ? Film : ImageIcon;

/* ═══════════════════════════════════════════════════════
   Hero Demo Reel — cycles through generated "output" previews
   ═══════════════════════════════════════════════════════ */

const DEMO_SCENES = [
  { icon: Clapperboard, title: "产品宣传片", desc: "30s 电影级咖啡广告", color: "from-amber-500/20 to-orange-500/10", accent: "amber" },
  { icon: Mic, title: "数字人口播", desc: "AI 虚拟主播带货", color: "from-cyan-500/20 to-blue-500/10", accent: "cyan" },
  { icon: Layers, title: "系列写真", desc: "4 张国风统一风格", color: "from-brand/20 to-accent-violet/10", accent: "purple" },
  { icon: Film, title: "短剧生成", desc: "赛博朋克概念短片", color: "from-rose-500/20 to-pink-500/10", accent: "rose" },
];

function DemoReel() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => setActive((a) => (a + 1) % DEMO_SCENES.length), 3000);
    return () => clearInterval(timer);
  }, []);

  const current = DEMO_SCENES[active];
  const CurrentIcon = current.icon;

  return (
    <div className="relative mb-8 rounded-2xl overflow-hidden border border-cosmic-border bg-cosmic-surface shadow-elevation-sm">
      <div className="grid md:grid-cols-2">
        {/* Left: cycle demo */}
        <AnimatePresence mode="wait">
          <motion.div
            key={active}
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.97 }}
            transition={{ duration: 0.4 }}
            className={cn("flex flex-col items-center justify-center p-10 text-center min-h-[280px]", current.color)}
          >
            <CurrentIcon className="w-16 h-16 text-text-primary/20 mb-4" />
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <h3 className="text-xl font-semibold text-text-primary mb-1">{current.title}</h3>
              <p className="text-text-secondary text-sm mb-4">{current.desc}</p>
              <div className="flex items-center justify-center gap-1.5 text-xs text-text-tertiary">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                一键生成 · 全自动工作流
              </div>
            </motion.div>
          </motion.div>
        </AnimatePresence>

        {/* Right: step flow preview */}
        <div className="p-8 flex flex-col justify-center border-l border-cosmic-border">
          <p className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-4">Agent 执行流程</p>
          <div className="space-y-3">
            {["💡 解析意图 → 规划脚本", "🎨 智能选模型 → 生成视觉", "🎥 转视频 → 配乐 → 合成"].map((step, i) => (
              <motion.div
                key={step}
                initial={{ opacity: 0, x: -12 }}
                animate={{
                  opacity: active === i || (i === 0) ? 1 : 0.35,
                  x: 0,
                  borderColor: active === i ? "hsl(252 78% 63% / 0.25)" : "transparent",
                }}
                transition={{ duration: 0.4, delay: i * 0.1 }}
                className="flex items-center gap-3 px-4 py-3 rounded-xl border bg-cosmic-subtle/50 text-sm text-text-secondary"
              >
                <span className="text-lg">{step.slice(0, 2)}</span>
                <span>{step.slice(3)}</span>
                {i < 2 && (
                  <motion.div
                    className="text-text-disabled text-[10px]"
                    animate={{ opacity: active > i ? 1 : 0.3 }}
                  >→</motion.div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Dot indicators */}
      <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
        {DEMO_SCENES.map((_, i) => (
          <button key={i} onClick={() => setActive(i)}
            className={cn("w-2 h-2 rounded-full transition-all", active === i ? "bg-brand w-5" : "bg-cosmic-border hover:bg-text-disabled")} />
        ))}
      </div>
    </div>
  );
}

export default function AgentPage() {
  const [sessions, setSessions] = useState<Session[]>([{ id: "1", title: "新导演会话", lastMessage: "不写提示词，只做导演" }]);
  const [activeSession, setActiveSession] = useState("1");
  const [brief, setBrief] = useState("");
  const [refImage, setRefImage] = useState(false);
  const [duration, setDuration] = useState(15);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [run, setRun] = useState<RunResult | null>(null);
  const [phase, setPhase] = useState<"idle" | "planning" | "planned" | "running" | "done">("idle");
  const [err, setErr] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [activeUid, setActiveUid] = useState<string | null>(null);

  const loadSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/director/sessions?user_id=0`);
      if (res.ok) {
        const d = await res.json();
        if (Array.isArray(d.sessions) && d.sessions.length)
          setSessions(d.sessions.map((s: any) => ({ id: s.session_uid, title: s.title, lastMessage: s.brief || "导演会话" })));
      }
    } catch {}
  };
  useEffect(() => { loadSessions(); }, []);

  const saveSession = async (p: Plan, r: RunResult | null) => {
    try {
      let uid = activeUid;
      if (!uid) {
        const res = await fetch(`${API_BASE}/director/sessions`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: (p.brief || "新会话").slice(0, 30), brief: p.brief, user_id: 0 }),
        });
        if (res.ok) { uid = (await res.json()).session_uid; setActiveUid(uid); }
      }
      if (uid) {
        await fetch(`${API_BASE}/director/sessions/${uid}`, {
          method: "PATCH", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: (p.brief || "新会话").slice(0, 30), intent: p.intent, plan: p, assets: r?.assets || [], status: r ? "done" : "planned" }),
        });
        loadSessions();
      }
    } catch {}
  };

  const reset = () => { setPlan(null); setRun(null); setPhase("idle"); setErr(null); };

  const makePlan = async (text?: string) => {
    const b = (text ?? brief).trim();
    if (!b) return;
    setBrief(b); reset(); setPhase("planning");
    try {
      const res = await fetch(`${API_BASE}/director/plan`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief: b, has_ref_image: refImage, duration }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Plan = await res.json();
      setPlan(data); setPhase("planned");
    } catch (e: any) { setErr(`无法连接导演引擎 (${e?.message}) — 请确认后端已启动`); setPhase("idle"); }
  };

  const execute = async () => {
    if (!plan) return;
    setPhase("running"); setErr(null);
    try {
      const res = await fetch(`${API_BASE}/director/run`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief: plan.brief, has_ref_image: refImage, duration }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: RunResult = await res.json();
      setRun(data); setPlan(data.plan); setPhase("done");
      saveSession(data.plan, data);
    } catch (e: any) { setErr(`执行失败 (${e?.message})`); setPhase("planned"); }
  };

  const newSession = () => {
    setActiveUid(null); setActiveSession(""); reset(); setBrief("");
  };

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Sessions */}
      <div className="hidden md:flex w-60 flex-shrink-0 flex-col border-r border-cosmic-border/40">
        <div className="p-3 border-b border-cosmic-border/40">
          <button onClick={newSession} className="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl bg-accent-cyan/[0.08] text-accent-cyan text-sm font-medium hover:bg-accent-cyan/[0.12] transition-all">
            <Plus className="w-4 h-4" /><span>新会话</span>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.map((s) => (
            <button key={s.id} onClick={() => setActiveSession(s.id)}
              className={cn("flex items-start gap-2.5 w-full p-2.5 rounded-lg text-left transition-all",
                activeSession === s.id ? "bg-cosmic-surface" : "hover:bg-cosmic-subtle")}>
              <MessageSquare className="w-4 h-4 text-text-secondary flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate">{s.title}</p>
                <p className="text-[10px] text-text-secondary truncate">{s.lastMessage}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Director canvas */}
      <div className="flex-1 flex flex-col overflow-y-auto">
        <div className="max-w-3xl w-full mx-auto px-4 py-8 flex-1">
          {/* Header */}
          <div className="text-center mb-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-accent-cyan/10 text-accent-cyan text-xs font-medium mb-3">
              <Sparkles className="w-3.5 h-3.5" /> DIRECTOR AGENT
            </div>
            <h1 className="text-2xl font-bold mb-1">不写提示词，只做导演</h1>
            <p className="text-sm text-text-secondary">一句话说出你想要的，AI 自动规划多步、智能选模型、产出成品</p>
          </div>

          {/* Input */}
          <div className="bg-cosmic-surface/40 border border-cosmic-border/40 rounded-2xl p-3 focus-within:border-accent-cyan/30 transition-all mb-3">
            <textarea value={brief} onChange={(e) => setBrief(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); makePlan(); } }}
              placeholder="例如：做一个30秒的咖啡产品宣传片，电影级画质..."
              rows={2} className="w-full bg-transparent border-0 resize-none text-sm placeholder:text-text-secondary/50 focus:outline-none" />
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-cosmic-border/30">
              <div className="flex items-center gap-2">
                <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => setRefImage(!!e.target.files?.length)} />
                <button onClick={() => fileRef.current?.click()}
                  className={cn("flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-colors",
                    refImage ? "bg-accent-cyan/10 text-accent-cyan" : "text-text-secondary hover:text-text-primary")}>
                  <ImagePlus className="w-4 h-4" />{refImage ? "已加参考图" : "参考图"}
                </button>
                <div className="flex items-center gap-1 text-xs text-text-secondary">
                  <Film className="w-3.5 h-3.5" />
                  <select value={duration} onChange={(e) => setDuration(+e.target.value)}
                    className="bg-transparent focus:outline-none text-text-secondary cursor-pointer">
                    {[5, 10, 15, 30].map((d) => <option key={d} value={d} className="bg-cosmic-surface">{d}s</option>)}
                  </select>
                </div>
              </div>
              <button onClick={() => makePlan()} disabled={!brief.trim() || phase === "planning"}
                className={cn("flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-all",
                  brief.trim() && phase !== "planning" ? "bg-accent-cyan text-white hover:bg-accent-cyan/80" : "bg-cosmic-surface text-text-secondary cursor-not-allowed")}>
                {phase === "planning" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                {phase === "planning" ? "规划中" : "开始导演"}
              </button>
            </div>
          </div>

          {err && <p className="text-center text-sm text-amber-400 py-3">{err}</p>}

          {/* Agent 工作流示意 */}
          {phase === "idle" && !err && <DemoReel />}

          {/* Empty → quick starts */}
          {phase === "idle" && !err && (
            <div className="grid grid-cols-2 gap-2 mt-4">
              {QUICK.map((q) => (
                <button key={q.label} onClick={() => makePlan(q.brief)}
                  className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-cosmic-surface/40 border border-cosmic-border/40 text-sm text-text-secondary hover:text-accent-cyan hover:border-accent-cyan/30 transition-all text-left">
                  <q.icon className="w-4 h-4 flex-shrink-0" /><span className="truncate">{q.label}</span>
                </button>
              ))}
            </div>
          )}

          {/* Plan view */}
          <AnimatePresence>
            {plan && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mt-5">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 rounded-lg bg-accent-cyan/10 text-accent-cyan text-xs font-medium">
                      {intentLabel[plan.intent] || plan.intent}
                    </span>
                    <span className="text-xs text-text-secondary">{plan.steps.length} 步</span>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-amber-400">
                    <Coins className="w-3.5 h-3.5" />{plan.total_credits} 积分
                  </div>
                </div>
                <p className="text-sm text-text-secondary mb-4">{plan.summary}</p>

                <div className="space-y-2">
                  {plan.steps.map((s, i) => {
                    const Icon = actionIcon(s.action);
                    const done = s.status === "done";
                    const running = s.status === "running";
                    return (
                      <motion.div key={s.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
                        className="flex gap-3 p-3 rounded-xl bg-cosmic-surface/30 border border-cosmic-border/40">
                        <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0",
                          done ? "bg-emerald-500/15 text-emerald-400" : running ? "bg-accent-cyan/15 text-accent-cyan" : "bg-cosmic-border/30 text-text-secondary")}>
                          {done ? <Check className="w-4 h-4" /> : running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Icon className="w-4 h-4" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-medium">{s.title}</p>
                            {s.est_credits > 0 && <span className="text-[11px] text-amber-400/80 flex-shrink-0">{s.est_credits}积分</span>}
                          </div>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <span className="text-[11px] px-1.5 py-0.5 rounded bg-accent-cyan/10 text-accent-cyan">{s.model_name}</span>
                            <p className="text-[11px] text-text-secondary truncate">{s.reason}</p>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>

                {/* Execute */}
                {(phase === "planned" || phase === "running") && (
                  <button onClick={execute} disabled={phase === "running"}
                    className={cn("flex items-center justify-center gap-2 w-full mt-4 py-3 rounded-xl text-sm font-semibold transition-all",
                      phase === "running" ? "bg-cosmic-surface text-text-secondary" : "bg-gradient-to-r from-accent-cyan to-accent-cyan/80 text-white hover:opacity-90")}>
                    {phase === "running" ? <><Loader2 className="w-4 h-4 animate-spin" />导演执行中...</> : <><Clapperboard className="w-4 h-4" />一键执行 · 产出成品<ArrowRight className="w-4 h-4" /></>}
                  </button>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Assets */}
          {run && run.assets.length > 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6">
              <div className="flex items-center gap-2 mb-3">
                <Check className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold">产出 {run.asset_count} 个资产{run.dry_run && <span className="text-[11px] text-text-secondary ml-1">(预览模式)</span>}</h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {run.assets.map((a, i) => {
                  const media = a.media_url || a.url || "";
                  const hasMedia = media.startsWith("/api/v1/media") || media.startsWith("http");
                  return (
                    <div key={i} className="group rounded-xl overflow-hidden bg-cosmic-surface/30 border border-cosmic-border/40 hover:border-brand/40 transition-colors">
                      <div className="relative aspect-video bg-gradient-to-br from-cosmic-surface to-cosmic-border/40 flex items-center justify-center overflow-hidden">
                        {hasMedia && a.type === "video" ? (
                          <video src={media} poster={a.thumbnail} muted loop playsInline
                            className="w-full h-full object-cover"
                            onMouseEnter={(e) => e.currentTarget.play().catch(() => {})}
                            onMouseLeave={(e) => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }}
                          />
                        ) : hasMedia ? (
                          <img src={media} alt={a.step} className="w-full h-full object-cover" loading="lazy" />
                        ) : a.type === "video" ? (
                          <Film className="w-8 h-8 text-accent-cyan/40" />
                        ) : (
                          <ImageIcon className="w-8 h-8 text-accent-cyan/40" />
                        )}
                        {a.type === "video" && hasMedia && (
                          <span className="absolute top-2 left-2 inline-flex items-center gap-1 px-1.5 py-0.5 bg-black/60 backdrop-blur-md rounded text-[10px] text-white">
                            <Film className="w-2.5 h-2.5" /> 视频
                          </span>
                        )}
                      </div>
                      <div className="p-2.5">
                        <p className="text-xs font-medium truncate">{a.step}</p>
                        <p className="text-[10px] text-text-secondary truncate">{a.model}</p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
