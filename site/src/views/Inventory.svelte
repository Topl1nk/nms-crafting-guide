<script>
  // What you carry, what it makes now, and what it is one ingredient short of.
  // Kept in this browser (lib/inventory.svelte.js).
  import Action from "../components/Action.svelte";
  import ItemLink from "../components/ItemLink.svelte";
  import List from "../components/List.svelte";
  import { craftableNow, fmtInt, oneHopAway } from "../lib/core.js";
  import { D, ITEM_NAMES, name, placement, RECIPES } from "../lib/data.js";
  import { inventory } from "../lib/inventory.svelte.js";
  import { setKeys } from "../lib/keys.js";
  import { local } from "../lib/local.js";
  import { go } from "../lib/router.svelte.js";
  import { toast } from "../lib/toast.svelte.js";

  let cook = $state(local.get("inv-cook", true));
  let adding = $state("");
  let count = $state(1);
  let can = $state();
  let search = $state();

  const byName = Object.fromEntries(Object.entries(D.items).map(([id, i]) => [i.name.toLowerCase(), id]));
  const domains = $derived(cook ? ["refine", "cook"] : ["refine"]);
  const carried = $derived(Object.entries(inventory.items).sort((a, b) => name(a[0]).localeCompare(name(b[0]))));
  const canMake = $derived(craftableNow(D.recipes, inventory.items, domains).slice(0, 200));
  // With nothing carried, every one-input recipe is "one short": noise.
  const near = $derived(Object.keys(inventory.items).length
    ? oneHopAway(D.recipes, inventory.items, domains).slice(0, 200) : []);

  function add(e) {
    e.preventDefault();
    const id = byName[adding.trim().toLowerCase()];
    if (!id) { toast("No item by that name - pick one from the list"); return; }
    const n = inventory.add(id, Math.max(1, Number(count) || 1));
    adding = "";
    count = 1;
    toast(`${name(id)}: ${n}`);
  }

  function setCount(id, value) {
    const next = { ...inventory.items };
    const n = Math.floor(Number(value));
    if (n > 0) next[id] = n; else delete next[id];
    inventory.save(next);
  }

  function drop(id) {
    const next = { ...inventory.items };
    delete next[id];
    inventory.save(next);
  }

  function clear() {
    if (Object.keys(inventory.items).length && confirm("Clear the whole inventory?")) inventory.save({});
  }

  const open = ([i]) => go(`#/recipes?item=${encodeURIComponent(RECIPES[i].out[0])}`);

  setKeys({
    get list() { return can; },
    get search() { return search; },
    enter: () => { const row = can?.current(); if (row) open(row); },
  });
</script>

{#snippet itemCell([id])}<ItemLink {id} />{/snippet}
{#snippet countCell([id, n])}
  <input type="number" class="count" min="0" value={n} aria-label="count" onchange={(e) => setCount(id, e.target.value)}>
{/snippet}
{#snippet goesTo([id])}{#if placement(id)}<Action placement={placement(id)} />{/if}{/snippet}
{#snippet dropCell([id])}<button class="x" title="drop" onclick={() => drop(id)}>×</button>{/snippet}
{#snippet missing([, m])}{#each m as [id, n], j}{j ? ", " : ""}{n} <ItemLink {id} />{/each}{/snippet}

<div class="toolbar">
  <h1 class="view-title">Inventory</h1>
  <form class="inline" onsubmit={add}>
    <input list="item-names" placeholder="/  add an item - type its name" autocomplete="off"
      bind:this={search} bind:value={adding}>
    <input type="number" min="1" bind:value={count} aria-label="how many">
    <button class="btn">Add</button>
  </form>
  <label class="check"><input type="checkbox" bind:checked={cook} onchange={() => local.set("inv-cook", cook)}> include cooking</label>
  <button class="btn danger" onclick={clear}>Clear all</button>
</div>
<datalist id="item-names">{#each ITEM_NAMES as n}<option value={n}></option>{/each}</datalist>
<p class="muted small pad-x">Kept in this browser only.</p>
<div class="grid3">
  <section><h3>Carrying</h3>
    <List rows={carried} empty="Nothing yet. Add what you are carrying above." columns={[
      { title: "Item", cell: itemCell, cls: "strong" },
      { title: "Count", cell: countCell, cls: "num" },
      { title: "Value", text: ([id, n]) => fmtInt((D.items[id]?.value ?? 0) * n), cls: "num" },
      { title: "Goes to", cell: goesTo, cls: "wide-only" },
      { title: "", cell: dropCell },
    ]} /></section>
  <section><h3>Can make now</h3>
    <List bind:this={can} rows={canMake} onEnter={open} empty="Nothing your inventory makes yet." columns={[
      { title: "Make", text: ([i]) => RECIPES[i].outLabel, cls: "strong" },
      { title: "From", text: ([i]) => RECIPES[i].inputs },
      { title: "Mult", text: ([i]) => RECIPES[i].mult, cls: "num" },
      { title: "Batches", text: ([, b]) => b, cls: "num" },
    ]} /></section>
  <section><h3>One ingredient short</h3>
    <List rows={near} onEnter={open} empty="-" columns={[
      { title: "Make", text: ([i]) => RECIPES[i].outLabel, cls: "strong" },
      { title: "From", text: ([i]) => RECIPES[i].inputs, cls: "wide-only" },
      { title: "Missing", cell: missing },
    ]} /></section>
</div>

<style>
  form.inline { display: flex; gap: 6px; flex: 1 1 380px; min-width: 0; }
  form.inline input:not([type]) { flex: 1 1 320px; min-width: 0; }
  .grid3 {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr);
    gap: 16px;
    padding: 0 0 24px;
  }
  .grid3 h3 { margin-top: 0; }
  .grid3 :global(.list) { max-height: 60vh; }
  input.count { width: 5em; padding: 1px 6px; text-align: right; }
  .x { background: none; border: 0; color: var(--p-faint); cursor: pointer; font-size: 1.1em; padding: 0 4px; }
  .x:hover { color: var(--p-red); }
  @media (max-width: 1000px) {
    .grid3 { grid-template-columns: minmax(0, 1fr); }
  }
</style>
