"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Plus, Trash2, Loader2, X, Film } from "lucide-react";
import {
  getProject, addProjectItem, removeProjectItem, deleteProject, listLibrary,
  API_BASE, type ProjectDTO,
} from "@/lib/api";
import { useToast } from "@/components/Toast";

function resolveMedia(url?: string | null): string {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  return `${API_BASE.replace(/\/api\/v1$/, "")}${url}`;
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const toast = useToast();
  const [project, setProject] = useState<ProjectDTO | null>(null);
  const [loading, setLoading] = useState(true);
  const [picker, setPicker] = useState(false);
  const [lib, setLib] = useState<any[]>([]);
  const [libLoading, setLibLoading] = useState(false);

  const load = useCallback(async () => {
    try { setProject(await getProject(id)); }
    catch (e: any) { toast.error("加载失败", e.message || ""); }
    finally { setLoading(false); }
  }, [id]);
  useEffect(() => { load(); }, [load]);

  const openPicker = async () => {
    setPicker(true);
    setLibLoading(true);
    try { setLib((await listLibrary({ limit: 60 })).items || []); }
    catch (e: any) { toast.error("加载素材库失败", e.message || ""); }
    finally { setLibLoading(false); }
  };

  const add = async (it: any) => {
    try {
      const p = await addProjectItem(id, { item_id: it.id, url: it.url, thumbnail: it.thumbnail, media_type: it.media_type, title: it.title });
      setProject(p);
      toast.success("已添加到项目", "");
    } catch (e: any) { toast.error("添加失败", e.message || ""); }
  };
  const remove = async (itemId: string) => {
    try { setProject(await removeProjectItem(id, itemId)); }
    catch (e: any) { toast.error("移除失败", e.message || ""); }
  };
  const del = async () => {
    if (!confirm("确定删除该项目？（不影响素材库原作品）")) return;
    try { await deleteProject(id); router.push("/projects"); }
    catch (e: any) { toast.error("删除失败", e.message || ""); }
  };

  if (loading) return <div className="max-w-6xl mx-auto px-4 py-16 text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto text-brand" /></div>;
  if (!project) return null;

  const inProject = new Set(project.items.map((i) => i.item_id));

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <button onClick={() => router.push("/projects")} className="inline-flex items-center gap-1.5 text-sm text-text-secondary hover:text-text-primary mb-4">
        <ArrowLeft className="w-4 h-4" /> 全部项目
      </button>

      <div className="flex items-start justify-between mb-6 gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-text-primary truncate">{project.name}</h1>
          {project.description && <p className="text-text-secondary text-sm mt-1">{project.description}</p>}
          <p className="text-xs text-text-tertiary mt-1">{project.item_count} 个作品</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <button onClick={openPicker} className="btn-primary"><Plus className="w-4 h-4" /> 添加作品</button>
          <button onClick={del} className="btn-secondary text-destructive"><Trash2 className="w-4 h-4" /></button>
        </div>
      </div>

      {project.items.length === 0 ? (
        <div className="h-64 rounded-2xl border border-dashed border-cosmic-border flex flex-col items-center justify-center text-text-tertiary gap-3">
          <Film className="w-10 h-10" />
          <p className="text-sm">项目还没有作品。点击「添加作品」从素材库选择。</p>
        </div>
      ) : (
        <div className="columns-2 md:columns-3 lg:columns-4 gap-3 space-y-3">
          {project.items.map((it) => (
            <div key={it.item_id} className="group relative rounded-xl overflow-hidden break-inside-avoid ring-1 ring-cosmic-border">
              {it.media_type === "video" ? (
                <video src={resolveMedia(it.url)} poster={resolveMedia(it.thumbnail)} muted loop playsInline
                  onMouseEnter={(e) => (e.currentTarget as HTMLVideoElement).play().catch(() => {})}
                  onMouseLeave={(e) => (e.currentTarget as HTMLVideoElement).pause()}
                  className="w-full object-cover align-middle" />
              ) : (
                <img src={resolveMedia(it.thumbnail || it.url)} alt={it.title || ""} loading="lazy" className="w-full object-cover align-middle" />
              )}
              <button onClick={() => remove(it.item_id)} title="从项目移除"
                className="absolute top-2 right-2 w-7 h-7 rounded-lg bg-black/60 text-white opacity-0 group-hover:opacity-100 hover:bg-red-500 flex items-center justify-center transition-all">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Library picker modal */}
      <AnimatePresence>
        {picker && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm" onClick={() => setPicker(false)}>
            <motion.div initial={{ scale: 0.96, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.98, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-4xl max-h-[85vh] rounded-2xl bg-cosmic-surface border border-cosmic-border overflow-hidden flex flex-col">
              <div className="flex items-center justify-between px-5 py-3 border-b border-cosmic-border">
                <span className="font-semibold text-text-primary">从素材库添加</span>
                <button onClick={() => setPicker(false)} className="btn-icon"><X className="w-4 h-4" /></button>
              </div>
              <div className="p-4 overflow-y-auto">
                {libLoading ? (
                  <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">{[...Array(10)].map((_, i) => <div key={i} className="aspect-square rounded-lg skeleton" />)}</div>
                ) : (
                  <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
                    {lib.map((it) => {
                      const added = inProject.has(it.id);
                      return (
                        <button key={it.id} onClick={() => !added && add(it)} disabled={added}
                          className={`group relative aspect-square rounded-lg overflow-hidden ring-1 transition-all ${added ? "ring-brand/60 opacity-60" : "ring-cosmic-border hover:ring-brand/50"}`}>
                          {it.media_type === "video" ? (
                            <video src={resolveMedia(it.url)} poster={resolveMedia(it.thumbnail)} muted className="w-full h-full object-cover" />
                          ) : (
                            <img src={resolveMedia(it.thumbnail || it.url)} alt="" className="w-full h-full object-cover" />
                          )}
                          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/40 transition-opacity">
                            <span className="px-2 py-1 rounded bg-white text-black text-xs font-semibold">{added ? "已添加" : "+ 添加"}</span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
