"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Menu,
  X,
  Home,
  Bot,
  ImageIcon,
  Video,
  FolderOpen,
  Settings,
  LogIn,
  LogOut,
  User,
  Zap,
  ChevronDown,
  Mic,
  LayoutDashboard,
  Sun,
  Moon,
} from "lucide-react";
import { useUIStore, useCreationStore, useAuthStore, useCmdKStore } from "@/lib/stores";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { useTheme } from "@/components/ThemeProvider";

// ─── NAV ITEMS ──────────────────────────────────────────
const mainNav = [
  { href: "/", icon: Home, label: "首页", exact: true },
  { href: "/create/image", icon: ImageIcon, label: "图片创作" },
  { href: "/create/video", icon: Video, label: "视频创作" },
  { href: "/agent", icon: Bot, label: "AI Agent" },
  { href: "/gallery", icon: FolderOpen, label: "内容库" },
];

// 工具下拉(顶部导航的 Tools 菜单)
const toolMenu = [
  { label: "图片编辑器", href: "/create/image?tool=editor" },
  { label: "产品图", href: "/create/image?tool=product" },
  { label: "专业头像", href: "/create/image?tool=avatar" },
  { label: "照片包", href: "/create/image?tool=batch" },
  { label: "图片扩展", href: "/create/image?tool=expand" },
  { label: "去背景", href: "/create/image?tool=removebg" },
  { label: "放大", href: "/create/image?tool=upscale" },
  { label: "唇形同步", href: "/create/lipsync" },
];

const rightNav = [
  { href: "/pricing", label: "定价" },
  { href: "/models", label: "模型" },
];

// 移动端完整导航项
const mobileNav = [
  ...mainNav,
  { href: "/pricing", icon: Zap, label: "定价" },
  { href: "/models", icon: Settings, label: "模型" },
  { href: "/create/lipsync", icon: Mic, label: "唇形同步" },
  { href: "/settings", icon: User, label: "设置" },
];

// ─── SIDEBAR (停用: 已切换为顶部导航) ───────────────────
function Sidebar() {
  return null;
}

// ─── MOBILE DRAWER ──────────────────────────────────────
function MobileSidebar() {
  const { sidebarOpen, setSidebarOpen } = useUIStore();
  const pathname = usePathname();

  return (
    <AnimatePresence>
      {sidebarOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-text-primary/20 backdrop-blur-sm md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
          <motion.div
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", damping: 22, stiffness: 240 }}
            className="fixed left-0 top-0 z-50 h-screen w-72 bg-cosmic-surface border-r border-cosmic-border flex flex-col md:hidden"
          >
            <div className="flex items-center justify-between h-16 px-4 border-b border-cosmic-border">
              <Link href="/" className="flex items-center gap-2" onClick={() => setSidebarOpen(false)}>
                <img src="/brand/logo-icon.png" alt="betty" className="w-8 h-8 rounded-lg object-cover" />
                <span className="font-semibold text-lg tracking-tight">betty</span>
              </Link>
              <button onClick={() => setSidebarOpen(false)} className="p-1.5 rounded-lg text-text-secondary hover:bg-cosmic-subtle">
                <X className="w-5 h-5" />
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
              {mobileNav.map((item) => {
                const Icon = item.icon;
                const active = (item as any).exact ? pathname === item.href : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setSidebarOpen(false)}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors",
                      active
                        ? "bg-brand/[0.10] text-brand font-medium"
                        : "text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle"
                    )}
                  >
                    <Icon className="w-5 h-5" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// ─── TOP NAVBAR (主导航) ────────────────────────────────
function Navbar() {
  const { toggleSidebar } = useUIStore();
  const { setActivePage } = useCreationStore();
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuthStore();
  const { setOpen: setCmdKOpen } = useCmdKStore();
  const router = useRouter();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleLogout = () => { logout(); router.push("/"); };
  const userInitial = user?.name?.charAt(0) || user?.email?.charAt(0) || "U";
  const isActive = (href: string, exact = false) =>
    exact ? pathname === href : pathname.startsWith(href) && href !== "/";

  return (
    <header
      className={cn(
        "fixed top-0 inset-x-0 z-40 h-16 transition-all duration-300",
        scrolled
          ? "bg-cosmic-surface/80 backdrop-blur-xl border-b border-cosmic-border"
          : "bg-cosmic-surface/60 backdrop-blur-md border-b border-transparent"
      )}
    >
      <div className="mx-auto max-w-[1440px] h-full px-4 md:px-6 flex items-center gap-4">
        {/* Mobile menu */}
        <button onClick={toggleSidebar} className="md:hidden p-2 -ml-2 rounded-lg text-text-secondary hover:bg-cosmic-subtle">
          <Menu className="w-5 h-5" />
        </button>

        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <img src="/brand/logo-icon.png" alt="betty" className="w-8 h-8 rounded-lg object-cover" />
          <span className="font-semibold text-lg tracking-[-0.02em] text-text-primary">betty</span>
        </Link>

        {/* Primary nav (desktop) */}
        <nav className="hidden md:flex items-center gap-1 ml-2">
          {mainNav.map((item) => {
            const active = isActive(item.href, item.exact);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => {
                  if (item.label === "图片创作") setActivePage("image");
                  if (item.label === "视频创作") setActivePage("video");
                  if (item.label === "AI Agent") setActivePage("agent");
                }}
                className={cn(
                  "px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                  active
                    ? "text-brand bg-brand/[0.08]"
                    : "text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle"
                )}
              >
                {item.label}
              </Link>
            );
          })}

          {/* Tools dropdown */}
          <div className="relative" onMouseEnter={() => setToolsOpen(true)} onMouseLeave={() => setToolsOpen(false)}>
            <button className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle transition-colors">
              工具 <ChevronDown className="w-3.5 h-3.5" />
            </button>
            <AnimatePresence>
              {toolsOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 6 }}
                  transition={{ duration: 0.15 }}
                  className="absolute left-0 top-full pt-2 w-52"
                >
                  <div className="rounded-xl border border-cosmic-border bg-cosmic-surface shadow-elevation-lg p-1.5">
                    {toolMenu.map((t) => (
                      <Link
                        key={t.label}
                        href={t.href}
                        className="block px-3 py-2 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle transition-colors"
                      >
                        {t.label}
                      </Link>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {rightNav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive(item.href)
                  ? "text-brand bg-brand/[0.08]"
                  : "text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Search (⌘K) */}
        <button
          onClick={() => setCmdKOpen(true)}
          className="hidden lg:flex items-center gap-2 h-9 px-3 rounded-lg border border-cosmic-border bg-cosmic-subtle text-text-tertiary text-sm hover:border-cosmic-border-hover transition-colors w-56"
        >
          <Search className="w-4 h-4 shrink-0" />
          <span className="flex-1 text-left">搜索…</span>
          <kbd className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-cosmic-surface border border-cosmic-border text-[10px] font-mono text-text-tertiary">⌘K</kbd>
        </button>

        {/* Actions */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle transition-colors"
            aria-label="切换主题"
          >
            {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>

          <button className="hidden sm:flex items-center gap-1 px-2.5 py-2 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-cosmic-subtle transition-colors">
            <span>🇨🇳</span><span className="text-xs">CN</span>
          </button>

          <Link
            href="/pricing"
            className="hidden sm:inline-flex items-center gap-1.5 h-9 px-4 rounded-lg bg-brand text-white text-sm font-semibold shadow-button-glow hover:bg-brand-strong hover:-translate-y-px transition-all"
          >
            <Zap className="w-4 h-4" />
            <span>升级</span>
          </Link>

          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="p-1 rounded-lg hover:bg-cosmic-subtle transition-colors">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-brand/[0.12] text-brand text-xs font-semibold">{userInitial}</AvatarFallback>
                  </Avatar>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <DropdownMenuLabel className="text-xs text-text-secondary font-normal">{user.email}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => router.push("/dashboard")}>
                  <LayoutDashboard className="w-4 h-4 mr-2" />仪表盘
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => router.push("/settings")}>
                  <Settings className="w-4 h-4 mr-2" />设置
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-destructive">
                  <LogOut className="w-4 h-4 mr-2" />退出登录
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Link
              href="/auth/login"
              className="inline-flex items-center gap-1.5 h-9 px-4 rounded-lg border border-cosmic-border text-text-primary text-sm font-medium hover:bg-cosmic-subtle hover:border-cosmic-border-hover transition-all"
            >
              <LogIn className="w-4 h-4" />
              <span>登录</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

// ─── EXPORT ─────────────────────────────────────────────
export { Sidebar, MobileSidebar, Navbar };
