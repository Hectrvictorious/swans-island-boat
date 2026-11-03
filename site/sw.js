/* Swan's Island Boat — service worker.
   The app shell is cached so the page opens with no signal at the terminal.
   conditions.json and the government weather feeds are network-first with a cached fallback. */
const VERSION = 'boat-20261103T1515';
const SHELL = ['./', './index.html', './manifest.json', './icon-192.png', './icon-512.png', './apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const isShell = url.origin === self.location.origin && SHELL.some(p => url.pathname.endsWith(p.replace('./', '/')) || url.pathname.endsWith('/'));
  const isData = url.pathname.endsWith('conditions.json') || /weather\.gov|tidesandcurrents\.noaa\.gov/.test(url.hostname);
  if (isData) {
    e.respondWith(fetch(req).then(res => { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); return res; }).catch(() => caches.match(req)));
  } else if (isShell || /fonts\.(googleapis|gstatic)\.com/.test(url.hostname)) {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); return res; })));
  }
});
