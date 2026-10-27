// lib/facets.js, tried on thousands of made-up tables: whatever the visitor has chosen, however it came about, the
// filters shown are ones that tell something apart, nothing impossible is in force, and the table is never empty
// unless there is nothing in it to begin with.
import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
import { join } from "node:path";
import { test } from "node:test";

const LIB = join(import.meta.dirname, "..", "..", "site", "src", "lib");
const { applyFacets, facets } = await import(pathToFileURL(join(LIB, "facets.js")));

function rng(seed) {
  let a = seed >>> 0;
  const next = () => { a = (a + 0x6d2b79f5) >>> 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  return Object.assign(next, { int: (n) => Math.floor(next() * n), pick: (l) => l[Math.floor(next() * l.length)], chance: (p) => next() < p });
}

const DEFS = [
  { key: "kind", options: [["all", "all"], ["a", "a"], ["b", "b"], ["c", "c"], ["d", "d"]], neutral: "all", test: (r, v) => v === "all" || r.kind === v },
  { key: "level", options: [[0, "any"], [1, "1"], [2, "2"], [3, "3"]], neutral: 0, test: (r, v) => !v || r.level <= v },
  { key: "tag", options: [["any", "any"], ["x", "x"], ["y", "y"]], neutral: "any", test: (r, v) => v === "any" || r.tag === v },
  { key: "flag", options: [[false, ""], [true, ""]], neutral: false, test: (r, v) => !v || r.flag },
];
const randomRows = (r) => Array.from({ length: r.int(40) }, () => ({ kind: r.pick(["a", "b", "c", "d"]), level: r.int(4), tag: r.pick(["x", "y", "z"]), flag: r.chance(0.3) }));
const randomState = (r) => ({ kind: r.pick(["all", "a", "b", "c", "d"]), level: r.int(4), tag: r.pick(["any", "x", "y"]), flag: r.chance(0.4) });
const count = (rows, defs, state, skip) => applyFacets(rows, defs.filter((d) => d.key !== skip), state).length;

test("counts are exact, choices offered are useful, and what is in force is a choice that was made", () => {
  for (let seed = 1; seed <= 1500; seed++) {
    const r = rng(seed);
    const rows = randomRows(r);
    const state = randomState(r);
    const fx = facets(rows, DEFS, state);
    for (const d of DEFS) {
      // counts: with every *other* filter as in force, how many rows each choice leaves
      for (const [v] of d.options) {
        const others = DEFS.filter((o) => o !== d);
        const base = applyFacets(rows, others, fx.effective);
        assert.equal(fx.counts[d.key].get(v), base.filter((x) => d.test(x, v)).length, `seed ${seed} ${d.key}=${v}`);
      }
      const all = fx.counts[d.key].get(d.neutral);
      const offered = fx.options[d.key].map(([v]) => v);
      assert.ok(offered.includes(d.neutral), "the neutral choice is always there");
      for (const v of offered) if (v !== d.neutral) { assert.ok(fx.counts[d.key].get(v) > 0 && fx.counts[d.key].get(v) < all, `useless choice offered: seed ${seed} ${d.key}=${v}`); }
      assert.equal(fx.show[d.key], offered.length > 1, "shown exactly when there is something to choose");
      const e = fx.effective[d.key];
      assert.ok(e === d.neutral || e === state[d.key], "in force is neutral or what was chosen");
      if (e !== d.neutral) assert.ok(offered.includes(e), "what is in force is among what is offered");
      if (!fx.show[d.key]) assert.equal(e, d.neutral, "a hidden filter is not in force");
    }
  }
});

test("never an empty table unless the table was empty; dropping the useless changes nothing when something was left", () => {
  let dropped = 0;
  for (let seed = 1; seed <= 3000; seed++) {
    const r = rng(seed * 13);
    const rows = randomRows(r);
    const state = randomState(r);
    const fx = facets(rows, DEFS, state);
    const left = applyFacets(rows, DEFS, fx.effective);
    if (rows.length) assert.ok(left.length > 0, `empty: seed ${seed} state ${JSON.stringify(state)}`);
    else assert.equal(left.length, 0);
    const asked = applyFacets(rows, DEFS, state);
    if (asked.length) assert.deepEqual(left, asked, `a filter that left rows was dropped (seed ${seed})`);
    if (JSON.stringify(fx.effective) !== JSON.stringify(state)) dropped++;
  }
  assert.ok(dropped > 500, `only ${dropped} cases dropped anything: the generator is too tame`);
});

test("settled: asking again with what is in force changes nothing; the order of the definitions does not matter to emptiness", () => {
  for (let seed = 1; seed <= 1500; seed++) {
    const r = rng(seed * 101);
    const rows = randomRows(r);
    const state = randomState(r);
    const fx = facets(rows, DEFS, state);
    const again = facets(rows, DEFS, fx.effective);
    assert.deepEqual(again.effective, fx.effective, `not settled (seed ${seed})`);
    assert.deepEqual(Object.keys(again.show).filter((k) => again.show[k]), Object.keys(fx.show).filter((k) => fx.show[k]));
    const reversed = [...DEFS].reverse();
    const back = facets(rows, reversed, state);
    if (rows.length) assert.ok(applyFacets(rows, reversed, back.effective).length > 0);
  }
});

test("corners: no rows, no filters, one row, every row alike", () => {
  const fx0 = facets([], DEFS, randomState(rng(1)));
  assert.ok(Object.values(fx0.show).every((s) => !s), "nothing to tell apart in nothing");
  assert.equal(applyFacets([], DEFS, fx0.effective).length, 0);
  assert.deepEqual(facets([{ kind: "a", level: 0, tag: "x", flag: false }], [], {}).show, {});
  const one = [{ kind: "a", level: 1, tag: "x", flag: true }];
  const fx1 = facets(one, DEFS, { kind: "b", level: 0, tag: "y", flag: true });
  assert.equal(applyFacets(one, DEFS, fx1.effective).length, 1);
  const same = Array.from({ length: 9 }, () => ({ kind: "c", level: 2, tag: "y", flag: false }));
  assert.ok(Object.values(facets(same, DEFS, randomState(rng(7))).show).every((s) => !s), "identical rows: nothing worth a filter");
});