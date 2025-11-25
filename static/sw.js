self.addEventListener('install', e => {
    e.waitUntil(
        caches.open('novafrost-v1').then(cache => {
            return cache.addAll([
                '/',
                '/static/',
                '/dashboard',
                '/dashboard_tecnico'
            ]);
        })
    );
});

self.addEventListener('fetch', e => {
    e.respondWith(
        caches.match(e.request).then(response => {
            return response || fetch(e.request);
        })
    );
});