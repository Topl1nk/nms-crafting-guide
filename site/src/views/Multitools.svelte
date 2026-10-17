<script module>
  const MT_TABS = [["types", "Types"], ["weapons", "Weapons"], ["getting", "Getting one"], ["tips", "Tips"]];
</script>

<script>
  // Multi-tools in four tabs (#/multitools?tab=): two tables, two pages of
  // cards, all from data/multitools.json.
  import List from "../components/List.svelte";
  import { D } from "../lib/data.js";
  import { setKeys } from "../lib/keys.js";
  import { arrival } from "../lib/router.svelte.js";

  const { params } = arrival();

  const mt = D.multitools;
  const tab = MT_TABS.some(([k]) => k === params.get("tab")) ? params.get("tab") : "types";
  let cur = $state.raw(null);
  let list = $state();

  setKeys({ get list() { return list; } });
</script>

{#snippet procedure(p)}
  <section class="card"><h3>{p.title}</h3>
    <ol>{#each p.steps as s}<li>{s}</li>{/each}</ol>
    {#if p.note}<p class="muted">{p.note}</p>{/if}
    {#if (p.after || []).length}<ul>{#each p.after as s}<li>{s}</li>{/each}</ul>{/if}
  </section>
{/snippet}

<div class="toolbar">
  <h1 class="view-title">Multi-tools</h1>
  <a class="btn" href="#/portals?kind=multi-tool">Portal addresses for these tools</a>
</div>
<p class="headline">{mt._headline}</p>
<nav class="tabs">
  {#each MT_TABS as [k, label] (k)}<a href="#/multitools?tab={k}" class:on={k === tab}>{label}</a>{/each}
</nav>
<div class="tab">
  {#if tab === "types"}
    <List bind:this={list} rows={mt.types} onSelect={(t) => { cur = t; }} columns={[
      { title: "Type", text: (t) => t.type, cls: "strong" },
      { title: "Damage", text: (t) => t.damage },
      { title: "Mining", text: (t) => t.mining },
      { title: "Scan", text: (t) => t.scan },
      { title: "Slots", text: (t) => t.slots },
      { title: "Notes", text: (t) => t.note, cls: "wide-only muted" },
    ]} />
    {#if cur}
      <aside class="detail detail-below"><h2>{cur.type}</h2>
        <p><span class="hl2">damage</span> {cur.damage} · <span class="hl2">mining</span> {cur.mining}
          · <span class="hl2">scan</span> {cur.scan} · <span class="hl2">slots at spawn</span> {cur.slots}</p>
        <p>{cur.note}</p></aside>
    {/if}
  {:else if tab === "weapons"}
    <List bind:this={list} rows={mt.weapons} onSelect={(w) => { cur = w; }} columns={[
      { title: "Weapon", text: (w) => w.weapon, cls: "strong" },
      { title: "Like a", text: (w) => w.kind },
      { title: "Best hit", text: (w) => w.best_hit, cls: "num" },
      { title: "Good", text: (w) => w.pro, cls: "wide-only" },
      { title: "Bad", text: (w) => w.con, cls: "wide-only muted" },
    ]} />
    {#if cur}
      <aside class="detail detail-below"><h2>{cur.weapon} <span class="muted small">{cur.kind}, best measured hit {cur.best_hit}</span></h2>
        <p><span class="ok">+</span> {cur.pro}</p><p><span class="err">−</span> {cur.con}</p></aside>
    {/if}
  {:else if tab === "getting"}
    <div class="prose">
      <section class="card"><h3>Where each type comes from</h3>
        <dl class="rows">
          {#each mt.getting as g}
            <dt><b>{g.type}</b> <span class="muted">({g.cost})</span></dt>
            <dd>{g.where}<div class="muted small">{g.how}</div></dd>
          {/each}
        </dl>
      </section>
      {#each [mt.sentinel_puzzle, mt.cabinet_trick, mt.hunting] as p}{@render procedure(p)}{/each}
    </div>
  {:else}
    <div class="prose">
      {#each mt.rules as r}<section class="card"><h3>{r.title}</h3><p>{r.body}</p></section>{/each}
      <section class="card"><h3>Where upgrades come from</h3>
        <dl class="rows">
          {#each mt.upgrade_sources as u}
            <dt><b>{u.kind}</b></dt>
            <dd>{u.where} <div class="muted small">{u.note}</div></dd>
          {/each}
        </dl></section>
      <section class="card"><h3>Upgrade order</h3>
        <ol>{#each mt.upgrade_order as s}<li>{s}</li>{/each}</ol></section>
    </div>
  {/if}
</div>

<style>
  .headline { padding: 0; color: var(--p-green); font-weight: 700; }
  .tabs { display: flex; gap: 2px; padding: 6px 0 12px; flex-wrap: wrap; font-family: var(--p-mono); }
  .tab > :global(.list) { margin: 0; }
  .tab > .detail-below { margin: 12px 0 24px; }
</style>
