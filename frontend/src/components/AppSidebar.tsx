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
  Rss,
  Library,
  FolderKanban,
  Bot,
  ImageIcon,
  Video,
  Music,
  Mic,
  Clock,
  Wand2,
  User,
  Maximize2,
  Scissors,
  Expand,
  AudioLines,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Sparkles,
  Users,
} from "lucide-react";

// ─── NAV ITEMS ──────────────────────────────────────────
const mainNav = [
  { href: "/", icon: Home, labelKey: "nav.home", exact: true },
  { href: "/explore", icon: Compass, labelKey: "nav.explore" },
  { href: "/feed", icon: Rss, labelKey: "nav.feed" },
  { href: "/library", icon: Library, labelKey: "nav.library" },
  { href: "/projects", icon: FolderKanban, labelKey: "nav.projects" },
  { href: "/teams", icon: Users, labelKey: "nav.teams" },
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
  const active = exact ? pathname === href : pathname.startsWith(href);

  const link = (
    <Link
      href={href}
      className={cn(
        "group relative flex items-center rounded-lg transition-all duration-200",
        collapsed ? "justify-center w-10 h-10 mx-auto" : "gap-3 px-3 py-2.5 mx-2",
        active
          ? "bg-brand/[0.08] text-brand"
          : "text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle"
      )}
    >
      {/* Active indicator bar — left edge 3px bg-brand */}
      {active && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-6 rounded-r-full bg-brand" />
      )}
      <Icon
        className={cn(
          "shrink-0 transition-colors",
          collapsed ? "w-5 h-5" : "w-5 h-5",
          active ? "text-brand" : "text-text-secondary group-hover:text-text-primary"
        )}
      />
      {!collapsed && (
        <span className="text-sm font-medium leading-none truncate">
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
  const { sidebarCollapsed, toggleSidebarCollapsed } = useUIStore();
  const [toolsOpen, setToolsOpen] = useState(true);

  return (
    <motion.aside
      initial={false}
      animate={{ width: sidebarCollapsed ? 64 : 240 }}
      transition={{
        duration: 0.28,
        ease: [0.16, 1, 0.3, 1], // --ease-out-expo
      }}
      className={cn(
        "fixed left-0 top-0 bottom-0 z-30 flex flex-col",
        "bg-cosmic-surface border-r border-cosmic-border",
        "overflow-hidden"
      )}
    >
      {/* ── Brand / Logo ── */}
      {!sidebarCollapsed && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="flex items-center gap-2.5 h-12 px-4 border-b border-cosmic-border shrink-0"
        >
          <BrandMark className="w-7 h-7" />
          <span className="font-semibold text-base tracking-[-0.02em] text-text-primary truncate">
            betty
          </span>
        </motion.div>
      )}
      {sidebarCollapsed && (
        <div className="flex items-center justify-center h-12 border-b border-cosmic-border shrink-0">
          <Tooltip delayDuration={200}>
            <TooltipTrigger asChild>
              <Link href="/" className="p-1 rounded-lg">
                <BrandMark className="w-7 h-7" />
              </Link>
            </TooltipTrigger>
            <TooltipContent side="right" sideOffset={12}>
              首页
            </TooltipContent>
          </Tooltip>
        </div>
      )}

      {/* ── Navigation ── */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden py-3 space-y-1">
        {/* Main Section */}
        {!sidebarCollapsed && (
          <p className="px-4 py-1 text-[11px] font-semibold uppercase tracking-wider text-text-tertiary/70 select-none">
            主导航
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
        <div className="my-2 mx-3 border-t border-cosmic-border" />

        {/* Tools Section */}
        {!sidebarCollapsed ? (
          <Collapsible open={toolsOpen} onOpenChange={setToolsOpen}>
            <CollapsibleTrigger
              className={cn(
                "flex items-center justify-between w-full px-4 py-1.5",
                "text-[11px] font-semibold uppercase tracking-wider text-text-tertiary/70",
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
                className="space-y-1 pt-1"
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
            {/* Collapsed: show tools items inline below divider */}
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

      {/* ── Upgrade CTA ── */}
      {!sidebarCollapsed && (
        <div className="shrink-0 border-t border-cosmic-border p-3">
          <Link
            href="/pricing"
            className="flex items-center gap-2 px-3 py-2 rounded-xl bg-brand/[0.06] border border-brand/10 text-brand text-sm font-medium hover:bg-brand/[0.10] transition-all"
          >
            <Sparkles className="w-4 h-4" /> 升级 Pro
          </Link>
        </div>
      )}

      {/* ── Collapse Toggle ── */}
      <div className="shrink-0 border-t border-cosmic-border p-2">
        <button
          onClick={toggleSidebarCollapsed}
          className={cn(
            "flex items-center justify-center w-full rounded-lg h-9",
            "text-text-tertiary hover:text-text-primary hover:bg-cosmic-subtle",
            "transition-all duration-200"
          )}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <ChevronLeft className="w-4 h-4" />
              <span className="ml-2 text-xs font-medium">收起</span>
            </>
          )}
        </button>
      </div>
    </motion.aside>
  );
}

export default AppSidebar;
