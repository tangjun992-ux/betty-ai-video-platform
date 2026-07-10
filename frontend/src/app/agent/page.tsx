"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send, Plus, MessageSquare, ImagePlus, Sparkles, Wand2, Lightbulb,
  Film, Image as ImageIcon, Mic, Layers, Clapperboard, Check, Loader2, Coins, ArrowRight,
  Pencil, RefreshCw, ChevronDown, X, Music, Type as TypeIcon, Scissors, Ratio,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api";

const MEDIA_ORIGIN = API_BASE.replace(/\/api\/v1$/, "");
const resolveMedia = (u?: string) => (!u ? "" : u.startsWith("/") ? `${MEDIA_ORIGIN}${u}` : u);

interface StepParams { aspect_ratio?: string; duration?: number; shot?: number; styles?: string[]; }
interface Step {
  id: string; action: string; title: string; model_id: string; model_name: string;
  reason: string; prompt: string; depends_on: string[]; est_credits: number;
  status: string; result?: any; params?: StepParams; skip?: boolean;
}
interface Plan { brief: string; intent: string; summary: string; total_credits: number; steps: Step[]; }
interface Asset { step_id?: string; step: string; model: string; type?: string; media_url?: string; url?: string; thumbnail?: string; shot?: number; }
interface Session { id: string; title: string; lastMessage: string; }
interface ModelOpt { id: string; name: string; }

const QUICK = [
  { icon: Clapperboard, label: "咖啡产品宣传片", brief: "做一个30秒的咖啡产品宣传片，电影级画质，温暖光线" },
  { icon: Mic, label: "数字人口播", brief: "生成一个数字人口播讲解新品发布的视频，竖屏" },
  { icon: Layers, label: "国风系列写真", brief: "给我一组国风人像写真，四张，统一风格" },
  { icon: Lightbulb, label: "赛博朋克短片", brief: "科幻赛博朋克城市概念短片，15秒，霓虹质感" },
];

const intentLabel: Record<string, string> = {
  campaign: "营销宣传片", talking: "数字人口播", video_from_text: "文生视频",
  video_from_image: "图生视频", image_series: "系列图", image: "单图创作",
};
const actionIcon = (a: string) =>
  a === "enhance_prompt" ? Wand2 : a === "lipsync" ? Mic : a === "audio" ? Music
  : a === "subtitle" ? TypeIcon : a === "compose" ? Scissors : a.includes("video") ? Film : ImageIcon;

const isMediaStep = (a: string) => ["image", "video", "lipsync"].includes(a);
const isSkippable = (a: string) => ["audio", "subtitle"].includes(a);

export default function AgentPage() {
  const [sessions, setSessions] = useState<Session[]>([{ id: "1", title: "新导演会话", lastMessage: "不写提示词，只做导演" }]);
  const [activeSession, setActiveSession] = useState("1");
  const [brief, setBrief] = useState("");
  const [refImage, setRefImage] = useState(false);
  const [duration, setDuration] = useState(15);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [phase, setPhase] = useState<"idle" | "planning" | "planned" | "running" | "done">("idle");
  const [dryRunMode, setDryRunMode] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [rerunning, setRerunning] = useState<string | null>(null);
  const [models, setModels] = useState<{ image: ModelOpt[]; video: ModelOpt[] }>({ image: [], video: [] });
  const fileRef = useRef<HTMLInputElement>(null);
  const [activeUid, setActiveUid] = useState<string | null>(null);

  // ── models catalog (for per-step model swap) ──
  useEffect(() => {
    fetch(`${API_BASE}/models/`).then((r) => r.json()).then((d) => {
      const img: ModelOpt[] = [], vid: ModelOpt[] = [];
      for (const m of d.models || []) {
        const opt = { id: m.id, name: m.display_name || m.name || m.id };
        if (m.capabilities?.media_types?.includes("video")) vid.push(opt);
        else img.push(opt);
      }
      setModels({ image: img, video: vid });
    }).catch(() => {});
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/director/sessions?user_id=0`);
      if (res.ok) {
        const d = await res.json();
        if (Array.isArray(d.sessions) && d.sessions.length)
          setSessions(d.sessions.map((s: any) => ({ id: s.session_uid, title: s.title, lastMessage: s.brief || "导演会话" })));
      }
    } catch {}
  }, []);
  useEffect(() => { loadSessions(); }, [loadSessions]);

  const saveSession = async (p: Plan, a: Asset[]) => {
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
          body: JSON.stringify({ title: (p.brief || "新会话").slice(0, 30), intent: p.intent, plan: p, assets: a, status: a.length ? "done" : "planned" }),
        });
        loadSessions();
      }
    } catch {}
  };

  const reset = () => { setPlan(null); setAssets([]); setPhase("idle"); setErr(null); setEditingId(null); };

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

  // ── edit a step in place ──
  const updateStep = (id: string, patch: Partial<Step>) => {
    setPlan((p) => p ? { ...p, steps: p.steps.map((s) => s.id === id ? { ...s, ...patch } : s) } : p);
  };
  const swapModel = (id: string, opt: ModelOpt) => updateStep(id, { model_id: opt.id, model_name: opt.name });
  const toggleSkip = (id: string, skip: boolean) => updateStep(id, { skip });

  // ── streaming execution ──
  const execute = async (dryRun = true) => {
    if (!plan) return;
    setDryRunMode(dryRun);
    setPhase("running"); setErr(null); setAssets([]);
    // reset live statuses
    setPlan((p) => p ? { ...p, steps: p.steps.map((s) => ({ ...s, status: s.skip ? "skipped" : "pending" })) } : p);
    const planForRun: Plan = { ...plan, steps: plan.steps };
    const liveAssets: Asset[] = [];
    try {
      const res = await fetch(`${API_BASE}/director/run/stream`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief: plan.brief, has_ref_image: refImage, duration, dry_run: dryRun, plan: planForRun }),
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() || "";
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          let ev: any;
          try { ev = JSON.parse(line.slice(5).trim()); } catch { continue; }
          if (ev.type === "step_start") {
            setPlan((p) => p ? { ...p, steps: p.steps.map((s) => s.id === ev.id ? { ...s, status: "running" } : s) } : p);
          } else if (ev.type === "step_done") {
            setPlan((p) => p ? { ...p, steps: p.steps.map((s) => s.id === ev.id ? { ...s, status: "done", result: ev.step?.result } : s) } : p);
            if (ev.asset) { liveAssets.push(ev.asset); setAssets([...liveAssets]); }
          } else if (ev.type === "step_error") {
            setPlan((p) => p ? { ...p, steps: p.steps.map((s) => s.id === ev.id ? { ...s, status: "failed" } : s) } : p);
          } else if (ev.type === "complete") {
            setPhase("done");
            setPlan((cur) => { if (cur) saveSession(cur, liveAssets); return cur; });
          }
        }
      }
      setPhase("done");
    } catch (e: any) { setErr(`执行失败 (${e?.message})`); setPhase("planned"); }
  };

  // ── per-step regenerate ──
  const regenerate = async (asset: Asset) => {
    if (!plan || !asset.step_id) return;
    const step = plan.steps.find((s) => s.id === asset.step_id);
    if (!step) return;
    setRerunning(asset.step_id);
    try {
      const res = await fetch(`${API_BASE}/director/step/rerun`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ step, dry_run: dryRunMode }),
      });
      const d = await res.json();
      if (d.ok && d.asset) setAssets((prev) => prev.map((a) => a.step_id === asset.step_id ? d.asset : a));
    } catch {} finally { setRerunning(null); }
  };

  const newSession = () => { setActiveUid(null); setActiveSession(""); reset(); setBrief(""); };

  const modelOptsFor = (action: string) => (action.includes("video") || action === "lipsync" ? models.video : models.image);
  const running = phase === "running";

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Sessions */}
      <div className="hidden md:flex w-60 flex-shrink-0 flex-col border-r border-cosmic-border/40">
        <div className="p-3 border-b border-cosmic-border/40">
          <button onClick={newSession} className="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl bg-brand/[0.08] text-brand text-sm font-medium hover:bg-brand/[0.12] transition-all">
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
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand/10 text-brand text-xs font-medium mb-3">
              <Sparkles className="w-3.5 h-3.5" /> DIRECTOR AGENT
            </div>
            <h1 className="text-2xl font-bold mb-1">不写提示词，只做导演</h1>
            <p className="text-sm text-text-secondary">一句话说出你想要的，AI 自动拆分镜、智能选模型、逐镜生成、剪辑成片</p>
          </div>

          {/* Input */}
          <div className="bg-cosmic-surface/40 border border-cosmic-border/40 rounded-2xl p-3 focus-within:border-brand/30 transition-all mb-3">
            <textarea value={brief} onChange={(e) => setBrief(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); makePlan(); } }}
              placeholder="例如：做一个30秒的咖啡产品宣传片，电影级画质，竖屏抖音..."
              rows={2} className="w-full bg-transparent border-0 resize-none text-sm placeholder:text-text-secondary/50 focus:outline-none" />
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-cosmic-border/30">
              <div className="flex items-center gap-2">
                <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={(e) => setRefImage(!!e.target.files?.length)} />
                <button onClick={() => fileRef.current?.click()}
                  className={cn("flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs transition-colors",
                    refImage ? "bg-brand/10 text-brand" : "text-text-secondary hover:text-text-primary")}>
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
                  brief.trim() && phase !== "planning" ? "bg-brand text-white hover:bg-brand-strong" : "bg-cosmic-surface text-text-secondary cursor-not-allowed")}>
                {phase === "planning" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                {phase === "planning" ? "规划中" : "开始导演"}
              </button>
            </div>
          </div>

          {err && <p className="text-center text-sm text-amber-500 py-3">{err}</p>}

          {/* Empty → quick starts */}
          {phase === "idle" && !err && (
            <div className="grid grid-cols-2 gap-2 mt-4">
              {QUICK.map((q) => (
                <button key={q.label} onClick={() => makePlan(q.brief)}
                  className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-cosmic-surface/40 border border-cosmic-border/40 text-sm text-text-secondary hover:text-brand hover:border-brand/30 transition-all text-left">
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
                    <span className="px-2.5 py-1 rounded-lg bg-brand/10 text-brand text-xs font-medium">
                      {intentLabel[plan.intent] || plan.intent}
                    </span>
                    <span className="text-xs text-text-secondary">{plan.steps.length} 步 · 分镜脚本</span>
                  </div>
                  <div className="flex items-center gap-1 text-xs text-amber-500">
                    <Coins className="w-3.5 h-3.5" />{plan.steps.filter((s) => !s.skip).reduce((n, s) => n + s.est_credits, 0)} 积分
                  </div>
                </div>
                <p className="text-sm text-text-secondary mb-4">{plan.summary}</p>

                <div className="space-y-2">
                  {plan.steps.map((s, i) => {
                    const Icon = actionIcon(s.action);
                    const done = s.status === "done";
                    const isRunning = s.status === "running";
                    const failed = s.status === "failed";
                    const skipped = s.skip;
                    const editing = editingId === s.id;
                    const opts = modelOptsFor(s.action);
                    return (
                      <motion.div key={s.id} initial={{ opacity: 0, x: -8 }} animate={{ opacity: skipped ? 0.5 : 1, x: 0 }} transition={{ delay: i * 0.03 }}
                        className={cn("rounded-xl border transition-colors",
                          isRunning ? "border-brand/40 bg-brand/[0.03]" : done ? "border-emerald-500/30 bg-emerald-500/[0.02]" : "border-cosmic-border/40 bg-cosmic-surface/30")}>
                        <div className="flex gap-3 p-3">
                          <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5",
                            done ? "bg-emerald-500/15 text-emerald-500" : isRunning ? "bg-brand/15 text-brand" : failed ? "bg-red-500/15 text-red-500" : "bg-cosmic-border/30 text-text-secondary")}>
                            {done ? <Check className="w-4 h-4" /> : isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : failed ? <X className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-2">
                              <p className={cn("text-sm font-medium truncate", skipped && "line-through")}>{s.title}</p>
                              <div className="flex items-center gap-1.5 flex-shrink-0">
                                {s.params?.aspect_ratio && (
                                  <span className="inline-flex items-center gap-0.5 text-[10px] text-text-tertiary"><Ratio className="w-2.5 h-2.5" />{s.params.aspect_ratio}</span>
                                )}
                                {s.est_credits > 0 && <span className="text-[11px] text-amber-500/80">{s.est_credits}积分</span>}
                                {isMediaStep(s.action) && phase !== "running" && (
                                  <button onClick={() => setEditingId(editing ? null : s.id)} title="编辑此步"
                                    className="p-1 rounded hover:bg-cosmic-subtle text-text-tertiary hover:text-brand transition-colors">
                                    <Pencil className="w-3 h-3" />
                                  </button>
                                )}
                                {isSkippable(s.action) && phase !== "running" && (
                                  <button onClick={() => toggleSkip(s.id, !skipped)} title={skipped ? "启用此步" : "跳过此步"}
                                    className={cn("text-[10px] px-1.5 py-0.5 rounded transition-colors", skipped ? "text-brand hover:bg-brand/10" : "text-text-tertiary hover:bg-cosmic-subtle")}>
                                    {skipped ? "启用" : "跳过"}
                                  </button>
                                )}
                              </div>
                            </div>
                            <div className="flex items-center gap-1.5 mt-1">
                              <span className="text-[11px] px-1.5 py-0.5 rounded bg-brand/10 text-brand whitespace-nowrap">{s.model_name}</span>
                              <p className="text-[11px] text-text-secondary truncate">{s.reason}</p>
                            </div>
                          </div>
                        </div>

                        {/* Inline editor */}
                        <AnimatePresence>
                          {editing && (
                            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }}
                              className="overflow-hidden border-t border-cosmic-border/40">
                              <div className="p-3 space-y-2.5">
                                <div>
                                  <label className="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider">镜头 Prompt</label>
                                  <textarea value={s.prompt} onChange={(e) => updateStep(s.id, { prompt: e.target.value })} rows={3}
                                    className="mt-1 w-full text-xs rounded-lg bg-cosmic-subtle border border-cosmic-border/60 p-2 resize-none focus:outline-none focus:border-brand/40" />
                                </div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <label className="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider">模型</label>
                                  <div className="flex flex-wrap gap-1">
                                    {opts.slice(0, 8).map((o) => (
                                      <button key={o.id} onClick={() => swapModel(s.id, o)}
                                        className={cn("text-[11px] px-2 py-1 rounded-lg border transition-colors",
                                          s.model_id === o.id ? "bg-brand/10 text-brand border-brand/30" : "border-cosmic-border/60 text-text-secondary hover:border-cosmic-border")}>
                                        {o.name}
                                      </button>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </motion.div>
                    );
                  })}
                </div>

                {/* Execute */}
                {(phase === "planned" || phase === "running" || phase === "done") && (
                  <div className="flex flex-col sm:flex-row gap-2 mt-4">
                    <button onClick={() => execute(true)} disabled={running}
                      className={cn("flex items-center justify-center gap-2 flex-1 py-3 rounded-xl text-sm font-semibold transition-all",
                        running ? "bg-cosmic-surface text-text-secondary" : "bg-brand text-white hover:bg-brand-strong shadow-button-glow")}>
                      {running && dryRunMode ? <><Loader2 className="w-4 h-4 animate-spin" />导演执行中...</> : <><Clapperboard className="w-4 h-4" />免费预览成片<ArrowRight className="w-4 h-4" /></>}
                    </button>
                    <button onClick={() => execute(false)} disabled={running}
                      title="调用真实模型逐镜生成，消耗积分"
                      className={cn("flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold border transition-all",
                        running ? "border-cosmic-border/40 text-text-secondary" : "border-amber-400/50 text-amber-500 hover:bg-amber-400/10")}>
                      {running && !dryRunMode ? <Loader2 className="w-4 h-4 animate-spin" /> : <Coins className="w-4 h-4" />}
                      真实生成 · {plan.steps.filter((s) => !s.skip).reduce((n, s) => n + s.est_credits, 0)}积分
                    </button>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Assets */}
          {assets.length > 0 && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6">
              <div className="flex items-center gap-2 mb-3">
                {running ? <Loader2 className="w-4 h-4 text-brand animate-spin" /> : <Check className="w-4 h-4 text-emerald-500" />}
                <h3 className="text-sm font-semibold">
                  {running ? "逐镜产出中" : "产出"} {assets.length} 个资产
                  {dryRunMode && <span className="text-[11px] text-text-secondary ml-1">(预览模式)</span>}
                </h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {assets.map((a, i) => {
                  const media = resolveMedia(a.media_url || a.url);
                  const thumb = resolveMedia(a.thumbnail);
                  const hasMedia = media.startsWith("/api/v1/media") || media.startsWith("http");
                  const isVideo = a.type === "video";
                  const busy = rerunning === a.step_id;
                  return (
                    <motion.div key={a.step_id || i} initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}
                      className="group rounded-xl overflow-hidden bg-cosmic-surface/30 border border-cosmic-border/40 hover:border-brand/40 transition-colors">
                      <div className="relative aspect-video bg-gradient-to-br from-cosmic-surface to-cosmic-border/40 flex items-center justify-center overflow-hidden">
                        {hasMedia && isVideo ? (
                          <video src={media} poster={thumb} muted loop playsInline
                            className="w-full h-full object-cover"
                            onMouseEnter={(e) => e.currentTarget.play().catch(() => {})}
                            onMouseLeave={(e) => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }} />
                        ) : hasMedia ? (
                          <img src={media} alt={a.step} className="w-full h-full object-cover" loading="lazy" />
                        ) : isVideo ? <Film className="w-8 h-8 text-brand/40" /> : <ImageIcon className="w-8 h-8 text-brand/40" />}
                        {isVideo && hasMedia && (
                          <span className="absolute top-2 left-2 inline-flex items-center gap-1 px-1.5 py-0.5 bg-black/60 backdrop-blur-md rounded text-[10px] text-white">
                            <Film className="w-2.5 h-2.5" /> {a.shot ? `分镜 ${a.shot}` : "视频"}
                          </span>
                        )}
                        {a.step_id && !running && (
                          <button onClick={() => regenerate(a)} disabled={busy} title="重生成此镜"
                            className="absolute top-2 right-2 w-7 h-7 rounded-lg bg-black/55 backdrop-blur-md flex items-center justify-center text-white opacity-0 group-hover:opacity-100 hover:bg-black/70 transition-all">
                            <RefreshCw className={cn("w-3.5 h-3.5", busy && "animate-spin")} />
                          </button>
                        )}
                      </div>
                      <div className="p-2.5">
                        <p className="text-xs font-medium truncate">{a.step}</p>
                        <p className="text-[10px] text-text-secondary truncate">{a.model}</p>
                      </div>
                    </motion.div>
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
