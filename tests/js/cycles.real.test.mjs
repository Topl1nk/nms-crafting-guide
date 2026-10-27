// lib/cycles.js over the real recipes: the loops it finds are real (a turn takes nothing from outside and leaves something),
// and the well-known pairs are among them.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { pathToFileURL } from "node:url";
import { join } from "node:path";

const ROOT = join(import.meta.dirname, "..", "..");
const LIB = join(ROOT, "site", "src", "lib");
const bundle = JSON.parse(readFileSync(join(ROOT, "web", "data.json"), "utf8"));
const { findCycles } = await import(pathToFileURL(join(LIB, "cycles.js")));

const refine = bundle.recipes.map((r, index) => ({ ...r, index })).filter((r) => r.domain === "refine");
const t0 = Date.now();
const loops = findCycles(refine, { maxSize: 8 });
const took = Date.now() - t0;
const byIndex = Object.fromEntries(refine.map((r) => [r.index, r]));

test("it finds loops, in a reasonable time", () => {
  console.log(`# ${loops.length} loops of at most 8 recipes in ${took} ms`);
  assert.ok(loops.length >= 6, `only ${loops.length} loops`);
  assert.ok(took < 120000, `took ${took} ms`);
});

test("every loop is real: one turn takes nothing from outside and leaves something", () => {
  for (const loop of loops) {
    const net = new Map();
    for (const { recipe, runs } of loop.parts) {
      const r = byIndex[recipe];
      net.set(r.out[0], (net.get(r.out[0]) ?? 0) + r.out[1] * runs);
      for (const [id, n] of r.in) net.set(id, (net.get(id) ?? 0) - n * runs);
    }
    for (const [id, v] of net) assert.ok(v >= -1e-9, `${id} is net-consumed (${v}) in ${JSON.stringify(loop.parts)}`);
    assert.ok([...net.values()].some((v) => v > 1e-9), "nothing grows");
    assert.deepEqual(loop.net.map(([id]) => id).sort(), [...net].filter(([, v]) => v > 1e-9).map(([id]) => id).sort());
  }
});

test("a turn can be begun from its seed, and the seed is enough", () => {
  for (const loop of loops) {
    const stock = new Map(loop.seed);
    assert.equal(loop.order.length, loop.parts.reduce((s, p) => s + p.runs, 0));
    for (const index of loop.order) {
      const r = byIndex[index];
      for (const [id, n] of r.in) {
        assert.ok((stock.get(id) ?? 0) >= n, `${id} is short at recipe ${index}; seed ${JSON.stringify(loop.seed)}, order ${loop.order}`);
        stock.set(id, stock.get(id) - n);
      }
      stock.set(r.out[0], (stock.get(r.out[0]) ?? 0) + r.out[1]);
    }
  }
});

const has = (...inRec) => loops.some((l) => l.parts.length === inRec.length && inRec.every((i) => l.parts.some((p) => p.recipe === i)));
const idOf = (inputs, out) => refine.find((r) => r.out[0] === out[0] && r.out[1] === out[1] && JSON.stringify(r.in) === JSON.stringify(inputs))?.index;

test("the pairs of Chromatic Metal are found: Indium, Quartzite, Emeril", () => {
  for (const [metal, take, give] of [["BLUE2", 2, 4], ["PURPLE2", 2, 4], ["GREEN2", 2, 3]]) {
    const smelt = idOf([[metal, take]], ["STELLAR2", give]);
    const grow = idOf([[metal, 1], ["STELLAR2", 1]], [metal, 2]);
    assert.ok(smelt !== undefined && grow !== undefined, `recipes of ${metal} not in the data`);
    assert.ok(has(smelt, grow), `the pair of ${metal} is not among the loops`);
  }
});

test("Dihydrogen and its gel are a loop of two", () => {
  const gel = idOf([["LAUNCHSUB", 30]], ["JELLY", 1]);
  const back = idOf([["JELLY", 1]], ["LAUNCHSUB", 40]);
  assert.ok(gel !== undefined && back !== undefined);
  assert.ok(has(gel, back));
});

test("1 Chlorine + 2 Oxygen -> 6 Chlorine is not in any loop (the oxygen is spent and nothing makes it)", () => {
  const cl = idOf([["WATER2", 1], ["OXYGEN", 2]], ["WATER2", 6]);
  if (cl === undefined) return;
  assert.ok(!loops.some((l) => l.parts.some((p) => p.recipe === cl)));
});


test("a loop runs for ever: the seed is taken once, then 50 turns never run short, and the stock only grows", () => {
  for (const loop of loops) {
    const stock = new Map(loop.seed);
    let last = null;
    for (let turn = 0; turn < 50; turn++) {
      for (const index of loop.order) {
        const r = byIndex[index];
        for (const [id, n] of r.in) {
          assert.ok((stock.get(id) ?? 0) >= n, `turn ${turn}: ${id} runs out in ${JSON.stringify(loop.parts)}`);
          stock.set(id, stock.get(id) - n);
        }
        stock.set(r.out[0], (stock.get(r.out[0]) ?? 0) + r.out[1]);
      }
      const total = [...stock.values()].reduce((s, v) => s + v, 0);
      if (last !== null) assert.ok(total >= last, "the stock shrank");
      last = total;
    }
  }
});

test("simulate: the books of N turns agree with the net of one turn times N, and never come up short", async () => {
  const { simulate } = await import(pathToFileURL(join(LIB, "cycles.js")));
  for (const loop of loops) {
    const sim = simulate(loop, (i) => byIndex[i], 7);
    assert.ok(!sim.short);
    for (const [id, n] of loop.net) assert.equal((sim.end.get(id) ?? 0) - (sim.start.get(id) ?? 0), n * 7, id);
  }
});

test("no small loop is missed: every pair and triple of recipes that makes a loop (runs up to 4) holds a loop that was found", () => {
  let alive = refine;
  for (;;) {
    const made = new Set(alive.map((x) => x.out[0]));
    const keep = alive.filter((x) => x.in.every(([i]) => made.has(i)));
    if (keep.length === alive.length) break;
    alive = keep;
  }
  const sets = loops.map((l) => new Set(l.parts.map((p) => p.recipe)));
  const V = alive.map((x) => { const m = new Map([[x.out[0], x.out[1]]]); for (const [i, n] of x.in) m.set(i, (m.get(i) ?? 0) - n); return m; });
  const grows = (idx, runs) => {
    const net = new Map();
    idx.forEach((i, t) => { for (const [k, v] of V[i]) net.set(k, (net.get(k) ?? 0) + v * runs[t]); });
    const vs = [...net.values()];
    return vs.every((v) => v >= 0) && vs.some((v) => v > 0);
  };
  const covered = (idx) => sets.some((s) => [...s].every((q) => idx.some((i) => alive[i].index === q)));
  const n = alive.length;
  const missed = [];
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
    let hit = false;
    for (let x = 1; x <= 4 && !hit; x++) for (let y = 1; y <= 4 && !hit; y++) if (grows([i, j], [x, y])) hit = true;
    if (hit && !covered([i, j])) missed.push([alive[i].index, alive[j].index]);
    for (let k = j + 1; k < n; k++) {
      let h3 = false;
      for (let x = 1; x <= 4 && !h3; x++) for (let y = 1; y <= 4 && !h3; y++) for (let z = 1; z <= 4 && !h3; z++) if (grows([i, j, k], [x, y, z])) h3 = true;
      if (h3 && !covered([i, j, k])) missed.push([alive[i].index, alive[j].index, alive[k].index]);
    }
  }
  assert.deepEqual(missed, []);
});
