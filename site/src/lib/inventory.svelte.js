// What the visitor carries: {item id: count}. Two sources -- the game's own
// save (lib/gamesave.svelte.js), when the local launcher can read it and the
// switch is on, and otherwise a list typed in by hand under
// `nms-items:inventory`.
//
// Reactive, so the "+ Inventory" button on a recipe updates every count shown,
// and synced from other tabs through the storage event.

import { gamesave } from "./gamesave.svelte.js";
import { local, PREFIX } from "./local.js";

let manual = $state(local.get("inventory", {}));

export const inventory = {
  get items() { return gamesave.active ? gamesave.totals : manual; },
  get manual() { return manual; },
  get fromSave() { return gamesave.active; },
  save(next) {
    manual = next;
    local.set("inventory", next);
  },
  add(id, n = 1) {
    const next = { ...manual, [id]: Math.max(0, (manual[id] || 0) + n) };
    this.save(next);
    return next[id];
  },
};

window.addEventListener("storage", (e) => {
  if (e.key === `${PREFIX}inventory`) manual = local.get("inventory", {});
});
