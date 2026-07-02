"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Trash2, Sparkles, Layers, X, Play } from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Types ──────────────────────────────────────────────

interface BatchItem {
  id: string;
  prompt: string;
}

interface BatchPromptInputProps {
  onSubmit: (prompts: string[]) => void;
  loading?: boolean;
  className?: string;
  maxItems?: number;
}

// ─── Component ──────────────────────────────────────────

export function BatchPromptInput({
  onSubmit,
  loading = false,
  className,
  maxItems = 8,
}: BatchPromptInputProps) {
  const [items, setItems] = useState<BatchItem[]>([
    { id: crypto.randomUUID(), prompt: "" },
  ]);
  const [batchMode, setBatchMode] = useState(false);

  const addItem = () => {
    if (items.length >= maxItems) return;
    setItems([...items, { id: crypto.randomUUID(), prompt: "" }]);
  };

  const removeItem = (id: string) => {
    if (items.length <= 1) return;
    setItems(items.filter((i) => i.id !== id));
  };

  const updateItem = (id: string, prompt: string) => {
    setItems(items.map((i) => (i.id === id ? { ...i, prompt } : i)));
  };

  const handleSubmit = () => {
    const prompts = items.map((i) => i.prompt.trim()).filter(Boolean);
    if (prompts.length === 0) return;
    onSubmit(prompts);
  };

  const filledCount = items.filter((i) => i.prompt.trim()).length;

  return (
    <div className={cn("space-y-3", className)}>
      {/* Toggle */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setBatchMode(!batchMode)}
          className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all",
            batchMode
              ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
              : "bg-white/[0.03] text-text-secondary border border-white/[0.06] hover:text-text-accent-cyan"
          )}
        >
          <Layers className="w-3.5 h-3.5" />
          {batchMode ? "批量模式" : "批量生成"}
        </button>
        {batchMode && (
          <span className="text-xs text-text-secondary">
            {filledCount}/{items.length} 已填写 · 最多 {maxItems} 个
          </span>
        )}
      </div>

      {/* Batch inputs */}
      <AnimatePresence>
        {batchMode && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden space-y-2"
          >
            {items.map((item, index) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="flex items-start gap-2"
              >
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-white/[0.05] border border-white/[0.08] flex items-center justify-center text-xs text-text-secondary mt-2">
                  {index + 1}
                </span>
                <div className="flex-1 relative">
                  <textarea
                    value={item.prompt}
                    onChange={(e) => updateItem(item.id, e.target.value)}
                    placeholder={`提示词 ${index + 1}...`}
                    rows={2}
                    className="w-full px-3 py-2 rounded-xl bg-white/[0.03] border border-white/[0.08] text-sm text-text-accent-cyan placeholder:text-text-accent-cyan/20 focus:outline-none focus:ring-2 focus:ring-blue-400/20 focus:border-blue-400/30 resize-none transition-all"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey && item.prompt.trim()) {
                        e.preventDefault();
                        addItem();
                      }
                    }}
                  />
                  {items.length > 1 && (
                    <button
                      onClick={() => removeItem(item.id)}
                      className="absolute top-2 right-2 p-1 rounded-md text-text-secondary hover:text-red-400 hover:bg-red-500/10 transition-all"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </motion.div>
            ))}

            {/* Add button */}
            <div className="flex gap-4">
              <button
                onClick={addItem}
                disabled={items.length >= maxItems}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-accent-cyan bg-white/[0.03] border border-dashed border-white/[0.1] hover:border-white/[0.2] transition-all disabled:opacity-30"
              >
                <Plus className="w-3.5 h-3.5" />
                添加提示词
              </button>

              {/* Submit button */}
              <button
                onClick={handleSubmit}
                disabled={loading || filledCount === 0}
                className={cn(
                  "flex items-center gap-2 px-5 py-1.5 rounded-lg text-xs font-medium transition-all",
                  "bg-white text-black hover:bg-white/90 active:scale-95",
                  "disabled:opacity-30 disabled:cursor-not-allowed"
                )}
              >
                {loading ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                    生成中...
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    批量生成 ({filledCount})
                  </>
                )}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
