// lib/data.js retext(): the game's texts in another language and back.
import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const LIB = join(import.meta.dirname, "..", "..", "site", "src", "lib");
const item = (name, extra = {}) => ({ name, sub: `sub ${name}`, cat: "", value: 1, store: 0, ...extra });
const bundle = {
  source: null,
  items: {
    IRON: item("Железо"),
    PLATE: item("Пластина"),
    PIE: item("Пирог", { effect: "Дальность бега", effect_id: "Suit_Stamina_Strength", potency: 0.5 }),
  },
  ease: {},
  recipes: [{ domain: "refine", op: "Очистка", out: ["PLATE", 2], in: [["IRON", 3]], time: 10, machine: "m", ratio: 2, loop: 0, profit: 0, rate: 0 }],
  cooking: [{ effect: "Дальность бега", id: "Suit_Stamina_Strength", use: "crossing ground on foot", dishes: [] }],
  storage: { homes: [], outcomes: [] },
};
globalThis.fetch = async () => ({ ok: true, json: async () => structuredClone(bundle) });
const data = await import(pathToFileURL(join(LIB, "data.js")));
await data.load();

const german = {
  items: { IRON: ["Eisen", "Metall", "d"], PLATE: ["Platte", "", "d"], PIE: ["Kuchen", "Essen", "d"] },
  ops: { "Очистка": "Raffinieren" },
  fx: { Suit_Stamina_Strength: "Sprintdistanz" },
};

test("loading shows the built language, and keeps the buff use in English for lib/language.svelte.js to word", () => {
  assert.equal(data.D.items.IRON.name, "Железо");
  assert.equal(data.D.cooking[0].use, "crossing ground on foot");
  assert.deepEqual(data.ENGLISH.use, ["crossing ground on foot"]);
  assert.equal(data.PACK, null);
});

test("a language changes names, subtitles, operations and buffs, and rebuilds the lookups", () => {
  data.retext(german);
  assert.equal(data.D.items.IRON.name, "Eisen");
  assert.equal(data.D.items.IRON.sub, "Metall");
  assert.equal(data.D.items.PIE.effect, "Sprintdistanz");
  assert.equal(data.D.cooking[0].effect, "Sprintdistanz");
  assert.equal(data.D.recipes[0].op, "Raffinieren");
  assert.equal(data.RECIPES[0].outName, "Platte");
  assert.equal(data.RECIPES[0].inputs, "3 Eisen");
  assert.ok(data.RECIPES[0].key.includes("raffinieren"));
  assert.deepEqual(data.ITEM_NAMES, ["Eisen", "Kuchen", "Platte"]);
  assert.equal(data.PRODUCED.PLATE.length, 1);
  assert.equal(data.CONSUMED.IRON.length, 1);
  assert.equal(data.PACK, german);
});

test("a missing text keeps the built one (an empty subtitle in the pack does not blank it)", () => {
  assert.equal(data.D.items.PLATE.sub, "sub Пластина");
  data.retext({ items: { IRON: ["Eisen"] }, ops: {}, fx: {} });
  assert.equal(data.D.items.PLATE.name, "Пластина");
  assert.equal(data.D.recipes[0].op, "Очистка");
  assert.equal(data.D.items.PIE.effect, "Дальность бега");
});

test("null goes back to the built language, repeatably", () => {
  data.retext(german);
  data.retext(null);
  assert.equal(data.D.items.IRON.name, "Железо");
  assert.equal(data.D.recipes[0].op, "Очистка");
  assert.equal(data.D.cooking[0].effect, "Дальность бега");
  assert.deepEqual(data.ITEM_NAMES, ["Железо", "Пирог", "Пластина"]);
  assert.equal(Object.keys(data.PRODUCED).length, 1); // rebuilt, not appended to
  assert.equal(data.PRODUCED.PLATE.length, 1);
});
