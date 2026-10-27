// lib/tree.js on a tiny made-up world, so every expectation can be done by hand.
//
//   A <- 2 B + 1 C        (r0)      B <- 1 X, makes 2   (r2)
//   A <- 1 D, makes 3     (r1)      C <- 1 Y            (r3)
//   B <- 1 A              (r5)  a loop: must never show up in any chain
//   F <- 3 B              (r6)      3 needs 2 batches of B (waste is real)
//   G <- 1 X, cooked      (r7)      only with `cook`
//   D <- 1 X + 1 Y        (r4)      X, Y are raw (the planner's "T0 raw")
//   H <- 1 P (r8), H <- 1 Q (r9), P <- 1 X (r10), Q <- 1 X (r11): two ways to the same sum
import assert from "node:assert/strict";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const LIB = join(import.meta.dirname, "..", "..", "site", "src", "lib");
const raw = { label: "T0 raw", band: "easy", score: 100, describe: "", where: "", note: "" };
const names = ["A", "B", "C", "D", "F", "G", "H", "K", "L", "N", "P", "Q", "R", "S", "W", "X", "Y"];
const rec = (out, outN, ins, domain = "refine") =>
  ({ domain, op: "t", out: [out, outN], in: ins, time: 1, machine: "m", ratio: outN, loop: 0, profit: 0, rate: 0 });
const bundle = {
  source: null,
  items: Object.fromEntries(names.map((n) => [n, { name: n, sub: "", cat: "", value: 1, store: 0 }])),
  ease: { X: raw, Y: raw, W: raw, L: { ...raw, label: "loot (easy)" } },
  recipes: [
    rec("A", 1, [["B", 2], ["C", 1]]),
    rec("A", 3, [["D", 1]]),
    rec("B", 2, [["X", 1]]),
    rec("C", 1, [["Y", 1]]),
    rec("D", 1, [["X", 1], ["Y", 1]]),
    rec("B", 1, [["A", 1]]),
    rec("F", 1, [["B", 3]]),
    rec("G", 1, [["X", 1]], "cook"),
    rec("H", 1, [["P", 1]]),
    rec("H", 1, [["Q", 1]]),
    rec("P", 1, [["X", 1]]),
    rec("Q", 1, [["X", 1]]),
    rec("K", 1, [["L", 1]]),
    rec("L", 1, [["X", 1]]),
    rec("N", 1, [["X", 1], ["Y", 1], ["W", 1]]),
    rec("N", 1, [["R", 1], ["S", 1]]),
    rec("R", 1, [["X", 1]]),
    rec("S", 1, [["Y", 1], ["W", 1]]),
  ],
  cooking: [],
  storage: { homes: [], outcomes: [] },
};
globalThis.fetch = async () => ({ ok: true, json: async () => bundle });
const { load } = await import(pathToFileURL(join(LIB, "data.js")));
const { finder, ordered, paretoLayers, pyramids, plan } = await import(pathToFileURL(join(LIB, "tree.js")));
await load();

const totals = (p, runs) => Object.fromEntries(plan(p, runs).total);
const viaC = (list) => list.find((p) => p.root.kids.length === 2);
const viaD = (list) => list.find((p) => p.root.kids.length === 1);

test("every recipe of the target gives a pyramid, and the loop through B -> A gives none", () => {
  const { pyramids: list, truncated } = pyramids("A");
  assert.equal(truncated, false);
  assert.equal(list.length, 2);
  for (const p of list) for (const n of p.all) assert.notEqual(n.ri, 5, "the A-from-B loop recipe is in a chain");
});

test("the foundation is raw stuff only, and all of it sits on the lowest floor", () => {
  for (const p of pyramids("A").pyramids) {
    assert.ok(p.leaves.size > 0);
    for (const n of p.all.filter((x) => !x.kids.length && x !== p.root)) {
      assert.ok(["X", "Y"].includes(n.id), n.id);
      assert.equal(n.floor, p.height - 1);
    }
    for (const n of p.all.filter((x) => x.kids.length)) assert.equal(n.floor, n.depth);
  }
});

test("no two foundation nodes share a column", () => {
  for (const p of pyramids("A").pyramids) {
    const cols = p.all.filter((x) => !x.kids.length).map((x) => x.col);
    assert.equal(new Set(cols).size, cols.length);
    assert.equal(p.width, cols.length);
  }
});

test("a parent stands over the middle of its children", () => {
  for (const p of pyramids("A").pyramids) {
    for (const n of p.all.filter((x) => x.kids.length)) {
      assert.equal(n.col, (n.kids[0].col + n.kids.at(-1).col) / 2);
    }
  }
});

test("one run: the top is what one run makes, ingredients follow the recipe", () => {
  const p = viaC(pyramids("A").pyramids);
  const { info } = plan(p, 1);
  assert.equal(info.get(p.root.key).yield, 1);
  assert.deepEqual(totals(p, 1), { X: 1, Y: 1 }); // B x2 = 1 batch of 2 = 1 X; C x1 = 1 Y
});

test("two runs: every number doubles (top = runs x yield)", () => {
  const p = viaD(pyramids("A").pyramids);
  const one = plan(p, 1);
  const two = plan(p, 2);
  assert.equal(one.info.get(p.root.key).yield, 3);
  assert.equal(two.info.get(p.root.key).yield, 6);
  assert.deepEqual(totals(p, 2), { X: 2, Y: 2 });
  for (const k of Object.keys(totals(p, 1))) assert.equal(totals(p, 2)[k], 2 * totals(p, 1)[k]);
});

test("a step runs whole batches: 3 B need 2 batches of 2, so 2 X", () => {
  const [p] = pyramids("F").pyramids;
  const { info } = plan(p, 1);
  const b = p.root.kids[0];
  assert.deepEqual(info.get(b.key), { need: 3, batches: 2, yield: 4 });
  assert.deepEqual(totals(p, 1), { X: 2 });
});

test("runs below 1 count as 1", () => {
  const p = viaD(pyramids("A").pyramids);
  assert.deepEqual(totals(p, 0), totals(p, 1));
  assert.deepEqual(totals(p, -3), totals(p, 1));
});

test("cooking recipes are used only when asked for", () => {
  const [plain] = pyramids("G").pyramids;
  assert.equal(plain.root.kids.length, 0); // nothing else makes G: it is "found"
  const [cooked] = pyramids("G", { cook: true }).pyramids;
  assert.equal(cooked.root.kids.length, 1);
  assert.deepEqual(totals(cooked, 1), { X: 1 });
});

test("smaller pyramids come first", () => {
  const list = pyramids("A").pyramids;
  for (let i = 1; i < list.length; i++) {
    const [a, b] = [list[i - 1], list[i]];
    assert.ok(a.height < b.height || (a.height === b.height && a.nodes <= b.nodes));
  }
});

test("chains with the same raw materials and the same result are one: the smallest stays", () => {
  const f = finder("H");
  f.more(10);
  assert.equal(f.out.length, 1);
  assert.equal(f.hiddenCount, 1);
  assert.equal(f.hidden[0].why, "no better than another chain");
  assert.deepEqual(totals(f.out[0], 1), { X: 1 });
  assert.equal(f.done, true);
});

test("what the world hands out is picked up; crafting it is kept, but put away as a detour", () => {
  const f = finder("K");
  f.more(10);
  assert.equal(f.out.length, 1);
  assert.deepEqual(totals(f.out[0], 1), { L: 1 });
  assert.equal(f.hiddenCount, 1);
  assert.match(f.hidden[0].why, /a detour/);
  assert.deepEqual(totals(f.hidden[0], 1), { X: 1 });
});

test("a chain that is cheaper but needs a bigger refiner does not hide one that needs a smaller one", () => {
  const f = finder("N");
  f.more(10);
  assert.deepEqual(f.out.map((p) => p.level).sort(), [2, 3]);
  assert.equal(f.hiddenCount, 0);
});

test("what you hold is a floor of the pyramid, never made again from what lies further down", () => {
  const f = finder("A", { have: new Set(["B"]) });
  f.more(10);
  const viaBC = f.out.find((p) => p.root.kids.length === 2);
  assert.ok(viaBC);
  assert.deepEqual(viaBC.root.kids.map((k) => k.kids.length), [0, 1]); // B is a bare tile, C is made from Y
  assert.deepEqual(totals(viaBC, 1), { B: 2, Y: 1 });
  for (const p of f.out) for (const n of p.all) assert.ok(!(n.id === "B" && n.kids.length), "B was made though it is held");
});

test("a pyramid knows its cost, machine time, rarity and profit; cooking has no time to rank by", () => {
  const viaDirect = viaD(pyramids("A").pyramids);
  // 3 A per run; raw X and Y at 1 each; two refining steps of 1 s each
  assert.deepEqual({ ...viaDirect.m }, { cost: 2, time: 2, cooks: false, yield: 3, rarity: 0, profit: 1 });
  const [cooked] = pyramids("G", { cook: true }).pyramids;
  assert.equal(cooked.m.cooks, true);
});

test("order: the best are those nothing beats on every axis, and no order loses a pyramid", () => {
  const list = pyramids("A").pyramids;
  const layers = paretoLayers(list);
  assert.equal(layers.size, list.length);
  assert.ok([...layers.values()].includes(0));
  for (const order of ["best", "size", "cost", "time", "floors", "rarity", "profit"]) {
    assert.equal(ordered(list, order, layers).length, list.length, order);
  }
  const byCost = ordered(list, "cost", layers).map((p) => p.m.cost);
  assert.deepEqual(byCost, [...byCost].sort((a, b) => a - b));
});
