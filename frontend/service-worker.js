/*
 * Service Worker — Secretária Particular IA
 *
 * Estratégia: cache "app shell" (HTML/CSS/JS/ícones estáticos) para que o
 * app abra rápido e funcione offline na parte de interface. Chamadas à API
 * (dados sensíveis: memórias, tokens, respostas do agente) NUNCA são
 * cacheadas — sempre vão direto à rede, para não deixar dados pessoais
 * gravados em cache local indevidamente.
 */
const CACHE_NAME = "secretaria-particular-shell-v1";

const APP_SHELL = [
  "/index.html",
  "/app.html",
  "/manifest.json",
  "/src/css/tokens.css",
  "/src/css/components.css",
  "/src/css/layout.css",
  "/src/js/api.js",
  "/src/js/auth.js",
  "/src/js/mediaCapture.js",
  "/src/js/chat.js",
  "/src/js/history.js",
  "/src/js/app.js",
  "/src/js/sw-register.js",
  "/public/icons/icon-192.png",
  "/public/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Nunca interceptar/cachear chamadas de API — sempre rede, sempre fresco.
  if (url.pathname.startsWith("/api") || event.request.method !== "GET") {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).catch(() => cached);
    })
  );
});
