// Service Worker — Planfin Monitor
// สำคัญ: ทำงานเฉพาะไฟล์ของหน้าใหม่ ไม่แตะ /v1/ (เวอร์ชันเดิม) และไม่แตะคำขอข้ามโดเมน (Google Apps Script ของ v1)
const CACHE_NAME = 'planfin-monitor-v1';
const STATIC_ASSETS = ['./', './index.html', './manifest.webmanifest', './icons/icon-192.png'];
const DATA_URL_PATTERN = /\/data\//i;

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then((c) => c.addAll(STATIC_ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== location.origin) return;           // ข้ามโดเมน -> ปล่อยผ่าน
  if (/\/v1\//.test(url.pathname)) return;              // เวอร์ชันเดิม -> ปล่อยผ่าน
  if (DATA_URL_PATTERN.test(url.pathname) || request.mode === 'navigate') {
    event.respondWith(networkFirst(request, DATA_URL_PATTERN.test(url.pathname)));  // ข้อมูลการเงิน + หน้าหลัก = network-first
  } else {
    event.respondWith(cacheFirst(request));
  }
});
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) { fetch(request).then((r) => { if (r.ok) caches.open(CACHE_NAME).then((c) => c.put(request, r.clone())); }).catch(() => {}); return cached; }
  const res = await fetch(request);
  if (res.ok) (await caches.open(CACHE_NAME)).put(request, res.clone());
  return res;
}
async function networkFirst(request, isData) {
  try {
    const res = await fetch(request);
    if (res.ok) (await caches.open(CACHE_NAME)).put(request, res.clone());
    return res;
  } catch (err) {
    const cached = await caches.match(request, { ignoreSearch: true });
    if (cached) { if (isData) notify({ type: 'data-stale', url: request.url }); return cached; }
    throw err;
  }
}
async function notify(msg) { (await self.clients.matchAll()).forEach((c) => c.postMessage(msg)); }
