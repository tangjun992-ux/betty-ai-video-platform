"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useUIStore } from "@/lib/stores";
import { ToastContainer } from "@/components/Toast";
import { ThemeProvider } from "@/components/ThemeProvider";
import { PageTransition } from "@/components/PageTransition";
import { ScrollProgress } from "@/components/ScrollProgress";
import { CommandPalette } from "@/components/CommandPalette";
import { AppShell } from "@/components/AppShell";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
    },
  },
});

function SidebarWidthHandler({ children }: { children: React.ReactNode }) {
  const { sidebarCollapsed } = useUIStore();

  useEffect(() => {
    const width = sidebarCollapsed ? "64px" : "240px";
    document.documentElement.style.setProperty("--sidebar-width", width);
  }, [sidebarCollapsed]);

  return <>{children}</>;
}

export function ClientLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isDashboard = pathname.startsWith("/dashboard");
  const isAuth = pathname.startsWith("/auth");

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider delayDuration={200}>
          <SidebarWidthHandler>
            {isDashboard ? (
              <>
                <ScrollProgress />
                {children}
                <ToastContainer />
              </>
            ) : isAuth ? (
              <>
                {children}
                <ToastContainer />
              </>
            ) : (
              <AppShell>
                <ScrollProgress />
                <PageTransition>{children}</PageTransition>
                <ToastContainer />
              </AppShell>
            )}

            {/* ⌘K Command Palette — global */}
            <CommandPalette />
          </SidebarWidthHandler>
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
