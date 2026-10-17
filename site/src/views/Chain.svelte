<script>
  // The chain planner: #/chain/ITEM?tier=&qty=&cook=, the tree from what you
  // can pick up to the item, walked by lib/core.js over the exported `via`.
  import ItemLink from "../components/ItemLink.svelte";
  import { fmtTime, plan } from "../lib/core.js";
  import { D, easeOf, name, PRODUCED, RECIPES } from "../lib/data.js";
  import { arrival, replace } from "../lib/router.svelte.js";
  import { debounce } from "../lib/util.js";

  const { params, arg: target } = arrival();

  let tier = $state(Number(params.get("tier") || 0));
  let qty = $state(Math.max(1, Number(params.get("qty") || 1)));
  let cook = $state(params.get("cook") === "1");

  const known = Boolean(D.items[target] || PRODUCED[target]);
  const t = $derived(D.tiers[tier]);
  const p = $derived(known ? plan(D.recipes, t.via[cook ? "all" : "refine"], new Set(t.sources), target, qty) : null);
  const producers = PRODUCED[target] || [];

  // Keep the settings in the URL, so a plan is a link. Not on arrival: the
  // link that brought you here stays as it was.
  let arrived = false;
  $effect(() => {
    const q = new URLSearchParams();
    if (tier) q.set("tier", tier); // read first, so the effect tracks them
    if (qty !== 1) q.set("qty", qty);
    if (cook) q.set("cook", "1");
    if (!arrived) { arrived = true; return; }
    replace(`#/chain/${encodeURIComponent(target)}${q.size ? `?${q}` : ""}`);
  });

  const typedQty = debounce((value) => {
    const n = Math.floor(Number(value));
    if (n >= 1) qty = Math.min(n, 9999);
  });
</script>

{#snippet node(step)}
  {#if step.recipe === undefined}
    {@const tag = step.raw ? "gather" : "find"}
    <li class="leaf">{step.qty} × <ItemLink id={step.id} /> <span class="tag tag-{tag}">{tag}</span></li>
  {:else}
    {@const r = RECIPES[step.recipe]}
    <li><span>{step.qty} × <ItemLink id={step.id} /></span>
      <span class="muted small">{r.op} ×{step.batches}, {fmtTime(r.time * step.batches)}, {r.machine}</span>
      <ul>{#each step.children as child}{@render node(child)}{/each}</ul></li>
  {/if}
{/snippet}

{#if !known}
  <p class="pad">Unknown item <code>{target}</code>. <a href="#/recipes">Back to recipes</a></p>
{:else}
  <div class="toolbar">
    <h1 class="view-title">Chain · {name(target)}</h1>
    <label>From <select bind:value={tier}>
      {#each D.tiers as tr, i (i)}<option value={i}>{tr.name}</option>{/each}
    </select></label>
    <label>How many <input type="number" min="1" max="9999" value={qty} oninput={(e) => typedQty(e.target.value)}></label>
    <label class="check"><input type="checkbox" bind:checked={cook}> allow cooking</label>
  </div>
  <div class="chain">
    <p><b>{qty} × {name(target)}</b> from <b>{t.name}</b>
      <span class="muted">- {t.sources.map(name).sort().join(", ")}</span></p>
    {#if !p.ok}
      <p class="err">Not reachable from this source set.</p>
      <p class="muted">Try a wider tier{cook ? "" : ", or allow cooking recipes"}.</p>
      {#if producers.length}
        <h3>It is made by</h3>
        <ul>{#each producers.slice(0, 6) as r (r.index)}<li>{r.inputs} → {r.outLabel}</li>{/each}</ul>
      {:else}
        <p class="muted">No recipe produces it - this one you have to find.</p>
        <p>{easeOf(target).where || ""}</p>
      {/if}
    {:else}
      <p><span class="ok">Gather:</span>
        {#each Object.entries(p.raw).sort((a, b) => b[1] - a[1]) as [id, n] (id)}<span class="pill">{n} {name(id)}</span>{" "}{/each}</p>
      <p class="muted">{p.steps} refining step(s), {fmtTime(p.seconds)} of machine time (one refiner, unattended).
        {cook ? "" : " Refining only."}</p>
      <ul class="tree">{@render node(p.root)}</ul>
    {/if}
  </div>
{/if}

<style>
  /* The TUI Tree's ├─ └─ branches, drawn as borders. */
  .chain { padding: 0 0 24px; }
  .tree, .tree :global(ul) { list-style: none; padding-left: 0; margin: 0; }
  .tree { font-size: 0.95rem; --mid: calc(3px + 0.8em); }
  .tree ul { margin-left: 0.5em; }
  .tree li { position: relative; padding: 3px 0; }
  .tree ul > li { padding-left: 1.7em; }
  .tree ul > li::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    width: 1.2em;
    height: var(--mid);
    border-left: 1px solid var(--p-outline);
    border-bottom: 1px solid var(--p-outline);
  }
  .tree ul > li:not(:last-child)::after {
    content: "";
    position: absolute;
    left: 0;
    top: var(--mid);
    bottom: 0;
    border-left: 1px solid var(--p-outline);
  }
  .tree li > span:first-child { font-weight: 700; }
  .tree :global(a) { text-decoration: none; }
  .tree .muted { margin-left: 6px; font-family: var(--p-mono); }
</style>
