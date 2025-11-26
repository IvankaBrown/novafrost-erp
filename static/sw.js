const CACHE_NAME = 'novafrost-v1';

// Archivos esenciales que siempre quieres en caché (carga instantánea)
const ESSENTIAL_FILES = [
  '/',
  '/static/manifest.json',
  '/static/logo192.png',
  '/static/logo512.png',
  '/static/logo.png',
  '/static/css/bootstrap.min.css',        // si usas alguno local (opcional)
  '/static/js/bootstrap.bundle.min.js',   // si usas alguno local (opcional)
  // CDN se cachean solos gracias a la estrategia cache-first
];

// Instala y precachea lo esencial
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Cacheando archivos esenciales de NovaFrost ERP');
        return cache.addAll(ESSENTIAL_FILES);
      })
      .then(() => self.skipWaiting())
  );
});

// Activa y limpia cachés antiguas
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log('Eliminando caché antigua:', cache);
            return caches.delete(cache);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// ESTRATEGIA PERFECTA: Cache First → Network fallback → Offline fallback
self.addEventListener('fetch', event => {
  // Solo aplica a GET y mismas origin (evita errores con Firebase, etc.)
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request)
      .then(cachedResponse => {
        // Si está en caché → devuelve rapidísimo
        if (cachedResponse) {
          return cachedResponse;
        }

        // Si no → intenta red y guarda en caché para la próxima
        return fetch(event.request)
          .then(networkResponse => {
            if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
              return networkResponse;
            }

            // Clona la respuesta porque se consume una sola vez
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });

            return networkResponse;
          })
          .catch(() => {
            // OFFLINE FALLBACK → página bonita cuando no hay internet
            if (event.request.destination === 'document') {
              return caches.match('/'); // muestra la página principal cacheada
            }
            // Para imágenes, puedes devolver un placeholder (opcional)
            // if (event.request.destination === 'image') {
            //   return caches.match('/static/offline-image.png');
            // }
          });
      })
  );
});