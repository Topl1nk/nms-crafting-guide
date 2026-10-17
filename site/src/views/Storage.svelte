<script>
  // Where does it go? Every item's storage answer (#/storage?q=), and with
  // nothing typed, the layout of the containers themselves.
  import Action from "../components/Action.svelte";
  import List from "../components/List.svelte";
  import { fmtInt } from "../lib/core.js";
  import { CONSUMED, D, PRODUCED } from "../lib/data.js";
  import { inventory } from "../lib/inventory.svelte.js";
  import { setKeys } from "../lib/keys.js";
  import { arrival, replace } from "../lib/router.svelte.js";
  import { debounce } from "../lib/util.js";

  const { params } = arrival();

  let q = $state(params.get("q") || "");
  let cur = $state.raw(null);
  let list = $state();
  let search = $state();

  const homes = Object.fromEntries(D.storage.homes.map((h) => [h.key, h]));
  const all = Object.entries(D.items).map(([id, item]) => {
    const p = D.storage.outcomes[item.store];
    return { id, item, p, key: `${item.name} ${item.sub} ${p.label} ${p.verdict}`.toLowerCase() };
  });

  const byHome = {};
  const byAction = {};
  for (const r of all) {
    byHome[r.p.home] = (byHome[r.p.home] || 0) + 1;
    byAction[r.p.action] = (byAction[r.p.action] || 0) + 1;
  }

  const matches = $derived.by(() => {
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    const exact = q.trim().toLowerCase();
    const rows = all.filter((r) => terms.every((t) => r.key.includes(t)));
    // Exact name first, then names that start with it.
    rows.sort((a, b) => {
      const an = a.item.name.toLowerCase();
      const bn = b.item.name.toLowerCase();
      return (an !== exact) - (bn !== exact) || !an.startsWith(exact) - !bn.startsWith(exact) || an.localeCompare(bn);
    });
    return rows;
  });
  const rows = $derived(matches.slice(0, 300));

  // With nothing typed the pane shows the layout, until you move into the
  // list to look at something.
  function onSelect(r, i, user) {
    cur = user || q.trim() ? r : null;
  }

  const typed = debounce((value) => {
    q = value;
    replace(q ? `#/storage?q=${encodeURIComponent(q)}` : "#/storage");
  });

  setKeys({
    get list() { return list; },
    get search() { return search; },
    escape: () => { search.value = ""; q = ""; },
  });
</script>

{#snippet goesTo(r)}<Action placement={r.p} />{/snippet}

{#snippet row(label, n, cls = "")}
  <li><a href="#/storage?q={encodeURIComponent(label)}"><b class={cls}>{label}</b></a> <span class="muted">{n} items</span></li>
{/snippet}

<div class="toolbar">
  <h1 class="view-title">Where does it go?</h1>
  <input type="search" placeholder="/  item name, or a home: sell, junk, cold, components…" value={q}
    autocomplete="off" bind:this={search} oninput={(e) => typed(e.target.value)}>
</div>
<div class="split">
  <List bind:this={list} {rows} {onSelect} columns={[
    { title: "Item", text: (r) => r.item.name, cls: "strong" },
    { title: "What it is", text: (r) => r.item.sub, cls: "muted wide-only" },
    { title: "Goes to", cell: goesTo },
  ]} />
  <aside class="detail">
    {#if cur && matches.length}
      {@const { id, item, p } = cur}
      {@const home = homes[p.home]}
      {@const have = inventory.items[id]}
      <h2>{item.name}</h2>
      <p class="muted">{item.sub} · {fmtInt(item.value)}u</p>
      <p class="big"><Action placement={p} /></p>
      <p>{p.advice}</p>
      <dl><dt>Why</dt><dd>{p.why}</dd>
        {#if home && home.key !== "none"}<dt>{home.label}</dt><dd class="muted">{home.note}</dd>{/if}</dl>
      {#if have}<p class="ok">You are carrying {have}.</p>{/if}
      {#if home?.container}<p class="muted">Once one is in its container, sending more to storage routes them there by itself.</p>{/if}
      {#if PRODUCED[id] || CONSUMED[id]}<p><a class="btn" href="#/recipes?item={encodeURIComponent(id)}">Recipes</a></p>{/if}
    {:else}
      <h3>The ten containers</h3>
      <ul class="plain">
        {#each D.storage.homes.filter((h) => h.container) as h (h.key)}{@render row(h.label, byHome[h.key] || 0)}{/each}
      </ul>
      <h3>Everything else</h3>
      <ul class="plain">
        {#each D.storage.homes.filter((h) => !h.container && h.key !== "none") as h (h.key)}{@render row(h.label, byHome[h.key] || 0)}{/each}
        {@render row("Sell", byAction.sell || 0, "act-sell")}
        {@render row("Junk", byAction.discard || 0, "act-discard")}
        {@render row("Use it", byAction.use || 0, "act-use")}
      </ul>
      <p class="muted">From the storage guide, section 10.</p>
      <p class="muted">{q.trim() ? `${matches.length} items match.` : "Type a name - or sell, junk, use."}</p>
    {/if}
  </aside>
</div>
