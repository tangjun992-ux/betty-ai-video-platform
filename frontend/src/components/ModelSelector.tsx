"use client";

import { useEffect, useState } from "react";
import { listModels, analyzePrompt, type GenerateRequest, type ModelInfo } from "@/lib/api";

interface ModelSelectorProps {
  selectedModel: string;
  onChange: (model: string) => void;
  prompt?: string;
  mediaType?: "image" | "video" | "auto";
  quality?: "fast" | "balanced" | "high";
  estimatedModel?: string | null;
}

const MODEL_ICONS: Record<string, string> = {
  auto: "⚡",
  "openai/gpt-5.4-image": "🖼️",
  "openai/dall-e-3": "🖼️",
  "bytedance/seedart": "🎨",
  "bytedance/seedance-2-fast": "🎬",
  "kling/video-v3-pro": "🎞️",
  "kling/video-v2": "🎥",
};

export function ModelSelector({
  selectedModel, onChange, prompt, mediaType, quality, estimatedModel,
}: ModelSelectorProps) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [analysis, setAnalysis] = useState<any>(null);

  // Load model list
  useEffect(() => {
    listModels().then((data) => setModels(data.models || [])).catch(() => {});
  }, []);

  // Analyze prompt when it changes
  useEffect(() => {
    if (!prompt || prompt.length < 3) {
      setAnalysis(null);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const result = await analyzePrompt({
          prompt,
          media_type: mediaType,
          quality,
          model: "auto",
        });
        setAnalysis(result);
      } catch {
        setAnalysis(null);
      }
    }, 500);
    return () => clearTimeout(t);
  }, [prompt, mediaType, quality]);

  // If user selected "auto", show router-recommended model
  const displayModel = selectedModel === "auto"
    ? (analysis?.recommended_model?.model_id || estimatedModel || "auto")
    : selectedModel;

  const autoModel = analysis?.recommended_model;

  return (
    <div className="mt-4">
      <label className="text-sm text-dark-400 mb-2 block">选择模型</label>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {/* Auto option — always first */}
        <button
          onClick={() => onChange("auto")}
          className={`text-left p-3 rounded-xl border transition-all ${
            selectedModel === "auto"
              ? "border-accent-cyan/60 bg-accent-cyan/[0.08]"
              : "border-dark-800 bg-dark-900/30 hover:border-dark-700"
          }`}
        >
          <div className="text-sm font-medium text-text-accent-cyan">⚡ 自动选择</div>
          <div className="text-xs text-dark-500 mt-0.5">
            {autoModel
              ? `推荐: ${autoModel.model_id.split("/").pop()} (匹配度 ${autoModel.score}分)`
              : "系统智能匹配最优模型"}
          </div>
          {autoModel?.reasons && autoModel.reasons.length > 0 && (
            <div className="text-xs text-accent-cyan mt-1">
              {autoModel.reasons.join("、")}
            </div>
          )}
        </button>

        {/* Specific model options */}
        {models
          .filter((m) => m.status === "active")
          .map((m) => {
            const icon = MODEL_ICONS[m.id] || "🤖";
            const isRecommended = autoModel?.model_id === m.id;
            return (
              <button
                key={m.id}
                onClick={() => onChange(m.id)}
                className={`text-left p-3 rounded-xl border transition-all relative ${
                  selectedModel === m.id
                    ? "border-accent-cyan/60 bg-accent-cyan/[0.08]"
                    : "border-dark-800 bg-dark-900/30 hover:border-dark-700"
                }`}
              >
                {isRecommended && (
                  <span className="absolute top-1 right-2 text-xs bg-accent-cyan600 text-text-accent-cyan px-1.5 py-0.5 rounded text-[10px]">
                    推荐
                  </span>
                )}
                <div className="text-sm font-medium text-text-accent-cyan">
                  {icon} {m.display_name}
                </div>
                <div className="text-xs text-dark-500 mt-0.5 line-clamp-2">
                  {m.description}
                </div>
              </button>
            );
          })}
      </div>

      {/* Model scores breakdown */}
      {analysis && analysis.all_scores && analysis.all_scores.length > 0 && (
        <details className="mt-3">
          <summary className="text-xs text-dark-500 cursor-pointer hover:text-dark-400">
            📊 各模型评分详情
          </summary>
          <div className="mt-2 space-y-1">
            {analysis.all_scores.map((s: any) => (
              <div key={s.model} className="flex items-center gap-2 text-xs">
                <span className="text-dark-300 w-40 truncate">{s.model}</span>
                <div className="flex-1 bg-dark-700 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full ${
                      s.score >= 70 ? "bg-green-500" : s.score >= 55 ? "bg-yellow-500" : "bg-dark-500"
                    }`}
                    style={{ width: `${Math.min(s.score, 100)}%` }}
                  />
                </div>
                <span className="text-dark-400 w-8 text-right">{s.score}分</span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
