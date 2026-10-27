// Real loops in the recipe book: sets of recipes that, run together, take nothing from outside and give back more than
// they take. (1 Chlorine + 2 Oxygen -> 6 Chlorine is none: the oxygen is spent and nothing makes it again.)
//
// A mix of runs x >= 0 of recipes nets, per item, what it makes less what it takes. A loop is a *smallest* set of recipes
// with a mix whose net is >= 0 for every item (nothing is taken from outside) and > 0 for some (it grows), each recipe of
// the set really used. Found by linear programming over all recipes at once, not by trying pairs:
//
//   for each recipe: force it into the mix and minimise the total runs (a two-phase simplex, below), then try to do
//   without each other recipe of the mix in turn, keeping every one that can go. What is left is minimal.
//
// Pure, no page and no data module: it takes the recipes it is given, so a worker can run it and a test can check it.

const EPS = 1e-9;

/**
 * min sum(z) over z >= 0 with  -A z + s = b  (s >= 0), i.e. A z >= -b.. built from `cols` of A (rows are items).
 * Dense two-phase simplex with Bland's rule (no cycling). Returns the z of each column or null when infeasible.
 */
function solve(A, rows, cols, force, banned) {
  const act = cols.filter((j) => !banned.has(j));
  const n = act.length;
  const m = rows;
  // Row i:  -sum_j A[i][j] z_j + s_i = b_i, with b_i = A[i][force] (the forced run is x_force = 1 + z_force).
  const pos = act.indexOf(force);
  if (pos < 0) return null;
  const width = n + m; // z, slacks, then one artificial per row whose b is negative
  const art = [];
  const rhsOf = (i) => A[i][force];
  for (let i = 0; i < m; i++) if (rhsOf(i) < -EPS) art.push(i);
  const W = width + art.length + 1;
  const T = Array.from({ length: m + 1 }, () => new Float64Array(W));
  const basis = new Int32Array(m);
  let a = 0;
  for (let i = 0; i < m; i++) {
    const b = rhsOf(i);
    const flip = b < -EPS;
    const sign = flip ? -1 : 1;
    for (let k = 0; k < n; k++) T[i][k] = -A[i][act[k]] * sign;
    T[i][n + i] = sign; // the slack
    T[i][W - 1] = Math.abs(b) < EPS ? 0 : b * sign;
    if (flip) { T[i][width + a] = 1; basis[i] = width + a; a++; } else basis[i] = n + i;
  }
  const lastRow = m;

  const pivot = (r, c) => {
    const pr = T[r];
    const pv = pr[c];
    for (let k = 0; k < W; k++) pr[k] /= pv;
    for (let i = 0; i <= m; i++) {
      if (i === r) continue;
      const f = T[i][c];
      if (Math.abs(f) < 1e-14) continue;
      const row = T[i];
      for (let k = 0; k < W; k++) row[k] -= f * pr[k];
    }
    basis[r] = c;
  };
  // Simplex on the objective row `lastRow` (reduced costs, minimise): enter the lowest column with a negative cost.
  const run = (allowed) => {
    for (let guard = 0; guard < 20000; guard++) {
      let c = -1;
      for (let k = 0; k < allowed; k++) if (T[lastRow][k] < -1e-9) { c = k; break; }
      if (c < 0) return true;
      let r = -1;
      let best = Infinity;
      for (let i = 0; i < m; i++) {
        const v = T[i][c];
        if (v > 1e-9) {
          const ratio = T[i][W - 1] / v;
          if (ratio < best - 1e-12 || (Math.abs(ratio - best) <= 1e-12 && basis[i] < basis[r])) { best = ratio; r = i; }
        }
      }
      if (r < 0) return false; // unbounded (cannot happen: sum(z) >= 0)
      pivot(r, c);
    }
    return false;
  };

  if (art.length) {
    // Phase 1: minimise the sum of the artificials.
    T[lastRow].fill(0);
    for (let q = 0; q < art.length; q++) T[lastRow][width + q] = 1;
    for (let i = 0; i < m; i++) if (basis[i] >= width) for (let k = 0; k < W; k++) T[lastRow][k] -= T[i][k];
    if (!run(width)) return null;
    if (-T[lastRow][W - 1] > 1e-7) return null; // the artificials cannot all go: no mix
    // An artificial left in the basis at zero: pivot it out on any real column, or leave the redundant row alone.
    for (let i = 0; i < m; i++) {
      if (basis[i] < width) continue;
      for (let k = 0; k < width; k++) if (Math.abs(T[i][k]) > 1e-9) { pivot(i, k); break; }
    }
  }
  // Phase 2: minimise sum(z).
  T[lastRow].fill(0);
  for (let k = 0; k < n; k++) T[lastRow][k] = 1;
  for (let i = 0; i < m; i++) {
    const cb = basis[i] < n ? 1 : 0;
    if (cb) for (let k = 0; k < W; k++) T[lastRow][k] -= T[i][k];
  }
  if (!run(width)) return null;

  const x = new Map(act.map((j) => [j, 0]));
  for (let i = 0; i < m; i++) if (basis[i] < n) x.set(act[basis[i]], T[i][W - 1]);
  x.set(force, x.get(force) + 1);
  return x;
}

/** Runs as whole numbers, the fewest that keep the proportions; null when none up to 240 turns does. */
function wholeRuns(x) {
  for (let k = 1; k <= 240; k++) {
    if ([...x.values()].every((v) => Math.abs(v * k - Math.round(v * k)) < 1e-4)) return new Map([...x].map(([j, v]) => [j, Math.round(v * k)]));
  }
  return null;
}

/**
 * Every smallest loop of `recipes` ({index, in: [[id, n]], out: [id, q], time, machine}), each handed to `onFound` as soon as
 * it is found: {parts: [{recipe, runs}], net: [[id, n]], seed: [[id, n]], order: [recipe, ...]}. `net` is what one turn (the runs of `parts` once)
 * leaves over, `seed` what has to be at hand once to begin. `stop()` ends the search early. Returns every loop found.
 */
export function findCycles(recipes, { maxSize = 8, onFound = () => {}, stop = () => false } = {}) {
  const rec = recipes.map((r) => ({ index: r.index, ins: Object.fromEntries(r.in), out: r.out[0], q: r.out[1], time: r.time ?? 0 }));

  // Only recipes whose every ingredient some other recipe of the set makes can be in a loop: shrink to that.
  let alive = rec.map((_, k) => k);
  for (;;) {
    const made = new Set(alive.map((k) => rec[k].out));
    const keep = alive.filter((k) => Object.keys(rec[k].ins).every((id) => made.has(id)));
    if (keep.length === alive.length) break;
    alive = keep;
  }
  const items = [...new Set(alive.flatMap((k) => [rec[k].out, ...Object.keys(rec[k].ins)]))];
  const row = new Map(items.map((id, i) => [id, i]));
  const A = Array.from({ length: items.length }, () => new Float64Array(alive.length));
  alive.forEach((k, j) => {
    A[row.get(rec[k].out)][j] += rec[k].q;
    for (const [id, n] of Object.entries(rec[k].ins)) A[row.get(id)][j] -= n;
  });
  const cols = alive.map((_, j) => j);

  const found = new Map();
  const loops = [];
  // One loop of the mix `j0` is forced into, made minimal; `ban`: recipes left out of the search. Null when there is none.
  const minimal = (j0, ban) => {
    const banned = new Set(ban);
    let x = solve(A, items.length, cols, j0, banned);
    if (!x) return null;
    for (const j of [...x].filter(([c, v]) => v > 1e-7 && c !== j0).map(([c]) => c).sort((p, q) => p - q)) {
      if (!(x.get(j) > 1e-7)) { banned.add(j); continue; } // already out of the mix by an earlier step
      banned.add(j);
      const y = solve(A, items.length, cols, j0, banned);
      if (y) x = y; else banned.delete(j);
    }
    return new Map([...x].filter(([, v]) => v > 1e-7));
  };
  const record = (mix) => {
    const key = [...mix.keys()].sort((p, q) => p - q).join(",");
    if (found.has(key)) return;
    const runs = wholeRuns(mix);
    if (!runs) return;
    // What a turn leaves, from the whole runs themselves (not from the floating-point solution).
    const net = new Map();
    for (const [j, r] of runs) {
      const k = alive[j];
      net.set(rec[k].out, (net.get(rec[k].out) ?? 0) + rec[k].q * r);
      for (const [id, n] of Object.entries(rec[k].ins)) net.set(id, (net.get(id) ?? 0) - n * r);
    }
    if ([...net.values()].some((v) => v < -1e-9) || ![...net.values()].some((v) => v > 1e-9)) return; // not a loop that grows
    found.set(key, true);
    const loop = {
      parts: [...runs].map(([j, r]) => ({ recipe: rec[alive[j]].index, runs: r })).sort((p, q) => p.recipe - q.recipe),
      net: [...net].filter(([, v]) => v > 1e-9).sort((p, q) => q[1] - p[1]),
      ...seedOf(runs, alive, rec),
    };
    loops.push(loop);
    onFound(loop);
  };
  // Another loop through the same recipe is found by leaving out, in turn, each recipe of the one found: down to `DEPTH`
  // recipes left out, and only below the loops that are not long (a long one has a thousand cousins and no use).
  const DEPTH = 4;
  for (const j0 of cols) {
    if (stop()) break;
    const seen = new Set();
    const todo = [[]];
    while (todo.length) {
      if (stop()) return loops;
      const ban = todo.pop();
      const key = ban.slice().sort((p, q) => p - q).join(",");
      if (seen.has(key)) continue;
      seen.add(key);
      const mix = minimal(j0, ban);
      if (!mix || mix.size > maxSize) continue;
      record(mix);
      if (ban.length < DEPTH && mix.size <= 6) for (const j of mix.keys()) if (j !== j0) todo.push([...ban, j]);
    }
  }
  return loops;
}
/** What has to be at hand to begin a turn, and an order of its runs that works from it: run what is nearest to ready, lend what is missing. */
function seedOf(runs, alive, rec) {
  const left = new Map([...runs].map(([j, r]) => [alive[j], r]));
  const stock = new Map();
  const seed = new Map();
  const order = [];
  while ([...left.values()].some((r) => r > 0)) {
    let pick = -1;
    let least = Infinity;
    for (const [k, r] of left) {
      if (r <= 0) continue;
      const missing = Object.entries(rec[k].ins).reduce((s, [id, n]) => s + Math.max(0, n - (stock.get(id) ?? 0)), 0);
      if (missing < least) { least = missing; pick = k; }
    }
    for (const [id, n] of Object.entries(rec[pick].ins)) {
      const lack = Math.max(0, n - (stock.get(id) ?? 0));
      if (lack) { seed.set(id, (seed.get(id) ?? 0) + lack); stock.set(id, (stock.get(id) ?? 0) + lack); }
      stock.set(id, stock.get(id) - n);
    }
    stock.set(rec[pick].out, (stock.get(rec[pick].out) ?? 0) + rec[pick].q);
    left.set(pick, left.get(pick) - 1);
    order.push(rec[pick].index);
  }
  return { seed: [...seed], order };
}


/**
 * A loop run for `turns` turns from its seed: the stock before and after, and the stock after each run of the first turn.
 * `get(index)` is the recipe ({in, out}). {start, end: Map id -> n, steps: [{index, stock: [[id, n]]}], short: true when a run lacked something}.
 */
export function simulate(loop, get, turns = 1) {
  const stock = new Map(loop.seed);
  const start = new Map(stock);
  const steps = [];
  let short = false;
  for (let t = 0; t < Math.max(1, turns); t++) {
    for (const index of loop.order) {
      const r = get(index);
      for (const [id, n] of r.in) {
        if ((stock.get(id) ?? 0) < n) short = true;
        stock.set(id, (stock.get(id) ?? 0) - n);
      }
      stock.set(r.out[0], (stock.get(r.out[0]) ?? 0) + r.out[1]);
      if (t === 0) steps.push({ index, stock: [...stock].filter(([, n]) => n !== 0) });
    }
  }
  return { start, end: stock, steps, short };
}


