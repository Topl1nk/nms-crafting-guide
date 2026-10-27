// data.json, and the lookups every view makes over it.
//
// The bundle is fetched once at start-up (it is not built into the JS: the
// Pages workflow regenerates it from the Python on every deploy). App.svelte
// awaits load() before it draws a view, so the views can read `D` and the
// tables below as plain, already-filled objects.

import { multiplierLabel, qtyLabel, timeLabel } from "./core.js";
import { N_, t } from "./i18n.js";

export let D; // data.json
export let RECIPES = []; // D.recipes with labels and a search key attached
export const PRODUCED = {}; // item id -> recipes that make it
export const CONSUMED = {}; // item id -> recipes that use it
export let ITEM_NAMES = []; // for the "type an item" boxes
export let PACK = null; // the game-language texts in use (lib/language.svelte.js); null: as built

// The texts of the language data.json was built in, kept so any language can be
// switched to, and back, without a reload.
const BASE = { items: {}, ops: [], effects: [] };

// The page's own words data.json carries in English (the storage guide, what each buff is for), as exported:
// lib/language.svelte.js puts them into the chosen language from here.
export const ENGLISH = { storage: null, use: [] };

export async function load(url = "data.json") {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  D = await res.json();
  prepare();
  return D;
}

export const name = (id) => D.items[id]?.name ?? id;

function prepare() {
  ENGLISH.storage = structuredClone(D.storage);
  ENGLISH.use = D.cooking.map((g) => g.use);
  for (const [id, i] of Object.entries(D.items)) BASE.items[id] = { name: i.name, sub: i.sub, effect: i.effect, sym: i.sym };
  BASE.ops = D.recipes.map((r) => r.op);
  BASE.effects = D.cooking.map((g) => g.effect);
  index();
}

/**
 * Show the game's texts in another language: item names and subtitles, what a
 * recipe's operation and a buff are called. `pack` is web/lang/<language>.json;
 * null goes back to the language data.json was built in. Anything a pack lacks
 * keeps its built text, so a half-translated language never shows a blank.
 */
export function retext(pack) {
  PACK = pack;
  for (const [id, item] of Object.entries(D.items)) {
    const was = BASE.items[id];
    const t = pack?.items[id];
    item.name = t?.[0] || was.name;
    item.sub = t?.[1] || was.sub;
    if (was.sym) item.sym = t?.[3] || was.sym;
    if (was.effect) item.effect = pack?.fx[item.effect_id] || was.effect;
  }
  D.recipes.forEach((r, i) => { r.op = pack?.ops[BASE.ops[i]] || BASE.ops[i]; });
  D.cooking.forEach((g, i) => { g.effect = pack?.fx[g.id] || BASE.effects[i]; });
  index();
}

function index() {
  for (const table of [PRODUCED, CONSUMED]) for (const k of Object.keys(table)) delete table[k];
  RECIPES = D.recipes.map((r, index) => {
    const outName = name(r.out[0]);
    const inputs = r.in.map(([id, n]) => qtyLabel(n, name(id))).join(" + ");
    return {
      ...r,
      index,
      outName,
      outLabel: qtyLabel(r.out[1], outName),
      inputs,
      mult: multiplierLabel(r),
      timeLabel: timeLabel(r.time),
      key: `${outName} ${inputs} ${r.op}`.toLowerCase(),
    };
  });
  for (const r of RECIPES) {
    (PRODUCED[r.out[0]] ||= []).push(r);
    for (const [id] of r.in) (CONSUMED[id] ||= []).push(r);
  }
  ITEM_NAMES = Object.values(D.items).map((i) => i.name).sort();
}

// What eating a dish does: {effect, id, potency, use}, or null for anything else.
export function buffOf(id) {
  const item = D.items[id];
  if (!item?.effect_id) return null;
  return { effect: item.effect, id: item.effect_id, potency: item.potency, use: D.cooking.find((g) => g.id === item.effect_id)?.use ?? "" };
}

// The refiner a recipe needs, as a level: 1 portable (one ingredient), 2 medium (two), 3 large (three). 0: not a refiner at all (cooking).
export const refinerLevel = (r) => (r.domain === "refine" ? r.in.length : 0);

export const easeOf = (id) =>
  D.ease[id] ?? { label: "loot (unknown)", band: "hard", score: 25, describe: "", where: "", note: "" };

// The hardest ingredient is what gates a recipe.
export const easeOfRecipe = (r) =>
  r.in.map(([id]) => easeOf(id)).reduce((a, b) => (b.score < a.score ? b : a));

export function placement(id) {
  const item = D.items[id];
  return item ? D.storage.outcomes[item.store] : null;
}

// Which game release the data was read from, as build_web.py exports it from
// data/source.json -- {game: {update, version, build}, extracted, tools}.
// Every mention on the page is built from this, so a game patch needs no
// frontend edit. Null unless data.json's `source` (null when
// data/source.json is missing) says the data was read from the game; the
// NMS-Handbook fallback records no game version.
export function gameRelease() {
  const s = D?.source;
  if (s?.from !== "game" || !s.version) return null;
  return {
    name: [s.game, s.version].filter(Boolean).join(" "),
    build: s.build ? `build ${s.build}` : "",
    extracted: s.extracted ?? "",
  };
}

export const galaxyName = (n) => D.portals.galaxies[n - 1] ?? t("Galaxy {n}", { n });

export const REPO_URL = "https://github.com/Topl1nk/nms-crafting-guide";

// The sections, in key order: 1-7 jump to the first seven, ? to Help. The names are English keys for t().
export const NAV = [
  ["inventory", N_("My items")], ["recipes", N_("Craft")], ["tree", N_("Tree")], ["wiki", N_("Wiki")],
  ["multitools", N_("Multi-tools")], ["portals", N_("Portals")], ["help", N_("Help")],
];
