<script>
  // The shortest way to one item, in the place of Craft's table: the steps from what you can pick up to the item, walked
  // by lib/core.js over the exported `via` and drawn as a pyramid, like a chain of the Tree. When nothing can be made
  // from what is allowed, the smallest chains of the Tree are drawn instead, so there is always something to see.
  import CycleLedger from "./CycleLedger.svelte";
  import PanCanvas from "./PanCanvas.svelte";
  import CycleSteps from "./CycleSteps.svelte";
  import Pyramid from "./Pyramid.svelte";
  import RecipeTip from "./RecipeTip.svelte";
  import { plan } from "../lib/core.js";
  import { D, easeOf, PRODUCED, RECIPES } from "../lib/data.js";
  import { inventory } from "../lib/inventory.svelte.js";
  import { t } from "../lib/i18n.js";
  import { pyramidOf, pyramids } from "../lib/tree.js";
  import { easeDescribe } from "../lib/words.js";

  // `rootRecipe` (bound): the recipe at the top of what is drawn, for the card beside the canvas.
  // `cycle`: a loop (lib/cycles.js) to draw whole, in the place of a path; the card beside it stays the loop's own.
  let { target, tier, qty, cook, cycle = null, zoom = $bindable(1), rootRecipe = $bindable(null) } = $props();

  const tierRow = $derived(D.tiers[tier]);
  const p = $derived(plan(D.recipes, tierRow.via[cook ? "all" : "refine"], new Set(tierRow.sources), target, qty));
  const producers = $derived(PRODUCED[target] || []);

  // The path as a pyramid: the recipe of every step that crafts something, in a pyramid of the Tree's own kind.
  const path = $derived.by(() => {
    if (cycle || !p.ok) return null;
    const choices = new Map();
    const walk = (s) => { if (s.recipe !== undefined) { choices.set(s.id, s.recipe); s.children.forEach(walk); } };
    walk(p.root);
    return pyramidOf(target, choices, p.root.batches);
  });
  // No path from what is allowed: the smallest chains there are (they need more raw materials than that).
  const shortest = $derived(!cycle && !p.ok && producers.length ? pyramids(target, { cook: true, limit: 3, budget: 150000 }).pyramids : []);

  $effect(() => {
    const top = cycle ? null : path?.root ?? shortest[0]?.root;
    rootRecipe = top && top.ri !== undefined ? RECIPES[top.ri] : null;
  });

  let tip = $state.raw(null);
  let pan = $state();
  /** "Fit height" of the page's zoom panel. */
  export const fit = () => pan?.fit();
</script>

<PanCanvas bind:this={pan} bind:zoom onpan={() => { tip = null; }}>
  {#if cycle}
    <CycleSteps {cycle} mult={qty} />
    <CycleLedger {cycle} mult={qty} time={cycle.parts.reduce((s, p) => s + (RECIPES[p.recipe].time || 0) * p.runs, 0)} />
  {:else if path}
    <Pyramid p={path} index={0} {target} have={inventory.items} qty={p.root.batches} title={t("Short path")} onTip={(x) => { tip = x; }} />
  {:else if shortest.length}
    <!-- No notice above them: the chains are the answer, and "what is allowed" is in the bar over the page. -->
    {#each shortest as pyr, i (pyr)}<Pyramid p={pyr} index={i} {target} have={inventory.items} qty={1} onTip={(x) => { tip = x; }} />{/each}
  {:else if p.ok}
    <p class="note muted">{t("This path is too big to draw:")} <a href="#/tree/{encodeURIComponent(target)}">{t("all chains")}</a>.</p>
  {:else}
    <div class="card note">
      <p><b>{t("It cannot be made from this set of raws")}</b></p>
      {#if !producers.length}<p class="muted">{t("There is no recipe: it can only be found.")} {easeOf(target).where ? easeDescribe(easeOf(target).where) : ""}</p>{/if}
    </div>
  {/if}
</PanCanvas>
{#if tip}<RecipeTip {tip} />{/if}

<style>
  .note { max-width: 520px; margin: 0; }
  .note p { margin: 0 0 8px; }
</style>








