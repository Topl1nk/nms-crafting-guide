// data.json, and the lookups every view makes over it.
//
// The bundle is fetched once at start-up (it is not built into the JS: the
// Pages workflow regenerates it from the Python on every deploy). App.svelte
// awaits load() before it draws a view, so the views can read `D` and the
// tables below as plain, already-filled objects.

import { multiplierLabel, qtyLabel, timeLabel } from "./core.js";

export let D; // data.json
export let RECIPES = []; // D.recipes with labels and a search key attached
export const PRODUCED = {}; // item id -> recipes that make it
export const CONSUMED = {}; // item id -> recipes that use it
export let ITEM_NAMES = []; // for the "type an item" boxes

export async function load(url = "data.json") {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  D = await res.json();
  prepare();
  return D;
}

export const name = (id) => D.items[id]?.name ?? id;

function prepare() {
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
// frontend edit. Null when the export predates it.
export function gameRelease() {
  const game = D?.source?.game;
  if (!game?.version) return null;
  return {
    name: `${game.update ?? ""} ${game.version}`.trim(),
    build: game.build ?? "",
    extracted: D.source.extracted ?? "",
  };
}

export const galaxyName =(n) => D.portals.galaxies[n - 1] ?? `Galaxy ${n}`;

export const REPO_URL = "https://github.com/rdlu/nms-items-interface";

// The sections, in key order: 1-7 jump to the first seven, ? to Help.
export const NAV = [
  ["recipes", "Recipes"], ["nanites", "Nanites"], ["cooking", "Cooking"],
  ["multitools", "Multi-tools"], ["portals", "Portals"], ["storage", "Storage"],
  ["inventory", "Inventory"], ["help", "Help"],
];
