// lib/tree.js over the real exported data (web/data.json): invariants that
// must hold for any item, whatever the game patch changed.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const ROOT = join(import.meta.dirname, "..", "..");
const LIB = join(ROOT, "site", "src", "lib");
const bundle = JSON.parse(readFileSync(join(ROOT, "web", "data.json"), "utf8"));
globalThis.fetch = async () => ({ ok: true, json: async () => bundle });
const data = await import(pathToFileURL(join(LIB, "data.js")));
const { pyramids, plan, finder, pyramidOf } = await import(pathToFileURL(join(LIB, "tree.js")));
const core = await import(pathToFileURL(join(LIB, "core.js")));
await data.load();
// D and RECIPES are reassigned by load(): read them off the module, not a copy.
const { D, RECIPES } = data;

const TARGETS = ["TECHFRAG", "ANTIMATTER", "HYPERFUEL1", "STELLAR2", "MICROCHIP", "FOOD_R_FLOUR", "BLUE2", "AF_METAL"];

for (const id of TARGETS.filter((t) => D.items[t])) {
  test(`${id}: pyramids are sound`, () => {
    const { pyramids: list } = pyramids(id, { cook: true });
    for (const p of list) {
      assert.equal(p.root.id, id);
      assert.ok(p.nodes <= 1200);
      // no item is its own ancestor
      const check = (n, above) => {
        // (an amplifier's own result under it is a bare foundation, not another round)
        assert.ok(!above.has(n.id) || (n.id === id && !n.kids.length), `${n.id} sits above itself in ${id}`);
        const next = new Set(above).add(n.id);
        n.kids.forEach((k) => check(k, next));
      };
      check(p.root, new Set());
      // the foundation is on the lowest floor and in columns of its own
      const leaves = p.all.filter((n) => !n.kids.length && n !== p.root);
      assert.equal(new Set(leaves.map((n) => n.col)).size, leaves.length);
      for (const n of leaves) assert.equal(n.floor, p.height - 1);
      // a node's kids are exactly the inputs of its recipe, in order
      for (const n of p.all.filter((x) => x.kids.length)) {
        assert.deepEqual(n.kids.map((k) => k.id), RECIPES[n.ri].in.map(([i]) => i));
      }
    }
  });

  test(`${id}: running twice makes the top exactly twice as much`, () => {
    for (const p of pyramids(id, { cook: true }).pyramids.slice(0, 20)) {
      if (!p.root.kids.length) continue;
      const one = plan(p, 1);
      const two = plan(p, 2);
      assert.equal(two.info.get(p.root.key).yield, 2 * one.info.get(p.root.key).yield);
      const a = Object.fromEntries(one.total);
      for (const [item, n] of two.total) {
        // whole batches: never less than double minus rounding, never more than double
        assert.ok(n >= a[item], `${item}: ${n} < ${a[item]}`);
        assert.ok(n <= 2 * a[item], `${item}: ${n} > 2 x ${a[item]}`);
      }
    }
  });
}

test("a recipe turning three metals into an item is found among the pyramids", () => {
  // Regression: one item's many recipes once starved this recipe out of the search.
  const three = RECIPES.filter((r) => r.in.length === 3 && r.in.every(([i]) => D.ease[i]?.label === "T0 raw" || D.ease[i]?.label === "T1 raw"));
  assert.ok(three.length > 0);
  let checked = 0;
  for (const r of three.slice(0, 40)) {
    const { pyramids: list } = pyramids(r.out[0], { cook: true });
    assert.ok(list.some((p) => p.root.ri === r.index), `no pyramid for recipe ${r.index} of ${r.out[0]}`);
    checked++;
  }
  assert.ok(checked > 0);
});

// The page says "no recipe" when the only pyramid is the bare item. That must never be said of an item that has a
// recipe: Cadmium (RED2) is only made as Cadmium + Chromatic Metal -> 2 Cadmium, a loop, and was left with no tree.
test("every item with a recipe has a pyramid with something under it", () => {
  const bare = [];
  for (const id of Object.keys(data.PRODUCED)) {
    const { pyramids: list } = pyramids(id, { cook: true, limit: 1 });
    if (!list.length || list.every((p) => p.height === 1)) bare.push(id);
  }
  assert.deepEqual(bare, [], `no tree for: ${bare.join(", ")}`);
});

// Nothing is thrown away: an amplifier beside other recipes is kept, put away under "hidden".
test("a recipe that takes its own result is never lost, beside other recipes either", () => {
  const lost = [];
  for (const [id, rs] of Object.entries(data.PRODUCED)) {
    for (const r of rs.filter((x) => x.in.some(([i]) => i === id))) {
      const f = finder(id, { cook: true });
      f.more(1e9, 1e9);
      const seen = [...f.out, ...f.hidden].some((p) => p.choices.get(id) === r.index);
      if (!seen && !f.capped && !f.cappedDetours && f.hiddenMore === 0) lost.push(`${id}: ${r.inputs}`);
    }
  }
  assert.deepEqual(lost, []);
});

test("an amplifier (Cadmium + Chromatic Metal -> 2 Cadmium) is drawn on top of the Cadmium it takes", () => {
  const { pyramids: list } = pyramids("RED2", { cook: true });
  assert.ok(list.length >= 1);
  for (const p of list) {
  assert.deepEqual(p.root.kids.map((k) => k.id), RECIPES[p.root.ri].in.map(([i]) => i));
  assert.ok(p.root.kids.filter((k) => k.id === "RED2").every((k) => !k.kids.length), "the Cadmium it takes is a foundation, not another round");
  assert.ok(p.leaves.has("RED2"));
  }
});

// The short path (#/chain/ITEM) is drawn as a pyramid, like the Tree's: the pyramid is the path, step for step.
test("the short path of every craftable item is a pyramid of the same recipes", () => {
  const stepsOf = (s, out = new Map()) => { if (s.recipe !== undefined) { out.set(s.id, s.recipe); s.children.forEach((c) => stepsOf(c, out)); } return out; };
  let checked = 0;
  for (const id of Object.keys(data.PRODUCED)) {
    for (const tier of D.tiers) {
      const path = core.plan(D.recipes, tier.via.all, new Set(tier.sources), id, 1);
      if (!path.ok) continue;
      const choices = stepsOf(path.root);
      const p = pyramidOf(id, choices, path.root.batches);
      if (!p) continue; // too big to draw: the page says so
      checked++;
      assert.equal(p.root.id, id);
      for (const n of p.all.filter((x) => x.kids.length)) assert.equal(n.ri, choices.get(n.id), `${id}: ${n.id} is not made as the path says`);
      assert.ok(p.m && Number.isFinite(p.m.cost), `${id}: no figures`);
      break;
    }
  }
  assert.ok(checked > 50, `only ${checked} paths drawn`);
});
