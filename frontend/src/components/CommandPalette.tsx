"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Home, Image, Video, Bot, FolderOpen, Sparkles,
  Wand2, Scissors, Maximize2, Camera, Mic, Layers,
  Zap, CreditCard, LogIn, UserPlus, Search, ExternalLink,
} from "lucide-react";
import {
  CommandDialog, CommandInput, CommandList,
  CommandEmpty, CommandGroup, CommandItem, CommandShortcut,
} from "@/components/ui/command";
import { useCmdKStore } from "@/lib/stores";

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
  { group: "创作", icon: Image, label: "图片生成", shortcut: "C I", href: "/create/image" },
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

  const filtered = query
    ? ITEMS.filter((item) =>
        item.label.toLowerCase().includes(query.toLowerCase()) ||
        item.href?.toLowerCase().includes(query.toLowerCase()) ||
        item.shortcut?.toLowerCase().includes(query.toLowerCase())
      )
    : ITEMS;

  // Group filtered items
  const groups = filtered.reduce<Record<string, CommandItem[]>>((acc, item) => {
    (acc[item.group] ||= []).push(item);
    return acc;
  }, {});

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput
        placeholder="搜索工具、页面、功能..."
        value={query}
        onValueChange={setQuery}
      />
      <CommandList>
        <CommandEmpty>没有找到匹配的结果</CommandEmpty>
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
