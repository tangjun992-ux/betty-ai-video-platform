"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send, Plus, MessageSquare, ImagePlus, Sparkles, Wand2, Lightbulb,
  Film, Image as ImageIcon, Mic, Layers, Clapperboard, Check, Loader2, Coins, ArrowRight,
  Pencil, RefreshCw, X, Music, Type as TypeIcon, Scissors, Ratio,
  Download, Trash2, StopCircle, CornerDownLeft, Star,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api";
import { useLocale } from "@/i18n/LocaleProvider";
import { PayModal, type PayTarget } from "@/components/PayModal";

const MEDIA_ORIGIN = API_BASE.replace(/\/api\/v1$/, "");
const resolveMedia = (u?: string) => (!u ? "" : u.startsWith("/") ? `${MEDIA_ORIGIN}${u}` : u);

interface StepParams { aspect_ratio?: string; duration?: number; shot?: number; styles?: string[]; }
interface Step {
  id: string; action: string; title: string; model_id: string; model_name: string;
  reason: string; prompt: string; depends_on: string[]; est_credits: number;
  status: string; result?: any; params?: StepParams; skip?: boolean;
}
interface Plan { brief: string; intent: string; summary: string; total_credits: number; steps: Step[]; }
interface Asset { step_id?: string; step: string; model: string; type?: string; media_url?: string; url?: string; thumbnail?: string; shot?: number; final?: boolean; shot_count?: number; }
interface Session { id: string; title: string; lastMessage: string; }
interface ModelOpt { id: string; name: string; }

// 场景化专业工作流 — 严格对标 yapper.so/agent 的 "Try Feature" 能力卡片
interface Scenario {
  icon: any; cat: "视频" | "图片" | "工具"; title: string; desc: string;
  brief: string; duration?: number; vertical?: boolean; color: string;
}
const SCENARIOS: Scenario[] = [
  { icon: Clapperboard, cat: "视频", title: "产品广告", color: "from-amber-500 to-orange-600",
    desc: "从产品/卖点/粗略创意，快速生成高转化投放广告",
    brief: "为新品制作一条高转化产品广告视频，突出核心卖点，适合社媒快速投放测试，电影级画质", duration: 15 },
  { icon: Film, cat: "视频", title: "产品商业片", color: "from-brand to-accent-violet",
    desc: "电影级产品视频与品牌大片，用于发布与品牌campaign",
    brief: "一条电影级产品商业宣传片，精致布光与流畅运镜，高级品牌质感，多镜头叙事", duration: 30 },
  { icon: Mic, cat: "视频", title: "UGC 种草", color: "from-rose-500 to-pink-600",
    desc: "真实、原生的创作者风格短视频，适配社交信息流",
    brief: "一条 UGC 风格种草短视频，真实自然，竖屏手机拍摄感，口语化推荐产品", duration: 15, vertical: true },
  { icon: Layers, cat: "视频", title: "微短剧", color: "from-violet-500 to-purple-600",
    desc: "从一个前提/反转/人物弧，生成可追的竖屏短剧",
    brief: "一部竖屏微短剧短片，强钩子开场加剧情反转，人物情绪张力，电影级叙事运镜", duration: 30, vertical: true },
  { icon: Sparkles, cat: "视频", title: "动漫生成", color: "from-cyan-500 to-blue-600",
    desc: "从故事或情绪，生成电影级动漫场景、角色与运动",
    brief: "一段电影级动漫短片，唯美场景与角色，新海诚式光影与色彩，细腻氛围", duration: 15 },
  { icon: ImageIcon, cat: "图片", title: "产品摄影", color: "from-emerald-500 to-teal-600",
    desc: "影棚级产品图，布光/场景/道具/商业质感一步到位",
    brief: "一组影棚级产品摄影图，柔光箱布光，纯净背景，反射高光，商业级质感，系列四张" },
  { icon: Lightbulb, cat: "图片", title: "AI 写真", color: "from-fuchsia-500 to-pink-600",
    desc: "专业形象照，适合领英、简历、名片、社媒头像",
    brief: "一组专业形象写真，正装，柔和棚拍布光，自然表情，四张统一风格" },
  { icon: Wand2, cat: "视频", title: "数字人口播", color: "from-sky-500 to-indigo-600",
    desc: "图像 + 文案生成开口说话的数字人讲解视频",
    brief: "一个竖屏数字人口播视频，自然口型同步，正面棚拍形象，讲解产品卖点", duration: 15, vertical: true },
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
  const { t } = useLocale();
  const [sessions, setSessions] = useState<Session[]>([{ id: "1", title: "新导演会话", lastMessage: "不写提示词，只做导演" }]);
  const [activeSession, setActiveSession] = useState("1");
  const [brief, setBrief] = useState("");
  const [refImage, setRefImage] = useState(false);
  const [refImageUrl, setRefImageUrl] = useState<string | null>(null);
  const [uploadingRef, setUploadingRef] = useState(false);
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
  const [refineText, setRefineText] = useState("");
  const [refining, setRefining] = useState(false);
  const [changes, setChanges] = useState<string[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const pollStop = useRef(false);
  const [stepTimes, setStepTimes] = useState<Record<string, number>>({});
  const [totalMs, setTotalMs] = useState<number | null>(null);
  const [realAvailable, setRealAvailable] = useState<boolean | null>(null);
  const [modeLabel, setModeLabel] = useState<string>("");
  const [payTarget, setPayTarget] = useState<PayTarget | null>(null);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [userCredits, setUserCredits] = useState<number | null>(null);
  const [brain, setBrain] = useState<"fast" | "quality" | "rules">("fast");
  const [creditGateOpen, setCreditGateOpen] = useState(false);
  const [creditNeeded, setCreditNeeded] = useState(0);

  const maybePromptUpgrade = useCallback(async (force = false) => {
    if (!force && dryRunMode) return;
    try {
      const r = await fetch(`${API_BASE}/models/pricing/user`);
      if (!r.ok) return;
      const d = await r.json();
      setUserCredits(d.credits);
      if (d.credits < 20 || d.role === "guest" || d.role === "free") {
        setShowUpgrade(true);
      }
    } catch {}
  }, [dryRunMode]);

  // ── director mode (real vs preview) ──
  useEffect(() => {
    fetch(`${API_BASE}/director/mode`)
      .then((r) => r.json())
      .then((d) => {
        setRealAvailable(!!d.real_available);
        setModeLabel(d.real_available ? "真实生成可用" : "预览模式（本地/未配置 Key）");
      })
      .catch(() => {
        setRealAvailable(false);
        setModeLabel("预览模式（本地/未配置 Key）");
      });
  }, []);

  // ── models catalog (active only, for per-step model swap) ──
  useEffect(() => {
    fetch(`${API_BASE}/models/?status=active`).then((r) => r.json()).then((d) => {
      const img: ModelOpt[] = [], vid: ModelOpt[] = [];
      const pool = [...(d.active || []), ...(d.models || []).filter((m: any) => m.status === "active")];
      const seen = new Set<string>();
      for (const m of pool) {
        if (seen.has(m.id)) continue;
        seen.add(m.id);
        const opt = { id: m.id, name: m.display_name || m.name || m.id };
        if (m.capabilities?.media_types?.includes("video")) vid.push(opt);
        else img.push(opt);
      }
      setModels({ image: img, video: vid });
    }).catch(() => {});
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      // Auth bearer is injected by ClientLayout installAuthFetch — sessions are user-scoped.
      const res = await fetch(`${API_BASE}/director/sessions`);
      if (res.ok) {
        const d = await res.json();
        if (Array.isArray(d.sessions) && d.sessions.length)
          setSessions(d.sessions.map((s: any) => ({ id: s.session_uid, title: s.title, lastMessage: s.brief || "导演会话" })));
        else setSessions([]);
      }
    } catch {}
  }, []);
  useEffect(() => { loadSessions(); }, [loadSessions]);

  // ── resume a session via ?session=<uid> deep-link (from /sessions) ──
  const loadSession = useCallback(async (uid: string) => {
    try {
      const res = await fetch(`${API_BASE}/director/sessions/${uid}`);
      if (!res.ok) {
        setErr(res.status === 403 ? "无权访问此会话" : `无法加载会话 (HTTP ${res.status})`);
        return;
      }
      const s = await res.json();
      setActiveUid(uid);
      setActiveSession(uid);
      if (typeof window !== "undefined") {
        const url = new URL(window.location.href);
        url.searchParams.set("session", uid);
        window.history.replaceState({}, "", url.toString());
      }
      if (s.brief) setBrief(s.brief);
      const p = s.plan && s.plan.steps ? s.plan as Plan : null;
      const a = Array.isArray(s.assets) ? s.assets as Asset[] : [];
      if (p) { setPlan(p); setAssets(a); setPhase(a.length ? "done" : "planned"); }
      else if (s.brief) { setPhase("idle"); }
    } catch { setErr("加载会话失败"); }
  }, []);
  useEffect(() => {
    const uid = new URLSearchParams(window.location.search).get("session");
    if (uid) loadSession(uid);
  }, [loadSession]);

  const saveSession = async (p: Plan, a: Asset[]) => {
    try {
      let uid = activeUid;
      if (!uid) {
        const res = await fetch(`${API_BASE}/director/sessions`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: (p.brief || "新会话").slice(0, 30), brief: p.brief }),
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

  const makePlan = async (text?: string, opts?: { duration?: number }) => {
    const b = (text ?? brief).trim();
    if (!b) return;
    const dur = opts?.duration ?? duration;
    setBrief(b); if (opts?.duration) setDuration(opts.duration);
    reset(); setPhase("planning");
    try {
      const res = await fetch(`${API_BASE}/director/plan`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief: b, has_ref_image: refImage, duration: dur, ref_image_url: refImageUrl }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Plan = await res.json();
      setPlan(data); setPhase("planned");
    } catch (e: any) { setErr(`无法连接导演引擎 (${e?.message}) — 请确认后端已启动`); setPhase("idle"); }
  };

  const startScenario = (sc: Scenario) => {
    if (sc.duration) setDuration(sc.duration);
    makePlan(sc.brief, { duration: sc.duration });
  };

  // ── composer modes (对标 yapper: Help Prompt / Help Ideate) ──
  const [concepts, setConcepts] = useState<{ title: string; brief: string }[]>([]);
  const [composerBusy, setComposerBusy] = useState<"polish" | "ideate" | null>(null);
  const polishBrief = async () => {
    if (!brief.trim() || composerBusy) return;
    setComposerBusy("polish");
    try {
      const r = await fetch(`${API_BASE}/generate/enhance`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: brief.trim(), media_type: "auto" }),
      });
      const d = await r.json();
      if (d.enhanced) setBrief(d.enhanced);
    } catch {} finally { setComposerBusy(null); }
  };
  const ideate = async () => {
    if (!brief.trim() || composerBusy) return;
    setComposerBusy("ideate");
    try {
      const r = await fetch(`${API_BASE}/director/ideate`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief: brief.trim(), brain }),
      });
      const d = await r.json();
      setConcepts(d.concepts || []);
    } catch {} finally { setComposerBusy(null); }
  };

  // ── edit a step in place ──
  const updateStep = (id: string, patch: Partial<Step>) => {
    setPlan((p) => p ? { ...p, steps: p.steps.map((s) => s.id === id ? { ...s, ...patch } : s) } : p);
  };
  const swapModel = (id: string, opt: ModelOpt) => updateStep(id, { model_id: opt.id, model_name: opt.name });
  const toggleSkip = (id: string, skip: boolean) => updateStep(id, { skip });

  // ── conversational director refine ──
  const refine = async (directive?: string) => {
    const dir = (directive ?? refineText).trim();
    if (!dir || !plan || refining) return;
    setRefining(true);
    try {
      const res = await fetch(`${API_BASE}/director/refine`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan, directive: dir, brain }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      setPlan(d.plan);
      setChanges(d.changes || []);
      setRefineText("");
      setPhase("planned"); setAssets([]);
    } catch (e: any) { setErr(`迭代失败 (${e?.message})`); }
    finally { setRefining(false); }
  };

  // ── remove a shot locally (safe: also detach from compose deps) ──
  const removeShot = (id: string) => {
    setPlan((p) => {
      if (!p) return p;
      const steps = p.steps.filter((s) => s.id !== id).map((s) => ({
        ...s, depends_on: (s.depends_on || []).filter((x) => x !== id),
      }));
      return { ...p, steps };
    });
  };

  const cancelRun = () => { abortRef.current?.abort(); pollStop.current = true; setPhase("planned"); };

  // Apply an async progress snapshot to the live UI (steps / assets / timing).
  const applyProgress = (s: any) => {
    setPlan((p) => p ? { ...p, steps: p.steps.map((st) => {
      const ps = (s.steps || []).find((x: any) => x.id === st.id);
      return ps ? { ...st, status: ps.status } : st;
    }) } : p);
    const times: Record<string, number> = {};
    (s.steps || []).forEach((x: any) => { if (x.elapsed_ms != null) times[x.id] = x.elapsed_ms; });
    setStepTimes(times);
    if (Array.isArray(s.assets)) setAssets(s.assets);
  };

  // Real generation → background Celery task + polling (no long-lived connection).
  const executeAsync = async () => {
    if (!plan) return;
    pollStop.current = false;
    setDryRunMode(false);
    try {
      const res = await fetch(`${API_BASE}/director/run/async`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          brief: plan.brief, has_ref_image: refImage, duration, dry_run: false, plan,
          session_uid: activeUid || undefined,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const { job_id } = await res.json();
      while (!pollStop.current) {
        await new Promise((r) => setTimeout(r, 1800));
        if (pollStop.current) break;
        let s: any;
        try { s = await (await fetch(`${API_BASE}/director/progress/${job_id}`)).json(); }
        catch { continue; }
        applyProgress(s);
        if (s.done || s.status === "failed") {
          if (s.status === "failed") setErr(`执行失败 (${s.error || "未知错误"})`);
          if (typeof s.total_ms === "number") setTotalMs(s.total_ms);
          setPhase("done");
          setPlan((cur) => { if (cur) saveSession(cur, s.assets || []); return cur; });
          void maybePromptUpgrade(true);
          break;
        }
      }
    } catch (e: any) { setErr(`执行失败 (${e?.message})`); setPhase("planned"); }
  };

  const ensureCreditsForReal = async (needed: number): Promise<boolean> => {
    try {
      const r = await fetch(`${API_BASE}/models/pricing/user`);
      if (!r.ok) return true;
      const d = await r.json();
      setUserCredits(d.credits);
      if (d.credits < needed) {
        setCreditNeeded(needed);
        setCreditGateOpen(true);
        setPayTarget({ kind: "plan", id: "personal", cycle: "monthly" });
        return false;
      }
      return true;
    } catch { return true; }
  };

  // ── streaming execution ──
  const execute = async (dryRun = true) => {
    if (!plan) return;
    if (!dryRun) {
      const needed = plan.steps.filter((s) => !s.skip).reduce((n, s) => n + s.est_credits, 0);
      const ok = await ensureCreditsForReal(needed);
      if (!ok) {
        setErr(`积分不足：真实生成约需 ${needed} 积分，请先充值或升级`);
        return;
      }
    }
    setDryRunMode(dryRun);
    setPhase("running"); setErr(null); setAssets([]); setChanges([]); setStepTimes({}); setTotalMs(null);
    // reset live statuses
    setPlan((p) => p ? { ...p, steps: p.steps.map((s) => ({ ...s, status: s.skip ? "skipped" : "pending" })) } : p);
    // Real generation can take many minutes (6 shots × ~150s) → run as a
    // background task with polling so no connection times out. Free preview
    // stays on the snappy SSE stream.
    if (!dryRun) { await executeAsync(); return; }
    const planForRun: Plan = { ...plan, steps: plan.steps };
    const liveAssets: Asset[] = [];
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      const res = await fetch(`${API_BASE}/director/run/stream`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief: plan.brief, has_ref_image: refImage, duration, dry_run: dryRun, plan: planForRun }),
        signal: ctrl.signal,
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
            if (typeof ev.elapsed_ms === "number") setStepTimes((t) => ({ ...t, [ev.id]: ev.elapsed_ms }));
            if (ev.asset) { liveAssets.push(ev.asset); setAssets([...liveAssets]); }
          } else if (ev.type === "step_error") {
            setPlan((p) => p ? { ...p, steps: p.steps.map((s) => s.id === ev.id ? { ...s, status: "failed" } : s) } : p);
          } else if (ev.type === "complete") {
            setPhase("done");
            if (typeof ev.total_ms === "number") setTotalMs(ev.total_ms);
            setPlan((cur) => { if (cur) saveSession(cur, liveAssets); return cur; });
          }
        }
      }
      setPhase("done");
    } catch (e: any) {
      if (e?.name === "AbortError") { setPhase("planned"); setErr("已取消执行"); }
      else { setErr(`执行失败 (${e?.message})`); setPhase("planned"); }
    } finally { abortRef.current = null; }
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

  const newSession = () => { setActiveUid(null); setActiveSession(""); reset(); setBrief(""); setRefImage(false); setRefImageUrl(null); };

  // Upload a reference image → its URL feeds real image-to-video for every shot.
  const uploadRef = async (file: File) => {
    setUploadingRef(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API_BASE}/library/upload`, { method: "POST", body: fd });
      const d = await res.json();
      if (d.url) { setRefImageUrl(d.url); setRefImage(true); }
    } catch {} finally { setUploadingRef(false); }
  };

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
            <button key={s.id} onClick={() => { setActiveSession(s.id); loadSession(s.id); }}
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
            <div className="flex items-center justify-center gap-2 mb-3 flex-wrap">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand/10 text-brand text-xs font-medium">
                <Sparkles className="w-3.5 h-3.5" /> DIRECTOR AGENT
              </div>
              {modeLabel && (
                <div className={cn(
                  "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border",
                  realAvailable
                    ? "bg-emerald-500/10 text-emerald-600 border-emerald-500/25"
                    : "bg-amber-500/10 text-amber-600 border-amber-500/25"
                )}>
                  <span className={cn("w-1.5 h-1.5 rounded-full", realAvailable ? "bg-emerald-500" : "bg-amber-500")} />
                  {modeLabel}
                </div>
              )}
            </div>
            <h1 className="text-2xl font-display font-bold mb-1">{t("agent.title")}</h1>
            <p className="text-sm text-text-secondary">一句话说出你想要的，AI 自动拆分镜、智能选模型、逐镜生成、剪辑成片</p>
          </div>

          {/* Input — 旗舰画布输入 */}
          <div className="bg-cosmic-surface border border-cosmic-border rounded-2xl p-3 shadow-sm focus-within:border-brand/50 focus-within:shadow-[0_0_0_4px_hsl(var(--brand)/0.10)] transition-all mb-3">
            <textarea value={brief} onChange={(e) => setBrief(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); makePlan(); } }}
              placeholder="例如：做一个30秒的咖啡产品宣传片，电影级画质，竖屏抖音…（⌘/Ctrl + ⏎ 开始导演）"
              rows={3} className="w-full bg-transparent border-0 resize-none text-[15px] leading-relaxed placeholder:text-text-tertiary focus:outline-none" />
            <div className="flex items-center justify-between mt-2 pt-2 border-t border-cosmic-border/30">
              <div className="flex items-center gap-2">
                <input ref={fileRef} type="file" accept="image/*" className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) uploadRef(f); e.target.value = ""; }} />
                {refImageUrl ? (
                  <div className="flex items-center gap-1.5 px-1.5 py-1 rounded-lg bg-brand/10 text-brand text-xs">
                    <img src={resolveMedia(refImageUrl)} alt="ref" className="w-5 h-5 rounded object-cover" />
                    参考图
                    <button onClick={() => { setRefImageUrl(null); setRefImage(false); }} className="hover:text-red-500"><X className="w-3 h-3" /></button>
                  </div>
                ) : (
                  <button onClick={() => fileRef.current?.click()} disabled={uploadingRef}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary transition-colors">
                    {uploadingRef ? <Loader2 className="w-4 h-4 animate-spin" /> : <ImagePlus className="w-4 h-4" />}
                    {uploadingRef ? "上传中" : "参考图"}
                  </button>
                )}
                <div className="flex items-center gap-1 text-xs text-text-secondary">
                  <Film className="w-3.5 h-3.5" />
                  <select value={duration} onChange={(e) => setDuration(+e.target.value)}
                    className="bg-transparent focus:outline-none text-text-secondary cursor-pointer">
                    {[5, 10, 15, 30].map((d) => <option key={d} value={d} className="bg-cosmic-surface">{d}s</option>)}
                  </select>
                </div>
                {/* composer modes — 对标 yapper Help Prompt / Help Ideate */}
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] text-text-tertiary mr-1">导演大脑</span>
                  {([
                    { id: "fast", label: "快速" },
                    { id: "quality", label: "深度" },
                    { id: "rules", label: "规则" },
                  ] as const).map((b) => (
                    <button key={b.id} type="button" onClick={() => setBrain(b.id)}
                      className={cn("px-2.5 py-1 rounded-lg text-[11px] font-medium border transition-all",
                        brain === b.id ? "bg-brand/10 text-brand border-brand/30" : "border-cosmic-border text-text-secondary hover:text-text-primary")}>
                      {b.label}
                    </button>
                  ))}
                </div>
                <button onClick={polishBrief} disabled={!brief.trim() || !!composerBusy}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-brand hover:bg-brand/5 transition-colors disabled:opacity-40">
                  {composerBusy === "polish" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />} 润色
                </button>
                <button onClick={ideate} disabled={!brief.trim() || !!composerBusy}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-brand hover:bg-brand/5 transition-colors disabled:opacity-40">
                  {composerBusy === "ideate" ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Lightbulb className="w-3.5 h-3.5" />} 帮我构思
                </button>
              </div>
              <button onClick={() => makePlan()} disabled={!brief.trim() || phase === "planning"}
                className={cn("flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium transition-all",
                  brief.trim() && phase !== "planning" ? "bg-brand text-white hover:bg-brand-strong" : "bg-cosmic-surface text-text-secondary cursor-not-allowed")}>
                {phase === "planning" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                {phase === "planning" ? "规划中" : t("agent.cta")}
              </button>
            </div>
          </div>

          {err && <p className="text-center text-sm text-amber-500 py-3">{err}</p>}

          {/* Ideate concepts — pick a creative direction */}
          {concepts.length > 0 && phase === "idle" && (
            <div className="mt-3">
              <p className="text-[11px] font-semibold text-text-tertiary uppercase tracking-wider mb-2">选一个创意方向 · 点击采用</p>
              <div className="flex flex-wrap gap-2">
                {concepts.map((c) => (
                  <button key={c.title} onClick={() => { setBrief(c.brief); setConcepts([]); }}
                    className="group flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cosmic-surface/50 border border-cosmic-border/50 hover:border-brand/40 transition-all text-left max-w-full">
                    <Lightbulb className="w-3.5 h-3.5 text-brand flex-shrink-0" />
                    <span className="text-xs font-medium text-text-primary">{c.title}</span>
                    <span className="text-[11px] text-text-secondary truncate hidden sm:inline max-w-[220px]">· {c.brief.slice(c.brief.indexOf("，") + 1)}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Empty → scenario feature cards (对标 yapper /agent Try Feature) */}
          {phase === "idle" && !err && (
            <div className="mt-5">
              <p className="text-xs font-semibold text-text-tertiary uppercase tracking-wider mb-3">选择一个专业场景 · 或直接描述你的创意</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {SCENARIOS.map((sc) => (
                  <button key={sc.title} onClick={() => startScenario(sc)}
                    className="group relative flex items-start gap-3 p-4 rounded-2xl bg-cosmic-surface/50 border border-cosmic-border/50 hover:border-brand/40 hover:shadow-card transition-all text-left">
                    <div className={cn("w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center flex-shrink-0", sc.color)}>
                      <sc.icon className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm font-semibold text-text-primary">{sc.title}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-cosmic-subtle text-text-tertiary">{sc.cat}</span>
                      </div>
                      <p className="text-[11px] text-text-secondary leading-snug line-clamp-2">{sc.desc}</p>
                    </div>
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 inline-flex items-center gap-1 text-[11px] font-medium text-brand opacity-0 group-hover:opacity-100 transition-opacity">
                      试用 <ArrowRight className="w-3 h-3" />
                    </span>
                  </button>
                ))}
              </div>
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
                                {stepTimes[s.id] != null && (
                                  <span className="text-[10px] text-emerald-500/80">{(stepTimes[s.id] / 1000).toFixed(1)}s</span>
                                )}
                                {s.est_credits > 0 && <span className="text-[11px] text-amber-500/80">{s.est_credits}积分</span>}
                                {isMediaStep(s.action) && phase !== "running" && (
                                  <button onClick={() => setEditingId(editing ? null : s.id)} title="编辑此步"
                                    className="p-1 rounded hover:bg-cosmic-subtle text-text-tertiary hover:text-brand transition-colors">
                                    <Pencil className="w-3 h-3" />
                                  </button>
                                )}
                                {(s.action === "video" || s.action === "lipsync") && phase !== "running" && (
                                  <button onClick={() => removeShot(s.id)} title="删除此镜"
                                    className="p-1 rounded hover:bg-red-500/10 text-text-tertiary hover:text-red-500 transition-colors">
                                    <Trash2 className="w-3 h-3" />
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

                {/* Add shot */}
                {phase !== "running" && plan.steps.some((s) => s.action === "video") && (
                  <button onClick={() => refine("加一个镜头")} disabled={refining}
                    className="mt-2 flex items-center justify-center gap-1.5 w-full py-2 rounded-xl border border-dashed border-cosmic-border/60 text-xs text-text-secondary hover:text-brand hover:border-brand/40 transition-colors">
                    <Plus className="w-3.5 h-3.5" /> 加一个分镜
                  </button>
                )}

                {/* Conversational refine bar */}
                {(phase === "planned" || phase === "done") && (
                  <div className="mt-4">
                    {changes.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        {changes.map((c, i) => (
                          <span key={i} className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600">
                            <Check className="w-3 h-3" /> {c}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="flex items-center gap-2 rounded-xl border border-cosmic-border/50 bg-cosmic-surface/40 p-1.5 focus-within:border-brand/40 transition-colors">
                      <Wand2 className="w-4 h-4 text-brand ml-1.5 flex-shrink-0" />
                      <input value={refineText} onChange={(e) => setRefineText(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); refine(); } }}
                        placeholder="告诉导演如何调整：把第2镜改暖 / 加个镜头 / 换成 Veo 3.1 / 竖屏…"
                        className="flex-1 bg-transparent text-sm placeholder:text-text-secondary/50 focus:outline-none" />
                      <button onClick={() => refine()} disabled={!refineText.trim() || refining}
                        className={cn("flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex-shrink-0",
                          refineText.trim() && !refining ? "bg-brand text-white hover:bg-brand-strong" : "bg-cosmic-surface text-text-secondary")}>
                        {refining ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CornerDownLeft className="w-3.5 h-3.5" />}
                        迭代
                      </button>
                    </div>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {["更有电影感", "画面更暖", "竖屏", "加一个镜头"].map((q) => (
                        <button key={q} onClick={() => refine(q)} disabled={refining}
                          className="text-[11px] px-2.5 py-1 rounded-full bg-cosmic-subtle text-text-secondary hover:text-brand hover:bg-brand/5 transition-colors">
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Execute */}
                {(phase === "planned" || phase === "running" || phase === "done") && (
                  <div className="flex flex-col sm:flex-row gap-2 mt-4">
                    {running ? (
                      <>
                        <div className="flex items-center justify-center gap-2 flex-1 py-3 rounded-xl text-sm font-semibold bg-cosmic-surface text-text-secondary">
                          <Loader2 className="w-4 h-4 animate-spin" />导演执行中...
                        </div>
                        <button onClick={cancelRun}
                          className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold border border-red-400/50 text-red-500 hover:bg-red-500/10 transition-all">
                          <StopCircle className="w-4 h-4" /> 取消
                        </button>
                      </>
                    ) : (
                      <>
                        {realAvailable !== false ? (
                          <>
                            <button
                              onClick={() => execute(false)}
                              className="flex items-center justify-center gap-2 flex-1 py-3 rounded-xl text-sm font-semibold bg-brand text-white hover:bg-brand-strong shadow-button-glow transition-all"
                            >
                              <Coins className="w-4 h-4" />
                              {t("agent.real")} · {plan.steps.filter((s) => !s.skip).reduce((n, s) => n + s.est_credits, 0)} 积分
                              <ArrowRight className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => execute(true)}
                              className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold border border-cosmic-border text-text-secondary hover:bg-cosmic-subtle transition-all"
                            >
                              <Clapperboard className="w-4 h-4" />{t("agent.preview")}
                            </button>
                          </>
                        ) : (
                          <>
                            <button onClick={() => execute(true)}
                              className="flex items-center justify-center gap-2 flex-1 py-3 rounded-xl text-sm font-semibold bg-brand text-white hover:bg-brand-strong shadow-button-glow transition-all">
                              <Clapperboard className="w-4 h-4" />{t("agent.preview")}（本地 Demo）<ArrowRight className="w-4 h-4" />
                            </button>
                            <div className="flex flex-col gap-1 flex-1 sm:flex-initial">
                              <button
                                disabled
                                className="flex items-center justify-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold border border-cosmic-border text-text-tertiary cursor-not-allowed opacity-60"
                              >
                                <Coins className="w-4 h-4" />{t("agent.real")} · {plan.steps.filter((s) => !s.skip).reduce((n, s) => n + s.est_credits, 0)} 积分
                              </button>
                              <p className="text-[11px] text-amber-600/90 text-center sm:text-left px-1">
                                预览模式：未配置 Key，真实生成已禁用
                              </p>
                            </div>
                          </>
                        )}
                      </>
                    )}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Assets */}
          {assets.length > 0 && (() => {
            const finalAsset = assets.find((a) => a.final);
            const shotAssets = assets.filter((a) => !a.final);
            const fMedia = resolveMedia(finalAsset?.media_url || finalAsset?.url);
            return (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-6">
              {/* Final film — hero deliverable */}
              {finalAsset && fMedia && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className="mb-4 rounded-2xl overflow-hidden border border-brand/30 bg-brand/[0.03]">
                  <div className="flex items-center justify-between px-4 py-2.5 border-b border-brand/15">
                    <div className="flex items-center gap-2">
                      <Star className="w-4 h-4 text-brand" />
                      <span className="text-sm font-semibold">成片 · Final Cut</span>
                      {finalAsset.shot_count ? <span className="text-[11px] text-text-secondary">{finalAsset.shot_count} 个分镜合成</span> : null}
                    </div>
                    <a href={fMedia} download target="_blank" rel="noreferrer"
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand text-white text-xs font-medium hover:bg-brand-strong transition-colors">
                      <Download className="w-3.5 h-3.5" /> 下载成片
                    </a>
                  </div>
                  <video src={fMedia} controls poster={resolveMedia(finalAsset.thumbnail)} className="w-full max-h-[52vh] bg-black object-contain" />
                  {showUpgrade && !dryRunMode && (
                    <div className="px-4 py-3 border-t border-brand/15 bg-gradient-to-r from-brand/[0.06] to-accent-violet/[0.04] flex flex-col sm:flex-row sm:items-center gap-3">
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-text-primary">🎉 成片已就绪 — 继续创作？</p>
                        <p className="text-xs text-text-secondary mt-0.5">
                          当前余额 {userCredits ?? "—"} 积分。升级套餐可解锁更多真实生成与商业授权。
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setPayTarget({ kind: "plan", id: "personal", cycle: "monthly" })}
                          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand text-white text-xs font-semibold hover:bg-brand-strong transition-colors"
                        >
                          <Coins className="w-3.5 h-3.5" /> 升级套餐
                        </button>
                        <button onClick={() => setShowUpgrade(false)} className="px-3 py-2 rounded-xl text-xs text-text-secondary hover:bg-cosmic-subtle transition-colors">
                          稍后
                        </button>
                      </div>
                    </div>
                  )}
                </motion.div>
              )}

              <div className="flex items-center gap-2 mb-3">
                {running ? <Loader2 className="w-4 h-4 text-brand animate-spin" /> : <Check className="w-4 h-4 text-emerald-500" />}
                <h3 className="text-sm font-semibold">
                  {running ? "逐镜产出中" : "分镜素材"} {shotAssets.length} 个
                  {dryRunMode && <span className="text-[11px] text-text-secondary ml-1">(预览模式)</span>}
                  {totalMs != null && !running && <span className="text-[11px] text-text-tertiary ml-2">⚡ 用时 {(totalMs / 1000).toFixed(1)}s</span>}
                </h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {shotAssets.map((a, i) => {
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
            );
          })()}
        </div>
      </div>
      <PayModal
        target={payTarget}
        onClose={() => setPayTarget(null)}
        onPaid={() => { setShowUpgrade(false); void maybePromptUpgrade(); }}
      />
    </div>
  );
}
