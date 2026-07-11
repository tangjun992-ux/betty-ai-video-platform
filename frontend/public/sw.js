/* betty PWA service worker — app-shell offline support.
   Strategy:
   - navigations: network-first, fall back to cached shell / /offline
   - static assets (_next/static, icons, images): cache-first
   - API (/api/v1): always network (never cache dynamic data)
*/
const CACHE = "betty-v1";
const SHELL = ["/", "/offline", "/manifest.webmanifest"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL).catch(() => {})).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);

  // Never cache API or auth traffic.
  if (url.pathname.startsWith("/api/")) return;

  // App navigations: network-first with offline fallback.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(request, copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match(request).then((r) => r || caches.match("/offline")))
    );
    return;
  }

  // Skip Next.js build chunks entirely (keep HMR/versioned assets fresh).
  if (url.pathname.startsWith("/_next/")) return;

  // Static assets (icons/images/fonts): cache-first.
  if (url.origin === self.location.origin &&
      (url.pathname.startsWith("/icons") ||
       /\.(png|jpg|jpeg|webp|svg|gif|ico|woff2?)$/.test(url.pathname))) {
    event.respondWith(
      caches.match(request).then((cached) =>
        cached || fetch(request).then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(request, copy)).catch(() => {});
          return res;
        })
      )
    );
  }
});
