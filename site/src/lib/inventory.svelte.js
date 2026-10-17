// What the visitor says they carry: {item id: count} under
// `nms-items:inventory`, the same shape the hand-written page stored.
//
// Reactive, so the "+ Inventory" button on a recipe updates every count shown,
// and synced from other tabs through the storage event.

import { local, PREFIX } from "./local.js";

let items = $state(local.get("inventory", {}));

export const inventory = {
  get items() { return items; },
  save(next) {
    items = next;
    local.set("inventory", next);
  },
  add(id, n = 1) {
    const next = { ...items, [id]: Math.max(0, (items[id] || 0) + n) };
    this.save(next);
    return next[id];
  },
};

window.addEventListener("storage", (e) => {
  if (e.key === `${PREFIX}inventory`) items = local.get("inventory", {});
});
