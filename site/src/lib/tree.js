// Every way to craft one item, as pyramids.
//
// A "chain" is one complete derivation: a recipe picked for the target, and for
// each ingredient that can itself be made, a recipe picked for it, and so on
// down to things you only gather. Two chains differ when any pick differs.
// Cycles are cut out at the source: a recipe is never used when one of its
// ingredients is already on the way down to it (so "1 Chlorine + 2 Oxygen ->
// 6 Chlorine" and any longer round trip simply do not exist here).
//
// A pyramid is a real tree: every use of an item is its own node, so a number
// on a node always means "for this step", never a sum over several steps.

import { D, PRODUCED, RECIPES, refinerLevel } from "./data.js";
import { N_ } from "./i18n.js";

// The search stops, and says so, when it has taken this many steps or holds this many open chains: with the
// worse ones thrown out as they are found, an item with endless variants would otherwise never run dry.
const MAX_WORK = 1500000; // raised by finder.raise() when the visitor asks to search deeper
const MAX_OPEN = 120000;
const HIDDEN_MAX = 3000; // hidden chains kept to show (the rest are only counted)
const MAX_NODES = 1200; // a chain bigger than this (counting every use) is counted as "too big", not drawn

// What is a source: you pick it up, you do not craft it. That is the raw materials. Whatever the world hands out
// ("loot") can be picked up too, but it may also be crafted: that way round is kept, as a chain of its own that
// is put away under "hidden" (it is a detour round a thing already lying there).
const rawItem = (id) => /^T\d raw/.test(D.ease[id]?.label ?? "");
const lootItem = (id) => /^loot/.test(D.ease[id]?.label ?? "");

// A binary min-heap on (size, arrival): the open chains, smallest first.
class Heap {
  constructor() { this.a = []; this.n = 0; }
  get size() { return this.a.length; }
  push(item) {
    item.k = this.n++;
    const a = this.a;
    let i = a.push(item) - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (!this.less(a[i], a[p])) break;
      [a[i], a[p]] = [a[p], a[i]];
      i = p;
    }
  }
  less(x, y) { return x.size < y.size || (x.size === y.size && x.k < y.k); }
  pop() {
    const a = this.a;
    const top = a[0];
    const last = a.pop();
    if (a.length) {
      a[0] = last;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1;
        const r = l + 1;
        let m = i;
        if (l < a.length && this.less(a[l], a[m])) m = l;
        if (r < a.length && this.less(a[r], a[m])) m = r;
        if (m === i) break;
        [a[i], a[m]] = [a[m], a[i]];
        i = m;
      }
    }
    return top;
  }
}

// Does `from` lead down to `to` through the recipes already chosen?
function leadsTo(from, to, assign) {
  const seen = new Set();
  const todo = [from];
  while (todo.length) {
    const x = todo.pop();
    if (x === to) return true;
    if (seen.has(x)) continue;
    seen.add(x);
    const ri = assign.get(x);
    if (ri !== undefined) for (const [i] of RECIPES[ri].in) todo.push(i);
  }
  return false;
}

/**
 * Every chain that starts with one recipe of the target, smallest first, one at
 * a time. A chain is a choice of one recipe for each item it crafts; the search
 * takes the open chain with the fewest crafted items, settles its next
 * unsettled ingredient every possible way, and a chain with nothing left to
 * settle is the next answer. Since a chain only grows, that order is exact: no
 * chain is skipped, none comes twice, and nothing is cut to keep the search
 * short. `ctx` counts the work; when it passes `ctx.until` the generator yields
 * null to say "ask again for more time".
 */
function* chainsOf(target, first, cook, ctx, have) {
  // size: crafted items so far; leaf: loot items settled as "pick it up".
  const open = new Heap(); // chains that pick up everything the world hands out
  const later = new Heap(); // chains that craft some of it: the detours, searched once the others are done
  open.push({ size: 1, assign: new Map([[target, first.index]]), todo: [...first.in].reverse().map(([i]) => i) });
  while (open.size || later.size) {
    const heap = open.size ? open : later;
    if (ctx.work > ctx.maxWork || open.size + later.size > ctx.maxOpen) {
      if (open.size) ctx.capped = true; else ctx.cappedDetours = true;
      yield null; // stopped here; finder.raise() lets it go on
      continue;
    }
    if (ctx.work >= ctx.until) { yield null; continue; } // out of time for now; nothing is touched, so slicing changes nothing
    ctx.work++;
    const s = heap.pop();
    const todo = s.todo.slice();
    let branched = false;
    while (todo.length) {
      const id = todo.pop();
      if (s.assign.has(id) || s.leaf?.has(id) || rawItem(id) || have?.has(id)) continue; // what you already hold is not crafted again
      const options = (PRODUCED[id] || []).filter((r) => (cook || r.domain !== "cook") && !r.in.some(([i]) => leadsTo(i, id, s.assign) || i === id));
      if (!options.length) continue; // nothing (acyclic) makes it: it is found, not crafted
      for (const r of options) {
        const assign = new Map(s.assign).set(id, r.index);
        (s.det || lootItem(id) ? later : open).push({ size: assign.size, assign, leaf: s.leaf, det: s.det || lootItem(id), todo: [...todo, ...[...r.in].reverse().map(([i]) => i)] });
      }
      if (lootItem(id)) (s.det ? later : open).push({ size: s.size, assign: s.assign, leaf: new Set(s.leaf).add(id), det: s.det, todo: [...todo] }); // or just pick it up
      branched = true;
      break;
    }
    if (!branched) yield { choices: s.assign, size: s.assign.size };
  }
}
/**
 * One chain as a tree with its place on the canvas.
 *
 * Every use of an item is a node of its own. A crafted node sits on the floor
 * of its depth; everything that is not crafted in this chain is the foundation
 * and sits on the lowest floor, in a column of its own straight under whatever
 * uses it. Columns are never shared, so a line down to the foundation never
 * runs past another tile. A crafted node stands over the middle of its
 * children's columns.
 */
function layout(target, choices) {
  let count = 0;
  let bad = false;
  const stack = new Set();
  const build = (id, depth) => {
    if (bad) return null;
    // A recipe that takes its own result (2 Cadmium from Cadmium + Chromatic Metal) stands on a Cadmium you already have.
    const selfLoop = depth > 0 && id === target && stack.has(id) && stack.size === 1;
    if ((stack.has(id) && !selfLoop) || ++count > MAX_NODES) { bad = true; return null; } // a loop across branches, or too big
    const ri = selfLoop ? undefined : choices.get(id);
    const node = { id, ri, depth, kids: [] };
    if (ri !== undefined) {
      stack.add(id);
      for (const [ing] of RECIPES[ri].in) {
        const kid = build(ing, depth + 1);
        if (!kid) return null;
        kid.parent = node;
        node.kids.push(kid);
      }
      stack.delete(id);
    }
    return node;
  };
  const root = build(target, 0);
  if (!root) return null;

  const all = [];
  const walk = (n) => { all.push(n); n.kids.forEach(walk); };
  walk(root);
  all.forEach((n, i) => { n.key = String(i); });

  const deepest = Math.max(...all.filter((n) => n.kids.length).map((n) => n.depth), 0);
  const bottom = root.kids.length ? deepest + 1 : 0;
  let col = 0;
  const place = (n) => {
    if (!n.kids.length) {
      n.floor = n === root ? 0 : bottom;
      n.col = col++;
      return;
    }
    n.floor = n.depth;
    n.kids.forEach(place);
    n.col = (n.kids[0].col + n.kids.at(-1).col) / 2;
  };
  place(root);
  root.kids.forEach((k, i) => {
    const mark = (n) => { n.branch = i; n.kids.forEach(mark); };
    mark(k);
  });
  root.branch = 0;

  return {
    root,
    nodes: all.length,
    all,
    choices,
    // The biggest refiner any step needs: as many ingredients as its recipe takes (1 portable, 2 medium, 3 large).
    level: Math.max(0, ...all.filter((n) => n.kids.length).map((n) => refinerLevel(RECIPES[n.ri]))),
    leaves: new Set(all.filter((n) => !n.kids.length && n !== root).map((n) => n.id)),
    height: bottom + 1,
    width: col,
  };
}

/**
 * The pyramids of `target`, found on demand: finder.more(count, budget) adds up
 * to `count` more (smallest first, every recipe of the target shown as soon as
 * it has one) within `budget` search steps; `done` says nothing is left.
 * `have`: ids of what the visitor holds (or null). Such an item is taken as it is, never crafted, so a chain that
 * makes a thing you already have, from materials further down, is not even looked for: it is a shortcut missed.
 * `runs` is how many times the top recipe is run: what a chain costs, and so
 * which one beats which, is worked out for that number (batches are whole).
 *
 * Nothing found is thrown away. `out` holds the chains no other one beats: not
 * a recipe more of anything, not a step more, not a floor more. The rest go to
 * `hidden`, each marked with `why`: a chain another one beats, or one that
 * crafts what the world hands out (a detour round a thing lying there). `skipped`
 * counts chains found but too big to draw.
 */
export function finder(target, { cook = false, runs = 1, have = null } = {}) {
  const ctx = { work: 0, until: Infinity, capped: false, cappedDetours: false, maxWork: MAX_WORK, maxOpen: MAX_OPEN };
  // A recipe that takes its own result (Cadmium + Chromatic Metal -> 2 Cadmium) is never thrown away: its chain stands on
  // a Cadmium you already have. When it is all there is, it is the answer; beside other recipes it is put away under
  // "hidden", for it only multiplies what you already hold.
  const loops = new Set((PRODUCED[target] || []).filter((r) => r.in.some(([i]) => i === target)).map((r) => r.index));
  const only = loops.size > 0 && (PRODUCED[target] || []).every((r) => loops.has(r.index) || (!cook && r.domain === "cook"));
  const gens = (PRODUCED[target] || []).filter((r) => cook || r.domain !== "cook")
    .map((r) => ({ it: chainsOf(target, r, cook, ctx, have), head: null, done: false, taken: 0 }));
  const out = [];
  const hidden = [];
  const rivals = new Map(); // result of one run -> the pyramids kept for it
  if (!gens.length) out.push(layout(target, new Map())); // nothing makes it: it is found, not crafted
  const hide = (p, why) => {
    p.why = why;
    if (hidden.length < HIDDEN_MAX) hidden.push(p); else self.hiddenMore++;
  };
  const self = {
    out,
    hidden,
    hiddenMore: 0,
    skipped: 0,
    get hiddenCount() { return hidden.length + self.hiddenMore; },
    get done() { return ctx.capped || ctx.cappedDetours || gens.every((g) => g.done && !g.head); },
    get capped() { return ctx.capped; },
    get cappedDetours() { return ctx.cappedDetours; },
    /** Search deeper: four times the steps and open chains. */
    raise() { ctx.maxWork *= 4; ctx.maxOpen *= 4; ctx.capped = false; ctx.cappedDetours = false; },
    more(count, budget = 200000) {
      ctx.until = ctx.work + budget;
      let added = 0;
      while (added < count) {
        let best = null;
        let paused = false;
        for (const g of gens) {
          if (!g.head && !g.done) {
            const v = g.it.next();
            if (v.done) g.done = true;
            else if (v.value === null) { paused = true; break; }
            else g.head = v.value;
          }
          if (g.head && (!best || (g.taken ? g.head.size : -1) < (best.taken ? best.head.size : -1))) best = g;
        }
        if (paused || !best) break;
        const { choices } = best.head;
        best.head = null;
        best.taken++;
        const p = layout(target, choices);
        if (!p) { self.skipped++; continue; }
        const cost = costOf(p, runs);
        // (the reasons are English keys: the view words them with t())
        if (!only && loops.has(choices.get(target))) { hide(p, N_("multiplies what you already have")); continue; }
        if ([...choices.keys()].some((id) => id !== target && lootItem(id))) { hide(p, N_("a detour: it makes what can be picked up")); continue; }
        // One that takes no less of anything and no fewer steps than another with the same result is
        // that other one with something added (or its summands in another order): the smaller stays up.
        const kept = (rivals.get(cost.yield) ?? rivals.set(cost.yield, []).get(cost.yield));
        if (kept.some((q) => beats(q.cost, cost))) { hide(p, N_("no better than another chain")); continue; }
        for (let i = kept.length - 1; i >= 0; i--) {
          if (beats(cost, kept[i].cost)) { out.splice(out.indexOf(kept[i].p), 1); hide(kept[i].p, N_("no better than another chain")); kept.splice(i, 1); }
        }
        kept.push({ p, cost });
        out.push(p);
        added++;
      }
      return added;
    },
  };
  return self;
}
/**
 * One chain as a pyramid with its figures, from a choice of recipe for each item that is crafted in it (`choices`:
 * {item: recipe index}, or a Map): how the short path of the Path page (lib/core.js `plan`) is drawn like the Tree's.
 * `runs` is how many times the top recipe runs. Null when the chain is too big to draw.
 */
export function pyramidOf(target, choices, runs = 1) {
  const p = layout(target, choices instanceof Map ? choices : new Map(Object.entries(choices)));
  if (p) costOf(p, runs);
  return p;
}
/** Pyramids for `target`, smallest first. {pyramids, truncated}: the first `limit` found. */
export function pyramids(target, { cook = false, limit = 1500, budget = 600000 } = {}) {
  const f = finder(target, { cook });
  f.more(limit, budget);
  const list = [...f.out].sort(bySize);
  return { pyramids: list, truncated: !f.done };
}

const RARITY_RANK = { Common: 0, Uncommon: 1, Rare: 2 }; // the game's own word for the item, nothing of ours

// What a pyramid costs. The hard part (which one beats which) is the raw materials, steps, floors and refiner; the
// rest is for ordering and for the labels, never for hiding, and is put on `p.m`:
//   cost    the raw materials at the game's price per piece, units
//   time    machine-time of all refining steps added up (one refiner doing them in turn); cooking has no
//           trustworthy time in the data, so a chain with cooking says so (`cooks`) and is not ranked by time
//   rarity  the rarest raw material it needs, by the game's rarity (0 common, 1 uncommon, 2 rare)
//   profit  what one run of the top sells for, less the raw materials (base prices)
function costOf(p, runs) {
  const { info, total } = plan(p, runs);
  const made = info.get(p.root.key)?.yield ?? 1;
  let time = 0;
  let cooks = false;
  for (const n of p.all) {
    if (!n.kids.length) continue;
    const r = RECIPES[n.ri];
    if (r.domain === "refine") time += info.get(n.key).batches * r.time; else cooks = true;
  }
  const cost = total.reduce((sum, [id, n]) => sum + n * (D.items[id]?.value ?? 0), 0);
  p.m = {
    cost, time, cooks, yield: made,
    rarity: Math.max(0, ...total.map(([id]) => RARITY_RANK[D.items[id]?.rar] ?? 0)),
    profit: made * (D.items[p.root.id]?.value ?? 0) - cost,
  };
  return { yield: made, raw: new Map(total), steps: p.all.filter((n) => n.kids.length).length, height: p.height, level: p.level };
}
// `a` is at least as good as `b` everywhere, so `b` adds nothing: every raw material of `a` is also in `b` in no
// greater amount, and `a` has no more steps, no more floors and needs no bigger refiner. (Exactly the things the
// visitor can filter by, so that no filter can ever uncover a hole where a hidden chain would have been the answer.) Of two equal ones the earlier (smaller) stays.
function beats(a, b) {
  if (a.steps > b.steps || a.height > b.height || a.level > b.level) return false;
  for (const [id, n] of a.raw) if (!(b.raw.get(id) >= n)) return false;
  return true;
}
/** Smaller pyramids first. */
export const bySize = (a, b) => a.height - b.height || a.nodes - b.nodes || a.width - b.width;
/**
 * What every step of a chain needs when the top recipe is run `runs` times.
 * The top node is exactly runs x what one run makes; every ingredient is the
 * recipe's amount times that, so doubling `runs` doubles every number. A step
 * below the top runs as many whole batches as it takes to cover what its
 * parent asks for, and asks its own ingredients for exactly that many batches.
 * `info` maps a node's key to {need, batches, yield}; `total` is what to
 * gather overall: the foundation nodes added up.
 */
export function plan(p, runs) {
  const info = new Map();
  const fill = (n, need, fixed) => {
    if (!n.kids.length) { info.set(n.key, { need }); return; }
    const r = RECIPES[n.ri];
    const batches = fixed ?? Math.ceil(need / r.out[1]);
    info.set(n.key, { need: fixed ? batches * r.out[1] : need, batches, yield: batches * r.out[1] });
    r.in.forEach(([, per], i) => fill(n.kids[i], batches * per));
  };
  fill(p.root, 0, Math.max(1, runs));
  const sum = new Map();
  for (const n of p.all) if (!n.kids.length && n !== p.root) sum.set(n.id, (sum.get(n.id) ?? 0) + info.get(n.key).need);
  return { info, total: [...sum].sort((a, b) => b[1] - a[1]) };
}

// -- order: which pyramids come first -----------------------------------------------------------------------
// No hidden weights: "the best" are the pyramids nothing beats on cost, time, floors and rarity at once (layer 0),
// then the ones only layer 0 beats (layer 1), and so on. A chain with cooking is left out of the time axis.

const axes = (a, b) => {
  const out = [[a.m.cost, b.m.cost], [a.height, b.height], [a.m.rarity, b.m.rarity]];
  if (!a.m.cooks && !b.m.cooks) out.push([a.m.time, b.m.time]);
  return out;
};
function beatsOn(a, b) {
  let better = false;
  for (const [x, y] of axes(a, b)) {
    if (x > y) return false;
    if (x < y) better = true;
  }
  return better;
}

/** Map pyramid -> layer (0 = nothing beats it). */
export function paretoLayers(list) {
  const layers = [];
  const of = new Map();
  for (const p of [...list].sort((a, b) => a.m.cost - b.m.cost || a.height - b.height)) {
    let i = 0;
    while (i < layers.length && layers[i].some((q) => beatsOn(q, p))) i++;
    (layers[i] ??= []).push(p);
    of.set(p, i);
  }
  return of;
}

/** The orders of the chain list, as [key, English text]: the view words them with t(). */
export const ORDERS = [
  ["best", N_("best first")], ["size", N_("by size")], ["cost", N_("by cost of raws")], ["time", N_("by time")],
  ["floors", N_("by floors")], ["rarity", N_("by rarity of raws")], ["profit", N_("by gain")],
];

// A chain's name, for the last tie: two chains that are equal in everything else still come in one fixed order.
const chainKey = (p) => (p.key ??= [...p.choices].sort((a, b) => (a[0] < b[0] ? -1 : 1)).join("|"));

/** `list` in the chosen order; ties fall back to the size order, so the result never jumps about. */
export function ordered(list, order, layers) {
  const by = {
    best: (a, b) => layers.get(a) - layers.get(b) || a.m.cost - b.m.cost,
    size: () => 0,
    cost: (a, b) => a.m.cost - b.m.cost,
    time: (a, b) => (a.m.cooks - b.m.cooks) || a.m.time - b.m.time,
    floors: (a, b) => a.height - b.height,
    rarity: (a, b) => a.m.rarity - b.m.rarity,
    profit: (a, b) => b.m.profit - a.m.profit,
  }[order] ?? (() => 0);
  return [...list].sort((a, b) => by(a, b) || bySize(a, b) || (chainKey(a) < chainKey(b) ? -1 : chainKey(a) > chainKey(b) ? 1 : 0));
}
/**
 * The visitor's own filters over one pyramid: at most `maxFloors` floors (0: any), a refiner no bigger than
 * `maxLevel` (0: any), none of the `excluded` raw materials in the foundation, and, with `mine`, every piece of the
 * foundation held (`have`: id -> count).
 */
export function passes(p, { maxFloors = 0, maxLevel = 0, excluded = new Set(), mine = false, have = {} } = {}) {
  return (!maxFloors || p.height <= maxFloors)
    && (!maxLevel || p.level <= maxLevel)
    && ![...p.leaves].some((id) => excluded.has(id))
    && (!mine || [...p.leaves].every((id) => have[id] > 0));
}



