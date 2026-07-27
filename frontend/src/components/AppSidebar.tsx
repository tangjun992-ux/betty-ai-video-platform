"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { useUIStore } from "@/lib/stores";
import { cn } from "@/lib/utils";
import { BrandMark } from "@/components/BrandLogo";
import { useLocale } from "@/i18n/LocaleProvider";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import {
  Home,
  Compass,
  Library,
  FolderKanban,
  Bot,
  ImageIcon,
  Video,
  Music,
  Mic,
  Clock,
  Wand2,
  MessageSquare,
  Maximize2,
  Scissors,
  Expand,
  AudioLines,
  PanelLeftClose,
  ChevronDown,
  Sparkles,
  X,
} from "lucide-react";

/* ═══════════════════════════════════════════════════════
   AppSidebar — STUDIO v5 (对标 yapper dashboard 侧栏)
   桌面: 固定左栏, 可收起为图标轨 · 移动: 抽屉 + 遮罩
   ═══════════════════════════════════════════════════════ */

// ─── NAV ITEMS ──────────────────────────────────────────
const mainNav = [
  { href: "/", icon: Home, labelKey: "nav.home", exact: true },
  { href: "/explore", icon: Compass, labelKey: "nav.explore" },
  { href: "/library", icon: Library, labelKey: "nav.library" },
  { href: "/projects", icon: FolderKanban, labelKey: "nav.projects" },
  { href: "/sessions", icon: MessageSquare, labelKey: "nav.sessions" },
];

const toolNav = [
  { href: "/agent", icon: Bot, labelKey: "nav.agent" },
  { href: "/create/image", icon: ImageIcon, labelKey: "nav.image" },
  { href: "/create/video", icon: Video, labelKey: "nav.video" },
  { href: "/create/image-editor", icon: Wand2, labelKey: "nav.imageEdit" },
  { href: "/create/motion", icon: Music, labelKey: "nav.motion" },
  { href: "/create/lipsync", icon: Mic, labelKey: "nav.lipsync" },
  { href: "/create/timeline", icon: Clock, labelKey: "nav.timeline" },
  { href: "/create/upscale", icon: Maximize2, labelKey: "nav.upscale" },
  { href: "/create/bg-remove", icon: Scissors, labelKey: "nav.removeBg" },
  { href: "/create/extend", icon: Expand, labelKey: "nav.extend" },
  { href: "/create/audio", icon: AudioLines, labelKey: "nav.audio" },
];

// ─── HELPER: Nav Item ───────────────────────────────────
function NavItem({
  href,
  icon: Icon,
  label,
  exact,
  collapsed,
}: {
  href: string;
  icon: React.ElementType;
  label: string;
  exact?: boolean;
  collapsed: boolean;
}) {
  const pathname = usePathname();
  const { setSidebarOpen } = useUIStore();
  const active = exact ? pathname === href : pathname.startsWith(href);

  const link = (
    <Link
      href={href}
      onClick={() => {
        // 移动端点选后收起抽屉
        if (typeof window !== "undefined" && window.innerWidth < 768) setSidebarOpen(false);
      }}
      className={cn(
        "group relative flex items-center rounded-lg transition-colors duration-150",
        collapsed ? "justify-center w-10 h-10 mx-auto" : "gap-3 px-3 py-2 mx-2",
        active
          ? "bg-cosmic-subtle text-text-primary"
          : "text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle/60"
      )}
    >
      <Icon
        className={cn(
          "shrink-0 w-[18px] h-[18px] transition-colors",
          active ? "text-brand" : "text-text-tertiary group-hover:text-text-primary"
        )}
      />
      {!collapsed && (
        <span className="text-[13px] font-medium leading-none truncate">
          {label}
        </span>
      )}
    </Link>
  );

  if (collapsed) {
    return (
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>{link}</TooltipTrigger>
        <TooltipContent side="right" sideOffset={12}>
          {label}
        </TooltipContent>
      </Tooltip>
    );
  }

  return link;
}

// ─── APP SIDEBAR ────────────────────────────────────────
export function AppSidebar() {
  const { t } = useLocale();
  const { sidebarOpen, sidebarCollapsed, toggleSidebarCollapsed, setSidebarOpen } = useUIStore();
  const [toolsOpen, setToolsOpen] = useState(true);

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarCollapsed ? 64 : 232 }}
      transition={{
        duration: 0.24,
        ease: [0.16, 1, 0.3, 1],
      }}
      className={cn(
        "fixed left-0 top-0 bottom-0 z-50 md:z-30 flex flex-col",
        "bg-cosmic-deep border-r border-cosmic-border",
        "overflow-hidden transition-transform duration-300",
        // 移动端: 固定宽抽屉, 开合由 translate 控制
        "max-md:!w-[276px]",
        sidebarOpen ? "max-md:translate-x-0" : "max-md:-translate-x-full",
        "md:translate-x-0"
      )}
    >
      {/* ── Brand / Logo ── */}
      <div className={cn(
        "flex items-center h-14 px-4 shrink-0",
        sidebarCollapsed ? "justify-center" : "justify-between"
      )}>
        <Link href="/" className="flex items-center gap-2.5 min-w-0">
          <BrandMark className="w-7 h-7" />
          {!sidebarCollapsed && (
            <span className="font-semibold text-[15px] tracking-[-0.01em] text-text-primary truncate">
              betty
            </span>
          )}
        </Link>
        {/* 移动端关闭按钮 */}
        <button
          onClick={() => setSidebarOpen(false)}
          className="md:hidden btn-icon -mr-1"
          aria-label="关闭菜单"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* ── Navigation ── */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden py-2 space-y-0.5">
        {/* Main Section */}
        {!sidebarCollapsed && (
          <p className="px-4 pt-1 pb-1.5 text-[11px] font-medium text-text-tertiary select-none">
            导航
          </p>
        )}
        {mainNav.map((item) => (
          <NavItem
            key={item.href}
            href={item.href}
            icon={item.icon}
            label={t(item.labelKey as any)}
            exact={item.exact}
            collapsed={sidebarCollapsed}
          />
        ))}

        {/* Divider */}
        <div className="my-3 mx-4 border-t border-cosmic-border/70" />

        {/* Tools Section */}
        {!sidebarCollapsed ? (
          <Collapsible open={toolsOpen} onOpenChange={setToolsOpen}>
            <CollapsibleTrigger
              className={cn(
                "flex items-center justify-between w-full px-4 py-1.5",
                "text-[11px] font-medium text-text-tertiary",
                "hover:text-text-secondary transition-colors select-none group"
              )}
            >
              <span>创作工具</span>
              <ChevronDown
                className={cn(
                  "w-3.5 h-3.5 transition-transform duration-200",
                  toolsOpen && "rotate-180"
                )}
              />
            </CollapsibleTrigger>
            <CollapsibleContent asChild>
              <motion.div
                initial={false}
                animate={
                  toolsOpen ? { height: "auto", opacity: 1 } : { height: 0, opacity: 0 }
                }
                transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                className="space-y-0.5 pt-0.5"
              >
                {toolNav.map((item) => (
                  <NavItem
                    key={item.href}
                    href={item.href}
                    icon={item.icon}
                    label={t(item.labelKey as any)}
                    collapsed={false}
                  />
                ))}
              </motion.div>
            </CollapsibleContent>
          </Collapsible>
        ) : (
          <>
            {toolNav.map((item) => (
              <NavItem
                key={item.href}
                href={item.href}
                icon={item.icon}
                label={t(item.labelKey as any)}
                collapsed={true}
              />
            ))}
          </>
        )}
      </nav>

      {/* ── Upgrade card (yapper 式底部升级区) ── */}
      {!sidebarCollapsed && (
        <div className="shrink-0 p-3">
          <div className="rounded-xl border border-cosmic-border bg-cosmic-surface p-3">
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="w-3.5 h-3.5 text-brand" />
              <span className="text-[13px] font-semibold text-text-primary">升级 Pro</span>
            </div>
            <p className="text-[11px] text-text-tertiary leading-relaxed mb-2.5">
              更多 Credits · 4K · 全部模型
            </p>
            <Link
              href="/pricing"
              className="btn-primary w-full h-8 text-xs"
            >
              查看方案
            </Link>
          </div>
        </div>
      )}

      {/* ── Collapse Toggle (桌面) ── */}
      <div className="shrink-0 border-t border-cosmic-border p-2 max-md:hidden">
        <button
          onClick={toggleSidebarCollapsed}
          className={cn(
            "flex items-center justify-center w-full rounded-lg h-9",
            "text-text-tertiary hover:text-text-primary hover:bg-cosmic-subtle",
            "transition-colors duration-150"
          )}
          aria-label={sidebarCollapsed ? "展开侧栏" : "收起侧栏"}
        >
          <PanelLeftClose
            className={cn(
              "w-[18px] h-[18px] transition-transform duration-200",
              sidebarCollapsed && "rotate-180"
            )}
          />
        </button>
      </div>
    </motion.aside>
  );
}
