<script module>
  // The search, the recipe set and the sort outlive a visit: going to an
  // item's recipes and back keeps them.
  const st = { q: "", domain: "refine", sort: "mult" };

  const DOMAINS = [["refine", "Refining"], ["cook", "Cooking"], ["all", "All recipes"]];
  const SORTS = [
    ["mult", "multiplier"], ["time", "fastest"], ["rate", "output/hour"],
    ["profit", "units profit"], ["ease", "how gettable"], ["name", "name"],
  ];
  const MAX_ROWS = 400;
</script>

<script>
  // Every recipe, searchable, or the ones touching one item (?item=&role=).
  import Action from "../components/Action.svelte";
  import Band from "../components/Band.svelte";
  import ItemLink from "../components/ItemLink.svelte";
  import List from "../components/List.svelte";
  import { fmtInt, fmtSigned, machineShort } from "../lib/core.js";
  import {
    CONSUMED, D, easeOf, easeOfRecipe, name, placement, PRODUCED, RECIPES,
  } from "../lib/data.js";
  import { inventory } from "../lib/inventory.svelte.js";
  import { setKeys } from "../lib/keys.js";
  import { arrival, go } from "../lib/router.svelte.js";
  import { toast } from "../lib/toast.svelte.js";
  import { debounce } from "../lib/util.js";

  const { params } = arrival();
  const item = params.get("item");
  const role = params.get("role") || "any";
  if (params.has("domain")) st.domain = params.get("domain");

  let q = $state(st.q);
  let domain = $state(st.domain);
  let sort = $state(st.sort);
  let cur = $state.raw(null);
  let list = $state();
  let search = $state();

  function sortRecipes(rows, mode) {
    const by = {
      mult: (a, b) => Math.max(b.loop, b.ratio) - Math.max(a.loop, a.ratio) || a.time - b.time,
      time: (a, b) => (a.time || 1e9) - (b.time || 1e9) || b.ratio - a.ratio,
      rate: (a, b) => b.rate - a.rate || a.time - b.time,
      profit: (a, b) => b.profit - a.profit || a.time - b.time,
      ease: (a, b) => easeOfRecipe(b).score - easeOfRecipe(a).score || a.time - b.time,
      name: (a, b) => a.outName.localeCompare(b.outName) || a.inputs.localeCompare(b.inputs),
    }[mode];
    return rows.sort(by);
  }

  function searchRecipes() {
    let pool;
    if (item) {
      if (role === "output") pool = PRODUCED[item] || [];
      else if (role === "input") pool = CONSUMED[item] || [];
      else pool = [...new Set([...(PRODUCED[item] || []), ...(CONSUMED[item] || [])])];
    } else {
      pool = RECIPES;
    }
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    return pool.filter((r) =>
      (domain === "all" || r.domain === domain) && terms.every((t) => r.key.includes(t)));
  }

  const matches = $derived(sortRecipes(searchRecipes(), sort));
  const rows = $derived(matches.slice(0, MAX_ROWS));
  const carried = $derived(Object.keys(inventory.items).length);
  const verb = { output: "produced by", input: "used in", any: "anything touching" }[role];

  const typed = debounce((value) => { q = value; st.q = value; });
  const enter = (r) => { if (r) go(`#/recipes?item=${encodeURIComponent(r.out[0])}`); };

  function addToInventory(id) {
    const n = inventory.add(id);
    toast(`${name(id)}: ${n} in inventory`);
  }

  setKeys({
    get list() { return list; },
    get search() { return search; },
    enter: () => enter(list?.current()),
    escape: () => {
      if (item) { go("#/recipes"); return; }
      search.value = "";
      q = st.q = "";
    },
  });

  const columns = [
    { title: "Make", text: (r) => r.outLabel, cls: "strong" },
    { title: "From", text: (r) => r.inputs },
    { title: "Mult", text: (r) => r.mult, cls: "num" },
    { title: "Time", text: (r) => r.timeLabel, cls: "num" },
    { title: "Machine", text: (r) => machineShort(r.machine), cls: "wide-only" },
  ];
</script>

<div class="toolbar">
  <input type="search" placeholder="/  search recipes - output, ingredient or operation" value={st.q}
    autocomplete="off" bind:this={search} oninput={(e) => typed(e.target.value)}>
  <label>Show <select bind:value={domain} onchange={() => { st.domain = domain; }}>
    {#each DOMAINS as [k, label] (k)}<option value={k}>{label}</option>{/each}
  </select></label>
  <label>Sort <select bind:value={sort} onchange={() => { st.sort = sort; }}>
    {#each SORTS as [k, label] (k)}<option value={k}>{label}</option>{/each}
  </select></label>
</div>
<div class="note">
  <b>{DOMAINS.find(([k]) => k === domain)[1]}</b>
  &nbsp;·&nbsp; sorted by <b>{SORTS.find(([k]) => k === sort)[1]}</b>
  {#if item}
    &nbsp;·&nbsp; {verb} <b class="hl">{name(item)}</b> <a href="#/recipes" class="chip">clear filter</a>
  {/if}
  &nbsp;·&nbsp; {matches.length > MAX_ROWS ? `${MAX_ROWS} of ${matches.length}` : `${matches.length} recipes`}
  {#if carried}&nbsp;·&nbsp; <a href="#/inventory">inventory: {carried} items</a>{/if}
</div>
<div class="split">
  <List bind:this={list} {rows} {columns} onSelect={(r) => { cur = r; }} onEnter={enter} empty="No recipe matches." />
  {#if !matches.length}
    <aside class="detail"><p class="muted">No recipe matches.</p></aside>
  {:else if cur}
    {@const r = cur}
    {@const id = encodeURIComponent(r.out[0])}
    {@const p = placement(r.out[0])}
    {@const others = (PRODUCED[r.out[0]] || []).filter((o) => o.index !== r.index)}
    {@const uses = CONSUMED[r.out[0]] || []}
    <aside class="detail">
      <h2>{r.outLabel}</h2>
      <p class="muted">{D.items[r.out[0]]?.sub ?? ""}</p>
      <p class="equation"><b>{r.inputs}</b><br>→ <b>{r.outLabel}</b></p>
      <dl>
        <dt>Operation</dt><dd>{r.op}</dd>
        <dt>Machine</dt><dd>{r.machine}</dd>
        <dt>Batch time</dt><dd>{r.timeLabel}</dd>
        <dt>Multiplier</dt><dd>{r.mult}</dd>
        <dt>Rate</dt><dd>{fmtInt(r.rate)}/h per machine</dd>
        <dt>Profit</dt><dd>{fmtSigned(r.profit)} units per batch</dd>
        <dt>Gettable</dt><dd><Band ease={easeOfRecipe(r)} /> <span class="muted">(hardest ingredient)</span></dd>
        {#if p}
          <dt>Store</dt><dd><Action placement={p} /> <a class="muted" href="#/storage?q={encodeURIComponent(name(r.out[0]))}">why?</a></dd>
        {/if}
      </dl>
      <div class="actions">
        <a class="btn" href="#/chain/{id}">Chain plan</a>
        <a class="btn" href="#/recipes?item={id}&role=output">Produced by</a>
        <a class="btn" href="#/recipes?item={id}&role=input">Used in</a>
        <button class="btn" onclick={() => addToInventory(r.out[0])}>+ Inventory</button>
      </div>
      <h3>Ingredients</h3>
      <ul class="ings">
        {#each r.in as [ing, n]}
          {@const ie = easeOf(ing)}
          <li>{n} × <ItemLink id={ing} /> <span class="muted">{fmtInt(D.items[ing]?.value ?? 0)}u</span>
            {#if inventory.items[ing]}<span class="ok">(have {inventory.items[ing]})</span>{/if}
            <Band ease={ie} />
            <div class="muted small">{ie.describe}</div></li>
        {/each}
      </ul>
      {#if others.length}
        <h3>Other ways to make it <span class="muted">({others.length})</span></h3>
        <ul>
          {#each [...others].sort((a, b) => Math.max(b.loop, b.ratio) - Math.max(a.loop, a.ratio)).slice(0, 5) as o (o.index)}
            <li>{o.inputs} <span class="muted">{o.mult}</span></li>
          {/each}
        </ul>
        <p><a href="#/recipes?item={id}&role=output">List them all</a></p>
      {/if}
      {#if uses.length}
        <h3>Used in</h3><p><a href="#/recipes?item={id}&role=input">{uses.length} recipe(s)</a></p>
      {/if}
    </aside>
  {/if}
</div>

<style>
  .equation { margin: 10px 0; }
  .ings li { margin-bottom: 4px; }
</style>
