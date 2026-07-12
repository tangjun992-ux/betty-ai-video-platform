"use client";

import { type ReactNode, useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/stores";
import { AppSidebar } from "./AppSidebar";
import { TopBar } from "./TopBar";

/* ═══════════════════════════════════════════════════════
   AppShell — AURORA 亮色主题
   左侧 AppSidebar + 右侧 (TopBar + main content)
   ═══════════════════════════════════════════════════════ */

interface AppShellProps {
  children: ReactNode;
  showTopBar?: boolean;
}

export function AppShell({ children, showTopBar = true }: AppShellProps) {
  const { sidebarCollapsed, setSidebarCollapsed } = useUIStore();
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

  return (
    <div className="flex h-screen bg-cosmic-deep text-text-primary overflow-hidden">
      {/* ── Left: AppSidebar ── */}
      <AppSidebar />

      {/* ── Right: TopBar + main content area ── */}
      <div
        className={cn(
          "flex-1 flex flex-col min-w-0 overflow-hidden",
          "transition-all duration-300"
        )}
        style={{
          marginLeft: sidebarCollapsed ? "64px" : "220px",
        }}
      >
        {/* ── TopBar (optional) ── */}
        {showTopBar && <TopBar />}

        {/* ── Main content ── */}
        <main className="flex-1 overflow-y-auto bg-cosmic-subtle/50">
          {children}
        </main>
      </div>
    </div>
  );
}
