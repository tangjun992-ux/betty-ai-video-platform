"use client";

import { useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { Upload, Video, Image, Play, ArrowRight, RefreshCw, CheckCircle, Lightbulb } from "lucide-react";
import { useCreationStore } from "@/lib/stores";
import { API_BASE, type TaskResult } from "@/lib/api";
import { CapabilityNotice } from "@/components/CapabilityNotice";
import { cn } from "@/lib/utils";

const MOTION_EXAMPLES = [
  {
    id: "dance",
    title: "街舞律动",
    desc: "将街舞动作迁移到人物全身",
    style: "realistic",
    prompt: "街舞律动，全身动作，节奏感强，自然光影",
    steps: ["上传正面全身照", "上传 5–10s 街舞参考", "选择写实风格生成"],
  },
  {
    id: "product",
    title: "产品展示",
    desc: "模特转身展示服装细节",
    style: "realistic",
    prompt: "电商模特缓慢转身展示，专业棚拍灯光",
    steps: ["上传模特正面图", "上传转身参考视频", "保持写实风格"],
  },
  {
    id: "anime",
    title: "二次元舞蹈",
    desc: "动漫角色动作迁移",
    style: "anime",
    prompt: "二次元角色舞蹈，流畅肢体，赛璐璐风格",
    steps: ["上传角色立绘", "上传舞蹈 MV 片段", "选择动漫风格"],
  },
];

const WIZARD_STEPS = [
  { n: 1, title: "目标人物", hint: "正面清晰、四肢完整" },
  { n: 2, title: "参考动作", hint: "5–15 秒，动作连贯" },
  { n: 3, title: "风格 & 生成", hint: "选择风格后一键提交" },
];

const STYLES = [
  { id: "realistic", label: "写实", desc: "自然真实的动作迁移" },
  { id: "anime", label: "动漫", desc: "二次元风格动作" },
  { id: "cartoon", label: "卡通", desc: "3D卡通角色动画" },
  { id: "artistic", label: "艺术", desc: "艺术风格动作迁移" },
];

export default function MotionControlPage() {
  const router = useRouter();
  const { addResult } = useCreationStore();

  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoPreview, setVideoPreview] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [selectedStyle, setSelectedStyle] = useState("realistic");
  const [submitting, setSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [tier, setTier] = useState<"demo" | "studio">("demo");
  const [demoMode, setDemoMode] = useState(false);

  const imageInputRef = useRef<HTMLInputElement>(null);
  const videoInputRef = useRef<HTMLInputElement>(null);

  const handleImageSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
    setError(null);
  }, []);

  const handleVideoSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 100 * 1024 * 1024) {
      setError("视频文件不能超过 100MB");
      return;
    }
    setVideoFile(file);
    setVideoPreview(URL.createObjectURL(file));
    setError(null);
  }, []);

  const uploadFile = async (file: File): Promise<string> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
    if (!res.ok) throw new Error("上传失败");
    const data = await res.json();
    return data.url || data.file_url;
  };

  const handleSubmit = async () => {
    if (!imageFile || !videoFile) {
      setError("请上传目标图片和参考动作视频");
      return;
    }
    setSubmitting(true);
    setError(null);
    setProgress(0);
    setResult(null);

    try {
      setPhase("uploading");
      setProgress(10);
      const imageUrl = await uploadFile(imageFile);
      setProgress(30);
      const videoUrl = await uploadFile(videoFile);
      setProgress(40);

      setPhase("submitting");
      const res = await fetch(`${API_BASE}/motion`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_url: imageUrl,
          video_url: videoUrl,
          prompt: prompt || undefined,
          style: selectedStyle,
          tier,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "提交任务失败");
      }
      const data = await res.json();
      setPhase("processing");
      setProgress(50);

      // Poll for progress
      const poll = setInterval(async () => {
        try {
          const taskRes = await fetch(`${API_BASE}/tasks/${data.task_id}`);
          if (!taskRes.ok) return;
          const taskData = await taskRes.json();

          if (taskData.status === "completed") {
            clearInterval(poll);
            setProgress(100);
            setPhase("completed");
            setResult(taskData);
            addResult({
              id: data.task_id,
              type: "video",
              url: taskData.result_url,
              prompt: prompt || "运动控制生成",
              model: "motion-control",
              taskId: data.task_id,
            } as any);
            setSubmitting(false);
          } else if (taskData.status === "failed") {
            clearInterval(poll);
            setError(taskData.error_message || "运动控制生成失败");
            setSubmitting(false);
          } else {
            const p = taskData.parameters?.progress;
            if (p) {
              setProgress(Math.max(50, Math.min(95, p)));
            } else {
              setProgress((prev) => Math.min(95, prev + 1));
            }
          }
        } catch {
          // polling error, ignore
        }
      }, 2000);
    } catch (err: any) {
      setError(err.message || "未知错误");
      setSubmitting(false);
    }
  };

  // Motion transfer has no demo fallback — it fails without provider keys, so
  // block submission in demo mode instead of letting the request error out.
  const canSubmit = imageFile && videoFile && !submitting && !demoMode;
  const wizardStep = !imageFile ? 1 : !videoFile ? 2 : 3;

  const applyExample = (ex: typeof MOTION_EXAMPLES[0]) => {
    setSelectedStyle(ex.style);
    setPrompt(ex.prompt);
    setError(null);
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold mb-1 text-text-accent-cyan">运动控制</h1>
        <p className="text-text-secondary text-sm mb-4">
          上传人物图片和参考动作视频，AI 将动作精准迁移到目标人物
        </p>
        <CapabilityNotice feature="motion" className="mb-6" onDemoChange={setDemoMode} />
      </motion.div>

      {/* Wizard progress */}
      <div className="grid grid-cols-3 gap-2 mb-6">
        {WIZARD_STEPS.map((s) => (
          <div
            key={s.n}
            className={cn(
              "rounded-xl border px-3 py-2.5 transition-all",
              wizardStep === s.n
                ? "border-brand/40 bg-brand/[0.06]"
                : wizardStep > s.n
                  ? "border-emerald-500/30 bg-emerald-500/[0.04]"
                  : "border-cosmic-border bg-cosmic-subtle"
            )}
          >
            <div className="text-[11px] font-semibold text-text-primary">
              {wizardStep > s.n ? "✓ " : `${s.n}. `}{s.title}
            </div>
            <div className="text-[10px] text-text-secondary mt-0.5">{s.hint}</div>
          </div>
        ))}
      </div>

      {/* Examples */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-3">
          <Lightbulb className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-semibold text-text-primary">示例场景</h2>
          <span className="text-xs text-text-tertiary">点击快速填充风格与提示词</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {MOTION_EXAMPLES.map((ex) => (
            <button
              key={ex.id}
              type="button"
              onClick={() => applyExample(ex)}
              className="text-left rounded-xl border border-cosmic-border bg-cosmic-subtle p-3 hover:border-brand/40 hover:bg-brand/[0.04] transition-all"
            >
              <div className="text-sm font-medium text-text-primary">{ex.title}</div>
              <div className="text-xs text-text-secondary mt-1">{ex.desc}</div>
              <ol className="mt-2 space-y-0.5">
                {ex.steps.map((step, i) => (
                  <li key={i} className="text-[10px] text-text-tertiary">{i + 1}. {step}</li>
                ))}
              </ol>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Uploads */}
        <div className="space-y-4">
          <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}>
            <label className="block">
              <span className="text-sm font-medium text-text-accent-cyan mb-2 block">1. 目标人物图片</span>
              <div
                onClick={() => imageInputRef.current?.click()}
                className="relative aspect-square rounded-2xl border-2 border-dashed border-cosmic-border hover:border-accent-cyan/40 bg-cosmic-subtle flex items-center justify-center cursor-pointer overflow-hidden transition-all group"
              >
                {imagePreview ? (
                  <>
                    <img src={imagePreview} alt="target" className="w-full h-full object-cover" />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <span className="text-sm text-text-accent-cyan">点击更换</span>
                    </div>
                  </>
                ) : (
                  <div className="text-center p-8">
                    <Image className="w-10 h-10 text-text-secondary mx-auto mb-3 group-hover:text-blue-400 transition-colors" />
                    <p className="text-sm text-text-secondary">点击上传目标人物</p>
                    <p className="text-xs text-text-secondary/50 mt-1">JPG / PNG，正面照最佳</p>
                  </div>
                )}
                <input ref={imageInputRef} type="file" accept="image/*" onChange={handleImageSelect} className="hidden" />
              </div>
            </label>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
            <label className="block">
              <span className="text-sm font-medium text-text-accent-cyan mb-2 block">2. 参考动作视频</span>
              <div
                onClick={() => videoInputRef.current?.click()}
                className="relative aspect-video rounded-2xl border-2 border-dashed border-cosmic-border hover:border-accent-violet/40 bg-cosmic-subtle flex items-center justify-center cursor-pointer overflow-hidden transition-all group"
              >
                {videoPreview ? (
                  <>
                    <video src={videoPreview} className="w-full h-full object-cover" controls muted />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <span className="text-sm text-text-accent-cyan">点击更换</span>
                    </div>
                  </>
                ) : (
                  <div className="text-center p-8">
                    <Video className="w-10 h-10 text-text-secondary mx-auto mb-3 group-hover:text-purple-400 transition-colors" />
                    <p className="text-sm text-text-secondary">点击上传参考动作视频</p>
                    <p className="text-xs text-text-secondary/50 mt-1">MP4，≤100MB，单人动作为佳</p>
                  </div>
                )}
                <input ref={videoInputRef} type="file" accept="video/*" onChange={handleVideoSelect} className="hidden" />
              </div>
            </label>
          </motion.div>
        </div>

        {/* Right: Controls */}
        <div className="space-y-4">
          <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}>
          <div>
            <span className="text-sm font-medium text-text-accent-cyan mb-2 block">产品档位</span>
            <div className="grid grid-cols-2 gap-2 mb-4">
              {([
                { id: "demo" as const, label: "Demo", desc: "6 积分 · 标准动作迁移" },
                { id: "studio" as const, label: "Studio", desc: "14 积分 · 高保真 · Personal+" },
              ]).map((t) => (
                <button key={t.id} type="button" onClick={() => setTier(t.id)}
                  className={cn("p-3 rounded-xl border text-left transition-all",
                    tier === t.id ? "border-brand/40 bg-brand/[0.06]" : "border-cosmic-border bg-cosmic-subtle")}>
                  <div className="text-sm font-semibold">{t.label}</div>
                  <div className="text-[10px] text-text-secondary mt-0.5">{t.desc}</div>
                </button>
              ))}
            </div>
            <span className="text-sm font-medium text-text-accent-cyan mb-2 block">3. 选择风格</span>
            <div className="grid grid-cols-2 gap-2">
              {STYLES.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedStyle(s.id)}
                  className={`flex flex-col p-3 rounded-xl text-left transition-all ${
                    selectedStyle === s.id
                      ? "bg-blue-500/10 border border-blue-500/30"
                      : "bg-cosmic-subtle border border-cosmic-border hover:border-cosmic-border-hover"
                  }`}
                >
                  <span className={`text-sm font-medium ${selectedStyle === s.id ? "text-blue-400" : "text-text-accent-cyan"}`}>
                    {s.label}
                  </span>
                  <span className="text-xs text-text-secondary mt-0.5">{s.desc}</span>
                </button>
              ))}
            </div>
          </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
            <span className="text-sm font-medium text-text-accent-cyan mb-2 block">4. 描述（可选）</span>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="描述你想要的最终效果..."
              rows={3}
              className="w-full rounded-xl bg-cosmic-subtle border border-cosmic-border px-4 py-3 text-sm text-text-accent-cyan placeholder:text-text-secondary/50 focus:outline-none focus:border-accent-cyan/40 resize-none"
            />
          </motion.div>

          {submitting && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="rounded-2xl bg-cosmic-subtle border border-cosmic-border p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-text-accent-cyan">
                  {phase === "uploading" ? "上传中..." : phase === "submitting" ? "提交中..." : "AI 处理中..."}
                </span>
                <span className="text-xs text-text-secondary">{Math.round(progress)}%</span>
              </div>
              <div className="h-2 rounded-full bg-cosmic-subtle overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500"
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                />
              </div>
              {result && (
                <div className="mt-3 flex items-center gap-2 text-green-400 text-sm">
                  <CheckCircle className="w-4 h-4" />
                  <span>生成完成！</span>
                </div>
              )}
            </motion.div>
          )}

          {error && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          <motion.button
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="w-full py-3.5 rounded-2xl bg-accent-cyan text-white font-semibold hover:brightness-110 shadow-button-glow transition-all active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {submitting ? (
              <>
                <RefreshCw className="w-5 h-5 animate-spin" />
                生成中...
              </>
            ) : demoMode ? (
              <>
                <Play className="w-5 h-5" />
                需配置模型 Key 后可用
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                开始运动迁移
              </>
            )}
          </motion.button>

          {result?.result_url && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-2xl overflow-hidden border border-cosmic-border"
            >
              <video src={result.result_url} controls className="w-full" poster={imagePreview || undefined} />
              <div className="p-3 flex items-center justify-between bg-cosmic-subtle">
                <span className="text-xs text-text-secondary">运动控制结果</span>
                <button onClick={() => router.push("/explore")} className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
                  前往探索 <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </motion.div>
          )}
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="mt-8 p-4 rounded-2xl bg-cosmic-subtle border border-cosmic-border"
      >
        <h3 className="text-sm font-semibold text-text-accent-cyan mb-2">使用技巧</h3>
        <ul className="space-y-1.5 text-xs text-text-secondary">
          <li>上传清晰的正面人物照，效果最佳</li>
          <li>参考视频建议选单人全身动作，10秒以内为佳</li>
          <li>写实风格适合真人照片，动漫风格适合插画人物</li>
          <li>生成时间约 60-90 秒</li>
        </ul>
      </motion.div>
    </div>
  );
}
