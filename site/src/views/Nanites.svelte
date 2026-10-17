<script module>
  const NANITE_SORTS = [
    ["rate", "nanites/hour"], ["ease", "how gettable"],
    ["per_input", "nanites per item"], ["nanites", "nanites per batch"],
  ];
  let lastSort = "rate"; // kept between visits
</script>

<script>
  // The nanite ladder: every recipe that makes Nanite Clusters, ranked.
  import Band from "../components/Band.svelte";
  import List from "../components/List.svelte";
  import { fmtInt } from "../lib/core.js";
  import { D, easeOfRecipe, name, RECIPES } from "../lib/data.js";
  import { setKeys } from "../lib/keys.js";

  let sort = $state(lastSort);
  let cur = $state.raw(null);
  let list = $state();

  const all = D.nanites.map((n) => {
    const r = RECIPES[n.recipe];
    return { ...n, r, nanites: r.out[1], perHour: r.rate, ease: easeOfRecipe(r) };
  });

  const rows = $derived.by(() => {
    const by = {
      rate: (a, b) => b.perHour - a.perHour,
      ease: (a, b) => b.ease.score - a.ease.score || b.perHour - a.perHour,
      per_input: (a, b) => b.per_input - a.per_input,
      nanites: (a, b) => b.nanites - a.nanites,
    }[sort];
    return [...all].sort(by);
  });

  setKeys({ get list() { return list; } });
</script>

{#snippet gettable(n)}<Band ease={n.ease} />{/snippet}

<div class="toolbar">
  <h1 class="view-title">Nanites</h1>
  <label>Sort <select bind:value={sort} onchange={() => { lastSort = sort; }}>
    {#each NANITE_SORTS as [k, label] (k)}<option value={k}>{label}</option>{/each}
  </select></label>
</div>
<div class="note"><b>{all.length}</b> ways to make nanites, sorted by
  <b>{NANITE_SORTS.find(([k]) => k === sort)[1]}</b>
  <span class="muted">· one refiner, kept fed</span></div>
<div class="split">
  <List bind:this={list} {rows} onSelect={(n) => { cur = n; }} columns={[
    { title: "Refine", text: (n) => n.r.inputs, cls: "strong" },
    { title: "Nan", text: (n) => n.nanites, cls: "num" },
    { title: "Time", text: (n) => n.r.timeLabel, cls: "num" },
    { title: "Nan/h", text: (n) => fmtInt(n.perHour), cls: "num" },
    { title: "Per item", text: (n) => n.per_input.toFixed(2), cls: "num wide-only" },
    { title: "Gettable", cell: gettable },
    { title: "Where it comes from", text: (n) => n.ease.where || n.ease.describe, cls: "wide-only muted" },
  ]} />
  {#if cur}
    {@const n = cur}
    <aside class="detail">
      <h2>{n.r.inputs} → {n.nanites} Nanite Cluster</h2>
      <p class="muted">{n.r.op}, {n.r.machine}</p>
      <dl>
        <dt>Nanites/hour</dt><dd><b>{fmtInt(n.perHour)}</b> per refiner</dd>
        <dt>Per item</dt><dd>{n.per_input.toFixed(2)} per item consumed</dd>
        <dt>Value spent</dt><dd>{fmtInt(n.units_cost)} units</dd>
        <dt>Gettable</dt><dd><Band ease={n.ease} /></dd>
      </dl>
      <p class={n.ease.where ? "ok" : "muted"}>{n.ease.where || n.ease.describe}</p>
      {#if n.ease.note}<p class="muted">{n.ease.note}</p>{/if}
      <p>{#each n.r.in as [id]}<a class="btn" href="#/recipes?item={encodeURIComponent(id)}">{name(id)}</a>{" "}{/each}</p>
    </aside>
  {/if}
</div>
