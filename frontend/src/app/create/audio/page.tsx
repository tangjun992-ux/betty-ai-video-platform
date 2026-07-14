"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Sparkles, Loader2, Mic, Download, Play, AlertTriangle } from "lucide-react";
import { generateSpeech, API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { cn } from "@/lib/utils";

const VOICES = [
  { id: "Rachel", name: "Rachel", desc: "自然·多语言女声" },
  { id: "Adam", name: "Adam", desc: "沉稳男声" },
  { id: "Bella", name: "Bella", desc: "亲和女声" },
  { id: "Antoni", name: "Antoni", desc: "磁性男声" },
  { id: "Elli", name: "Elli", desc: "清亮女声" },
  { id: "Josh", name: "Josh", desc: "年轻男声" },
];

const SAMPLES = [
  "欢迎来到 Betty AI 创作平台，让每一个创意一键成片。",
  "本季新品现已上市，用 AI 为你的品牌讲好每一个故事。",
  "Turn your ideas into cinematic videos with a single sentence.",
];

function resolveMedia(url: string): string {
  if (!url) return url;
  if (url.startsWith("http")) return url;
  const origin = API_BASE.replace(/\/api\/v1$/, "");
  return `${origin}${url}`;
}

export default function AudioPage() {
  const router = useRouter();
  const toast = useToast();
  const [text, setText] = useState("");
  const [voice, setVoice] = useState("Rachel");
  const [loading, setLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string>("");
  const [model, setModel] = useState<string>("");
  const [isDemo, setIsDemo] = useState<boolean | null>(null);
  const [demoLabel, setDemoLabel] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/system/capabilities`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        const demo = !!d.demo_mode || !d.real_generation_available;
        setIsDemo(demo);
        setDemoLabel(d.label || "预览模式：未配置 TTS Key");
      })
      .catch(() => setIsDemo(true));
  }, []);

  const handleGenerate = async () => {
    if (!text.trim()) {
      toast.error("请输入文本", "先写一句想要配音的文字");
      return;
    }
    setLoading(true);
    setAudioUrl("");
    try {
      const res = await generateSpeech(text.trim(), voice);
      setAudioUrl(resolveMedia(res.url));
      setModel(res.model);
      setIsDemo(!!res.demo || res.model?.startsWith("demo"));
      toast.success("配音完成", res.demo ? "演示音频已生成" : "音频已生成，可试听或下载");
    } catch (e: any) {
      toast.error("配音失败", e.message || "请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  const subtitle = isDemo
    ? "演示模式 · 本地合成音（非真实 ElevenLabs）"
    : "文字转语音 · 已验证 TTS 模型";

  return (
    <div className="max-w-3xl mx-auto px-4 py-10">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-3 mb-2">
          <span className="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-brand-50 border border-cosmic-border text-2xl">🎙️</span>
          <div>
            <h1 className="text-2xl font-bold gradient-text-static">AI 配音</h1>
            <p className="text-text-secondary text-sm">{subtitle}</p>
          </div>
        </div>
        {isDemo && (
          <div className="mt-3 flex items-start gap-2 rounded-xl border border-amber-400/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-800 dark:text-amber-200">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span>{demoLabel || "配置 API Key 后可启用真实多语言 TTS"}</span>
          </div>
        )}
      </motion.div>

      <div className="mt-8 space-y-5">
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-text-primary">配音文本</span>
            <span className="text-xs text-text-tertiary">{text.length} / 5000</span>
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value.slice(0, 5000))}
            placeholder="输入要转成语音的文字，支持中文 / 英文 / 多语言..."
            rows={6}
            className="w-full px-4 py-3 rounded-2xl bg-cosmic-subtle border border-cosmic-border text-sm text-text-primary placeholder:text-text-tertiary/50 focus:outline-none focus:ring-2 focus:ring-brand/25 focus:border-brand/30 resize-none transition-all"
          />
          <div className="flex flex-wrap gap-2 mt-2">
            {SAMPLES.map((s) => (
              <button
                key={s}
                onClick={() => setText(s)}
                className="text-[11px] px-2.5 py-1 rounded-full bg-cosmic-surface border border-cosmic-border text-text-secondary hover:text-text-primary hover:border-brand/30 transition-colors"
              >
                {s.length > 22 ? s.slice(0, 22) + "…" : s}
              </button>
            ))}
          </div>
        </div>

        <div>
          <span className="text-sm font-medium text-text-primary mb-2 block">
            选择音色 {isDemo ? <span className="text-text-tertiary font-normal">（演示模式仅本地合成）</span> : null}
          </span>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {VOICES.map((v) => (
              <button
                key={v.id}
                onClick={() => setVoice(v.id)}
                className={cn(
                  "flex items-center gap-2.5 p-2.5 rounded-xl text-left transition-all duration-200 border",
                  voice === v.id
                    ? "bg-brand/[0.08] text-brand border-brand/25"
                    : "bg-cosmic-subtle border-cosmic-border text-text-secondary hover:text-text-primary hover:border-cosmic-border-hover"
                )}
              >
                <span className="w-8 h-8 rounded-lg bg-brand-50 flex items-center justify-center text-xs font-semibold flex-shrink-0">
                  {v.name[0]}
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-medium truncate">{v.name}</p>
                  <p className="text-[10px] text-text-tertiary truncate">{v.desc}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        <button onClick={handleGenerate} disabled={loading || !text.trim()} className="btn-primary w-full">
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              正在合成语音...
            </>
          ) : (
            <>
              <Mic className="w-5 h-5" />
              {isDemo ? "生成演示配音" : "生成配音"}
            </>
          )}
        </button>

        {audioUrl && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-4 rounded-2xl surface-raised space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-text-primary flex items-center gap-2">
                <Play className="w-4 h-4 text-brand" /> 生成结果
              </span>
              <span className={cn(
                "text-[11px] px-2 py-0.5 rounded-full border",
                isDemo || model?.startsWith("demo")
                  ? "bg-amber-500/15 border-amber-400/40 text-amber-700 dark:text-amber-200"
                  : "bg-cosmic-surface border-cosmic-border text-text-tertiary"
              )}>
                {isDemo || model?.startsWith("demo") ? "演示 demo" : model}
              </span>
            </div>
            <audio src={audioUrl} controls className="w-full" />
            <div className="flex gap-2">
              <a href={audioUrl} download className="btn-secondary flex-1 justify-center text-sm">
                <Download className="w-4 h-4" /> 下载
              </a>
              <button onClick={() => router.push("/create/lipsync")} className="btn-secondary flex-1 justify-center text-sm">
                <Sparkles className="w-4 h-4" /> 用于唇形同步
              </button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
