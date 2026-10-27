// What the tree stress tests share: a loader for any made-up world, and the
// *oracles* -- slow, plainly written versions of the things lib/tree.js does
// cleverly (all chains by brute force, what a chain costs by simulating it, who
// beats whom), so the fast code is checked against something that shares none of
// its tricks.
import { join } from "node:path";
import { pathToFileURL } from "node:url";

export const LIB = join(import.meta.dirname, "..", "..", "site", "src", "lib");
export const data = await import(pathToFileURL(join(LIB, "data.js")));
export const tree = await import(pathToFileURL(join(LIB, "tree.js")));

export async function loadBundle(bundle) {
  globalThis.fetch = async () => ({ ok: true, json: async () => structuredClone(bundle) });
  await data.load();
}

// -- a seeded random generator, so every failure can be replayed -------------------------------------------
export function rng(seed) {
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return Object.assign(next, {
    int: (n) => Math.floor(next() * n),
    pick: (list) => list[Math.floor(next() * list.length)],
    chance: (p) => next() < p,
    shuffle: (list) => { const out = [...list]; for (let i = out.length - 1; i > 0; i--) { const j = Math.floor(next() * (i + 1)); [out[i], out[j]] = [out[j], out[i]]; } return out; },
  });
}

// -- worlds -----------------------------------------------------------------------------------------------
const RAR = ["Common", "Uncommon", "Rare"];

/**
 * A made-up world. `acyclic`: item k is made only from items below k (so no loops are possible and the
 * brute force over assignments is an exact spec). Otherwise ingredients are anything, loops included.
 */
export function makeWorld(seed, { items = 10, raws = 3, loots = 1, acyclic = false, maxRecipes = 3, maxIngredients = 3, cookShare = 0.25 } = {}) {
  const r = rng(seed);
  const ids = Array.from({ length: items }, (_, i) => `I${i}`);
  const raw = new Set(ids.slice(0, raws));
  const loot = new Set(ids.slice(raws, raws + loots));
  const recipes = [];
  for (let k = raws; k < items; k++) {
    const id = ids[k];
    const count = loot.has(id) ? (r.chance(0.7) ? 1 : 0) : 1 + r.int(maxRecipes);
    for (let j = 0; j < count; j++) {
      const pool = acyclic ? ids.slice(0, k) : ids.filter((x) => x !== id || r.chance(0.1));
      const inCount = 1 + r.int(Math.min(maxIngredients, pool.length));
      const chosen = r.shuffle(pool).slice(0, inCount);
      recipes.push({
        domain: r.chance(cookShare) ? "cook" : "refine", op: "t", out: [id, 1 + r.int(4)],
        in: chosen.map((x) => [x, 1 + r.int(3)]), time: 1 + r.int(120), machine: "m", ratio: 1, loop: 0, profit: 0, rate: 0,
      });
    }
  }
  // refine recipes may take 1-3 ingredients (a refiner level); keep that true of the world too
  return { seed, ids, raw, loot, recipes, value: Object.fromEntries(ids.map((id) => [id, 1 + r.int(50)])), rar: Object.fromEntries(ids.map((id) => [id, r.pick(RAR)])), r };
}

export function bundleOf(world) {
  const ease = {};
  for (const id of world.raw) ease[id] = { label: "T0 raw", band: "easy", score: 100, describe: "", where: "", note: "" };
  for (const id of world.loot) ease[id] = { label: "loot (easy)", band: "ok", score: 60, describe: "", where: "", note: "" };
  return {
    source: null,
    items: Object.fromEntries(world.ids.map((id) => [id, { name: id, sub: "", cat: "", value: world.value[id], store: 0, rar: world.rar[id] }])),
    ease, recipes: world.recipes, cooking: [], storage: { homes: [], outcomes: [] },
  };
}

// -- oracles -----------------------------------------------------------------------------------------------

/** Every chain (as a sorted "item:recipe" key) by plain recursion; same rules as the spec in tree.js, none of its machinery. */
export function reference(world, target, { cook = false, have = new Set() } = {}) {
  const made = {};
  world.recipes.forEach((rc, i) => { (made[rc.out[0]] ||= []).push({ ...rc, i }); });
  const usable = (rc) => cook || rc.domain !== "cook";
  const reaches = (from, to, assign) => {
    const seen = new Set();
    const go = (x) => {
      if (x === to) return true;
      if (seen.has(x)) return false;
      seen.add(x);
      const ri = assign.get(x);
      return ri !== undefined && world.recipes[ri].in.some(([i]) => go(i));
    };
    return go(from);
  };
  const out = new Set();
  const solve = (assign, leaf, todo) => {
    for (let n = todo.length - 1; n >= 0; n--) {
      const id = todo[n];
      if (assign.has(id) || leaf.has(id) || world.raw.has(id) || have.has(id)) continue;
      const options = (made[id] || []).filter((rc) => usable(rc) && !rc.in.some(([i]) => i === id || reaches(i, id, assign)));
      if (!options.length) continue;
      const rest = todo.slice(0, n);
      for (const rc of options) solve(new Map(assign).set(id, rc.i), leaf, [...rest, ...rc.in.map(([i]) => i).reverse()]);
      if (world.loot.has(id)) solve(assign, new Set(leaf).add(id), rest);
      return;
    }
    out.add(keyOfChoices(assign));
  };
  // A recipe that takes its own result (an amplifier) is a chain too: it stands on the item you already hold.
  const top = (made[target] || []).filter(usable);
  for (const rc of top) {
    solve(new Map([[target, rc.i]]), new Set(), rc.in.map(([i]) => i).reverse());
  }
  if (!top.length) out.add("");
  return out;
}

/**
 * The exact spec for a world with no loops, by trying every assignment: each item takes one of its recipes or
 * nothing, and a chain is an assignment that is *closed* (every item reached that is not raw / held / a picked-up
 * loot item is made by a recipe) and *minimal* (nothing assigned that is not reached).
 */
export function bruteAcyclic(world, target, { cook = false, have = new Set() } = {}) {
  const made = {};
  world.recipes.forEach((rc, i) => { (made[rc.out[0]] ||= []).push({ ...rc, i }); });
  const usable = (rc) => cook || rc.domain !== "cook";
  const own = (id) => (made[id] || []).filter((rc) => usable(rc) && !rc.in.some(([i]) => i === id));
  const items = world.ids.filter((id) => id === target || (!world.raw.has(id) && !have.has(id)));
  const choices = items.map((id) => {
    const rs = own(id).map((rc) => rc.i);
    return id === target ? rs : [...rs, -1]; // -1: not made (picked up, found, or nothing makes it)
  });
  const out = new Set();
  const assign = new Map();
  const check = () => {
    const reached = new Set();
    let closed = true;
    const go = (id) => {
      if (reached.has(id)) return;
      reached.add(id);
      const ri = assign.get(id);
      if (ri === undefined || ri === -1) {
        // left unmade: fine for what is raw, held, loot, or has no recipe to use; not for anything else
        if (id !== target && !world.raw.has(id) && !have.has(id) && !world.loot.has(id) && own(id).length) closed = false;
        return;
      }
      for (const [i] of world.recipes[ri].in) go(i);
    };
    go(target);
    if (!closed) return;
    const made_ = [...assign].filter(([, ri]) => ri !== -1);
    if (made_.some(([id]) => !reached.has(id))) return; // something made that nothing needs
    out.add(keyOfChoices(new Map(made_)));
  };
  const walk = (k) => {
    if (k === items.length) { check(); return; }
    for (const c of choices[k]) { assign.set(items[k], c); walk(k + 1); }
    assign.delete(items[k]);
  };
  if (!own(target).length) return new Set([""]);
  walk(0);
  return out;
}
export function keyOfChoices(assign) {
  return [...assign].sort((a, b) => (a[0] < b[0] ? -1 : 1)).map(([id, ri]) => `${id}:${ri}`).join("|");
}
export const keyOf = (p) => keyOfChoices(p.choices);

/** Run a finder to the end (small worlds), in awkward slices if asked. */
export function drain(f, { slice = 1e9, budget = 5e6, guard = 200000 } = {}) {
  let n = 0;
  while (!f.done && n++ < guard) f.more(slice, budget);
  return f;
}

/** What a pyramid takes, by simulating it: raw by item, refining time, crafted steps, floors and refiner level. */
export function simulate(p, runs, recipes = data.RECIPES) {
  const raw = new Map();
  let time = 0;
  let steps = 0;
  let level = 0;
  let cooks = false;
  const go = (n, need, fixed) => {
    if (!n.kids.length) { raw.set(n.id, (raw.get(n.id) ?? 0) + need); return; }
    const r = recipes[n.ri];
    const batches = fixed ?? Math.ceil(need / r.out[1]);
    steps++;
    if (r.domain === "refine") { time += batches * r.time; level = Math.max(level, r.in.length); } else cooks = true;
    r.in.forEach(([, per], i) => go(n.kids[i], batches * per));
  };
  go(p.root, 0, runs);
  return { raw, time, steps, level, cooks, height: p.height };
}

/** a is at least as good as b on every axis a visitor can filter by (raw amounts by item, steps, floors, refiner). */
export function atLeastAsGood(a, b) {
  if (a.steps > b.steps || a.height > b.height || a.level > b.level) return false;
  for (const [id, n] of a.raw) if (!(b.raw.get(id) >= n)) return false;
  return true;
}

export function rawOf(p) { return new Set(p.leaves); }
