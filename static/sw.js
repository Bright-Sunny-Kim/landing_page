const CACHE_NAME = 'hyean-pwa-v2';
const ASSETS_TO_CACHE = [
  '/',
  '/static/css/style.css',
  '/static/js/main.js',
  '/static/manifest.json',
  '/static/icons/icon-512x512.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // POST 등 GET 이외의 요청 및 Chrome Extension 등 chrome-extension:// scheme 요청 무시
  if (event.request.method !== 'GET' || !event.request.url.startsWith(self.location.origin)) {
    return;
  }

  // Network-First 전략: 온라인 상태에서는 항상 네트워크에서 최신 정보 fetch, 실패 시 캐시 fallback
  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // 정상 응답이고 HTTP 200인 경우 캐시를 갱신
        if (response && response.status === 200 && response.type === 'basic') {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // 네트워크 연결 실패(오프라인) 시 캐시 검색
        return caches.match(event.request);
      })
  );
});

