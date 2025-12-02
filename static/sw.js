const CACHE_NAME = 'novafrost-erp-v2025.12';

// Archivos críticos (carga instantánea incluso sin internet)
const CRITICAL_ASSETS = [
  '/',
  '/login',
  '/dashboard',
  '/static/manifest.json',
  '/static/logo.png',
  '/static/logo192.png',
  '/static/logo512.png',
  '/static/firebase-init.js',
  '/static/push.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(CRITICAL_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(names => {
      return Promise.all(
        names.filter(name => name !== CACHE_NAME)
             .map(name => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  // Solo GET y mismo origen
  if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(cached => {
        if (cached) return cached;

        return fetch(event.request)
          .then(response => {
            // No cachear respuestas de error o no básicas
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }

            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
            return response;
          })
          .catch(() => {
            // Offline fallback
            if (event.request.destination === 'document') {
              return caches.match('/');
            }
          });
      })
  );
});