// The service worker: what makes the installed app work with no signal, next
// to the game. Not bundled; vite.config.js copies it to dist/sw.js after the
// build, with two constants written above this file:
//
//   VERSION   a hash of everything in PRECACHE, so any change to the page or
//             the data makes a new worker, and the page offers a reload
//   PRECACHE  the app shell: index.html, the hashed bundle, data.json, the
//             fonts and the icons, as paths relative to this file
//
// Strategies:
//   the app shell and hashed assets   cache-first, from this version's cache
//   data.json                         stale-while-revalidate
//   md/, pdf/, img/, llms*.txt        network-first, kept on demand, capped
//   a page load (navigation)          the cached index.html: the router is
//                                     the #fragment, so it is the only page
//
// A new worker waits until the page says to take over (the "reload" toast in
// site/src/components/UpdateToast.svelte), so a session is never switched to
// new code underneath it.

/* global VERSION, PRECACHE */

const SHELL = `nmsii-shell-${VERSION}`;
const DATA = "nmsii-data"; // data.json, kept across versions
const DOCS = "nmsii-docs"; // markdown, images and the rest, on demand
const PDF = "nmsii-pdf"; // the cheat sheets, a few hundred KB each
const KEEP = new Set([SHELL, DATA, DOCS, PDF]);
const CAPS = { [DOCS]: 150, [PDF]: 4 };

const scope = new URL(self.registration.scope);
const rel = (url) => (url.pathname.startsWith(scope.pathname) ? url.pathname.slice(scope.pathname.length) : null);
const PRECACHED = new Set(PRECACHE);

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const shell = await caches.open(SHELL);
    // Past the HTTP cache: Pages serves everything with max-age=600, and a
    // stale index.html would point at bundles this version does not have.
    await shell.addAll(PRECACHE.filter((p) => p !== "data.json").map((p) => new Request(p, { cache: "reload" })));
    const data = await fetch("data.json", { cache: "reload" });
    if (!data.ok) throw new Error(`data.json: ${data.status}`);
    await (await caches.open(DATA)).put("data.json", data);
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) {
      if (name.startsWith("nmsii-") && !KEEP.has(name)) await caches.delete(name);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("message", (event) => {
  if (event.data?.type === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== scope.origin) return;
  const path = rel(url);
  if (path === null) return;

  if (request.mode === "navigate" && (path === "" || path === "index.html")) {
    event.respondWith(shellFirst("index.html", request));
  } else if (path === "data.json") {
    event.respondWith(staleWhileRevalidate(event, request));
  } else if (PRECACHED.has(path)) {
    event.respondWith(shellFirst(path, request));
  } else if (path.startsWith("pdf/")) {
    event.respondWith(networkFirst(event, request, PDF));
  } else {
    // md/, img/, llms.txt, and a navigation to anything else: the network
    // when there is one, the copy from last time when not, and the app as
    // the last resort for a page it has never seen.
    event.respondWith(networkFirst(event, request, DOCS, request.mode === "navigate"));
  }
});

async function shellFirst(path, request) {
  const hit = await caches.match(path, { cacheName: SHELL });
  return hit ?? fetch(request);
}

async function staleWhileRevalidate(event, request) {
  const cache = await caches.open(DATA);
  const hit = await cache.match("data.json");
  // no-cache: revalidated against Pages by ETag, so an unchanged file is a 304.
  const fresh = fetch(request, { cache: "no-cache" }).then(async (res) => {
    if (res.ok) await cache.put("data.json", res.clone());
    return res;
  });
  if (!hit) return fresh;
  event.waitUntil(fresh.catch(() => {}));
  return hit;
}

async function networkFirst(event, request, name, navigation = false) {
  const cache = await caches.open(name);
  try {
    const res = await fetch(request);
    if (res.ok) event.waitUntil(cache.put(request, res.clone()).then(() => trim(cache, CAPS[name])));
    return res;
  } catch (exc) {
    const hit = (await cache.match(request)) ?? (navigation ? await caches.match("index.html", { cacheName: SHELL }) : null);
    if (hit) return hit;
    throw exc;
  }
}

// Oldest first: a cache lists its keys in the order they were added.
async function trim(cache, max) {
  const keys = await cache.keys();
  for (const key of keys.slice(0, Math.max(0, keys.length - max))) await cache.delete(key);
}
