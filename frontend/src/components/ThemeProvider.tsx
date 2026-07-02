"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";

type Theme = "light" | "dark";
type ThemeContextValue = {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (t: Theme) => void;
};

const ThemeContext = createContext<ThemeContextValue>({
  theme: "dark",
  toggleTheme: () => {},
  setTheme: () => {},
});

export function useTheme() {
  return useContext(ThemeContext);
}

function getSystemTheme(): Theme {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function getStoredTheme(): Theme | null {
  if (typeof window === "undefined") return null;
  try {
    const stored = localStorage.getItem("betty-theme");
    if (stored === "light" || stored === "dark") return stored;
  } catch {}
  return null;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [mounted, setMounted] = useState(false);

  // On mount, determine initial theme
  useEffect(() => {
    const stored = getStoredTheme();
    const initial = stored ?? getSystemTheme();
    setThemeState(initial);
    setMounted(true);
  }, []);

  // Apply theme class to <html> and persist
  useEffect(() => {
    if (!mounted) return;
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(theme);
    try {
      localStorage.setItem("betty-theme", theme);
    } catch {}
  }, [theme, mounted]);

  // Listen for system preference changes (only if no user override)
  useEffect(() => {
    if (!mounted) return;
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    const handler = (e: MediaQueryListEvent) => {
      const stored = getStoredTheme();
      if (!stored) {
        setThemeState(e.matches ? "light" : "dark");
      }
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [mounted]);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
  }, []);

  const toggleTheme = useCallback(() => {
    setThemeState((prev) => (prev === "dark" ? "light" : "dark"));
  }, []);

  // Prevent flash — render nothing until mounted
  if (!mounted) {
    return <>{children}</>;
  }

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}
