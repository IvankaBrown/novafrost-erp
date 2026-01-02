const CACHE_VERSION = '2026.01.01.1'; // Actualizado a 2026
const CACHE_NAME = `novafrost-v${CACHE_VERSION}`;

// Solo lo estrictamente necesario para que la app abra sin internet
const ASSETS_TO_CACHE = [
  '/',
  '/static/logo192.png',
  '/static/manifest.json',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css'
];

// 1. INSTALACIÓN: Guarda archivos básicos
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS_TO_CACHE))
  );
  self.skipWaiting();
});

// 2. ACTIVACIÓN: Borra cachés viejos automáticamente
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.map(key => key !== CACHE_NAME ? caches.delete(key) : null)
    ))
  );
  self.clients.claim();
});

// 3. ESTRATEGIA DE CARGA (FETCH)
self.addEventListener('fetch', event => {
  // Ignorar peticiones que no sean GET (como subir videos o POST de GPS)
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request)
      .then(networkResponse => {
        // Si hay internet, servimos y guardamos copia en caché
        if (networkResponse && networkResponse.status === 200) {
          const cacheCopy = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, cacheCopy));
        }
        return networkResponse;
      })
      .catch(() => {
        // SI NO HAY INTERNET: Buscamos en el caché
        return caches.match(event.request).then(cachedResponse => {
          return cachedResponse || caches.match('/');
        });
      })
  );
});