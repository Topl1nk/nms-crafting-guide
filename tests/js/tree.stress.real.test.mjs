// Stress on the real data (web/data.json): every craftable item of the game, with and without cooking, with
// made-up inventories and made-up visitor filters, against the same oracles as the made-up worlds.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { atLeastAsGood, data, drain, keyOf, loadBundle, reference, rng, simulate, tree } from "./treelib.mjs";

const bundle = JSON.parse(readFileSync(join(import.meta.dirname, "..", "..", "web", "data.json"), "utf8"));
await loadBundle(bundle);
const { finder, ordered, paretoLayers, passes, plan } = tree;
const { D, PRODUCED, RECIPES } = data;

const craftable = Object.keys(PRODUCED).filter((id) => D.items[id]).sort();
const all = (f) => [...f.out, ...f.hidden];
const group = (p) => RECIPES[p.root.ri]?.out[1] ?? 0;
const first = (id, opts = {}, count = 120, budget = 200000) => { const f = finder(id, opts); f.more(count, budget); return f; };

test("data: the numbers the tree leans on are all there and sane", () => {
  assert.ok(craftable.length > 300);
  for (const r of RECIPES) {
    assert.ok(r.in.length >= 1 && r.in.length <= 3, `recipe ${r.index}`);
    assert.ok(Number.isFinite(r.time) && r.time >= 0, `time of ${r.index}`);
    assert.ok(r.out[1] >= 1);
    assert.equal(data.refinerLevel(r), r.domain === "refine" ? r.in.length : 0);
    for (const [, n] of r.in) assert.ok(n >= 1);
  }
  for (const [id, item] of Object.entries(D.items)) {
    assert.ok(Number.isFinite(item.value) && item.value >= 0, `value of ${id}`);
    assert.ok(["Common", "Uncommon", "Rare"].includes(item.rar), `rarity of ${id}: ${item.rar}`);
  }
});

test("every craftable item, with and without cooking: sound chains, honest numbers, sane time", () => {
  let chains = 0;
  const slow = [];
  for (const id of craftable) {
    for (const cook of [false, true]) {
      for (const runs of [id.length % 2 ? 1 : 7]) {
        const t = performance.now();
        const f = first(id, { cook, runs }, 40, 40000);
        const dt = performance.now() - t;
        if (dt > 3000) slow.push([id, cook, runs, Math.round(dt)]);
        for (const p of all(f)) {
          chains++;
          assert.equal(p.root.id, id);
          const walk = (n, above) => {
            // (an amplifier's own result under it is a bare foundation, not another round)
            assert.ok(!above.has(n.id) || (n.id === id && !n.kids.length), `${n.id} above itself in ${id}`);
            if (n.kids.length) assert.deepEqual(n.kids.map((k) => k.id), RECIPES[n.ri].in.map(([i]) => i));
            n.kids.forEach((k) => walk(k, new Set(above).add(n.id)));
          };
          walk(p.root, new Set());
          assert.ok(p.nodes <= 1200);
          if (!p.m) continue;
          const s = simulate(p, runs);
          assert.equal(p.m.time, s.time, `time ${id}`);
          assert.equal(p.m.cooks, s.cooks);
          assert.equal(p.level, s.level);
          assert.ok(Number.isFinite(p.m.cost) && Number.isFinite(p.m.profit) && p.m.cost >= 0, `numbers of ${id}`);
          assert.equal(p.m.cost, [...s.raw].reduce((t2, [x, n]) => t2 + n * D.items[x].value, 0));
          if (!cook) assert.equal(s.cooks, false, `${id}: cooking in a chain with cooking off`);
        }
      }
    }
  }
  assert.ok(chains > 5000, `only ${chains} chains over the whole game`);
  assert.deepEqual(slow, [], "some first-120-chains took over 3 s");
});

test("the kept chains are an antichain and cover the hidden ones, on every item (first 80 chains)", () => {
  let covered = 0;
  for (const id of craftable.filter((_, i) => i % 2 === 0)) {
    const cook = true;
    const runs = 3;
    const f = first(id, { cook, runs }, 60, 100000);
    const kept = f.out.map((p) => ({ p, c: simulate(p, runs) }));
    for (const a of kept) for (const b of kept) {
      if (a !== b && group(a.p) === group(b.p)) assert.ok(!atLeastAsGood(a.c, b.c), `${id}: kept chains compare`);
    }
    for (const h of f.hidden.filter((x) => /no better/.test(x.why)).slice(0, 150)) {
      const hc = simulate(h, runs);
      assert.ok(kept.some((k) => group(k.p) === group(h) && atLeastAsGood(k.c, hc)), `${id}: a hidden chain nobody kept beats`);
      covered++;
    }
  }
  assert.ok(covered > 800, `only ${covered} hidden chains were ever checked`);
});

test("no hole on real items: under random visitor filters nothing that passes is left without a kept equal or better", () => {
  const r = rng(424242);
  let checked = 0;
  for (const id of r.shuffle(craftable).slice(0, 160)) {
    const runs = r.pick([1, 2, 9]);
    const f = first(id, { cook: true, runs }, 100, 200000);
    const universe = f.out.concat(f.hidden.filter((h) => /no better/.test(h.why)));
    const raws = [...new Set(universe.flatMap((p) => [...p.leaves]))];
    for (let k = 0; k < 10; k++) {
      const filter = {
        maxFloors: r.pick([0, 0, 2, 3, 4, 6]), maxLevel: r.pick([0, 0, 1, 2]),
        excluded: new Set(r.shuffle(raws).slice(0, r.int(4))), mine: r.chance(0.5),
        have: Object.fromEntries(r.shuffle(raws).slice(0, Math.ceil(raws.length * r.pick([0.2, 0.5, 0.9]))).map((x) => [x, 1 + r.int(50)])),
      };
      const shown = f.out.filter((p) => passes(p, filter));
      for (const c of universe.filter((p) => passes(p, filter))) {
        const cc = simulate(c, runs);
        assert.ok(shown.some((s) => group(s) === group(c) && atLeastAsGood(simulate(s, runs), cc)), `hole on ${id} runs ${runs}`);
        checked++;
      }
    }
  }
  assert.ok(checked > 3000, `only ${checked} pairs`);
});

test("completeness on the real game: whatever finishes is exactly the plain recursion's answer, with and without holdings", () => {
  const r = rng(99);
  let compared = 0;
  for (const id of craftable.filter((_, i) => i % 6 === 0)) {
    for (const cook of [false, true]) {
      const f = finder(id, { cook });
      let n = 0;
      while (!f.done && n++ < 6) f.more(400, 30000);
      if (!f.done || f.capped || f.cappedDetours || all(f).length > 150) continue; // only searches that ended, and small enough for the slow oracle
      const world = { raw: new Set(Object.keys(D.ease).filter((x) => /^T\d raw/.test(D.ease[x].label))), loot: new Set(Object.keys(D.ease).filter((x) => /^loot/.test(D.ease[x].label))), recipes: RECIPES };
      const expect = reference(world, id, { cook });
      assert.deepEqual([...new Set(all(f).map(keyOf))].sort(), [...expect].sort(), `${id} cook ${cook}`);
      compared++;
      // and with something held from the middle of its chains
      const middle = [...new Set(all(f).flatMap((p) => p.all.filter((x) => x.kids.length && x.id !== id).map((x) => x.id)))];
      if (middle.length) {
        const have = new Set(r.shuffle(middle).slice(0, 1 + r.int(2)));
        const g = finder(id, { cook, have });
        let m = 0;
        while (!g.done && m++ < 6) g.more(400, 30000);
        if (g.done && !g.capped && !g.cappedDetours && all(g).length <= 150) {
          assert.deepEqual([...new Set(all(g).map(keyOf))].sort(), [...reference(world, id, { cook, have })].sort(), `${id} holding ${[...have]}`);
          for (const p of all(g)) for (const x of p.all) if (have.has(x.id) && x !== p.root) assert.equal(x.kids.length, 0);
        }
      }
    }
  }
  assert.ok(compared > 25, `only ${compared} searches were small enough to compare`);
});

test("slicing the search into awkward pieces changes nothing on real items", () => {
  const pick = craftable.filter((_, i) => i % 58 === 0);
  for (const id of pick) {
    const whole = finder(id, { cook: true, runs: 2 });
    let n = 0;
    while (!whole.done && n++ < 40) whole.more(1e9, 400000);
    for (const [count, budget] of [[3, 700], [50, 5000]]) {
      const f = finder(id, { cook: true, runs: 2 });
      let guard = 0;
      while (!f.done && guard++ < 100000) f.more(count, budget);
      if (!whole.done || whole.capped) continue;
      assert.deepEqual([...new Set(f.out.map(keyOf))].sort(), [...new Set(whole.out.map(keyOf))].sort(), `${id} count ${count}`);
      assert.equal(f.hiddenCount, whole.hiddenCount, `${id} hidden count`);
    }
  }
});

test("a search that hits its limit says so, and 'search deeper' lets it go on", () => {
  let found = null;
  for (const id of craftable.filter((x) => /^FOOD/.test(x))) {
    const f = finder(id, { cook: true });
    let n = 0;
    while (!f.done && n++ < 80) f.more(1e9, 400000);
    if (f.capped || f.cappedDetours) { found = [id, f]; break; }
  }
  assert.ok(found, "no item reached the limit; the test needs one that does");
  const [id, f] = found;
  const before = all(f).length;
  assert.equal(f.done, true);
  f.raise();
  assert.equal(f.capped, false);
  assert.equal(f.cappedDetours, false);
  assert.equal(f.done, false, `${id}: raise() did not reopen the search`);
  let n = 0;
  while (!f.done && n++ < 40) f.more(1e9, 400000);
  assert.ok(all(f).length >= before, "searching deeper lost chains");
});

test("a big list: ordering and layers are quick and stay a permutation (thousands of pyramids)", () => {
  const f = finder("TECHFRAG", { cook: true });
  f.more(2500, 3000000);
  const list = all(f).filter((p) => p.m).slice(0, 3000); // kept and hidden alike: a visitor can ask for both
  assert.ok(list.length > 2000, `only ${list.length}`);
  const t = performance.now();
  const layers = paretoLayers(list);
  for (const order of ["best", "size", "cost", "time", "floors", "rarity", "profit"]) {
    const out = ordered(list, order, layers);
    assert.equal(out.length, list.length);
    assert.equal(new Set(out).size, list.length);
  }
  assert.ok(performance.now() - t < 6000, "ordering a few thousand pyramids took too long");
  assert.equal(layers.size, list.length);
  assert.ok([...layers.values()].includes(0));
});

test("huge runs keep every number finite and exact", () => {
  for (const id of ["TECHFRAG", "STELLAR2", "FUEL2", "ALLOY3"].filter((x) => D.items[x])) {
    const f = first(id, { cook: true, runs: 9999 }, 40);
    for (const p of f.out) {
      assert.ok(Number.isSafeInteger(p.m.cost) && Number.isSafeInteger(p.m.time) && Number.isSafeInteger(Math.round(p.m.profit)), id);
      const s = simulate(p, 9999);
      assert.equal(p.m.cost, [...s.raw].reduce((t2, [x, n]) => t2 + n * D.items[x].value, 0));
      assert.equal(plan(p, 9999).info.get(p.root.key).yield, 9999 * RECIPES[p.root.ri].out[1]);
    }
  }
});