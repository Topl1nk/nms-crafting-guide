// Browser storage can be missing (private windows, blocked site data); the
// page has to work without it, it just forgets.
//
// Keys and values are the ones the hand-written page used -- `nms-items:` and
// JSON -- so a visitor's inventory, saved addresses and theme carry over.
// The theme key is also read by the inline script in index.html.

export const PREFIX = "nms-items:";

export const local = {
  get(key, fallback) {
    try {
      const raw = localStorage.getItem(`${PREFIX}${key}`);
      return raw === null ? fallback : JSON.parse(raw);
    } catch { return fallback; }
  },
  set(key, value) {
    try { localStorage.setItem(`${PREFIX}${key}`, JSON.stringify(value)); } catch { /* forget */ }
  },
};
