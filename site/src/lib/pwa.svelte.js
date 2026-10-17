// The site as an installed app: the service worker (site/sw.js, written into
// dist/ by vite.config.js), the browser's install prompt, and whether there is
// a network. Components read `pwa`; main.js calls startPwa() once.
//
// The worker is registered in a build only: `vite dev` serves no sw.js, and a
// worker caching the dev server's modules would only get in the way.

export const pwa = $state({
  // The browser offered to install (beforeinstallprompt) and has not yet.
  canInstall: false,
  // iOS Safari, which installs from Share -> Add to Home Screen and never
  // fires beforeinstallprompt.
  ios: false,
  // Already running as the installed app: no install offers at all.
  standalone: false,
  // A new worker, with a new page or new data, is waiting for a reload.
  update: false,
  offline: false,
});

let deferred = null; // the beforeinstallprompt event, held until a click
let waiting = null; // the worker that takes over on reload

function isIosSafari() {
  const ua = navigator.userAgent;
  // iPadOS reports itself as a Mac; the touch points give it away.
  const ios = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  return ios && /Safari\//.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS|GSA\//.test(ua);
}

export function startPwa() {
  const standalone = matchMedia("(display-mode: standalone)");
  const sync = () => { pwa.standalone = standalone.matches || navigator.standalone === true; };
  sync();
  standalone.addEventListener("change", sync);
  pwa.ios = isIosSafari();

  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault(); // shown by our own button instead of the mini-infobar
    deferred = e;
    pwa.canInstall = true;
  });
  window.addEventListener("appinstalled", () => {
    deferred = null;
    pwa.canInstall = false;
  });

  pwa.offline = !navigator.onLine;
  window.addEventListener("online", () => { pwa.offline = false; });
  window.addEventListener("offline", () => { pwa.offline = true; });

  if (import.meta.env.PROD && "serviceWorker" in navigator) register();
}

async function register() {
  let reg;
  try {
    reg = await navigator.serviceWorker.register("./sw.js");
  } catch {
    return; // a private window, or a browser that refuses: the page still works
  }
  const offer = (worker) => {
    // The first install has nothing to replace, so nothing to offer.
    if (!navigator.serviceWorker.controller) return;
    waiting = worker;
    pwa.update = true;
  };
  if (reg.waiting) offer(reg.waiting);
  reg.addEventListener("updatefound", () => {
    const worker = reg.installing;
    worker?.addEventListener("statechange", () => {
      if (worker.state === "installed") offer(worker);
    });
  });

  // Left open next to the game for hours: look for a new version when the tab
  // comes back, at most every half hour.
  let checked = Date.now();
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible" || Date.now() - checked < 30 * 60e3) return;
    checked = Date.now();
    reg.update().catch(() => {});
  });
}

export async function install() {
  if (!deferred) return;
  const prompt = deferred;
  deferred = null;
  pwa.canInstall = false;
  await prompt.prompt();
}

// Only when asked: the new worker takes over, and the page reloads onto it.
export function applyUpdate() {
  if (!waiting) return;
  navigator.serviceWorker.addEventListener("controllerchange", () => location.reload(), { once: true });
  waiting.postMessage({ type: "SKIP_WAITING" });
}

export function dismissUpdate() {
  pwa.update = false;
}
