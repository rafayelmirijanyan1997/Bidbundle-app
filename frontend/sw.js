self.addEventListener("install", e => {
  e.waitUntil(
    caches.open("bidbundle-v1").then(cache =>
      cache.addAll(["/", "/static/index.html"])
    )
  );
});

self.addEventListener("fetch", e => {
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});