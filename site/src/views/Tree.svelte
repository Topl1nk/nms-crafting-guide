<script>
  // The craft tree: #/tree/ITEM?cook=0&qty=. Every way to craft the item as a
  // pyramid -- the item itself on top of every one, smallest pyramid on the
  // left, biggest on the right -- on one canvas you can drag and zoom, with how
  // much of everything each chain needs for the amount you ask for.
  import Check from "../components/Check.svelte";
  import Icon from "../components/Icon.svelte";
  import ItemIcon from "../components/ItemIcon.svelte";
  import PanCanvas from "../components/PanCanvas.svelte";
  import Pyramid from "../components/Pyramid.svelte";
  import ZoomBar from "../components/ZoomBar.svelte";
  import TreePicker from "../components/TreePicker.svelte";
  import Reset from "../components/Reset.svelte";
  import Select from "../components/Select.svelte";
  import RecipeTip from "../components/RecipeTip.svelte";
  import { D, name, PRODUCED } from "../lib/data.js";
  import { inventory } from "../lib/inventory.svelte.js";
  import { arrival, replace } from "../lib/router.svelte.js";
  import { collate, t, tn } from "../lib/i18n.js";
  import { refiners } from "../lib/options.js";
  import { closeOutside } from "../lib/util.js";
  import { applyFacets, facets, flag } from "../lib/facets.js";
  import { bySize, finder, ORDERS, ordered, paretoLayers, passes } from "../lib/tree.js";

  const { params, arg: target } = arrival();
  const known = Boolean(D.items[target] || PRODUCED[target]);

  // Cooking: no opinion (every craft counts, cooking included), ✔ only chains that cook, − none that cook (?cook=1, ?cook=0).
  let cook = $state(params.get("cook") === "0" ? "not" : params.get("cook") === "1");
  const withCook = $derived(cook !== "not");
  // null = "one batch of the top recipe" (nothing makes 1 Silver, a batch makes 250).
  let qty = $state(params.has("qty") ? Math.max(1, Number(params.get("qty"))) : null);
  let mine = $state(false); // false: no opinion, true: only what you hold, "not": nothing that is only what you hold
  let maxFloors = $state(0); // 0 = any
  let maxLevel = $state(0); // the biggest refiner allowed: 1 portable, 2 medium; 0 = any
  let excluded = $state(new Set()); // base materials the visitor does not want in the foundation
  let zoom = $state(1);
  let pan = $state();
  let limit = $state(24);

  // The chains are found a little at a time (lib/tree.js finder), smallest first,
  // so the first ones are on the canvas at once and the biggest are reached by
  // asking for more -- nothing is left out, only left for later.
  const LOAD_FIRST = 120;
  let fnd = null;
  let loaded = $state.raw([]);
  let done = $state(false);
  let skipped = $state(0);
  let hidden = $state.raw([]); // found, but another chain is as good in everything, or it is a detour round the loot
  let hiddenCount = $state(0);
  let showHidden = $state(false);
  let order = $state("best");
  let capped = $state(false);
  let cappedDetours = $state(false);
  let halt = false;
  let working = $state(false);
  let loadMax = $state(1500);
  let busy = $state(known);

  async function pump(f, wanted) {
    working = true;
    halt = false;
    while (f === fnd && !f.done && !halt && f.out.length < wanted) {
      f.more(40, 40000);
      loaded = [...f.out].sort(bySize);
      skipped = f.skipped;
      hidden = f.hidden.length ? [...f.hidden] : [];
      hiddenCount = f.hiddenCount;
      capped = f.capped;
      cappedDetours = f.cappedDetours;
      done = f.done;
      busy = false;
      await new Promise((r) => setTimeout(r, 0));
    }
    if (f === fnd) { done = f.done; skipped = f.skipped; working = false; busy = false; }
  }
  $effect(() => {
    const runs = Math.max(1, Math.floor(Number(qty)) || 1); // which chain beats which depends on how many runs
    // "Only my things": the foundation is what you hold, and what you hold is not made again further up.
    const holds = mine === true && holding ? new Set(holding.split(",")) : null;
    if (!known) return;
    busy = true; done = false; capped = false; cappedDetours = false; loaded = []; loadMax = 1500; hidden = []; hiddenCount = 0;
    const f = (fnd = finder(target, { cook: withCook, runs, have: holds }));
    const timer = setTimeout(() => pump(f, LOAD_FIRST), 40);
    return () => { clearTimeout(timer); if (fnd === f) fnd = null; };
  });
  // A filter that leaves too few on the canvas goes on searching by itself, up to a point.
  $effect(() => {
    if (fnd && !busy && !working && !done && shown.length < limit && loaded.length < loadMax) pump(fnd, loaded.length + 150);
  });
  const deeper = () => { fnd.raise(); done = false; capped = false; cappedDetours = false; pump(fnd, loaded.length + 1500); };
  const more = () => { loadMax += 1500; pump(fnd, loaded.length + 1500); };
  const toTheEnd = () => { loadMax = Infinity; pump(fnd, Infinity); };
  // What is on the canvas: the chains nothing beats, and, when asked, the ones put away.
  const pool = $derived(showHidden ? [...loaded, ...hidden].sort(bySize) : loaded);
  const have = $derived(inventory.items);
  const holding = $derived(Object.keys(inventory.items).filter((id) => inventory.items[id] > 0).sort().join(","));
  const haveAny = $derived(Object.keys(have).length > 0);

  // Every gathered material that some chain stands on, with how many chains use it.
  const base = $derived.by(() => {
    const count = new Map();
    for (const p of pool) for (const id of p.leaves) count.set(id, (count.get(id) ?? 0) + 1);
    return [...count].sort((a, b) => b[1] - a[1] || collate(name(a[0]), name(b[0])));
  });

  // The visitor's filters: only the ones that still tell something apart are offered, and one that would leave nothing
  // (or change nothing) is let go. While the chains are still coming in, nothing is hidden: the list is not final.
  const heldAll = (p) => [...p.leaves].every((id) => have[id] > 0);
  const kept = $derived(excluded.size || mine || cook === true
    ? pool.filter((p) => passes(p, { excluded }) && flag(mine, heldAll(p)) && flag(cook, p.m.cooks))
    : pool);
  const defs = $derived([
    { key: "maxFloors", options: FLOORS, neutral: 0, test: (p, v) => passes(p, { maxFloors: v }) },
    { key: "maxLevel", options: REFINERS, neutral: 0, test: (p, v) => passes(p, { maxLevel: v }) },
  ]);
  const fx = $derived(facets(kept, defs, { maxFloors, maxLevel }));
  const settled = $derived(done && !working);
  const matched = $derived(settled ? applyFacets(kept, defs, fx.effective) : kept.filter((p) => passes(p, { maxFloors, maxLevel })));
  // "The best" are worked out among what is left on the canvas, so a filter never leaves it without one.
  const layers = $derived(paretoLayers(matched));
  const shown = $derived(ordered(matched, order, layers));
  const filtered = $derived(maxFloors || maxLevel || excluded.size || mine || cook);

  $effect(() => {
    if (!target) return;
    replace(`#/tree/${encodeURIComponent(target)}${cook !== false || qty ? `?${new URLSearchParams({ ...(cook === "not" ? { cook: "0" } : cook ? { cook: "1" } : {}), ...(qty ? { qty } : {}) })}` : ""}`);
  });
  // A new filter starts the canvas over at the first 24 (but a refresh of the save does not).
  $effect(() => { cook; maxFloors; maxLevel; excluded; mine; order; limit = 24; });

  function toggle(id) {
    const next = new Set(excluded);
    if (!next.delete(id)) next.add(id);
    excluded = next;
  }
  function reset() { maxFloors = 0; maxLevel = 0; excluded = new Set(); mine = false; cook = false; }

  // The recipe card over the tile under the pointer, a moment after it arrives.
  let tip = $state.raw(null);
  let tipTimer;
  function onTip(next) {
    clearTimeout(tipTimer);
    if (!next) { tip = null; return; }
    tipTimer = setTimeout(() => { tip = pan?.moved() ? null : next; }, 120);
  }
  const fit = () => pan.fit();

  const FLOORS = [[0, t("any number")], ...[2, 3, 4, 5, 6, 8].map((n) => [n, t("up to {n}", { n })])];
  const REFINERS = refiners();
  const ORDER_LIST = ORDERS.map(([k, label]) => [k, t(label)]);
  const empty = $derived(!busy && (!loaded.length || (loaded.length === 1 && loaded[0].height === 1)));
</script>

{#if !target}
  <TreePicker />
{:else if !known}
  <p class="pad">{t("There is no such item:")} <code>{target}</code>. <a href="#/tree">{t("Choose another")}</a></p>
{:else}
  <div class="fbar">
    <h1><ItemIcon id={target} size={32} /><span>{t("Tree: {item}", { item: name(target) })}</span></h1>
      <Reset active={filtered} onclick={reset} />
    <a class="btn other" href="#/tree" title={t("Every item that can be made")}><Icon name="tree" size={16} />{t("Another item")}</a>
    <label class="fsel qty" class:on={(qty || 1) > 1} title={t("How many batches of the top recipe to run. Every number on the tiles is multiplied by this.")}>
      <span>{t("Batches")}</span><span class="qfield"><input type="number" min="1" max="9999" placeholder="1" bind:value={qty}>
      <span class="qtystep"><button type="button" tabindex="-1" aria-label="+" onclick={() => { qty = Math.min(9999, (qty || 1) + 1); }}></button><button type="button" tabindex="-1" aria-label="−" onclick={() => { qty = Math.max(1, (qty || 1) - 1); }}></button></span></span></label>

    {#if !empty}
      <Select hidden={!(!settled || fx.show.maxFloors)} label={t("Floors")} value={settled ? fx.effective.maxFloors : maxFloors} options={settled ? fx.options.maxFloors : FLOORS} all={FLOORS} neutral={0} onchange={(v) => { maxFloors = v; }} title={t("How many floors the pyramid has: fewer floors, fewer steps in a row")} />
      <Select hidden={!(!settled || fx.show.maxLevel)} label={t("Refiner")} value={settled ? fx.effective.maxLevel : maxLevel} options={settled ? fx.options.maxLevel : REFINERS} all={REFINERS} neutral={0} onchange={(v) => { maxLevel = v; }} title={t("The biggest refiner you have: chains that need a bigger one leave the canvas")} />
      <details class="drop" use:closeOutside>
        <summary class="btn" class:active={excluded.size > 0} title={t("Remove the chains that have the chosen material in their base")}>{excluded.size ? t("Without raws: {n}", { n: excluded.size }) : t("Exclude raws")}</summary>
        <div class="drop-pop">
          <p class="muted small">{t("Click a material and the chains that stand on it disappear. The number is how many chains it is in.")}</p>
          <div class="mats">
            {#each base as [id, n] (id)}
              <button type="button" class="mat" class:off={excluded.has(id)} onclick={() => toggle(id)} title={name(id)}>
                <ItemIcon {id} size={28} /><span class="t">{name(id)}</span><i>{n}</i>
              </button>
            {/each}
          </div>
          <div class="pop-acts">
            <button class="btn" onclick={() => { excluded = new Set(base.map(([id]) => id)); }}>{t("Select all")}</button>
            <button class="btn" onclick={() => { excluded = new Set(); }} disabled={!excluded.size}>{t("Clear all")}</button>
          </div>
        </div>
      </details>
      <Check label={t("Cooking")} bind:value={cook} title={t("Chains where something is cooked")} />
      <Check label={t("My items")} bind:value={mine}
        title={t("Only chains where everything to gather is already yours; what you have is not made again")} />
      <Select label={t("Order")} bind:value={order} options={ORDER_LIST} title={t("Best: chains that no other beats at once in cost of raws, time, floors and rarity. The other orders go by one figure.")} />


    {/if}
  </div>

  {#if !empty}
    <div class="count row" title={t("On top the item you want, under it what it is made from; the dotted line at the bottom is what is only gathered. ×N is how many that step needs. A line's colour is its own branch. The canvas moves with the mouse, Ctrl + wheel zooms.")}>
      <span class="what">
      {t("Chains:")} <b>{shown.length}</b>{shown.length !== pool.length ? ` ${t("of {n}", { n: pool.length })}` : ""}
      {#if shown.length > limit}· {t("the first {n} are on the canvas", { n: limit })}{/if}
      · {t("the smallest on the left")}
      {#if working}<span class="muted">· {t("searching further…")}</span> <button class="link" onclick={() => { halt = true; }}>{t("stop")}</button>{:else if !done}<button class="link" onclick={more}>{t("search more")}</button> <button class="link" onclick={toTheEnd}>{t("search to the end")}</button>{/if}
      {#if hiddenCount}<button class="link" onclick={() => { showHidden = !showHidden; }} title={t("Chains that are no better than another in raws or steps, and those that make what can simply be picked up. Nothing is lost: they are under this button.")}>· {showHidden ? t("hide the hidden") : t("show the hidden")}: {hiddenCount}</button>{/if}
      {#if cappedDetours && !capped}<span class="muted" title={t("All the ordinary chains are found. There are so many detours round what can be picked up that the search stopped at the smallest.")}>· {t("not all detours found")}</span> <button class="link" onclick={deeper}>{t("search deeper")}</button>{/if}
      {#if capped}<span class="warn" title={t("There are so many variants that the search stopped at the smallest chains. What lies beyond is unknown: you can search deeper.")}>· {t("search stopped: too many variants")}</span> <button class="link" onclick={deeper}>{t("search deeper")}</button>{/if}

      {#if skipped}<span class="warn" title={t("Chains of more than 1200 tiles fit on no screen")}>· {t("too big to draw: {n}", { n: skipped })}</span>{/if}
      <span class="hint">?</span>
      </span>
      <ZoomBar bind:zoom onfit={fit} />
    </div>
  {/if}

  {#if busy}
    <div class="busy"><span class="spin"></span>{t("Counting every chain for “{item}”…", { item: name(target) })}</div>
  {:else if empty}
    <div class="card empty">
      <p><b>{t("This item has no recipe.")}</b> {t("It cannot be made, only found or mined.")}</p>
      <p><a class="btn" href="#/recipes?item={encodeURIComponent(target)}">{t("Where it is used")}</a></p>
    </div>
  {:else}
    <div class="stage">
      <PanCanvas bind:this={pan} bind:zoom onpan={() => onTip(null)}>
        {#each shown.slice(0, limit) as p, i (p)}<Pyramid {p} index={i} {target} {have} {qty} {onTip} layer={layers.get(p)} />{:else}
          <p class="muted pad">{t("No chain fits these conditions. Press “Reset”.")}</p>
        {/each}
        {#if shown.length > limit}
          <div class="more"><button class="btn" onclick={() => { limit += 24; }}>{t("Show {n} more", { n: Math.min(24, shown.length - limit) })}<br><small>{tn(shown.length - limit, "{n} chain left|{n} chains left")}</small></button>
          <button class="btn all" onclick={() => { limit = shown.length; }}>{t("Show all")}</button></div>
        {/if}
      </PanCanvas>
    </div>
    {#if tip}<RecipeTip {tip} />{/if}
  {/if}
{/if}

<style>
  .fsel input[type="number"] { width: 64px; appearance: textfield; -moz-appearance: textfield; }
  .fsel input[type="number"]::-webkit-inner-spin-button, .fsel input[type="number"]::-webkit-outer-spin-button { -webkit-appearance: none; display: none; }
  /* The field is a straight-edged tail of the bar button before it; set (above 1) it takes the accent, like any other filter. */
  /* The label keeps the shape of every filter; the field is inset in it: straight on the side of the word, on the other side
     it follows the label's corner (10px less its 1px line) and fills to its edge. Set (above 1), the line and the figure take the accent. */
  .qty { padding-right: 0; }
  .qfield { display: flex; flex: 1 1 auto; align-self: stretch; min-width: 0; overflow: hidden; border-radius: 0 9px 9px 0; background: color-mix(in srgb, var(--p-panel) 70%, black); }
  .qfield input { flex: 1 1 auto; min-width: 0; width: 64px; height: 100%; padding: 0 8px; border: 0; border-radius: 0; background: transparent; box-shadow: none; }
  .qty.on input { color: var(--p-accent-ink); }
  /* The two arrows share the whole height of the field, with no ground of their own. */
  .qtystep { display: flex; flex-direction: column; align-self: stretch; width: 26px; flex: none; }
  .qtystep button { flex: 1; display: grid; place-items: center; padding: 0; border: 0; background: none; box-shadow: none; color: var(--p-faint); cursor: pointer; }
  .qtystep button::before { content: ""; border: 4px solid transparent; }
  .qtystep button:first-child::before { border-bottom: 5px solid currentColor; border-top-width: 0; }
  .qtystep button:last-child::before { border-top: 5px solid currentColor; border-bottom-width: 0; }
  .qtystep button:hover { color: var(--p-accent-ink); }
  .count.row { display: flex; align-items: center; gap: 12px; }
  .count .what { flex: 1; min-width: 0; }
  .hint { display: inline-grid; place-items: center; width: 18px; height: 18px; margin-left: 4px; border-radius: 50%; border: 1px solid var(--p-outline); font-size: 0.72rem; cursor: help; }

  .empty { max-width: 520px; }
  .busy { display: flex; align-items: center; gap: 12px; padding: 40px 8px; color: var(--p-muted); }
  .spin { width: 20px; height: 20px; border-radius: 50%; border: 3px solid var(--p-outline); border-top-color: var(--p-edge-accent); animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .stage { position: relative; }
  .more { flex: none; align-self: center; display: flex; flex-direction: column; gap: 8px; align-items: stretch; }
  .more .btn { height: auto; padding: 16px 28px; flex-direction: column; gap: 2px; }
  .more .btn.all { height: 38px; padding: 0 28px; flex-direction: row; }
  .more small { font-weight: 400; color: var(--p-faint); }
  /* The "not in the foundation" picker (the dropdown itself is the shared .drop). */
  .drop > summary.active { border-color: var(--p-red); color: var(--p-red); }
  .pop-acts { display: flex; gap: 8px; }
  .mats { display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 6px; max-height: 300px; overflow: auto; margin-bottom: 12px; }
  .mat {
    display: flex; align-items: center; gap: 8px; height: 44px; padding: 0 10px; border-radius: 10px; cursor: pointer;
    background: var(--p-raised); border: 1px solid var(--p-outline); color: var(--p-text); font: inherit; font-size: 0.875rem; text-align: left;
  }
  .mat .t { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mat i { font-style: normal; color: var(--p-faint); font-size: 0.78rem; }
  .mat:hover { border-color: var(--p-edge-accent); }
  .mat.off { border-color: var(--p-red); background: color-mix(in srgb, var(--p-red) 14%, var(--p-raised)); }
  .mat.off .t { text-decoration: line-through; color: var(--p-faint); }
  .mat.off :global(.ico) { opacity: 0.45; }
</style>








