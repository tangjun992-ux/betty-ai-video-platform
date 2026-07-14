"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { API_BASE } from "@/lib/api";
import {
  PanelLeft,
  Zap,
  LogOut,
  ChevronDown,
  Menu,
  User,
  LogIn,
  Search,
  Sparkles,
  Sun,
  Moon,
  Languages,
  MessageSquare,
} from "lucide-react";
import { useUIStore, useAuthStore, useCmdKStore } from "@/lib/stores";
import { useTheme } from "@/components/ThemeProvider";
import { useLocale } from "@/i18n/LocaleProvider";
import { cn } from "@/lib/utils";
import { BrandMark } from "@/components/BrandLogo";
import { JobsTray } from "@/components/JobsTray";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";

/* ═══════════════════════════════════════════════════════
   TopBar — AURORA 亮色紫色主题
   Lovable 风格顶部栏：sidebar toggle · logo · 积分 · 用户菜单
   ═══════════════════════════════════════════════════════ */

export function TopBar() {
  const { sidebarCollapsed, toggleSidebarCollapsed, setSidebarOpen } = useUIStore();
  const { user, logout } = useAuthStore();
  const { setOpen: setCmdKOpen } = useCmdKStore();
  const { theme, toggleTheme } = useTheme();
  const { t, toggleLocale } = useLocale();
  const router = useRouter();
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  // Real available balance (credits + daily) from the same source the dashboard
  // and pricing use, so the header count is always consistent across the app.
  const [liveCredits, setLiveCredits] = useState<number | null>(null);
  useEffect(() => {
    let active = true;
    const load = () =>
      fetch(`${API_BASE}/billing/summary`)
        .then((r) => (r.ok ? r.json() : null))
        .then((d) => { if (active && d && typeof d.credits === "number") setLiveCredits(d.credits); })
        .catch(() => {});
    load();
    const onFocus = () => load();
    const onCredits = () => load();
    window.addEventListener("focus", onFocus);
    window.addEventListener("betty:credits", onCredits);
    return () => {
      active = false;
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("betty:credits", onCredits);
    };
  }, []);

  const credits = liveCredits ?? user?.credits ?? 0;
  const displayName = user?.name || user?.email?.split("@")[0] || t("top.guest");
  const initial = (displayName[0] ?? "B").toUpperCase();

  function handleLogout() {
    logout();
    setUserMenuOpen(false);
    router.push("/");
    router.refresh();
  }

  return (
    <header
      className={cn(
        "h-16 shrink-0 flex items-center justify-between px-4",
        "bg-cosmic-surface/90 backdrop-blur-md",
        "border-b border-cosmic-border",
        "z-20"
      )}
    >
      {/* ── Left: sidebar toggle + logo ── */}
      <div className="flex items-center gap-3">
        {/* Sidebar toggle */}
        <button
          onClick={toggleSidebarCollapsed}
          className={cn(
            "inline-flex items-center justify-center w-9 h-9 rounded-lg",
            "text-text-tertiary hover:text-text-primary hover:bg-cosmic-subtle",
            "transition-all duration-200"
          )}
          aria-label={sidebarCollapsed ? "展开侧栏" : "收起侧栏"}
        >
          <PanelLeft
            className={cn(
              "w-5 h-5 transition-transform duration-200",
              sidebarCollapsed && "rotate-180"
            )}
          />
        </button>

        {/* Logo + brand */}
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <BrandMark className="w-7 h-7" />
          <span className="font-semibold text-base tracking-[-0.02em] text-text-primary hidden sm:inline">
            betty
          </span>
        </Link>
      </div>

      {/* ── Center: global search (opens ⌘K palette) ── */}
      <div className="flex-1 max-w-md mx-4 hidden md:block">
        <button
          onClick={() => setCmdKOpen(true)}
          className="relative w-full text-left group"
          aria-label="搜索"
        >
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary group-hover:text-text-secondary transition-colors" />
          <span className="block w-full h-9 pl-10 pr-16 rounded-xl bg-cosmic-subtle border border-cosmic-border text-sm text-text-tertiary group-hover:border-brand/30 group-hover:bg-cosmic-surface transition-all flex items-center">
            {t("top.search")}
          </span>
          <kbd className="absolute right-3 top-1/2 -translate-y-1/2 inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-cosmic-surface border border-cosmic-border text-[10px] font-mono text-text-tertiary">⌘K</kbd>
        </button>
      </div>

      {/* ── Right: credits + user ── */}
      <div className="flex items-center gap-3">
        {/* Search (mobile) */}
        <button
          onClick={() => setCmdKOpen(true)}
          className="md:hidden inline-flex items-center justify-center w-9 h-9 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-cosmic-subtle transition-colors"
          aria-label="搜索"
        >
          <Search className="w-5 h-5" />
        </button>

        {/* Sessions — 对标 yapper 顶栏入口 */}
        <Link
          href="/sessions"
          className="hidden lg:inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-medium text-text-secondary hover:text-brand hover:bg-brand/5 transition-all"
        >
          <MessageSquare className="w-3.5 h-3.5" /> {t("nav.sessions")}
        </Link>

        {/* Create Now */}
        <Link
          href="/create/video"
          className="hidden sm:inline-flex items-center gap-1.5 h-8 px-3.5 rounded-lg bg-brand text-white text-xs font-semibold hover:bg-brand-strong hover:-translate-y-px shadow-button-glow transition-all"
        >
          <Sparkles className="w-3.5 h-3.5" /> {t("top.create")}
        </Link>

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="inline-flex items-center justify-center w-9 h-9 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-cosmic-subtle transition-colors"
          aria-label={theme === "dark" ? "切换到亮色" : "切换到暗色"}
          title={theme === "dark" ? "亮色模式" : "暗色模式"}
        >
          {theme === "dark" ? <Sun className="w-[18px] h-[18px]" /> : <Moon className="w-[18px] h-[18px]" />}
        </button>

        <button
          onClick={toggleLocale}
          className="inline-flex h-9 items-center gap-1 rounded-lg px-2 text-xs font-medium text-text-tertiary transition-colors hover:bg-cosmic-subtle hover:text-text-primary"
          aria-label="Switch language"
          title="Switch language"
        >
          <Languages className="h-[17px] w-[17px]" />
          <span className="hidden lg:inline">{t("top.language")}</span>
        </button>

        {/* Jobs Tray */}
        <JobsTray />

        {/* Credits → 积分中心 */}
        <Link
          href="/billing"
          className={cn(
            "hidden sm:inline-flex items-center gap-1.5 h-8 px-3 rounded-full",
            "bg-brand/[0.08] text-brand text-xs font-semibold",
            "hover:bg-brand/[0.14] transition-colors",
            "border border-brand/10"
          )}
          title="积分中心"
        >
          <Zap className="w-3.5 h-3.5" />
          <span>{credits.toLocaleString()}</span>
        </Link>

        {/* User dropdown or login */}
        {user ? (
          <DropdownMenu open={userMenuOpen} onOpenChange={setUserMenuOpen}>
            <DropdownMenuTrigger asChild>
              <button
                className={cn(
                  "flex items-center gap-2 px-2 py-1.5 rounded-lg",
                  "hover:bg-cosmic-subtle transition-colors",
                  "text-text-secondary hover:text-text-primary"
                )}
              >
                <Avatar className="w-7 h-7">
                  <AvatarFallback className="text-[11px] bg-brand/10 text-brand font-semibold">
                    {initial}
                  </AvatarFallback>
                </Avatar>
                <span className="text-sm font-medium hidden sm:inline max-w-[100px] truncate">
                  {displayName}
                </span>
                <ChevronDown className="w-3.5 h-3.5 hidden sm:block" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col gap-0.5">
                  <p className="text-sm font-medium text-text-primary">{displayName}</p>
                  <p className="text-xs text-text-tertiary">{user.email}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/settings" className="cursor-pointer">
                  <User className="w-4 h-4 mr-2" />
                  {t("top.settings")}
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/dashboard" className="cursor-pointer">
                  <Zap className="w-4 h-4 mr-2" />
                  {t("top.dashboard")}
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/billing" className="cursor-pointer">
                  <Zap className="w-4 h-4 mr-2" />
                  {t("top.billing")}
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/developer" className="cursor-pointer">
                  <User className="w-4 h-4 mr-2" />
                  {t("top.developer")}
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={handleLogout}
                className="text-destructive focus:text-destructive cursor-pointer"
              >
                <LogOut className="w-4 h-4 mr-2" />
                {t("top.logout")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Link
            href="/auth/login"
            className={cn(
              "inline-flex items-center gap-1.5 h-8 px-4 rounded-lg",
              "bg-brand text-white text-sm font-medium",
              "hover:bg-brand-strong transition-colors shadow-brand"
            )}
          >
            <LogIn className="w-4 h-4" />
            <span>{t("top.login")}</span>
          </Link>
        )}

        {/* Mobile menu trigger */}
        <button
          onClick={() => setSidebarOpen(true)}
          className="md:hidden inline-flex items-center justify-center w-9 h-9 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-cosmic-subtle transition-colors"
          aria-label="菜单"
        >
          <Menu className="w-5 h-5" />
        </button>
      </div>
    </header>
  );
}

export default TopBar;
