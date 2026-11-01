/**
 * Evidentia AI Service Worker (PWA Offline & Outbox Gateway)
 * Caches application shell, static assets, and intercepts offline navigations.
 */

const CACHE_NAME = 'evidentia-shell-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/favicon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;

  // Never cache API calls in service worker cache (handled strictly by IndexedDB outbox)
  if (request.url.includes('/cases/') || request.url.includes('/auth/') || request.url.includes('/security/')) {
    return;
  }

  // Network-first with cache fallback for static app assets
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response && response.status === 200 && response.type === 'basic') {
          const responseToCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseToCache);
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(request).then((cached) => {
          if (cached) return cached;
          if (request.mode === 'navigate') {
            return caches.match('/index.html');
          }
          return new Response('Offline: Resource unavailable', { status: 503, statusText: 'Offline' });
        });
      })
  );
});

// Periodic or background sync notification
self.addEventListener('sync', (event) => {
  if (event.tag === 'evidentia-outbox-sync') {
    event.waitUntil(
      self.clients.matchAll().then((clients) => {
        clients.forEach((client) => {
          client.postMessage({ type: 'EVIDENTIA_TRIGGER_OUTBOX_SYNC' });
        });
      })
    );
  }
});

