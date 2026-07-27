"use client";

import { useEffect } from "react";

/** Registers the PWA service worker once on the client. Safe in dev — the SW
 *  never caches /_next chunks, so HMR is unaffected. */
export function PWARegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    const onLoad = () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    };
    if (document.readyState === "complete") onLoad();
    else window.addEventListener("load", onLoad);
    return () => window.removeEventListener("load", onLoad);
  }, []);
  return null;
}
