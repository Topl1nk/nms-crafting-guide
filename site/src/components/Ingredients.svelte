<script>
  // A recipe's inputs as little pictures with a count: "3 × [icon] Carbon".
  import { name } from "../lib/data.js";
  import ItemIcon from "./ItemIcon.svelte";
  import RecipeNode from "./RecipeNode.svelte";

  // `tiles`: the scheme form, a tile per item (as in the craft tree) instead of a line of text.
  let { recipe, size = 26, compact = false, tiles = false } = $props();
</script>

{#if tiles}
  <span class="tiles">
    {#each recipe.in as [id, n], i (i)}{#if i}<span class="plus joint" aria-hidden="true">✚</span>{/if}<RecipeNode {id} qty={n} />{/each}
  </span>
{:else}
<span class="ings">
  {#each recipe.in as [id, n], i (i)}
    {#if i}<span class="plus">+</span>{/if}
    <span class="ing" title={name(id)}><ItemIcon {id} {size} />{#if n > 1}<b>{n}×</b>{/if}{#if !compact}<span class="nm">{name(id)}</span>{/if}</span>
  {/each}
</span>
{/if}

<style>
  /* Rows far enough apart for the count that sticks out over a tile. */
  .tiles { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 24px 8px; }
  .ings { display: inline-flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; }
  .ing { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; }
  /* No cap on a name: "Activated Indium" is written in full while there is room; a line that is too long for its
     cell fades out at the cell's edge (.cellclip), it is not cut short name by name. */
  .nm { white-space: nowrap; }
  .plus { color: var(--p-faint); }
  /* In a scheme the plus is a bold white glyph of its own (U+271A), never the thin letter of the text. */
  .plus.joint { color: var(--p-text); font-weight: 900; font-size: 1.1rem; }
  b { color: var(--p-accent-ink); }
</style>




