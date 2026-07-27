"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Home, Image as ImageIcon, Video, Bot, FolderOpen, Sparkles,
  Wand2, Scissors, Maximize2, Camera, Mic, Layers,
  CreditCard, LogIn, UserPlus, Music,
} from "lucide-react";
import {
  CommandDialog, CommandInput, CommandList,
  CommandEmpty, CommandGroup, CommandItem, CommandShortcut,
} from "@/components/ui/command";
import { useCmdKStore } from "@/lib/stores";
import { API_BASE } from "@/lib/api";

const MEDIA_ORIGIN = API_BASE.replace(/\/api\/v1$/, "");
const resolveMedia = (u: string) => (u?.startsWith("/") ? `${MEDIA_ORIGIN}${u}` : u);

interface AssetHit {
  id: string;
  media_type: "image" | "video" | "audio";
  url: string;
  thumbnail: string | null;
  title: string;
  prompt: string | null;
  model: string | null;
}

interface CommandItem {
  icon: React.ElementType;
  label: string;
  shortcut?: string;
  href?: string;
  action?: () => void;
  group: string;
}

const ITEMS: CommandItem[] = [
  // ── Navigation ──
  { group: "导航", icon: Home, label: "首页", shortcut: "G H", href: "/" },
  { group: "导航", icon: Sparkles, label: "探索", shortcut: "G G", href: "/explore" },
  { group: "导航", icon: FolderOpen, label: "我的资产库", shortcut: "G L", href: "/library" },
  { group: "导航", icon: CreditCard, label: "定价", shortcut: "G P", href: "/pricing" },
  { group: "导航", icon: Bot, label: "AI Agent", shortcut: "G A", href: "/agent" },

  // ── 创作 ──
  { group: "创作", icon: ImageIcon, label: "图片生成", shortcut: "C I", href: "/create/image" },
  { group: "创作", icon: Video, label: "视频生成", shortcut: "C V", href: "/create/video" },
  { group: "创作", icon: Mic, label: "唇形同步", shortcut: "C L", href: "/create/lipsync" },
  { group: "创作", icon: Camera, label: "运动控制", shortcut: "C M", href: "/create/motion" },
  { group: "创作", icon: Layers, label: "时间轴编辑", shortcut: "C T", href: "/create/timeline" },
  { group: "创作", icon: Wand2, label: "AI 放大", href: "/tools" },
  { group: "创作", icon: Scissors, label: "背景移除", href: "/tools" },
  { group: "创作", icon: Maximize2, label: "产品摄影", href: "/tools" },

  // ── 账户 ──
  { group: "账户", icon: UserPlus, label: "注册", shortcut: "A R", href: "/auth/register" },
  { group: "账户", icon: LogIn, label: "登录", shortcut: "A L", href: "/auth/login" },
];

export function CommandPalette() {
  const router = useRouter();
  const { open, setOpen } = useCmdKStore();
  const [query, setQuery] = useState("");
  const [assets, setAssets] = useState<AssetHit[]>([]);
  const [searching, setSearching] = useState(false);

  // Debounced real asset search against the library API.
  useEffect(() => {
    const q = query.trim();
    if (!open || q.length < 2) {
      setAssets([]);
      setSearching(false);
      return;
    }
    setSearching(true);
    const ctrl = new AbortController();
    const t = setTimeout(() => {
      fetch(`${API_BASE}/library/?q=${encodeURIComponent(q)}&limit=6`, { signal: ctrl.signal })
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => setAssets((d?.items || []).slice(0, 6)))
        .catch(() => {})
        .finally(() => setSearching(false));
    }, 250);
    return () => { clearTimeout(t); ctrl.abort(); };
  }, [query, open]);

  // Reset transient state when the palette closes.
  useEffect(() => { if (!open) { setQuery(""); setAssets([]); } }, [open]);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || e.key === "/") {
        if (
          (e.target instanceof HTMLElement && e.target.isContentEditable) ||
          (e.target instanceof HTMLInputElement) ||
          (e.target instanceof HTMLTextAreaElement) ||
          (e.target instanceof HTMLSelectElement)
        ) {
          return;
        }
        e.preventDefault();
        setOpen(!open);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [open, setOpen]);

  const runCommand = useCallback(
    (item: CommandItem) => {
      if (item.href) {
        router.push(item.href);
      } else if (item.action) {
        item.action();
      }
      setOpen(false);
    },
    [router, setOpen]
  );

  const openAsset = useCallback(
    (a: AssetHit) => {
      // Remix generated assets (prompt known) into the matching creator;
      // otherwise just open the media for a quick look.
      if (a.prompt) {
        const base = a.media_type === "video" ? "/create/video" : "/create/image";
        const params = new URLSearchParams({ prompt: a.prompt });
        if (a.model) params.set("model", a.model);
        router.push(`${base}?${params}`);
      } else {
        window.open(resolveMedia(a.url), "_blank");
      }
      setOpen(false);
    },
    [router, setOpen]
  );

  const q = query.trim().toLowerCase();
  const filtered = q
    ? ITEMS.filter((item) =>
        item.label.toLowerCase().includes(q) ||
        item.href?.toLowerCase().includes(q) ||
        item.shortcut?.toLowerCase().includes(q)
      )
    : ITEMS;

  // Group filtered items
  const groups = filtered.reduce<Record<string, CommandItem[]>>((acc, item) => {
    (acc[item.group] ||= []).push(item);
    return acc;
  }, {});

  const assetIcon = (t: string) => (t === "video" ? Video : t === "audio" ? Music : ImageIcon);

  return (
    <CommandDialog open={open} onOpenChange={setOpen} shouldFilter={false}>
      <CommandInput
        placeholder="搜索资产、工具或提示词..."
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        <CommandEmpty>{searching ? "搜索中…" : "没有找到匹配的结果"}</CommandEmpty>

        {/* Real assets from the library */}
        {assets.length > 0 && (
          <CommandGroup heading="资产库">
            {assets.map((a) => {
              const Icon = assetIcon(a.media_type);
              const thumb = a.thumbnail ? resolveMedia(a.thumbnail) : null;
              return (
                <CommandItem key={a.id} value={`asset-${a.id}`} onSelect={() => openAsset(a)}>
                  {thumb ? (
                    <img src={thumb} alt="" className="w-6 h-6 rounded object-cover flex-shrink-0" />
                  ) : (
                    <Icon className="w-4 h-4 text-text-secondary" />
                  )}
                  <span className="truncate">{a.title || a.prompt || "未命名资产"}</span>
                  <CommandShortcut>{a.prompt ? "做同款" : "查看"}</CommandShortcut>
                </CommandItem>
              );
            })}
          </CommandGroup>
        )}

        {Object.entries(groups).map(([group, items]) => (
          <CommandGroup key={group} heading={group}>
            {items.map((item) => (
              <CommandItem
                key={item.label}
                onSelect={() => runCommand(item)}
                value={item.label}
              >
                <item.icon className="w-4 h-4 text-text-secondary" />
                <span>{item.label}</span>
                {item.shortcut && (
                  <CommandShortcut>{item.shortcut}</CommandShortcut>
                )}
              </CommandItem>
            ))}
          </CommandGroup>
        ))}
      </CommandList>
    </CommandDialog>
  );
}
