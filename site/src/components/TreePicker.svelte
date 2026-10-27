<script module>
  // What was searched and chosen outlives a visit, like on the other pages.
  const st = { q: "", filters: null, sort: "name" };
</script>

<script>
  // #/tree with no item: everything that can be made, as square tiles like the ones of the tree itself, with the
  // filters that tell them apart (lib/pickfacets.js). Choose one to see every way to make it.
  import Check from "./Check.svelte";
  import ItemTile from "./ItemTile.svelte";
  import Reset from "./Reset.svelte";
  import Select from "./Select.svelte";
  import { craftableNow } from "../lib/core.js";
  import { CONSUMED, D, easeOfRecipe, name, PRODUCED, RECIPES } from "../lib/data.js";
  import { applyFacets, facets } from "../lib/facets.js";
  import { collate, t } from "../lib/i18n.js";
  import { inventory } from "../lib/inventory.svelte.js";
  import { PICK_DEFAULTS, pickDefs, pickSorts } from "../lib/pickfacets.js";
  import { byColor, byPotency, byRarity, byType } from "../lib/sortkeys.js";
  import { quiet } from "../lib/motion.js";
  import { debounce } from "../lib/util.js";

  const ids = Object.keys(PRODUCED).filter((id) => D.items[id]);
  let f = $state({ ...PICK_DEFAULTS, ...st.filters });
  let q = $state(st.q);
  let sort = $state(st.sort);
  $effect(() => { st.filters = { ...f }; st.sort = sort; });

  const makeable = $derived(new Set(craftableNow(D.recipes, inventory.items, ["refine", "cook"]).map(([i]) => RECIPES[i].out[0])));
  const defs = $derived(pickDefs({ makeable, held: inventory.items }, ids));
  const base = $derived.by(() => {
    const terms = q.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return terms.length ? ids.filter((id) => terms.every((w) => name(id).toLowerCase().includes(w))) : ids;
  });
  const fx = $derived(facets(base, defs, f));
  // The quickest recipe of an item (none: last), and the easiest to supply of its recipes.
  const fastest = (id) => Math.min(...(PRODUCED[id] || []).map((r) => r.time || 1e9), 1e9);
  const easiest = (id) => Math.max(0, ...(PRODUCED[id] || []).map((r) => easeOfRecipe(r).score));
  const BY = {
    name: (a, b) => collate(name(a), name(b)),
    ways: (a, b) => (PRODUCED[b] || []).length - (PRODUCED[a] || []).length || BY.name(a, b),
    needs: (a, b) => (CONSUMED[b] || []).length - (CONSUMED[a] || []).length || BY.name(a, b),
    value: (a, b) => (D.items[b].value - D.items[a].value) || BY.name(a, b),
    color: (a, b) => byColor(a, b) || BY.name(a, b),
    type: (a, b) => byType(a, b) || BY.name(a, b),
    rar: (a, b) => byRarity(a, b) || BY.name(a, b),
    potency: (a, b) => byPotency(a, b) || BY.name(a, b),
    time: (a, b) => fastest(a) - fastest(b) || BY.name(a, b),
    ease: (a, b) => easiest(b) - easiest(a) || BY.name(a, b),
  };
  const shown = $derived([...applyFacets(base, defs, fx.effective)].sort(BY[sort] ?? BY.name));
  // The first tiles are drawn at once, the rest as the end of the grid comes near (all 400 at once is a stall the page feels).
  const FIRST = 96;
  let drawn = $state(FIRST);
  $effect(() => { shown; drawn = FIRST; });
  // The end of the grid is watched again each time more is drawn: an observer tells only when the end comes into view or leaves it,
  // so on a big screen, where the end is still in view after a batch, it would never ask for the next one.
  function nearEnd(node) {
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) drawn = Math.min(shown.length, drawn + 96); }, { root: node.closest("main"), rootMargin: "800px 0px" }); // watched from the page's own scroller: the page clips it, so from the window its margin would count for nothing
    io.observe(node);
    return { update: () => { io.unobserve(node); io.observe(node); }, destroy: () => io.disconnect() };
  }  const filtered = $derived(Object.keys(PICK_DEFAULTS).some((k) => f[k] !== PICK_DEFAULTS[k]) || q !== "");
  let search = $state();
  const typed = debounce((v) => { q = v; st.q = v; });
  const set = (key) => (v) => { f[key] = v; };

  // Choosing a tile: the counts over the tiles go first; the tile is glass, so it only moves (no squeezing): it dips, jumps higher than
  // the lift of a pointed tile, lands, and when it lands the tiles around it rise and fade in a wave that runs outward (the nearer,
  // the stronger). The faded state is written into the tiles before the page changes, so the copy of the page that slides away keeps it.
  let grid = $state();
  let busy = false;

  // The chosen tile does not slide away with the old page: a copy of it stays over everything and flies to where the same item
  // stands in the new page (the top tile of its first chain), which waits hidden and takes over as the copy arrives.
  function fly(tile) {
    const from = tile.getBoundingClientRect();
    const copy = tile.cloneNode(true);
    copy.querySelector(".ib")?.remove();
    copy.removeAttribute("href");
    copy.style.cssText = `position:fixed; left:${from.left}px; top:${from.top}px; width:${from.width}px; height:${from.height}px; margin:0; z-index:60; pointer-events:none; transform-origin:0 0;`;
    document.body.append(copy);
    tile.style.opacity = "0"; // so the old page, copied to slide away, has no tile in it
    const started = performance.now();
    const seek = () => {
      const apex = document.querySelector("main .itile.apex");
      if (!apex) { if (performance.now() - started < 3000) setTimeout(seek, 16); else copy.remove(); return; }
      apex.style.opacity = "0";
      // Where the tile will stand: where it is now, less the slide the panes of the page are still making.
      const at = apex.getBoundingClientRect();
      let dx = 0, dy = 0;
      for (let n = apex.parentElement; n && n !== document.body; n = n.parentElement) {
        if (!n.getAnimations().length) continue;
        const m = new DOMMatrix(getComputedStyle(n).transform);
        dx += m.m41; dy += m.m42;
      }
      const to = `translate(${at.left - dx - from.left}px, ${at.top - dy - from.top}px) scale(${at.width / from.width})`;
      const flight = copy.animate([{ transform: "none" }, { transform: to }], { duration: 660, easing: "cubic-bezier(.3, .7, .2, 1)", fill: "forwards" });
      flight.onfinish = () => {
        apex.style.opacity = "";
        apex.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 140 });
        copy.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 140, fill: "forwards" }).onfinish = () => copy.remove();
      };
    };
    seek();
  }
  const LAND = 350, REACH = 760, OPEN = 800;
  function choose(e) {
    const tile = e.target.closest?.("a.itile");
    if (!tile || busy || e.button || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    e.preventDefault();
    busy = true;
    const href = tile.getAttribute("href");
    tile.style.zIndex = "5";
    const played = [];
    for (const count of grid.querySelectorAll(".ib")) played.push(count.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 140, easing: "ease-out", fill: "forwards" }));
    tile.animate([
      { transform: "translateY(-3px)", offset: 0, easing: "cubic-bezier(.3, 0, .6, 1)" },
      { transform: "translateY(3px)", offset: 0.12, easing: "cubic-bezier(.15, .9, .3, 1)" },
      { transform: "translateY(-36px)", offset: 0.42, easing: "cubic-bezier(.6, 0, .9, .6)" },
      { transform: "translateY(2px)", offset: 0.58, easing: "cubic-bezier(.2, .8, .3, 1)" },
      { transform: "translateY(-6px)", offset: 0.74, easing: "ease-in-out" },
      { transform: "translateY(0)", offset: 1 },
    ], { duration: 600 });
    const at = tile.getBoundingClientRect();
    const cx = at.left + at.width / 2, cy = at.top + at.height / 2;
    for (const other of grid.querySelectorAll("a.itile")) {
      if (other === tile) continue;
      const r = other.getBoundingClientRect();
      const d = Math.hypot(r.left + r.width / 2 - cx, r.top + r.height / 2 - cy);
      const k = Math.max(0.1, 1 - d / REACH); // the strength fades with distance, but every tile of the page goes
      played.push(other.animate([
        { transform: "translateY(0)", opacity: 1 },
        { transform: `translateY(${-8 - 14 * k}px)`, opacity: 1, offset: 0.35 },
        { transform: `translateY(${-24 - 26 * k}px)`, opacity: 0 },
      ], { duration: 440, delay: LAND + Math.min(d, 1400) * 0.25, easing: "cubic-bezier(.3, .6, .4, 1)", fill: "both" }));
    }
    setTimeout(() => {
      for (const a of played) { a.finish(); try { a.commitStyles(); } catch { /* the tile is gone */ } a.cancel(); }
      quiet();
      fly(tile);
      busy = false;
      location.hash = href;
    }, OPEN);
  }
  const LABEL = { kind: t("Kind"), type: t("Type"), rar: t("Rarity"), effect: t("Effect"), refiner: t("Refiner"), source: t("Source"), owned: t("My items"), ways: t("Ways to make") };
  const TITLE = {
    kind: t("What makes it: refining, cooking, or a way to get nanites"),
    type: t("What sort of item it is: substance, component, consumable, trade good"),
    effect: t("What a dish gives when it is eaten"),
    refiner: t("The biggest refiner you have: only the items made in it are shown"),
    source: t("How easy the rarest ingredient is to get"),
    owned: t("Whether you have enough of the items for it, or at least part"),
    ways: t("How many ways there are to make it: the more, the more chains"),
  };
</script>

<div class="fbar">
  <h1><span>{t("Craft tree")}</span></h1>
  <Reset active={filtered} onclick={() => { f = { ...PICK_DEFAULTS }; q = st.q = ""; if (search) search.value = ""; }} />
  <input class="search" type="search" placeholder={t("Which item to break down?")} autocomplete="off" value={q} bind:this={search} oninput={(e) => typed(e.target.value)}>
  {#each Object.keys(LABEL) as key (key)}
    <Select hidden={!(fx.show[key])} label={LABEL[key]} value={fx.effective[key]} options={fx.options[key]} all={fx.all[key]} neutral={fx.neutral[key]} onchange={set(key)} title={TITLE[key] ?? ""} />
  {/each}
  <Select label={t("Order")} value={sort} options={pickSorts()} onchange={(v) => { sort = v; }} />
</div>
<div class="count">{t("Items:")} <b>{shown.length}</b>{shown.length !== ids.length ? ` ${t("of {n}", { n: ids.length })}` : ""} · {t("choose one to see every way to make it, from the simplest to the hardest")}</div>
<div class="picks" bind:this={grid} onclick={choose}>
  {#each shown.slice(0, drawn) as id (id)}<ItemTile {id} />{:else}<p class="muted pad">{t("Nothing found.")}</p>{/each}
  {#if drawn < shown.length}<div class="end" use:nearEnd={drawn}></div>{/if}
</div>

<style>
  /* The columns share the whole width, so there is no empty strip at the right edge. */
  .end { grid-column: 1 / -1; height: 1px; }
  .picks { display: grid; grid-template-columns: repeat(auto-fill, minmax(var(--tile), 1fr)); justify-items: center; gap: 18px 10px; padding: 14px 0 16px; align-content: start; }
</style>







