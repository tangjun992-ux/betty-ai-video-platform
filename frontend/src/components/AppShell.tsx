"use client";

import { type ReactNode, useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/stores";
import { AppSidebar } from "./AppSidebar";
import { TopBar } from "./TopBar";

/* ═══════════════════════════════════════════════════════
   AppShell — STUDIO v5 深色创作台
   桌面: 左侧 AppSidebar + 右侧 (TopBar + main)
   移动: 抽屉式侧栏 + 遮罩, 内容全宽
   (--sidebar-width 由 ClientLayout 根据 collapsed 状态注入)
   ═══════════════════════════════════════════════════════ */

interface AppShellProps {
  children: ReactNode;
  showTopBar?: boolean;
}

export function AppShell({ children, showTopBar = true }: AppShellProps) {
  const { sidebarCollapsed, setSidebarCollapsed, sidebarOpen, setSidebarOpen } = useUIStore();
  const pathname = usePathname();
  const autoCollapsed = useRef(false);

  // Focus routes (creation / agent) collapse the global nav to an icon rail so
  // the contextual panels get maximum room (对标 Yapper/Krea 的创作视图)。
  // We only auto-toggle what we set ourselves, preserving manual preference.
  useEffect(() => {
    const isFocus = /^\/(create|agent)(\/|$)/.test(pathname || "");
    if (isFocus && !sidebarCollapsed) {
      setSidebarCollapsed(true);
      autoCollapsed.current = true;
    } else if (!isFocus && autoCollapsed.current) {
      setSidebarCollapsed(false);
      autoCollapsed.current = false;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  // 路由变化时关闭移动端抽屉
  useEffect(() => {
    setSidebarOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  return (
    <div className="flex h-screen bg-cosmic-deep text-text-primary overflow-hidden">
      {/* ── Left: AppSidebar (移动端为抽屉) ── */}
      <AppSidebar />

      {/* ── Mobile overlay ── */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-[2px] md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden
        />
      )}

      {/* ── Right: TopBar + main content area ── */}
      <div
        className={cn(
          "flex-1 flex flex-col min-w-0 overflow-hidden",
          "ml-0 md:ml-[var(--sidebar-width)] transition-[margin] duration-300"
        )}
      >
        {/* ── TopBar (optional) ── */}
        {showTopBar && <TopBar />}

        {/* ── Main content ── */}
        <main className="flex-1 overflow-y-auto bg-cosmic-deep">
          {children}
        </main>
      </div>
    </div>
  );
}
