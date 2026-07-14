"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { installAuthFetch } from "@/lib/api";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useAuthStore, useCreationStore, useUIStore } from "@/lib/stores";
import { ToastContainer } from "@/components/Toast";
import { ThemeProvider } from "@/components/ThemeProvider";
import { PageTransition } from "@/components/PageTransition";
import { ScrollProgress } from "@/components/ScrollProgress";
import { CommandPalette } from "@/components/CommandPalette";
import { CookieConsent } from "@/components/CookieConsent";
import { PWARegister } from "@/components/PWARegister";
import { FirstWorkOnboarding } from "@/components/FirstWorkOnboarding";
import { LocaleProvider } from "@/i18n/LocaleProvider";
import { AppShell } from "@/components/AppShell";
import { DemoModeBanner } from "@/components/DemoModeBanner";

if (typeof window !== "undefined") {
  installAuthFetch();
}

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
  const userId = useAuthStore((s) => s.user?.id);
  const resetCreation = useCreationStore((s) => s.resetCreation);

  // Attach the bearer token to all API requests so data is scoped to the
  // logged-in user (guest falls back to the shared account server-side).
  useEffect(() => {
    import("@/lib/api").then((m) => m.installAuthFetch()).catch(() => {});
  }, []);

  // creation-store is browser-local and was previously shared across accounts.
  // Clear its ephemeral results/prompts whenever the effective account changes;
  // durable creations remain available in the server-scoped Library.
  useEffect(() => {
    const scope = userId ? `user:${userId}` : "guest";
    const previous = localStorage.getItem("betty-account-scope");
    if (previous !== scope) {
      resetCreation();
      localStorage.setItem("betty-account-scope", scope);
    }
  }, [userId, resetCreation]);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <LocaleProvider>
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
                <DemoModeBanner />
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
            {/* Logged-in users with no completed work get a guided first win. */}
            {!isAuth && <FirstWorkOnboarding />}
          </SidebarWidthHandler>
        </TooltipProvider>
        </LocaleProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
