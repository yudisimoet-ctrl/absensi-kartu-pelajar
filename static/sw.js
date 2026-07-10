// Service Worker — cache kartu & aset supaya bisa buka offline
const CACHE = 'absensi-v2';
const ASSETS = ['/', '/scanner', '/admin', '/static/manifest.webmanifest'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  // kartu & qr/barcode: cache-first (offline friendly)
  if (url.pathname.startsWith('/kartu/') || url.pathname.startsWith('/api/qr/') || url.pathname.startsWith('/api/barcode/')) {
    e.respondWith(
      caches.open(CACHE).then(async c => {
        const cached = await c.match(e.request);
        const fetchP = fetch(e.request).then(res => { c.put(e.request, res.clone()); return res; })
          .catch(() => cached);
        return cached || fetchP;
      })
    );
    return;
  }
  // lainnya: network-first
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});
