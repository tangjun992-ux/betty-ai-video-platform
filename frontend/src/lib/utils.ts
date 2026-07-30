import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date) {
  // Locale-aware: follow the active UI language (set on <html lang> by the
  // LocaleProvider) instead of always formatting as zh-CN.
  let bcp47 = "zh-CN";
  if (typeof document !== "undefined") {
    const lang = document.documentElement.lang || "zh-CN";
    bcp47 = lang.startsWith("en") ? "en-US" : "zh-CN";
  }
  return new Intl.DateTimeFormat(bcp47, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));
}

export function formatCredits(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n);
}

export function truncate(str: string, len: number) {
  return str.length > len ? str.slice(0, len) + "…" : str;
}
