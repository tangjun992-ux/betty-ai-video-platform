"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { KeyRound, Plus, Copy, Trash2, Loader2, Check, Terminal, ShieldAlert } from "lucide-react";
import { listApiKeys, createApiKeyPlatform, revokeApiKey, API_BASE } from "@/lib/api";
import { useToast } from "@/components/Toast";
import { useAuthStore } from "@/lib/stores";
import { cn } from "@/lib/utils";

export default function DeveloperPage() {
  const toast = useToast();
  const { token } = useAuthStore();
  const [keys, setKeys] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [reveal, setReveal] = useState<{ id: string; secret: string } | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    try { setKeys((await listApiKeys()).keys); }
    catch (e: any) { toast.error("加载失败", e.message || ""); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { if (token) load(); else setLoading(false); }, [token, load]);

  const create = async () => {
    setCreating(true);
    try {
      const r = await createApiKeyPlatform(name.trim() || "默认密钥");
      setReveal({ id: r.id, secret: r.secret });
      setName("");
      await load();
    } catch (e: any) { toast.error("创建失败", e.message || ""); }
    finally { setCreating(false); }
  };
  const revoke = async (id: string) => {
    if (!confirm("吊销后使用该密钥的调用将立即失效，确定吗？")) return;
    try { await revokeApiKey(id); toast.success("已吊销", ""); await load(); }
    catch (e: any) { toast.error("吊销失败", e.message || ""); }
  };
  const copy = (s: string) => { navigator.clipboard.writeText(s); setCopied(true); setTimeout(() => setCopied(false), 1500); };

  const origin = API_BASE.replace(/\/api\/v1$/, "");
  const curl = `curl -X POST ${origin}/api/v1/public/generate \\\n  -H "X-API-Key: sk_betty_..." \\\n  -H "Content-Type: application/json" \\\n  -d '{"prompt":"a serene mountain lake at dawn, cinematic","webhook_url":"https://example.com/hooks/betty"}'`;
  const webhookNote = `任务结束时 betty 会 POST 到 webhook_url，请求体含 task_id/status/results。\n签名头：X-Betty-Timestamp + X-Betty-Signature (sha256=HMAC(secret, "{ts}." + body))\n密钥：WEBHOOK_SIGNING_SECRET（或回退 JWT_SECRET）`;

  if (!token) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-20 text-center">
        <ShieldAlert className="w-10 h-10 text-text-tertiary mx-auto mb-3" />
        <h1 className="text-xl font-bold text-text-primary mb-2">开发者 API</h1>
        <p className="text-text-secondary text-sm mb-5">请先登录以创建与管理 API 密钥。</p>
        <a href="/auth/login" className="btn-primary">去登录</a>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-2">
        <span className="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-brand-50 border border-cosmic-border"><KeyRound className="w-5 h-5 text-brand" /></span>
        <div>
          <h1 className="text-2xl font-bold gradient-text-static">开发者 API</h1>
          <p className="text-text-secondary text-sm">用 API 密钥以编程方式调用 betty 的生成能力（按你的账户计费）</p>
        </div>
      </div>

      {/* Create */}
      <div className="mt-6 flex gap-2">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="密钥名称，例如：生产环境 / 我的脚本" className="input-cosmic flex-1" />
        <button onClick={create} disabled={creating} className="btn-primary">
          {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} 新建密钥
        </button>
      </div>

      {/* Reveal once */}
      {reveal && (
        <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
          className="mt-4 p-4 rounded-2xl border border-brand/30 bg-brand/[0.05]">
          <p className="text-sm font-semibold text-text-primary mb-1">密钥已创建 — 请立即复制</p>
          <p className="text-xs text-text-tertiary mb-3">出于安全，完整密钥只显示这一次，之后无法再次查看。</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 px-3 py-2 rounded-lg bg-cosmic-surface border border-cosmic-border text-xs font-mono text-text-primary break-all">{reveal.secret}</code>
            <button onClick={() => copy(reveal.secret)} className="btn-secondary text-sm">{copied ? <Check className="w-4 h-4 text-success" /> : <Copy className="w-4 h-4" />}</button>
          </div>
        </motion.div>
      )}

      {/* Keys list */}
      <h2 className="text-sm font-semibold text-text-primary mt-8 mb-3">我的密钥</h2>
      {loading ? (
        <div className="space-y-2">{[...Array(2)].map((_, i) => <div key={i} className="h-14 rounded-xl skeleton" />)}</div>
      ) : keys.length === 0 ? (
        <div className="h-24 rounded-xl border border-dashed border-cosmic-border flex items-center justify-center text-sm text-text-tertiary">还没有密钥，点击「新建密钥」开始。</div>
      ) : (
        <div className="rounded-2xl border border-cosmic-border bg-cosmic-surface divide-y divide-cosmic-border">
          {keys.map((k) => (
            <div key={k.id} className="flex items-center justify-between px-4 py-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">{k.name}</p>
                <p className="text-xs text-text-tertiary font-mono">{k.masked} · 创建于 {(k.created_at || "").slice(0, 10)}{k.last_used_at ? ` · 最近使用 ${(k.last_used_at || "").slice(0, 10)}` : " · 未使用"}</p>
              </div>
              <button onClick={() => revoke(k.id)} className="btn-icon text-text-tertiary hover:text-destructive" title="吊销"><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
      )}

      {/* Docs */}
      <h2 className="text-sm font-semibold text-text-primary mt-8 mb-3 flex items-center gap-2"><Terminal className="w-4 h-4 text-brand" /> 快速开始</h2>
      <div className="rounded-2xl border border-cosmic-border bg-cosmic-deep overflow-hidden">
        <div className="px-4 py-2 border-b border-cosmic-border text-xs text-text-tertiary">POST /api/v1/public/generate</div>
        <pre className="p-4 text-xs font-mono text-text-secondary overflow-x-auto whitespace-pre">{curl}</pre>
      </div>
      <div className="mt-3 rounded-2xl border border-cosmic-border bg-cosmic-deep overflow-hidden">
        <div className="px-4 py-2 border-b border-cosmic-border text-xs text-text-tertiary">Webhook 回调（对标 Runway / Kling）</div>
        <pre className="p-4 text-xs font-mono text-text-secondary overflow-x-auto whitespace-pre-wrap">{webhookNote}</pre>
      </div>
      <p className="text-xs text-text-tertiary mt-3">
        鉴权：请求头 <code className="text-text-secondary">X-API-Key: sk_betty_...</code>（或 <code className="text-text-secondary">Authorization: Bearer sk_betty_...</code>）。
        返回 <code className="text-text-secondary">task_id</code>，可轮询 <code className="text-text-secondary">GET /api/v1/tasks/&#123;task_id&#125;</code> 或使用 <code className="text-text-secondary">webhook_url</code>。生成按你的账户积分计费，并受频率限制。
      </p>
    </div>
  );
}
