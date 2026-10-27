// The real Craft table through lib/facets.js: every combination of what a visitor can pick, and every link to an
// item, must leave rows, and the filters that mean nothing for what is on screen must not be on screen.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { data, loadBundle, rng } from "./treelib.mjs";

const LIB = join(import.meta.dirname, "..", "..", "site", "src", "lib");
const { applyFacets, facets } = await import(pathToFileURL(join(LIB, "facets.js")));
const { DEFAULTS, recipeDefs } = await import(pathToFileURL(join(LIB, "recipefacets.js")));
const { PICK_DEFAULTS, pickDefs } = await import(pathToFileURL(join(LIB, "pickfacets.js")));
await loadBundle(JSON.parse(readFileSync(join(import.meta.dirname, "..", "..", "web", "data.json"), "utf8")));
const { D, RECIPES, PRODUCED, CONSUMED } = data;

const optionsOf = (defs, key) => defs.find((d) => d.key === key).options.map(([v]) => v);
const NONE = recipeDefs({});

test("every combination of the Craft filters leaves rows, and what is on screen is what can still be chosen", () => {
  const kinds = optionsOf(NONE, "domain");
  const effects = optionsOf(NONE, "effect");
  const r = rng(2026);
  let states = 0;
  const check = (rows, defs, state, label) => {
    const fx = facets(rows, defs, state);
    const left = applyFacets(rows, defs, fx.effective);
    assert.ok(left.length > 0, `empty table: ${label} ${JSON.stringify(state)}`);
    for (const d of defs) if (!fx.show[d.key]) assert.equal(fx.effective[d.key], d.neutral, `hidden but in force: ${d.key} ${JSON.stringify(state)}`);
    states++;
    return fx;
  };
  for (const domain of kinds) for (const refiner of [0, 1, 2]) for (const source of ["any", "easy", "ok", "nohard"]) for (const owned of ["all", "can", "some"]) for (const loops of [false, true]) {
    check(RECIPES, NONE, { domain, effect: "any", refiner, source, owned, loops }, "grid");
  }
  for (let i = 0; i < 1500; i++) {
    check(RECIPES, NONE, { domain: r.pick(kinds), effect: r.pick(effects), refiner: r.int(3), source: r.pick(["any", "easy", "ok", "nohard"]), owned: r.pick(["all", "can", "some"]), loops: r.chance(0.5) }, "random");
  }
  assert.ok(states > 1500);
});

test("the meaningless filters are not shown: no self-multiplying in cooking, no effect in refining, nothing refined in cooking", () => {
  const show = (state) => facets(RECIPES, NONE, { ...DEFAULTS, ...state }).show;
  const refine = show({ domain: "refine" });
  assert.equal(refine.effect, false, "refining has no effect to pick");
  assert.equal(refine.refiner, true);
  const cook = show({ domain: "cook" });
  assert.equal(cook.loops, false, "no dish multiplies itself");
  assert.equal(cook.refiner, false, "cooking is not done in a refiner");
  assert.equal(cook.effect, true);
  const nan = show({ domain: "nanites" });
  assert.equal(nan.effect, false);
  assert.equal(nan.loops, false);
  // the dish types: no refiner either, and an effect only if the type has dishes
  const dishes = optionsOf(NONE, "domain").filter((v) => String(v).startsWith("type:"));
  assert.ok(dishes.length > 0);
});

test("a stale filter set can never empty a link to an item (every craftable and every used item, both ways)", () => {
  const r = rng(77);
  const stale = () => ({ domain: r.pick(optionsOf(NONE, "domain")), effect: r.pick(optionsOf(NONE, "effect")), refiner: r.int(3), source: r.pick(["any", "easy", "ok", "nohard"]), owned: r.pick(["all", "can", "some"]), loops: r.chance(0.5) });
  const makeable = new Set(RECIPES.filter((x) => x.in.every(([id]) => r.chance(0.6))).map((x) => x.index));
  let links = 0;
  for (const id of Object.keys(D.items)) {
    for (const [role, pool] of [["output", PRODUCED[id]], ["input", CONSUMED[id]]]) {
      if (!pool?.length) continue;
      const defs = recipeDefs({ makeable, held: {} });
      // a link starts from the defaults, with the item's own scope ("all" kinds), as the page does
      const fresh = facets(pool, defs, { ...DEFAULTS, domain: "all" });
      assert.ok(applyFacets(pool, defs, fresh.effective).length > 0, `${id} ${role}`);
      // and even if the page were handed whatever was set last time, the table would not be empty
      const old = facets(pool, defs, stale());
      assert.ok(applyFacets(pool, defs, old.effective).length > 0, `${id} ${role} with stale filters`);
      links++;
    }
  }
  assert.ok(links > 700, `only ${links} links`);
});

test("sorts: the one by strength of effect is only offered when a dish is among the rows", () => {
  const withDish = RECIPES.filter((x) => D.items[x.out[0]]?.potency > 0);
  const without = RECIPES.filter((x) => !(D.items[x.out[0]]?.potency > 0));
  assert.ok(withDish.length > 100 && without.length > 100);
  const has = (rows) => rows.some((x) => (D.items[x.out[0]]?.potency ?? 0) > 0);
  assert.equal(has(withDish), true);
  assert.equal(has(without), false);
});
test("the list of things to break down: no combination of its filters is empty, and the meaningless ones are not shown", () => {
  const ids = Object.keys(PRODUCED).filter((id) => D.items[id]);
  const r = rng(555);
  const makeable = new Set(ids.filter(() => r.chance(0.3)));
  const held = Object.fromEntries(Object.keys(D.items).filter(() => r.chance(0.2)).map((id) => [id, 3]));
  const defs = pickDefs({ makeable, held }, ids);
  const opts = (key) => defs.find((d) => d.key === key).options.map(([v]) => v);
  let n = 0;
  for (let i = 0; i < 2500; i++) {
    const state = Object.fromEntries(Object.keys(PICK_DEFAULTS).map((k) => [k, r.pick(opts(k))]));
    const fx = facets(ids, defs, state);
    assert.ok(applyFacets(ids, defs, fx.effective).length > 0, JSON.stringify(state));
    for (const d of defs) if (!fx.show[d.key]) assert.equal(fx.effective[d.key], d.neutral);
    n++;
  }
  assert.ok(n === 2500);
  // refining has no effect to pick; dishes have no refiner
  const refineOnly = facets(ids, defs, { ...PICK_DEFAULTS, kind: "refine" });
  assert.equal(refineOnly.show.effect, false);
  const cookOnly = facets(ids, defs, { ...PICK_DEFAULTS, kind: "cook" });
  assert.equal(cookOnly.show.refiner, false);
  // and a search narrowed to one thing leaves nothing worth a filter
  const one = facets([ids[0]], defs, PICK_DEFAULTS);
  assert.ok(Object.values(one.show).every((s) => !s));
});