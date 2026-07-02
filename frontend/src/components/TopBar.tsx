"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { motion } from "framer-motion";
import {
  PanelLeft,
  Zap,
  LogOut,
  ChevronDown,
  Menu,
  User,
  LogIn,
} from "lucide-react";
import { useUIStore, useAuthStore } from "@/lib/stores";
import { cn } from "@/lib/utils";
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
  const router = useRouter();
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const credits = user?.credits ?? 0;
  const displayName = user?.name || user?.email?.split("@")[0] || "访客";
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
          <img
            src="/brand/logo-icon.png"
            alt="betty"
            className="w-7 h-7 rounded-lg object-cover"
          />
          <span className="font-semibold text-base tracking-[-0.02em] text-text-primary hidden sm:inline">
            betty
          </span>
        </Link>
      </div>

      {/* ── Right: credits + user ── */}
      <div className="flex items-center gap-3">
        {/* Jobs Tray */}
        <JobsTray />

        {/* Credits */}
        <Link
          href="/pricing"
          className={cn(
            "hidden sm:inline-flex items-center gap-1.5 h-8 px-3 rounded-full",
            "bg-brand/[0.08] text-brand text-xs font-semibold",
            "hover:bg-brand/[0.14] transition-colors",
            "border border-brand/10"
          )}
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
                  设置
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/dashboard" className="cursor-pointer">
                  <Zap className="w-4 h-4 mr-2" />
                  控制台
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={handleLogout}
                className="text-destructive focus:text-destructive cursor-pointer"
              >
                <LogOut className="w-4 h-4 mr-2" />
                退出登录
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
            <span>登录</span>
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
