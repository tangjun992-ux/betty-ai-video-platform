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
import { CookieConsent } from "@/components/CookieConsent";
import { PWARegister } from "@/components/PWARegister";
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
  const isAuth = pathname.startsWith("/auth");

  // Attach the bearer token to all API requests so data is scoped to the
  // logged-in user (guest falls back to the shared account server-side).
  useEffect(() => {
    import("@/lib/api").then((m) => m.installAuthFetch()).catch(() => {});
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider delayDuration={200}>
          <SidebarWidthHandler>
            {isAuth ? (
              <>
                {children}
                <ToastContainer />
              </>
            ) : (
              // Single unified shell for the whole app (dashboard included)
              <AppShell>
                <ScrollProgress />
                <PageTransition>{children}</PageTransition>
                <ToastContainer />
              </AppShell>
            )}

            {/* ⌘K Command Palette — global */}
            <CommandPalette />
            {/* Cookie consent — global */}
            <CookieConsent />
            {/* PWA service worker registration */}
            <PWARegister />
          </SidebarWidthHandler>
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
