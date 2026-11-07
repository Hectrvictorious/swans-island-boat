/* Swan's Island Boat — service worker.
   The app shell is cached so the page opens with no signal at the terminal. Every published build changes
   BUILD, so the phone notices a new version the next time the app is opened (or comes back to the screen),
   caches it fresh, takes over, and tells open pages. A page reloads only if its own build is different, at most
   twice in two minutes; pages from before this existed don't answer, so those get reloaded from here once.
   Nothing ever needs reinstalling.
   conditions.json, data/sync.json and the government weather feeds are network-first with a cached fallback. */
const BUILD = '20261107T2103';
const VERSION = 'boat-' + BUILD;
const SHELL = ['./', './index.html', './manifest.json', './icon-192.png', './icon-512.png', './apple-touch-icon.png'];
let isUpdate = false;
const acked = new Set();

self.addEventListener('install', e => {
  e.waitUntil((async () => {
    const had = await caches.has(VERSION);           // same build installed again: nothing new to announce
    isUpdate = !!self.registration.active && !had;
    const c = await caches.open(VERSION);
    const complete = had && (await Promise.all(SHELL.map(u => c.match(u)))).every(Boolean);
    if (!complete) {
      // ?v= makes the CDN hand over this build's files, never a copy it cached before the deploy
      await Promise.all(SHELL.map(u => fetch(new Request(u + '?v=' + BUILD, { cache: 'reload' })).then(res => {
        if (!res.ok) throw new Error(u + ' ' + res.status);
        return c.put(u, res);
      })));
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k)));
    await self.clients.claim();
  })().then(() => { if (isUpdate) setTimeout(nudge, 50); }));   // after activation: a reload can't be served while still activating
});

// Tell open pages there's a new version. Pages from this version on answer, and reload themselves only if their
// build differs; older pages don't know the message, so after a short wait they're reloaded from here.
async function nudge() {
  isUpdate = false;
  const wins = await self.clients.matchAll({ type: 'window' });
  wins.forEach(c => { try { c.postMessage({ type: 'boat-updated', version: VERSION }); } catch (err) {} });
  setTimeout(() => { wins.forEach(c => { if (!acked.has(c.id) && 'navigate' in c) c.navigate(c.url).catch(() => {}); }); }, 2500);
}

self.addEventListener('message', e => {
  const d = e.data || {};
  if (d.type === 'boat-ack' && e.source) acked.add(e.source.id);
  if (d.type === 'boat-hello' && e.source) { try { e.source.postMessage({ type: 'boat-version', version: VERSION }); } catch (err) {} }
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const same = url.origin === self.location.origin;
  const isData = (same && /\/(conditions|data\/sync)\.json$/.test(url.pathname)) || /weather\.gov|tidesandcurrents\.noaa\.gov/.test(url.hostname);
  const isShell = same && (req.mode === 'navigate' || SHELL.some(p => p !== './' && url.pathname.endsWith(p.slice(1))));
  if (isData) {
    e.respondWith(fetch(req).then(res => { if (res.ok) { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); } return res; }).catch(() => caches.match(req)));
  } else if (isShell) {
    const key = req.mode === 'navigate' ? './' : req;
    e.respondWith(caches.match(key, { ignoreSearch: true }).then(hit => hit || fetch(req).then(res => { if (res.ok && req.mode !== 'navigate') { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); } return res; })).catch(() => caches.match('./')));
  } else if (/fonts\.(googleapis|gstatic)\.com/.test(url.hostname)) {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); return res; })));
  }
});
