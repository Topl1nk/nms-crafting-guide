// Stress: the craft-tree search against made-up worlds, hundreds of them, each checked against slow
// oracles (treelib.mjs): nothing is lost, nothing is repeated, the hard filter never leaves a hole under any
// visitor filter, and the order never changes what is shown.
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  atLeastAsGood, bruteAcyclic, bundleOf, data, drain, keyOf, loadBundle, makeWorld, reference, rng, simulate, tree,
} from "./treelib.mjs";

const { finder, ordered, paretoLayers, passes, pyramids, plan } = tree;

const keysOf = (list) => new Set(list.map(keyOf));
const all = (f) => [...f.out, ...f.hidden];

async function run(world, target, opts = {}, slice = 1e9) {
  await loadBundle(bundleOf(world));
  const f = drain(finder(target, opts), { slice });
  assert.equal(f.capped, false);
  assert.equal(f.cappedDetours, false);
  assert.equal(f.skipped, 0);
  assert.equal(f.hiddenMore, 0);
  return f;
}

// -- 1. nothing lost, nothing twice -------------------------------------------------------------------------

test("loop-free worlds: the finder finds exactly the chains a brute force over every assignment finds", async () => {
  let worlds = 0;
  let chains = 0;
  for (let seed = 1; seed <= 150; seed++) {
    const r = rng(seed * 7919);
    const world = makeWorld(seed, { items: 6 + r.int(3), raws: 2 + r.int(2), loots: r.int(2), acyclic: true, maxRecipes: 2, maxIngredients: 2 });
    const target = world.ids.at(-1);
    for (const cook of [false, true]) {
      const have = new Set(r.chance(0.5) ? [r.pick(world.ids.slice(3, -1))] : []);
      const f = await run(world, target, { cook, have });
      const expect = bruteAcyclic(world, target, { cook, have });
      const found = keysOf(all(f));
      assert.deepEqual([...found].sort(), [...expect].sort(), `seed ${seed} cook ${cook} have ${[...have]}`);
      assert.equal(found.size, all(f).length, `a chain came twice (seed ${seed})`);
      worlds++;
      chains += found.size;
    }
  }
  assert.ok(chains > 500, `only ${chains} chains over ${worlds} worlds: the worlds are too thin to mean anything`);
});

test("worlds with loops: the finder finds exactly what the plain recursion finds, with and without what you hold", async () => {
  for (let seed = 1; seed <= 200; seed++) {
    const r = rng(seed * 104729);
    const world = makeWorld(1000 + seed, { items: 7 + r.int(5), raws: 2 + r.int(2), loots: r.int(3), acyclic: false });
    const target = world.ids.at(-1 - r.int(3));
    for (const cook of [false, true]) {
      for (const have of [new Set(), new Set(r.shuffle(world.ids).slice(0, 1 + r.int(3)))]) {
        const f = await run(world, target, { cook, have: have.size ? have : null });
        const expect = reference(world, target, { cook, have });
        const found = keysOf(all(f));
        assert.deepEqual([...found].sort(), [...expect].sort(), `seed ${1000 + seed} target ${target} cook ${cook} have ${[...have]}`);
        assert.equal(found.size, all(f).length, "a chain came twice");
      }
    }
  }
});

// -- 2. every chain is a real pyramid ----------------------------------------------------------------------

test("every chain is sound: no loops, kids are the recipe's inputs, foundation on the lowest floor, columns apart", async () => {
  for (let seed = 1; seed <= 120; seed++) {
    const world = makeWorld(5000 + seed, { items: 9, raws: 3, loots: 1 });
    const target = world.ids.at(-1);
    const f = await run(world, target, { cook: true });
    for (const p of all(f)) {
      assert.equal(p.root.id, target);
      const walk = (n, above) => {
        // (an amplifier's own result under it is a bare foundation, not another round)
        assert.ok(!above.has(n.id) || (n.id === target && !n.kids.length), `${n.id} above itself`);
        if (n.kids.length) assert.deepEqual(n.kids.map((k) => k.id), data.RECIPES[n.ri].in.map(([i]) => i));
        n.kids.forEach((k) => walk(k, new Set(above).add(n.id)));
      };
      walk(p.root, new Set());
      const leaves = p.all.filter((n) => !n.kids.length && n !== p.root);
      assert.equal(new Set(leaves.map((n) => n.col)).size, leaves.length);
      for (const n of leaves) assert.equal(n.floor, p.height - 1);
      for (const n of p.all.filter((x) => x.kids.length)) {
        assert.equal(n.col, (n.kids[0].col + n.kids.at(-1).col) / 2);
        assert.equal(n.floor, n.depth);
      }
      assert.equal(p.nodes, p.all.length);
      assert.equal(p.level, simulate(p, 1).level);
    }
  }
});

// -- 3. the hard filter: antichain, cover, and no hole under any visitor filter -----------------------------

function costVec(p, runs) {
  const s = simulate(p, runs);
  return { ...s, yield: Math.ceil(0) };
}

const yieldOf = (p, runs) => runs * data.RECIPES[p.root.ri]?.out[1] || 0;

test("the kept chains beat nobody and are beaten by nobody; every hidden one is beaten by a kept one", async () => {
  let hiddenSeen = 0;
  for (let seed = 1; seed <= 150; seed++) {
    const world = makeWorld(9000 + seed, { items: 10, raws: 3, loots: 0 });
    const target = world.ids.at(-1);
    for (const runs of [1, 3, 17]) {
      const f = await run(world, target, { cook: true, runs });
      const group = (p) => data.RECIPES[p.root.ri]?.out[1] ?? 0; // chains of one top recipe have one yield
      const kept = f.out.map((p) => ({ p, c: simulate(p, runs) }));
      for (const a of kept) for (const b of kept) {
        if (a === b || group(a.p) !== group(b.p)) continue;
        assert.ok(!atLeastAsGood(a.c, b.c), `kept chains compare: seed ${seed} runs ${runs}`);
      }
      for (const h of f.hidden.filter((x) => /no better/.test(x.why))) {
        hiddenSeen++;
        const hc = simulate(h, runs);
        assert.ok(kept.some((k) => group(k.p) === group(h) && atLeastAsGood(k.c, hc)), `hidden chain with no better kept one: seed ${seed} runs ${runs}`);
      }
    }
  }
  assert.ok(hiddenSeen > 100, `only ${hiddenSeen} dominated chains were ever produced`);
});

function randomFilter(r, world) {
  const rawList = [...world.raw, ...world.loot];
  return {
    maxFloors: r.pick([0, 0, 2, 3, 4]),
    maxLevel: r.pick([0, 0, 1, 2]),
    excluded: new Set(r.shuffle(rawList).slice(0, r.int(3))),
  };
}

test("no hole: under any visitor filter the answer is still there, or something at least as good", async () => {
  let checked = 0;
  for (let seed = 1; seed <= 200; seed++) {
    const r = rng(seed * 31);
    const world = makeWorld(20000 + seed, { items: 9 + r.int(3), raws: 3, loots: r.int(2) });
    const target = world.ids.at(-1);
    const runs = r.pick([1, 2, 5]);
    // the universe: every chain, found with the hard filter off by reading kept + hidden
    const f = await run(world, target, { cook: true, runs });
    const universe = f.out.concat(f.hidden.filter((h) => /no better/.test(h.why))); // detours are a visitor's call, not part of the claim
    const group = (p) => data.RECIPES[p.root.ri]?.out[1] ?? 0;
    for (let k = 0; k < 14; k++) {
      const filter = randomFilter(r, world);
      const have = Object.fromEntries(r.shuffle(world.ids).slice(0, r.int(world.ids.length)).map((id) => [id, 1 + r.int(9)]));
      const mine = r.chance(0.4);
      const ok = (p) => passes(p, { ...filter, mine, have });
      const shown = f.out.filter(ok);
      for (const c of universe.filter(ok)) {
        const cc = simulate(c, runs);
        assert.ok(shown.some((s) => group(s) === group(c) && atLeastAsGood(simulate(s, runs), cc)),
          `hole: seed ${20000 + seed} runs ${runs} filter ${JSON.stringify({ ...filter, excluded: [...filter.excluded], mine })}`);
        checked++;
      }
    }
  }
  assert.ok(checked > 1000, `only ${checked} (chain, filter) pairs were checked`);
});

test("holding things: chains are found with what you hold as floor, and the held item is never made", async () => {
  for (let seed = 1; seed <= 150; seed++) {
    const r = rng(seed * 977);
    const world = makeWorld(30000 + seed, { items: 10, raws: 3, loots: 1 });
    const target = world.ids.at(-1);
    const held = new Set(r.shuffle(world.ids.slice(3, -1)).slice(0, 1 + r.int(3)));
    const f = await run(world, target, { cook: true, have: held });
    for (const p of all(f)) for (const n of p.all) {
      if (held.has(n.id) && n !== p.root) assert.equal(n.kids.length, 0, `${n.id} is held but was made (seed ${30000 + seed})`);
    }
  }
});

// -- 4. numbers ------------------------------------------------------------------------------------------

test("a pyramid's cost, time, rarity and profit are what a plain simulation says", async () => {
  const rank = { Common: 0, Uncommon: 1, Rare: 2 };
  for (let seed = 1; seed <= 150; seed++) {
    const world = makeWorld(40000 + seed, { items: 9, raws: 3, loots: 1 });
    const target = world.ids.at(-1);
    for (const runs of [1, 4, 250]) {
      const f = await run(world, target, { cook: true, runs });
      for (const p of all(f)) {
        if (!p.m) continue; // a lone tile has nothing to cost
        const s = simulate(p, runs);
        const cost = [...s.raw].reduce((t, [id, n]) => t + n * world.value[id], 0);
        assert.equal(p.m.cost, cost);
        assert.equal(p.m.time, s.time);
        assert.equal(p.m.cooks, s.cooks);
        assert.equal(p.m.rarity, Math.max(0, ...[...s.raw.keys()].map((id) => rank[world.rar[id]])));
        const made = runs * data.RECIPES[p.root.ri].out[1];
        assert.equal(p.m.yield, made);
        assert.equal(p.m.profit, made * world.value[target] - cost);
        // the shared plan() agrees with the simulation too
        assert.deepEqual(Object.fromEntries(plan(p, runs).total), Object.fromEntries(s.raw));
      }
    }
  }
});

// -- 5. order: a permutation, stable, honest layers -------------------------------------------------------

test("every order is a permutation, and the layers are honest", async () => {
  for (let seed = 1; seed <= 100; seed++) {
    const world = makeWorld(50000 + seed, { items: 10, raws: 3, loots: 0 });
    const target = world.ids.at(-1);
    const f = await run(world, target, { cook: true });
    const list = f.out.filter((p) => p.m);
    if (list.length < 2) continue;
    const layers = paretoLayers(list);
    assert.equal(layers.size, list.length);
    const better = (a, b) => {
      const ax = [[a.m.cost, b.m.cost], [a.height, b.height], [a.m.rarity, b.m.rarity]];
      if (!a.m.cooks && !b.m.cooks) ax.push([a.m.time, b.m.time]);
      return ax.every(([x, y]) => x <= y) && ax.some(([x, y]) => x < y);
    };
    for (const p of list) {
      const l = layers.get(p);
      if (l === 0) assert.ok(!list.some((q) => better(q, p)), "layer 0 is beaten");
      else assert.ok(list.some((q) => layers.get(q) === l - 1 && better(q, p)), `layer ${l} not beaten from the layer above`);
    }
    for (const order of ["best", "size", "cost", "time", "floors", "rarity", "profit"]) {
      const out = ordered(list, order, layers);
      assert.deepEqual(new Set(out), new Set(list), order);
      assert.equal(out.length, list.length, order);
      assert.deepEqual(ordered(list, order, layers).map(keyOf), out.map(keyOf), `${order} is not repeatable`);
      assert.deepEqual(ordered([...list].reverse(), order, layers).map(keyOf), out.map(keyOf), `${order} depends on the input order`);
    }
  }
});

// -- 6. slicing the search changes nothing; so does asking twice -------------------------------------------

test("any way of slicing the search gives the same chains, the same hidden ones, and the same reasons", async () => {
  for (let seed = 1; seed <= 80; seed++) {
    const world = makeWorld(60000 + seed, { items: 11, raws: 3, loots: 1 });
    const target = world.ids.at(-1);
    const whole = await run(world, target, { cook: true, runs: 3 });
    for (const slice of [1, 2, 7]) {
      await loadBundle(bundleOf(world));
      const f = drain(finder(target, { cook: true, runs: 3 }), { slice, budget: 40 });
      assert.deepEqual([...keysOf(f.out)].sort(), [...keysOf(whole.out)].sort(), `slice ${slice} seed ${60000 + seed}`);
      const reasons = (x) => x.hidden.map((h) => `${keyOf(h)} ${h.why}`).sort();
      assert.deepEqual(reasons(f), reasons(whole), `hidden differ at slice ${slice}`);
    }
    const again = await run(world, target, { cook: true, runs: 3 });
    assert.deepEqual(again.out.map(keyOf), whole.out.map(keyOf), "not repeatable");
  }
});

test("pyramids(): the first `limit` and the truncated flag agree with the finder", async () => {
  const world = makeWorld(777, { items: 12, raws: 3, loots: 1 });
  await loadBundle(bundleOf(world));
  const target = world.ids.at(-1);
  const everything = pyramids(target, { cook: true, limit: 100000 });
  assert.equal(everything.truncated, false);
  const few = pyramids(target, { cook: true, limit: 2 });
  assert.ok(few.pyramids.length <= 3);
  if (everything.pyramids.length > 3) assert.equal(few.truncated, true);
});

// -- 7. the visitor's own filters, one by one ------------------------------------------------------------

test("passes(): each visitor filter does what it says, alone and together", async () => {
  let world;
  let list = [];
  for (let seed = 31337; list.length < 40; seed++) {
    world = makeWorld(seed, { items: 11, raws: 3, loots: 1, maxRecipes: 3 });
    await loadBundle(bundleOf(world));
    list = all(drain(finder(world.ids.at(-1), { cook: true })));
  }
  const none = { maxFloors: 0, maxLevel: 0, excluded: new Set(), mine: false, have: {} };
  for (const p of list) assert.equal(passes(p, none), true);
  for (const p of list) assert.equal(passes(p), true, "defaults let everything through");
  for (const floors of [1, 2, 3, 5]) for (const p of list) assert.equal(passes(p, { ...none, maxFloors: floors }), p.height <= floors);
  for (const lvl of [1, 2]) for (const p of list) assert.equal(passes(p, { ...none, maxLevel: lvl }), p.level <= lvl);
  for (const id of world.raw) for (const p of list) assert.equal(passes(p, { ...none, excluded: new Set([id]) }), !p.leaves.has(id));
  for (const p of list) {
    const have = Object.fromEntries([...p.leaves].map((id) => [id, 1]));
    assert.equal(passes(p, { ...none, mine: true, have }), true);
    if (p.leaves.size) assert.equal(passes(p, { ...none, mine: true, have: {} }), false);
    if (p.leaves.size) assert.equal(passes(p, { ...none, mine: true, have: { ...have, [[...p.leaves][0]]: 0 } }), false, "a count of 0 is not holding it");
  }
  // together: the meet of the separate answers
  const r = rng(5);
  for (let i = 0; i < 300; i++) {
    const filter = { maxFloors: r.pick([0, 2, 3]), maxLevel: r.pick([0, 1, 2]), excluded: new Set(r.shuffle([...world.raw]).slice(0, r.int(3))), mine: r.chance(0.5), have: Object.fromEntries(world.ids.filter(() => r.chance(0.6)).map((id) => [id, 2])) };
    for (const p of list) {
      const parts = (!filter.maxFloors || p.height <= filter.maxFloors) && (!filter.maxLevel || p.level <= filter.maxLevel)
        && [...filter.excluded].every((id) => !p.leaves.has(id)) && (!filter.mine || [...p.leaves].every((id) => filter.have[id] > 0));
      assert.equal(passes(p, filter), parts);
    }
  }
});

// -- 8. odd corners --------------------------------------------------------------------------------------

test("corners: nothing makes it, only cooking makes it, a loop recipe, a raw target, a held target, everything held", async () => {
  const mk = (recipes, extra = {}) => {
    const ids = ["R", "S", "T", "U", "V"];
    const world = { seed: 0, ids, raw: new Set(["R", "S"]), loot: new Set(), value: Object.fromEntries(ids.map((i) => [i, 3])), rar: Object.fromEntries(ids.map((i) => [i, "Common"])), recipes, ...extra };
    return world;
  };
  const rec = (out, outN, ins, domain = "refine") => ({ domain, op: "t", out: [out, outN], in: ins, time: 10, machine: "m", ratio: 1, loop: 0, profit: 0, rate: 0 });

  // nothing makes T: one lone tile
  let w = mk([rec("U", 1, [["R", 1]])]);
  await loadBundle(bundleOf(w));
  let f = drain(finder("T"));
  assert.equal(f.out.length, 1);
  assert.equal(f.out[0].root.kids.length, 0);

  // only cooking makes T: nothing without cooking, one chain with
  w = mk([rec("T", 1, [["R", 1]], "cook")]);
  await loadBundle(bundleOf(w));
  f = drain(finder("T", { cook: false }));
  assert.equal(f.out[0].root.kids.length, 0);
  f = drain(finder("T", { cook: true }));
  assert.equal(f.out[0].root.kids.length, 1);

  // T makes more T (a loop recipe) next to an honest one: the honest one is on the canvas, the loop one is kept, put away
  w = mk([rec("T", 6, [["T", 1], ["R", 2]]), rec("T", 1, [["S", 1]])]);
  await loadBundle(bundleOf(w));
  f = drain(finder("T"));
  assert.deepEqual(f.out.map((p) => data.RECIPES[p.root.ri].in.map(([i]) => i)), [["S"]]);
  assert.deepEqual(f.hidden.map((p) => data.RECIPES[p.root.ri].in.map(([i]) => i)), [["T", "R"]]);

  // a raw target is still taken apart when something makes it
  w = mk([rec("R", 1, [["S", 1]])]);
  await loadBundle(bundleOf(w));
  f = drain(finder("R"));
  assert.equal(f.out[0].root.kids.length, 1);

  // the target itself is "held": it is still the top of the pyramid
  w = mk([rec("T", 1, [["U", 1]]), rec("U", 1, [["R", 1]])]);
  await loadBundle(bundleOf(w));
  f = drain(finder("T", { have: new Set(["T"]) }));
  assert.equal(f.out.length, 1);
  assert.equal(f.out[0].root.kids.length, 1);

  // everything below is held: one chain, one tile under the top
  f = drain(finder("T", { have: new Set(["U", "R", "S"]) }));
  assert.equal(f.out.length, 1);
  assert.deepEqual(f.out[0].root.kids.map((k) => k.kids.length), [0]);

  // runs of 0, negative, huge: plan treats them as at least one, and the finder does not choke
  for (const runs of [0, -4, 9999]) {
    f = drain(finder("T", { runs }));
    assert.ok(f.out.length >= 1);
  }
});

test("deep chains and wide worlds: a 14-step ladder is one chain; a diamond shares one choice", async () => {
  const rec = (out, outN, ins, domain = "refine") => ({ domain, op: "t", out: [out, outN], in: ins, time: 5, machine: "m", ratio: 1, loop: 0, profit: 0, rate: 0 });
  // ladder: L14 <- L13 <- ... <- L1 <- RAW
  const ids = ["RAW", ...Array.from({ length: 14 }, (_, i) => `L${i + 1}`)];
  const recipes = ids.slice(1).map((id, i) => rec(id, 1, [[ids[i], 1]]));
  const world = { seed: 0, ids, raw: new Set(["RAW"]), loot: new Set(), value: Object.fromEntries(ids.map((i) => [i, 2])), rar: Object.fromEntries(ids.map((i) => [i, "Common"])), recipes };
  await loadBundle(bundleOf(world));
  const f = drain(finder("L14"));
  assert.equal(f.out.length, 1);
  assert.equal(f.out[0].height, 15);
  assert.equal(f.out[0].m.time, 14 * 5);

  // diamond: T <- A + B; A <- S; B <- S; S has two recipes: both uses of S must agree
  const d = { seed: 0, ids: ["R1", "R2", "S", "A", "B", "T"], raw: new Set(["R1", "R2"]), loot: new Set(), value: { R1: 1, R2: 1, S: 1, A: 1, B: 1, T: 1 }, rar: { R1: "Common", R2: "Common", S: "Common", A: "Common", B: "Common", T: "Common" },
    recipes: [rec("S", 1, [["R1", 1]]), rec("S", 1, [["R2", 1]]), rec("A", 1, [["S", 1]]), rec("B", 1, [["S", 1]]), rec("T", 1, [["A", 1], ["B", 1]])] };
  await loadBundle(bundleOf(d));
  const g = drain(finder("T"));
  assert.equal(all(g).length, 2, "S has two recipes and the whole chain uses one of them");
  for (const p of all(g)) {
    const uses = p.all.filter((n) => n.id === "S").map((n) => n.ri);
    assert.equal(new Set(uses).size, 1);
  }
});