// Cambia esta versión en cada deploy importante (ej: 2025.12.16.1, 2025.12.17.1, etc.)
const CACHE_VERSION = '2025.12.16.1';
const CACHE_NAME = `novafrost-erp-${CACHE_VERSION}`;

// Archivos críticos para offline
const CRITICAL_ASSETS = [
  '/',
  '/login',
  '/dashboard',
  '/static/manifest.json',
  '/static/logo.png',
  '/static/logo192.png',
  '/static/logo512.png',
  '/static/firebase-init.js',
  '/static/push.js',
  '/static/sw.js'  // Cacheamos el propio SW para control total
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
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.filter(name => name !== CACHE_NAME)
                  .map(name => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) {
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        // Siempre intentar red fresca para recursos dinámicos (HTML, JS, CSS)
        if (event.request.destination === 'document' || 
            event.request.destination === 'script' || 
            event.request.destination === 'style') {
          return fetch(event.request).then(networkResponse => {
            if (networkResponse && networkResponse.status === 200) {
              const clone = networkResponse.clone();
              caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
            }
            return networkResponse;
          }).catch(() => cachedResponse || caches.match('/'));
        }

        // Para assets críticos: caché primero, luego red
        if (cachedResponse) {
          // Actualizar en segundo plano
          fetch(event.request).then(networkResponse => {
            if (networkResponse && networkResponse.status === 200) {
              caches.open(CACHE_NAME).then(cache => cache.put(event.request, networkResponse.clone()));
            }
          });
          return cachedResponse;
        }

        // Todo lo demás: red primero, caché después
        return fetch(event.request).then(networkResponse => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return networkResponse;
        }).catch(() => caches.match('/'));
      })
  );
});