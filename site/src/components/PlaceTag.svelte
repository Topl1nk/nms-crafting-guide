<script>
  // A place of the save (the exosuit, a storage container, a ship...) as a tag: the game's picture, then the name in a
  // coloured tag. The same in the table of "My items" and in its card; a link when it leads somewhere (`href`).
  import ItemIcon from "./ItemIcon.svelte";

  let { name, icon, tone = "keep", href = "", size = 40 } = $props();
</script>

{#if href}
  <a class="at" {href}><ItemIcon id={icon} {size} /><span class="act act-{tone}">{name}</span></a>
{:else}
  <span class="at"><ItemIcon id={icon} {size} /><span class="act act-{tone}">{name}</span></span>
{/if}

<style>
  .at { display: inline-flex; align-items: center; gap: 0; max-width: 100%; vertical-align: middle; text-decoration: none; }
  a.at:hover { filter: brightness(1.2); text-decoration: none; }
  /* A name that does not fit is cut with an ellipsis inside its tag, never by the edge of what holds it. */
  .at :global(.act) { min-width: 0; overflow: hidden; text-overflow: ellipsis; }
</style>
