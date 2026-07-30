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

  // Keep the full labeled sidebar on every route (including creation / agent),
  // matching Yapper — a persistent, navigable nav reads far more professional
  // than an unlabeled icon rail. Users can still collapse it manually.
  return (
    <div className="flex h-screen bg-cosmic-deep text-text-primary overflow-hidden">
      {/* ── Left: AppSidebar ── */}
      <AppSidebar />

      {/* ── Right: TopBar + main content area ── */}
      <div
        className={cn(
          "flex-1 flex flex-col min-w-0 overflow-hidden",
          "transition-[margin] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
        )}
        style={{
          marginLeft: sidebarCollapsed ? "64px" : "240px",
        }}
      >
        {/* ── TopBar (optional) ── */}
        {showTopBar && <TopBar />}

        {/* ── Main content ── subtle top-down gradient for gentle depth ── */}
        <main className="flex-1 overflow-y-auto bg-gradient-to-b from-cosmic-deep to-cosmic-subtle/60">
          {children}
        </main>
      </div>
    </div>
  );
}
