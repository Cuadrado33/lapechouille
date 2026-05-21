// Service Worker — Carnet Surfcasting PWA
// Cache les ressources statiques pour un démarrage rapide

const CACHE_NAME = 'surfcasting-v1';
const OFFLINE_URL = '/offline.html';

// Ressources à mettre en cache au premier chargement
const PRECACHE = [
  '/',
  OFFLINE_URL,
];

// ── Installation ──────────────────────────────────────────────────
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE).catch(() => {
        // Silencieux si certains assets ne sont pas disponibles
      });
    })
  );
  self.skipWaiting();
});

// ── Activation ───────────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_NAME)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// ── Fetch : réseau d'abord, cache en fallback ─────────────────────
self.addEventListener('fetch', (event) => {
  // Ignorer les requêtes non-GET et les WS Streamlit
  if (event.request.method !== 'GET') return;
  if (event.request.url.includes('/_stcore/')) return;
  if (event.request.url.includes('/stream')) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Mettre en cache les ressources statiques réussies
        if (response.ok && event.request.url.match(/\.(css|js|png|svg|ico|woff2?)$/)) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return response;
      })
      .catch(() => {
        // Hors ligne : retourner le cache ou la page offline
        return caches.match(event.request).then(
          (cached) => cached || caches.match(OFFLINE_URL)
        );
      })
  );
});
