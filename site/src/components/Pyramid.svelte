<script>
  // One chain as a pyramid. The top item is on top; each floor is made from the
  // floor above; what is only gathered stands in a row along the bottom, every
  // piece straight under the step that uses it. Wires are one straight line down
  // from an item, one across, one down into each ingredient -- never a bend
  // more -- and a branch (an ingredient of the top item and everything under it)
  // keeps one colour. A number on a tile is what *that step* needs; the strip
  // under the pyramid adds up what to gather in all.
  import { D, name } from "../lib/data.js";
  import { fmtInt, fmtSigned, fmtTime } from "../lib/core.js";
  import { plan } from "../lib/tree.js";
  import { t, tn } from "../lib/i18n.js";
  import { RARITIES } from "../lib/words.js";
  import Icon from "./Icon.svelte";
  import ItemIcon from "./ItemIcon.svelte";
  import Tile from "./Tile.svelte";
  import Units from "./Units.svelte";

  let { p, index, target, have = {}, qty = 0, onTip = undefined, layer = undefined, title = undefined } = $props();

  const BRANCH = ["#5ccbf0", "#f1c265", "#64f19f", "#c595f6", "#f09d5c", "#f37791", "#6af2e0", "#abbbf7"];
  const colour = (n) => BRANCH[(n.branch ?? 0) % BRANCH.length];

  // `qty` is how many times the top recipe runs (1 by default): the number on
  // the top tile is then exactly runs x what the recipe makes, and every number
  // below it follows from it.
  const calc = $derived(plan(p, qty || 1));
  const info = (n) => calc.info.get(n.key);

  // The grid: one column per foundation piece, one row per floor.
  const COL = 120, TILE = 108, ROWH = 168, TILEH = 108, PAD = 16, R = 10; // the tile is Tile.svelte's: one square size everywhere
  const px = (n) => PAD + n.col * COL + COL / 2;
  const top = (n) => PAD + n.floor * ROWH;
  const W = $derived(PAD * 2 + p.width * COL);
  const H = $derived(PAD * 2 + (p.height - 1) * ROWH + TILEH);

  // Bends are rounded; a straight run stays a straight run.
  function rounded(raw) {
    const pts = raw.filter((q, i) => i === 0 || q[0] !== raw[i - 1][0] || q[1] !== raw[i - 1][1]);
    let d = `M${pts[0][0]} ${pts[0][1]}`;
    for (let i = 1; i < pts.length - 1; i++) {
      const [px0, py0] = pts[i - 1];
      const [cx, cy] = pts[i];
      const [nx, ny] = pts[i + 1];
      const r = Math.min(R, Math.hypot(cx - px0, cy - py0) / 2, Math.hypot(nx - cx, ny - cy) / 2);
      d += ` L${cx - Math.sign(cx - px0) * r} ${cy - Math.sign(cy - py0) * r} Q${cx} ${cy} ${cx + Math.sign(nx - cx) * r} ${cy + Math.sign(ny - cy) * r}`;
    }
    const [lx, ly] = pts.at(-1);
    return `${d} L${lx} ${ly}`;
  }

  const wires = $derived.by(() => {
    const out = [];
    for (const n of p.all) {
      if (!n.kids.length) continue;
      const busY = top(n) + TILEH + (ROWH - TILEH) / 2;
      // The top item's branches leave side by side, so their colours do not stack on one line.
      n.kids.forEach((k, i) => {
        const x1 = n === p.root ? px(n) + (i - (n.kids.length - 1) / 2) * 10 : px(n);
        out.push({ d: rounded([[x1, top(n) + TILEH], [x1, busY], [px(k), busY], [px(k), top(k)]]), a: n.key, b: k.key, col: colour(k) });
      });
    }
    return out;
  });

  // The steps of the pyramid: one band per floor, as wide as that floor's tiles
  // need and never narrower than the floor above, so the whole is a ziggurat.
  const steps = $derived.by(() => {
    const cx = W / 2;
    let hw = 0;
    return Array.from({ length: p.height }, (_, f) => {
      const tiles = p.all.filter((n) => n.floor === f);
      const reach = Math.max(...tiles.map((n) => Math.abs(px(n) - cx))) + TILE / 2 + 16;
      hw = Math.max(reach, hw + 18, 76);
      // Never wider than the board: a band that reaches past the card is cut at its edge.
      const left = Math.max(4, cx - hw);
      const right = Math.min(W - 4, cx + hw);
      return { x: left, w: right - left, y: top({ floor: f }) - 14, h: TILEH + 28, f };
    });
  });

  // Only the pyramids near the visible part of the canvas are drawn; the rest are empty boxes of the size they had
  // (or are going to have), so a thousand chains cost what a screenful does.
  let seen = $state(false);
  let size = $state(null);
  let drawnW = $state(0);
  let drawnH = $state(0);
  const guess = $derived({ w: Math.max(W + 26, 300), h: H + 150 });
  function watch(node) {
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { seen = true; return; }
      if (drawnW) size = { w: drawnW, h: drawnH };
      seen = false;
    }, { root: node.closest(".canvas"), rootMargin: "900px" });
    io.observe(node);
    return { destroy: () => io.disconnect() };
  }

  // The path from the top down to the tile under the pointer, and everything below it.
  let hot = $state(null);
  const lit = $derived.by(() => {
    if (!hot) return null;
    const set = new Set();
    for (let n = hot; n; n = n.parent) set.add(n.key);
    const down = (n) => { set.add(n.key); n.kids.forEach(down); };
    down(hot);
    return set;
  });

  // A tile opens its own recipe in Craft; a gathered one, whatever touches it.
  const href = (n) => {
    const q = `item=${encodeURIComponent(n.id)}`;
    return n.kids.length ? `#/recipes?${q}&role=output&r=${n.ri}` : `#/recipes?${q}`;
  };

  // The card over a tile: the Tree view draws it, outside the zoomed, scrolling canvas.
  function enter(n, event) {
    hot = n;
    const i = info(n);
    onTip?.({ id: n.id, ri: n.kids.length ? n.ri : null, need: i.need, batches: i.batches, yield: i.yield, rect: event.currentTarget.getBoundingClientRect() });
  }
  function leave() {
    hot = null;
    onTip?.(null);
  }
</script>

<div class="slot" use:watch style={seen ? "" : `width:${(size ?? guess).w}px;height:${(size ?? guess).h}px`}>
{#if seen}
<article class="pyr" bind:clientWidth={drawnW} bind:clientHeight={drawnH}>
  <header>
    <b>{title ?? t("Chain {n}", { n: index + 1 })}</b>{#if p.why} <span class="why">{t(p.why)}</span>{/if}
    <span class="muted">{tn(p.height, "{n} floor|{n} floors")} · {t("tiles: {n}", { n: p.nodes })}</span>
  </header>
  <div class="metrics">
    {#if layer === 0}<span class="best" title={t("No other chain is better than this one at once in cost of raws, time, floors and rarity")}>{t("best")}</span>{/if}
    <span title={t("Raws at the game's base price")}><Units size={14} />{fmtInt(p.m.cost)}</span>
    <span title={p.m.cooks ? t("Refining time; the data has no time for cooking") : t("All the steps in turn on one refiner")}><Icon name="clock" size={14} />{p.m.time ? fmtTime(p.m.time) : ""}{p.m.cooks ? (p.m.time ? ` + ${t("cooking")}` : t("cooking")) : ""}</span>
    <span title={t("The rarest raw in the base, by the game's rarity")} style={p.m.rarity ? `color:${RARITIES[["", "Uncommon", "Rare"][p.m.rarity]][1]}` : ""}><Icon name="gauge" size={14} />{[t("common raws"), t("uncommon raws"), t("rare raws")][p.m.rarity]}</span>
    <span title={t("Price of one run's result minus the raws, at base prices")} class:neg={p.m.profit < 0}><Units size={14} />{fmtSigned(p.m.profit)}</span>
  </div>

  <div class="board" style="width:{W}px;height:{H}px">
    <svg width={W} height={H} aria-hidden="true">
      {#each steps as s (s.f)}
        <rect class="step" x={s.x} y={s.y} width={s.w} height={s.h} rx="14" style="--k:{4 + s.f * 1.6}%" />
      {/each}
      {#each wires as w (w.a + ">" + w.b)}
        <path d={w.d} style="--c:{w.col}" class:dim={lit && !(lit.has(w.a) && lit.has(w.b))} class:on={lit && lit.has(w.a) && lit.has(w.b)} />
      {/each}
    </svg>

    {#each p.all as n (n.key)}
      {@const i = info(n)}
      {@const got = have[n.id] ?? 0}
      <Tile id={n.id} href={href(n)} badge={`×${fmtInt(i.need)}`} tone={got >= i.need ? "enough" : got > 0 ? "some" : ""}
        mark={n === p.root ? "apex" : !n.kids.length ? "leaf" : ""} dim={Boolean(lit && !lit.has(n.key))}
        style="position:absolute; left:{px(n) - TILE / 2}px; top:{top(n)}px; z-index:2" onmouseenter={(e) => enter(n, e)} onmouseleave={leave} />
    {/each}
  </div>

  <footer>
    <b>{t("Total to gather")}</b>
    {#each calc.total as [id, n] (id)}
      <a class="sum" class:ok={(have[id] ?? 0) >= n} href="#/recipes?item={encodeURIComponent(id)}" draggable="false" title={t("{item}: need {n}, you have {have}", { item: name(id), n: fmtInt(n), have: fmtInt(have[id] ?? 0) })}>
        <ItemIcon {id} size={26} /><span>{name(id)}</span><i>×{fmtInt(n)}</i>
      </a>
    {/each}
  </footer>
</article>
{/if}
</div>

<style>
  .slot { flex: none; }
  .pyr {
    flex: none; padding: 10px 12px 12px; border-radius: 14px;
    background: var(--p-panel); border: 1px solid var(--p-outline);
    --surface: var(--p-raised); /* the tiles on it take their tone from this */
  }
  header { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-bottom: 8px; white-space: nowrap; }
  .board { position: relative; margin: 0 auto; }
  svg { position: absolute; inset: 0; pointer-events: none; overflow: visible; }
  .step { fill: color-mix(in srgb, var(--p-accent) var(--k), transparent); stroke: color-mix(in srgb, var(--p-accent) 22%, transparent); stroke-width: 1; }
  path { fill: none; stroke: var(--c); stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; opacity: 0.9; transition: opacity 0.1s; }
  path.dim { opacity: 0.15; }
  path.on { stroke-width: 3.5; opacity: 1; }

  .why { margin-left: 8px; padding: 2px 10px; border-radius: 999px; font-size: 0.75rem; color: var(--p-orange); background: color-mix(in srgb, var(--p-orange) 14%, transparent); }
  .metrics { display: flex; flex-wrap: wrap; gap: 4px 14px; margin: -2px 0 8px; font-size: 0.8rem; color: var(--p-muted); }
  .metrics span { display: inline-flex; align-items: center; gap: 5px; white-space: nowrap; }
  .metrics :global(.ic) { color: var(--p-faint); }
  .metrics .best { padding: 1px 10px; border-radius: 999px; font-weight: 700; color: var(--p-green); background: color-mix(in srgb, var(--p-green) 14%, transparent); }
  .metrics .neg { color: var(--p-red); }
  footer { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--p-outline); max-width: 100%; }
  footer b { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--p-faint); margin-right: 4px; }
  .sum {
    display: inline-flex; align-items: center; gap: 6px; height: 34px; padding: 0 10px 0 4px; border-radius: 999px;
    background: var(--p-raised); border: 1px solid var(--p-outline); color: var(--p-text); text-decoration: none; font-size: 0.85rem; white-space: nowrap;
  }
  .sum i { font-style: normal; font-weight: 700; color: var(--p-orange); }
  .sum.ok i { color: var(--p-green); }
  .sum:hover { border-color: var(--p-edge-accent); }
</style>







