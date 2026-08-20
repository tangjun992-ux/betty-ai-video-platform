"use client";

import { type ReactNode, useEffect } from "react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/lib/stores";
import { AppSidebar } from "./AppSidebar";
import { TopBar } from "./TopBar";

const STUDIO_RE = /^\/(create|agent|explore|gallery|library|dashboard|tools|sessions|models)(\/|$)/;

export function isStudioPath(pathname: string | null): boolean {
  return STUDIO_RE.test(pathname || "");
}

interface AppShellProps {
  children: ReactNode;
  showTopBar?: boolean;
}

export function AppShell({ children, showTopBar = true }: AppShellProps) {
  const { sidebarCollapsed } = useUIStore();
  const pathname = usePathname();
  const studio = isStudioPath(pathname);

  useEffect(() => {
    document.documentElement.classList.toggle("studio", studio);
    return () => document.documentElement.classList.remove("studio");
  }, [studio]);

  return (
    <div
      data-testid={studio ? "studio-shell" : "marketing-shell"}
      className={cn(
        "flex h-screen bg-cosmic-deep text-text-primary overflow-hidden",
        studio && "studio-shell",
      )}
    >
      <AppSidebar />

      <div
        className={cn(
          "flex-1 flex flex-col min-w-0 overflow-hidden",
          "transition-[margin] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]"
        )}
        style={{
          marginLeft: sidebarCollapsed ? "64px" : "240px",
        }}
      >
        {showTopBar && <TopBar />}
        <main className="flex-1 overflow-y-auto bg-gradient-to-b from-cosmic-deep to-cosmic-subtle/60">
          {children}
        </main>
      </div>
    </div>
  );
}
