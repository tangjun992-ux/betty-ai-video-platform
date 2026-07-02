"use client";

import { type ReactNode } from "react";
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
  const { sidebarCollapsed } = useUIStore();

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
