// What the player carries, read from the game's own save file by the local
// launcher (tools/launch.py -> tools/nms_save.py, read-only). Served at /api/;
// a plain static host has no such thing, and then `available` stays false.

import { D } from "./data.js";
import { t } from "./i18n.js";
import { local } from "./local.js";

let available = $state(false);
let on = $state(local.get("save-on", true));
let slots = $state.raw([]);
let slot = $state(local.get("save-slot", ""));
let report = $state.raw(null);
let error = $state("");
let loading = $state(false);
let skipped = $state(local.get("save-skip", [])); // container keys left out
let readAt = $state(0);

const slotKey = (s) => `${s.account}/${s.file}`;

async function getJson(url) {
  const res = await fetch(url, { cache: "no-store" });
  const body = await res.json();
  if (!res.ok) throw new Error(body.error || res.statusText);
  return body;
}

// What is read again and found the same is left as it was: a new object, even an equal one, would make every list built
// from it start over (its cursor and scroll back at the top) on each look at the save, every half minute.
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

export async function refresh() {
  loading = true;
  try {
    const seen = await getJson("api/saves");
    if (!same(seen, slots)) slots = seen;
    available = true;
    const pick = slots.find((s) => slotKey(s) === slot) ?? slots[0];
    if (!pick) { error = t("No game saves found."); report = null; return; }
    slot = slotKey(pick);
    const [account, file] = slot.split("/");
    const read = await getJson(`api/save?account=${encodeURIComponent(account)}&file=${encodeURIComponent(file)}`);
    if (!same(read, report)) report = read;
    error = "";
    readAt = Date.now();
  } catch (exc) {
    error = available ? t("Could not read the save: {error}", { error: exc.message }) : "";
    if (!available) report = null;
  } finally {
    loading = false;
  }
}

export function startSave() {
  refresh();
  // The game keeps writing while it is played: look again when the window
  // comes back to the front, and every half minute while it is in view.
  window.addEventListener("focus", () => on && refresh());
  setInterval(() => { if (on && document.visibilityState === "visible") refresh(); }, 30000);
}

export const gamesave = {
  get available() { return available; },
  get on() { return on; },
  set on(v) { on = v; local.set("save-on", v); if (v) refresh(); },
  get slots() { return slots; },
  get slot() { return slot; },
  set slot(v) { slot = v; local.set("save-slot", v); refresh(); },
  slotKey,
  get report() { return report; },
  get error() { return error; },
  get loading() { return loading; },
  get readAt() { return readAt; },
  get active() { return available && on && report !== null; },
  get skipped() { return skipped; },
  toggle(key) {
    skipped = skipped.includes(key) ? skipped.filter((k) => k !== key) : [...skipped, key];
    local.set("save-skip", skipped);
  },
  // Every place counted again (true), or every place left out (false).
  setAll(counted) {
    skipped = counted ? [] : (report?.containers ?? []).map((c) => c.key);
    local.set("save-skip", skipped);
  },
  // {item id: count} over the containers not left out, known items only.
  get totals() {
    const out = {};
    for (const c of report?.containers ?? []) {
      if (skipped.includes(c.key)) continue;
      for (const [id, n] of Object.entries(c.items)) {
        if (D?.items[id]) out[id] = (out[id] || 0) + n;
      }
    }
    return out;
  },
};
