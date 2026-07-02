"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Search, Filter, Download, Trash2, ImageIcon, Video, Grid3X3, List, MoreHorizontal } from "lucide-react";
import { cn } from "@/lib/utils";

const MOCK_ITEMS = Array.from({ length: 12 }, (_, i) => ({
  id: String(i),
  type: (i % 3 === 0 ? "video" : "image") as "image" | "video",
  url: i % 3 === 0
    ? "https://www.w3schools.com/html/mov_bbb.mp4"
    : `https://images.unsplash.com/photo-${1618005182384 + i}?w=400`,
  prompt: ["赛博朋克城市夜景", "日式庭院樱花", "产品摄影白底", "商务头像", "自然风光延时", "抽象艺术"][i % 6],
  date: new Date(Date.now() - i * 86400000),
  model: i % 2 === 0 ? "GPT Image 2" : "Seedance 2.0",
}));

export default function LibraryPage() {
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "image" | "video">("all");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const filtered = MOCK_ITEMS.filter((item) => {
    if (filter !== "all" && item.type !== filter) return false;
    if (search && !item.prompt.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const toggleSelect = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">内容库</h1>
          <p className="text-sm text-text-secondary">管理所有已生成的内容</p>
        </div>
        {selected.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-text-secondary">{selected.size} 项已选</span>
            <button className="px-3 py-1.5 rounded-lg bg-destructive/10 text-destructive text-sm hover:bg-destructive/20 transition-colors flex items-center gap-1.5">
              <Trash2 className="w-3.5 h-3.5" />
              删除
            </button>
            <button className="px-3 py-1.5 rounded-lg bg-accent-cyan/[0.08] text-accent-cyan text-sm hover:bg-accent-cyan/[0.12] transition-colors flex items-center gap-1.5">
              <Download className="w-3.5 h-3.5" />
              下载
            </button>
          </div>
        )}
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索 prompt..."
            className="w-full h-10 pl-10 pr-3 rounded-xl bg-cosmic-surface/50 border border-cosmic-border/40 text-sm placeholder:text-text-secondary/50 focus:outline-none focus:ring-2 focus:ring-accent-cyan/10 focus:border-accent-cyan/30"
          />
        </div>
        <div className="flex items-center gap-1.5 bg-cosmic-surface/30 rounded-lg p-1">
          {(["all", "image", "video"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                filter === f ? "bg-cosmic-surface text-text-accent-cyan" : "text-text-secondary hover:text-text-accent-cyan"
              )}
            >
              {f === "all" ? "全部" : f === "image" ? "图片" : "视频"}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 bg-cosmic-surface/30 rounded-lg p-1">
          <button
            onClick={() => setViewMode("grid")}
            className={cn("p-1.5 rounded-md", viewMode === "grid" ? "bg-cosmic-surface" : "text-text-secondary")}
          >
            <Grid3X3 className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={cn("p-1.5 rounded-md", viewMode === "list" ? "bg-cosmic-surface" : "text-text-secondary")}
          >
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Grid View */}
      {viewMode === "grid" && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {filtered.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.03 }}
              className={cn(
                "group relative rounded-xl overflow-hidden border border-cosmic-border/40 bg-cosmic-surface/10 cursor-pointer transition-all",
                selected.has(item.id) && "ring-2 ring-accent-cyan"
              )}
              onClick={() => toggleSelect(item.id)}
            >
              {item.type === "image" ? (
                <img src={item.url} alt={item.prompt} className="w-full aspect-square object-cover" loading="lazy" />
              ) : (
                <video src={item.url} className="w-full aspect-square object-cover" muted loop playsInline />
              )}
              <div className="absolute top-2 left-2 px-1.5 py-0.5 rounded text-[10px] bg-black/50 backdrop-blur-sm text-white/80">
                {item.type === "image" ? <ImageIcon className="w-3 h-3 inline mr-0.5" /> : <Video className="w-3 h-3 inline mr-0.5" />}
                {item.model}
              </div>
              {selected.has(item.id) && (
                <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-accent-cyan flex items-center justify-center">
                  <svg className="w-3 h-3 text-text-accent-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}

      {/* List View */}
      {viewMode === "list" && (
        <div className="space-y-1">
          {filtered.map((item) => (
            <div
              key={item.id}
              className={cn(
                "flex items-center gap-4 p-3 rounded-xl transition-all cursor-pointer",
                selected.has(item.id) ? "bg-accent-cyan/[0.04] border border-accent-cyan/20" : "hover:bg-cosmic-surface/30 border border-transparent"
              )}
              onClick={() => toggleSelect(item.id)}
            >
              {item.type === "image" ? (
                <img src={item.url} alt="" className="w-12 h-12 rounded-lg object-cover flex-shrink-0" />
              ) : (
                <video src={item.url} className="w-12 h-12 rounded-lg object-cover flex-shrink-0" muted />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm truncate">{item.prompt}</p>
                <p className="text-xs text-text-secondary">{item.model} · {item.date.toLocaleDateString("zh-CN")}</p>
              </div>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <a href={item.url} download className="p-1.5 rounded-lg hover:bg-cosmic-surface">
                  <Download className="w-4 h-4" />
                </a>
                <button className="p-1.5 rounded-lg hover:bg-cosmic-surface">
                  <MoreHorizontal className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {filtered.length === 0 && (
        <div className="text-center py-20 text-text-secondary">
          <p className="text-lg mb-1">暂无内容</p>
          <p className="text-sm">开始创作来填充你的内容库</p>
        </div>
      )}
    </div>
  );
}
