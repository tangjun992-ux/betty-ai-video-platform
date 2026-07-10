"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home, Sparkles, Image, Video, FolderOpen,
  Bot, ChevronDown, ChevronUp, Zap, Settings,
  LogOut, User, PanelLeftClose, PanelLeft,
  Search, Bell, Globe,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore, useCmdKStore } from "@/lib/stores";
import { useState, useEffect } from "react";
import { API_BASE } from "@/lib/api";

/* ═══════════════════════════════════════════════════════
   Dashboard Sidebar — AURORA 亮色
   ═══════════════════════════════════════════════════════ */

const mainNav = [
  { href: "/dashboard", icon: Home, label: "Home", exact: true },
  { href: "/explore", icon: Sparkles, label: "Explore" },
  { href: "/library", icon: FolderOpen, label: "My Library" },
  { href: "/agent", icon: Bot, label: "Agent", highlight: true },
  { href: "/create/image", icon: Image, label: "Create Image" },
  { href: "/create/video", icon: Video, label: "Create Video" },
];

const moreTools = [
  { href: "/create/lipsync", icon: Video, label: "Lip-Sync Studio" },
  { href: "/create/image?tool=upscale", icon: Sparkles, label: "Upscaler 4K" },
  { href: "/create/image?tool=removebg", icon: Image, label: "Background Remover" },
  { href: "/create/image?tool=avatar", icon: User, label: "Talking Avatar" },
  { href: "/create/image?tool=product", icon: Image, label: "Product Shots" },
];

interface SessionItem { id: string; title: string; }

function DashboardSidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const [showMore, setShowMore] = useState(false);
  const [sessions, setSessions] = useState<SessionItem[]>([]);

  useEffect(() => {
    let active = true;
    fetch(`${API_BASE}/director/sessions?user_id=0`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (active && d?.sessions) {
          setSessions(d.sessions.map((s: any) => ({ id: s.session_uid, title: s.title || "导演会话" })));
        }
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname.startsWith(href);

  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 280 }}
      className="relative h-screen bg-cosmic-surface border-r border-cosmic-border flex flex-col z-30 overflow-hidden"
    >
      {/* Logo */}
      <div className={cn("flex items-center h-16 border-b border-cosmic-border px-4", collapsed && "justify-center")}>
        {!collapsed && (
          <Link href="/dashboard" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand to-accent-violet flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight text-text-primary">betty</span>
          </Link>
        )}
        {collapsed && (
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand to-accent-violet flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
        )}
        <button
          onClick={onToggle}
          className={cn("ml-auto p-1.5 rounded-lg text-text-tertiary hover:text-text-secondary hover:bg-cosmic-subtle transition-colors", collapsed && "ml-0 mt-4")}
        >
          {collapsed ? <PanelLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
        </button>
      </div>

      {/* Main Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {mainNav.map((item) => {
          const active = isActive(item.href, item.exact);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150",
                collapsed && "justify-center px-2",
                active
                  ? "bg-brand/[0.08] text-brand"
                  : "text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle",
                item.highlight && !active && "text-brand/70"
              )}
            >
              <item.icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          );
        })}

        {/* Show More */}
        <button
          onClick={() => setShowMore(!showMore)}
          className={cn(
            "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-text-tertiary hover:text-text-secondary hover:bg-cosmic-subtle transition-all",
            collapsed && "justify-center px-2"
          )}
        >
          {collapsed ? (
            <ChevronDown className={cn("w-5 h-5 transition-transform", showMore && "rotate-180")} />
          ) : (
            <>
              <ChevronDown className={cn("w-5 h-5 transition-transform", showMore && "rotate-180")} />
              <span>Show More</span>
            </>
          )}
        </button>

        {showMore && !collapsed && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="pl-3 space-y-0.5 overflow-hidden"
          >
            {moreTools.map((t) => (
              <Link
                key={t.label}
                href={t.href}
                className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle transition-all"
              >
                <t.icon className="w-4 h-4" /> {t.label}
              </Link>
            ))}
          </motion.div>
        )}
      </nav>

      {/* Sessions */}
      {!collapsed && sessions.length > 0 && (
        <div className="border-t border-cosmic-border p-3">
          <div className="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-2 px-2">Recent Sessions</div>
          <div className="space-y-0.5">
            {sessions.slice(0, 5).map((s) => (
              <Link
                key={s.id}
                href="/agent"
                className="block w-full text-left px-3 py-2 rounded-xl text-xs text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle transition-colors truncate"
              >
                {s.title}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Upgrade */}
      {!collapsed && (
        <div className="border-t border-cosmic-border p-3">
          <Link
            href="/pricing"
            className="flex items-center gap-2 px-3 py-2 rounded-xl bg-brand/[0.06] border border-brand/10 text-brand text-sm font-medium hover:bg-brand/[0.10] transition-all"
          >
            <Zap className="w-4 h-4" /> Upgrade to Pro
          </Link>
        </div>
      )}

      {/* User */}
      <div className={cn("border-t border-cosmic-border p-3", collapsed && "flex justify-center")}>
        <div className={cn("flex items-center gap-3", collapsed && "flex-col")}>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-brand to-accent-violet flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {user?.name?.[0] || "U"}
          </div>
          {!collapsed && (
            <>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-text-primary truncate">{user?.name || "User"}</div>
                <div className="text-xs text-text-tertiary truncate">{user?.email || "user@betty.ai"}</div>
              </div>
              <button onClick={logout} className="p-1.5 rounded-lg text-text-tertiary hover:text-destructive hover:bg-destructive/5 transition-colors">
                <LogOut className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>
    </motion.aside>
  );
}

/* ═══════════════════════════════════════════════════════
   Dashboard Topbar — AURORA 亮色
   ═══════════════════════════════════════════════════════ */

function DashboardTopbar({ onMenuClick }: { onMenuClick: () => void }) {
  const { setOpen: setCmdKOpen } = useCmdKStore();
  return (
    <header className="h-16 border-b border-cosmic-border bg-cosmic-surface/90 backdrop-blur-xl flex items-center gap-4 px-4 md:px-6 sticky top-0 z-20">
      {/* Mobile menu button */}
      <button onClick={onMenuClick} className="md:hidden p-2 -ml-1 rounded-lg text-text-secondary hover:bg-cosmic-subtle">
        <PanelLeft className="w-5 h-5" />
      </button>
      <div className="flex-1 max-w-md">
        <button
          onClick={() => setCmdKOpen(true)}
          className="relative w-full text-left group"
        >
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary group-hover:text-text-secondary transition-colors" />
          <span className="block w-full h-10 pl-10 pr-16 rounded-xl bg-cosmic-subtle border border-cosmic-border text-sm text-text-tertiary group-hover:border-brand/30 group-hover:bg-cosmic-surface transition-all flex items-center">
            Search tools, assets, or prompts...
          </span>
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-cosmic-surface border border-cosmic-border text-[10px] font-mono text-text-tertiary">⌘K</kbd>
        </button>
      </div>

      <div className="flex items-center gap-3">
        <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle transition-colors">
          <Globe className="w-3.5 h-3.5" /> US
        </button>
        <button className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle transition-colors relative">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-brand" />
        </button>
        <Link
          href="/create/video"
          className="flex items-center gap-2 h-9 px-4 rounded-xl bg-brand text-white text-sm font-semibold hover:bg-brand-strong hover:-translate-y-px shadow-button-glow transition-all"
        >
          <Sparkles className="w-4 h-4" /> Create Now
        </Link>
      </div>
    </header>
  );
}

/* ═══════════════════════════════════════════════════════
   Dashboard Layout
   ═══════════════════════════════════════════════════════ */

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-cosmic-deep text-text-primary overflow-hidden">
      {/* Sidebar — hidden on mobile, toggle overlay */}
      <div className="hidden md:block">
        <DashboardSidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />
      </div>
      <div className="flex-1 flex flex-col overflow-hidden">
        <DashboardTopbar onMenuClick={() => setCollapsed(false)} />
        <main className="flex-1 overflow-y-auto bg-cosmic-subtle/50">{children}</main>
      </div>
    </div>
  );
}
