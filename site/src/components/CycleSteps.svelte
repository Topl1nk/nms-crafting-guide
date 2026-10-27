<script>
  // A full cycle in the style of the pyramids: one branch for each run of the loop, side by side. Under a run, what you put in;
  // the run itself, what you get. Nothing else is added to the tree.
  import Tile from "./Tile.svelte";
  import { fmtInt } from "../lib/core.js";
  import { RECIPES } from "../lib/data.js";
  import { t } from "../lib/i18n.js";

  // `mult`: how many times everything is taken (a multiplier of the whole scheme: every count on a tile is that many times more).
  let { cycle, mult = 1 } = $props();

  const BRANCH = ["#5ccbf0", "#f1c265", "#64f19f", "#c595f6", "#f09d5c", "#f37791", "#6af2e0", "#abbbf7"];
  const COL = 120, TILE = 108, ROWH = 156, TILEH = 108, PAD = 16, CAP = 0, R = 10;

  // Four or more runs of one recipe one after another are one branch ("×13"); fewer stay a branch each.
  const groups = $derived.by(() => {
    const out = [];
    for (const index of cycle.order) {
      if (out.at(-1)?.index === index) out.at(-1).times++; else out.push({ index, times: 1 });
    }
    return out.flatMap((g) => (g.times < 4 ? Array.from({ length: g.times }, () => ({ index: g.index, times: 1 })) : [g]));
  });

  // Each run is a branch of its own, side by side and never crossing: what you put in under it, what you get above it. Nothing
  // else: the oldest stock is used first, and no count or note is added to the tree.
  const graph = $derived.by(() => {
    const queue = new Map(); // item -> [{tile, left}]
    const give = (tile, id, n) => { if (!queue.has(id)) queue.set(id, []); queue.get(id).push({ tile, left: n }); };
    const start = { kind: "start" };
    for (const [id, n] of cycle.seed) give(start, id, n);
    const runs = groups.map((g, j) => {
      const r = RECIPES[g.index];
      const t = { kind: "run", step: j + 1, g, id: r.out[0], qty: r.out[1] * g.times * mult, ins: [] };
      for (const [id, need] of r.in) {
        let n = need * g.times;
        const q = queue.get(id) ?? [];
        while (n > 0 && q.length) {
          const h = q[0];
          const m = Math.min(n, h.left);
          t.ins.push({ id, qty: m * mult });
          h.left -= m;
          n -= m;
          if (!h.left) q.shift();
        }
      }
      give(t, t.id, t.qty);
      return t;
    });
    // Columns, branch after branch.
    const tiles = [];
    const wires = [];
    let c = 0;
    for (const t of runs) {
      const n = Math.max(1, t.ins.length);
      t.col = c + (n - 1) / 2;
      t.ins.forEach((s, i) => { tiles.push({ key: `${t.step}i${i}`, id: s.id, qty: s.qty, floor: 0, col: c + i }); wires.push({ from: c + i, ff: 0, to: t.col, tf: 1, n: s.qty, k: t.step * 10 + i }); });
      tiles.push({ key: `${t.step}r`, id: t.id, qty: t.qty, floor: 1, col: t.col, kind: "run", step: t.step, g: t.g });
      t.start = c;
      t.n = n;
      c += n + 0.4;
    }
    return { tiles, wires, runs, cols: c };
  });

  const px = (col) => PAD + CAP + col * COL + COL / 2;
  const top = (floor) => PAD + (1 - floor) * ROWH;
  const W = $derived(PAD * 2 + CAP + graph.cols * COL);
  const H = $derived(PAD * 2 + ROWH + TILEH);
  const colour = (i) => BRANCH[i % BRANCH.length];

  function rounded(raw) {
    const pts = raw.filter((q, i) => i === 0 || q[0] !== raw[i - 1][0] || q[1] !== raw[i - 1][1]);
    let d = `M${pts[0][0]} ${pts[0][1]}`;
    for (let i = 1; i < pts.length - 1; i++) {
      const [x0, y0] = pts[i - 1];
      const [cx, cy] = pts[i];
      const [nx, ny] = pts[i + 1];
      const r = Math.min(R, Math.hypot(cx - x0, cy - y0) / 2, Math.hypot(nx - cx, ny - cy) / 2);
      d += ` L${cx - Math.sign(cx - x0) * r} ${cy - Math.sign(cy - y0) * r} Q${cx} ${cy} ${cx + Math.sign(nx - cx) * r} ${cy + Math.sign(ny - cy) * r}`;
    }
    const [lx, ly] = pts.at(-1);
    return `${d} L${lx} ${ly}`;
  }
  // From the top edge of the tile that gives, up to a line under the tile that takes, across, and into it.
  const paths = $derived(graph.wires.map((w, i) => {
    const busY = top(w.tf) + TILEH + (ROWH - TILEH) / 2;
    return { k: w.k, d: rounded([[px(w.from), top(w.ff)], [px(w.from), busY], [px(w.to), busY], [px(w.to), top(w.tf) + TILEH]]), col: colour(Math.floor(w.k / 10)), lx: px(w.from), ly: busY, n: w.n };
  }));
  const FLOORS = [0, 1];
</script>

<article class="pyr">
  <header>
    <b>{t("Full loop")}</b>
  </header>
  <div class="board" style="width:{W}px;height:{H}px">
    <svg width={W} height={H} aria-hidden="true">
      {#each FLOORS as f}
        <rect class="step" x={PAD} y={top(f) - 14} width={W - PAD * 2} height={TILEH + 28} rx="14" style="--k:{4 + (1 - f) * 1.4}%" />
      {/each}
      {#each paths as w (w.k)}<path d={w.d} style="--c:{w.col}" />{/each}
    </svg>
    {#each graph.tiles as t (t.key)}
      <Tile id={t.id} href="#/recipes?item={encodeURIComponent(t.id)}" badge={`×${fmtInt(t.qty)}`} mark={t.kind === "run" ? "apex" : ""}
        style="position:absolute; left:{px(t.col) - TILE / 2}px; top:{top(t.floor)}px; z-index:2" />
    {/each}
  </div>
</article>
<style>
  .pyr { flex: none; padding: 10px 12px 12px; border-radius: 14px; background: var(--p-panel); border: 1px solid var(--p-outline); --surface: var(--p-raised); }
  header { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-bottom: 8px; white-space: nowrap; }
  .board { position: relative; margin: 0 auto; }
  svg { position: absolute; inset: 0; pointer-events: none; overflow: visible; }
  .step { fill: color-mix(in srgb, var(--p-accent) var(--k), transparent); stroke: color-mix(in srgb, var(--p-accent) 22%, transparent); stroke-width: 1; }
  path { fill: none; stroke: var(--c); stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; opacity: 0.9; }
</style>








