<script>
  // Cooking by what it does: a buff on the left (#/cooking?buff=), the dishes
  // that give it on the right, the highlighted dish under them.
  import List from "../components/List.svelte";
  import { fmtInt, fmtSigned } from "../lib/core.js";
  import { D, name, RECIPES } from "../lib/data.js";
  import { setKeys } from "../lib/keys.js";
  import { arrival, replace } from "../lib/router.svelte.js";

  const { params } = arrival();

  const groups = D.cooking;
  const total = groups.reduce((n, g) => n + g.dishes.length, 0);
  const start = Math.max(0, groups.findIndex((g) => g.effect === params.get("buff")));

  let group = $state.raw(groups[start]);
  let dish = $state.raw(null);
  let dishes = $state();

  // j/k walk the dishes; the buff list is a click away.
  setKeys({ get list() { return dishes; } });
</script>

<div class="toolbar"><h1 class="view-title">Cooking - what it does</h1></div>
<div class="note"><b>{total}</b> cooked dishes across <b>{groups.length}</b> buffs
  <span class="muted">· Pot = the game's own 0-1 quality for the buff · Uplift = units gained over the ingredients, one batch</span></div>
<div class="split split-food">
  <List rows={groups} {start} columns={[
    { title: "Boosts", text: (g) => g.effect, cls: "strong" },
    { title: "N", text: (g) => g.dishes.length, cls: "num" },
    { title: "Good for", text: (g) => g.use || "-", cls: "muted wide-only" },
  ]} onSelect={(g) => {
    group = g;
    // The buff in view is always in the link, ready to share.
    replace(`#/cooking?buff=${encodeURIComponent(g.effect)}`);
  }} />
  <div class="stack">
    <List bind:this={dishes} rows={group.dishes} onSelect={(d) => { dish = d; }} columns={[
      { title: "Dish", text: (d) => name(d.item), cls: "strong" },
      { title: "Pot", text: (d) => D.items[d.item].potency.toFixed(2), cls: "num" },
      { title: "Value", text: (d) => fmtInt(D.items[d.item].value), cls: "num" },
      { title: "Uplift", text: (d) => fmtSigned(RECIPES[d.recipe].profit), cls: "num wide-only" },
      { title: "Cook from", text: (d) => RECIPES[d.recipe].inputs, cls: "wide-only" },
      { title: "Time", text: (d) => RECIPES[d.recipe].timeLabel, cls: "num" },
    ]} />
    {#if dish}
      {@const item = D.items[dish.item]}
      {@const r = RECIPES[dish.recipe]}
      {@const use = groups.find((g) => g.effect === item.effect)?.use}
      <aside class="detail detail-below">
        <h2>{item.name} <span class="muted small">{item.sub}</span></h2>
        <p><span class="hl2">{item.effect}</span> at potency <b>{item.potency.toFixed(2)}</b>{#if use}{" "}<span class="muted">- {use}</span>{/if}
          {#if dish.ways > 1}<span class="muted">{` · ${dish.ways} recipes make it`}</span>{/if}</p>
        <p><span class="ok">{r.inputs}</span> → {r.outLabel} <span class="muted">{r.op}, {r.timeLabel}</span></p>
        <p class="muted">Sells for {fmtInt(item.value)} units; cooking one batch adds {fmtInt(r.profit)} over the ingredients.</p>
        <p><a class="btn" href="#/recipes?item={encodeURIComponent(dish.item)}">All recipes for it</a></p>
      </aside>
    {/if}
  </div>
</div>

<style>
  .split-food { grid-template-columns: minmax(260px, 30%) minmax(0, 1fr); }
  .stack { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
  .stack :global(.list) { max-height: 55vh; }
  @media (max-width: 1000px) {
    .split-food { grid-template-columns: minmax(0, 1fr); }
  }
</style>
