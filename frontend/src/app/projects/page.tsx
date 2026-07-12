"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { FolderPlus, Folder, Loader2, Plus, Image as ImageIcon } from "lucide-react";
import { listProjects, createProject, API_BASE, type ProjectDTO } from "@/lib/api";
import { useToast } from "@/components/Toast";

function resolveMedia(url?: string | null): string {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  return `${API_BASE.replace(/\/api\/v1$/, "")}${url}`;
}

export default function ProjectsPage() {
  const toast = useToast();
  const [projects, setProjects] = useState<ProjectDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");

  const load = async () => {
    try { setProjects((await listProjects()).projects); }
    catch (e: any) { toast.error("加载失败", e.message || ""); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const submit = async () => {
    if (!name.trim()) { toast.error("请输入项目名称", ""); return; }
    setCreating(true);
    try {
      await createProject(name.trim(), desc.trim() || undefined);
      setName(""); setDesc(""); setShowForm(false);
      await load();
      toast.success("项目已创建", "");
    } catch (e: any) { toast.error("创建失败", e.message || ""); }
    finally { setCreating(false); }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold gradient-text-static">我的项目</h1>
          <p className="text-text-secondary text-sm mt-1">把作品归入项目，集中管理与复用（对标 Runway / Yapper Projects）</p>
        </div>
        <button onClick={() => setShowForm((v) => !v)} className="btn-primary">
          <FolderPlus className="w-4 h-4" /> 新建项目
        </button>
      </div>

      {showForm && (
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
          className="mb-6 p-4 rounded-2xl border border-cosmic-border bg-cosmic-surface space-y-3">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="项目名称，例如：咖啡品牌 Campaign"
            className="input-cosmic" autoFocus />
          <input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="项目简介（可选）" className="input-cosmic" />
          <div className="flex justify-end gap-2">
            <button onClick={() => setShowForm(false)} className="btn-secondary text-sm">取消</button>
            <button onClick={submit} disabled={creating || !name.trim()} className="btn-primary text-sm">
              {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} 创建
            </button>
          </div>
        </motion.div>
      )}

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="aspect-[4/3] rounded-2xl skeleton" />)}
        </div>
      ) : projects.length === 0 ? (
        <div className="h-64 rounded-2xl border border-dashed border-cosmic-border flex flex-col items-center justify-center text-text-tertiary gap-3">
          <Folder className="w-10 h-10" />
          <p className="text-sm">还没有项目。点击「新建项目」开始整理你的作品。</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {projects.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`}
              className="group rounded-2xl border border-cosmic-border bg-cosmic-surface overflow-hidden hover:border-brand/40 hover:shadow-md transition-all">
              <div className="aspect-[4/3] bg-cosmic-subtle relative overflow-hidden">
                {p.cover ? (
                  <img src={resolveMedia(p.cover)} alt={p.name} className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-500" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-text-tertiary/50"><ImageIcon className="w-8 h-8" /></div>
                )}
                <span className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-black/55 backdrop-blur-md text-[10px] text-white font-medium">{p.item_count} 项</span>
              </div>
              <div className="p-3">
                <p className="text-sm font-semibold text-text-primary truncate">{p.name}</p>
                {p.description && <p className="text-xs text-text-tertiary truncate mt-0.5">{p.description}</p>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
