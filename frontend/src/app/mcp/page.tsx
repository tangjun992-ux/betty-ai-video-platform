"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Check, Copy, Image as ImageIcon, Video, Sparkles, FolderOpen, Terminal, KeyRound, Info } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { useLocale } from "@/i18n/LocaleProvider";
import { cn } from "@/lib/utils";

type ClientId = "cursor" | "claude" | "vscode" | "chatgpt";

const CLIENTS: { id: ClientId; label: string }[] = [
  { id: "cursor", label: "Cursor" },
  { id: "claude", label: "Claude" },
  { id: "vscode", label: "VS Code" },
  { id: "chatgpt", label: "ChatGPT" },
];

const COPY = {
  zh: {
    kicker: "Betty MCP & API",
    title: "从你的 Agent 或自己的应用里创作。",
    subtitle: "用 MCP 把 Betty 接到 Cursor / Claude / VS Code，或用 REST 把图/视生成接到你的产品与工作流。",
    honesty: "对标 Yapper 分发面，但不照抄话术：连接器要 API Key（不是账号 OAuth）；货架只列已验证 active，不写 54+，不宣称 Seedance 2.5 / Sora / Veo。",
    connectCta: "查看连接配置",
    restCta: "管理 API 密钥",
    worksWith: "可用于",
    s1: "01 — 连接",
    s1title: "一分钟接上。",
    s1sub: "选客户端看配置。Betty 走 Streamable HTTP JSON-RPC；鉴权是 sk_betty_ 密钥。",
    steps: {
      cursor: [
        "打开 Cursor Settings → MCP",
        "添加 HTTP 服务器，URL 贴下方 connector",
        "在 headers 里放 Authorization: Bearer sk_betty_…（在开发者页创建）",
      ],
      claude: [
        "Claude 自定义 Connector 默认走 OAuth，Betty 尚未提供账号 OAuth",
        "桌面版可把同一 URL 配成远程 MCP，并带上 API Key header",
        "能连上后即可 list_models / quote / generate",
      ],
      vscode: [
        "在 mcp.json 增加 betty 条目",
        "url 使用 connector，headers 带 Bearer",
        "重载窗口后在 Copilot / agent 里调用工具",
      ],
      chatgpt: [
        "ChatGPT 远程 MCP 同样需要可访问的 HTTPS connector",
        "Betty 不伪造「免 Key 登录」",
        "有 Key 后工具面与 Cursor 相同",
      ],
    },
    s2: "02 — 能力",
    s2title: "Agent 现在能做的四件事。",
    caps: [
      { id: "image", title: "图片生成", desc: "已验证图片模型，可带参考图。不是「任意 4K 全货架」。", icon: ImageIcon },
      { id: "video", title: "视频生成", desc: "Seedance 2.0 / Kling 等已验证视频 SKU。不是 Sora / Veo。", icon: Video },
      { id: "quote", title: "报价与积分", desc: "generate 前可 quote；失败退积分。ETA 是目录均时，不是 SLA。", icon: Sparkles },
      { id: "assets", title: "自己的资产", desc: "列出该 Key 账户下最近完成的作品，供下一轮参考。", icon: FolderOpen },
    ],
    s3: "03 — 已验证模型，一次连接",
    s3title: (n: number) => `${n} 个 active 模型`,
    s3sub: "数字来自 /public/models，随目录变化。lab 不算可售。",
    explore: "查看模型目录",
    s4: "04 — 给谁用",
    who: [
      { n: "01", t: "增强你的 AI Agent", d: "让 Cursor / Claude 真的出图出视频，而不只是描述。" },
      { n: "02", t: "做 AI 产品", d: "REST + 同一套积分账户，把生成接到你的后端。" },
      { n: "03", t: "自动化内容", d: "异步任务 + 可选 webhook，脚本里拉结果。" },
      { n: "04", t: "规模化生产", d: "并发受套餐限额（4/6/10/40），超限 429，不静默排队。" },
    ],
    s5: "05 — 问题",
    faqs: [
      { q: "连接器怎么工作？", a: "Betty 托管 MCP JSON-RPC。把 connector URL 配进客户端，带上 sk_betty_ Key，即可列出模型、报价、入队、查任务、列资产。" },
      { q: "要 API Key 吗？", a: "要。Yapper 托管连接器可以账号登录；Betty 复用已有开发者密钥，不假装已做 OAuth。" },
      { q: "有哪些模型？", a: "与 App 里已验证 active 货架相同。本环境通常是个位数，不是 54+。" },
      { q: "如何计费？", a: "走账户积分。quote 可先干跑；失败会退还预扣。" },
      { q: "生成要多久？", a: "图通常数十秒级，视频数分钟级，取决于模型和队列。不要把 demo 本地 3 秒写成 SLA。" },
    ],
    footer: "先创建密钥，再把 connector 贴进 Agent。",
    copied: "已复制",
    copy: "复制",
  },
  en: {
    kicker: "Betty MCP & API",
    title: "Create from your agent or your app.",
    subtitle: "Connect Betty to Cursor, Claude, or VS Code with MCP — or use the REST API in your own product.",
    honesty: "Yapper-parity distribution, honest contract: API key auth (not account OAuth). Shelf is verified active only — not 54+, not Seedance 2.5 / Sora / Veo.",
    connectCta: "See connector config",
    restCta: "Manage API keys",
    worksWith: "Works with",
    s1: "01 — Connect",
    s1title: "A minute, start to finish.",
    s1sub: "Pick a client. Betty speaks Streamable HTTP JSON-RPC; auth is a sk_betty_ key.",
    steps: {
      cursor: [
        "Open Cursor Settings → MCP",
        "Add an HTTP server and paste the connector URL",
        "Set Authorization: Bearer sk_betty_… (create the key on the developer page)",
      ],
      claude: [
        "Claude custom connectors expect OAuth — Betty does not ship account OAuth",
        "Desktop remote MCP can use the same URL plus an API key header",
        "Once connected: list_models / quote / generate",
      ],
      vscode: [
        "Add a betty entry to mcp.json",
        "Use the connector URL and a Bearer header",
        "Reload, then call the tools from your agent",
      ],
      chatgpt: [
        "ChatGPT remote MCP needs a reachable HTTPS connector",
        "Betty does not advertise key-less sign-in",
        "With a key, the tool surface matches Cursor",
      ],
    },
    s2: "02 — Capabilities",
    s2title: "Four things your agent can do.",
    caps: [
      { id: "image", title: "Image generation", desc: "Verified image models, optional references. Not “any model, always 4K”.", icon: ImageIcon },
      { id: "video", title: "Video generation", desc: "Verified video SKUs such as Seedance 2.0 / Kling. Not Sora / Veo.", icon: Video },
      { id: "quote", title: "Quotes and credits", desc: "Dry-run quote before generate. Failed jobs refund. ETA is catalog average, not an SLA.", icon: Sparkles },
      { id: "assets", title: "Your media", desc: "List recent completed assets owned by the API-key account.", icon: FolderOpen },
    ],
    s3: "03 — Verified models, one connection",
    s3title: (n: number) => `${n} active models`,
    s3sub: "Count comes from /public/models. Lab SKUs are not for sale.",
    explore: "Open model catalog",
    s4: "04 — Who it's for",
    who: [
      { n: "01", t: "Power your AI agent", d: "Let Cursor or Claude create real images and video, not just describe them." },
      { n: "02", t: "Build AI apps", d: "REST plus one credit balance for your backend." },
      { n: "03", t: "Automate content", d: "Async jobs and optional webhooks." },
      { n: "04", t: "Produce at scale", d: "Concurrency follows plan limits (4/6/10/40). Over-limit is 429, never a silent queue." },
    ],
    s5: "05 — Questions",
    faqs: [
      { q: "How does the connector work?", a: "Betty hosts MCP JSON-RPC. Paste the connector URL, send a sk_betty_ key, then list models, quote, enqueue, poll, and list assets." },
      { q: "Do I need an API key?", a: "Yes. Yapper’s hosted connector can sign in with an account. Betty reuses developer keys and does not fake OAuth." },
      { q: "Which models?", a: "The same verified active shelf as the app. Typically a single-digit count here — not 54+." },
      { q: "How does pricing work?", a: "Your existing credit balance. Quote is a dry run; failures refund the hold." },
      { q: "How long do jobs take?", a: "Images often tens of seconds; video a few minutes. Do not treat a 3s demo render as an SLA." },
    ],
    footer: "Create a key, then paste the connector into your agent.",
    copied: "Copied",
    copy: "Copy",
  },
};

export default function McpPage() {
  const { locale } = useLocale();
  const L = COPY[locale === "en" ? "en" : "zh"];
  const [client, setClient] = useState<ClientId>("cursor");
  const [copied, setCopied] = useState(false);
  const [activeCount, setActiveCount] = useState<number | null>(null);
  const [models, setModels] = useState<Array<{ id: string; display_name: string; media_types: string[] }>>([]);
  const [connector, setConnector] = useState(`${API_BASE}/mcp/connector`);

  useEffect(() => {
    fetch(`${API_BASE}/mcp/connector`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d?.endpoint) setConnector(d.endpoint); })
      .catch(() => {});
    fetch(`${API_BASE}/public/models`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (!d) return;
        setActiveCount(Number(d.active_count || (d.models || []).length || 0));
        setModels((d.models || []).slice(0, 12));
      })
      .catch(() => {});
  }, []);

  const config = useMemo(() => JSON.stringify({
    mcpServers: {
      betty: {
        url: connector,
        headers: { Authorization: "Bearer sk_betty_YOUR_KEY" },
      },
    },
  }, null, 2), [connector]);

  const copy = async () => {
    await navigator.clipboard.writeText(config);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-12">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-10">
        <p className="text-xs font-semibold tracking-widest text-accent-cyan mb-3">{L.kicker}</p>
        <h1 className="text-3xl md:text-4xl font-display font-bold text-text-accent-cyan mb-3" data-testid="mcp-headline">{L.title}</h1>
        <p className="text-text-secondary max-w-2xl mx-auto mb-4">{L.subtitle}</p>
        <p data-testid="mcp-honesty" className="max-w-2xl mx-auto mb-6 text-xs text-amber-800 dark:text-amber-200 bg-amber-500/10 border border-amber-400/30 rounded-xl px-3 py-2">
          {L.honesty}
        </p>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <a href="#connect" className="btn-primary">{L.connectCta}</a>
          <Link href="/developer" className="btn-secondary inline-flex items-center gap-1.5"><KeyRound className="w-4 h-4" />{L.restCta}</Link>
        </div>
        <p className="mt-5 text-xs text-text-tertiary">{L.worksWith} · Claude · Cursor · ChatGPT · VS Code</p>
      </motion.div>

      <section id="connect" className="mb-14" data-testid="mcp-connect">
        <p className="text-xs text-text-tertiary mb-1">{L.s1}</p>
        <h2 className="text-xl font-bold text-text-accent-cyan mb-2">{L.s1title}</h2>
        <p className="text-sm text-text-secondary mb-4">{L.s1sub}</p>
        <div className="flex gap-2 flex-wrap mb-4" role="tablist">
          {CLIENTS.map((c) => (
            <button
              key={c.id}
              type="button"
              data-testid={`mcp-client-${c.id}`}
              onClick={() => setClient(c.id)}
              className={cn(
                "px-3 py-1.5 rounded-full text-xs font-medium border",
                client === c.id ? "bg-brand text-white border-brand" : "border-cosmic-border text-text-secondary",
              )}
            >
              {c.label}
            </button>
          ))}
        </div>
        <ol className="space-y-2 mb-4 text-sm text-text-secondary">
          {L.steps[client].map((s) => <li key={s} className="pl-1">· {s}</li>)}
        </ol>
        <div className="rounded-2xl border border-cosmic-border bg-cosmic-deep overflow-hidden">
          <div className="px-4 py-2 border-b border-cosmic-border text-xs text-text-tertiary flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5"><Terminal className="w-3.5 h-3.5" />mcp.json</span>
            <button type="button" onClick={copy} className="inline-flex items-center gap-1 hover:text-text-primary">
              {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
              {copied ? L.copied : L.copy}
            </button>
          </div>
          <pre className="p-4 text-xs font-mono text-text-secondary overflow-x-auto" data-testid="mcp-config">{config}</pre>
        </div>
      </section>

      <section className="mb-14" data-testid="mcp-capabilities">
        <p className="text-xs text-text-tertiary mb-1">{L.s2}</p>
        <h2 className="text-xl font-bold text-text-accent-cyan mb-4">{L.s2title}</h2>
        <div className="grid md:grid-cols-2 gap-3">
          {L.caps.map((c) => (
            <div key={c.id} className="rounded-2xl border border-cosmic-border bg-cosmic-surface p-4">
              <c.icon className="w-4 h-4 text-accent-cyan mb-2" />
              <h3 className="font-semibold text-text-primary mb-1">{c.title}</h3>
              <p className="text-sm text-text-secondary">{c.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-14" data-testid="mcp-models">
        <p className="text-xs text-text-tertiary mb-1">{L.s3}</p>
        <h2 className="text-xl font-bold text-text-accent-cyan mb-1">{L.s3title(activeCount ?? 0)}</h2>
        <p className="text-sm text-text-secondary mb-4">{L.s3sub}</p>
        <div className="flex flex-wrap gap-2 mb-3">
          {models.map((m) => (
            <span key={m.id} className="px-3 py-1.5 rounded-full text-xs border border-cosmic-border bg-cosmic-subtle text-text-primary">
              {m.display_name}
            </span>
          ))}
        </div>
        <Link href="/models" className="text-sm text-accent-cyan hover:underline">{L.explore}</Link>
      </section>

      <section className="mb-14">
        <p className="text-xs text-text-tertiary mb-1">{L.s4}</p>
        <div className="grid md:grid-cols-2 gap-3">
          {L.who.map((w) => (
            <div key={w.n} className="rounded-2xl border border-cosmic-border p-4">
              <p className="text-xs text-accent-cyan mb-1">{w.n}</p>
              <h3 className="font-semibold text-text-primary mb-1">{w.t}</h3>
              <p className="text-sm text-text-secondary">{w.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-10" data-testid="mcp-faq">
        <p className="text-xs text-text-tertiary mb-3">{L.s5}</p>
        <div className="space-y-3">
          {L.faqs.map((f) => (
            <div key={f.q} className="border border-cosmic-border rounded-xl px-5 py-4">
              <p className="text-sm font-semibold text-text-accent-cyan mb-1">{f.q}</p>
              <p className="text-sm text-text-secondary">{f.a}</p>
            </div>
          ))}
        </div>
      </section>

      <p className="text-center text-sm text-text-secondary flex items-center justify-center gap-1">
        <Info className="w-3.5 h-3.5" />{L.footer}
      </p>
    </div>
  );
}
