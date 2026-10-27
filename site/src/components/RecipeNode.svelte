<script>
  // One item of a recipe scheme: the shared tile (Tile.svelte), with over it the little card of the item (or of the recipe
  // `ri`, when it is the result).
  import RecipeTip from "./RecipeTip.svelte";
  import Tile from "./Tile.svelte";

  let { id, qty = 1, ri = null, label = "" } = $props();

  let tip = $state.raw(null);
  let timer;
  function enter(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    clearTimeout(timer);
    timer = setTimeout(() => { tip = { id, ri, need: qty, rect }; }, 120);
  }
  function leave() {
    clearTimeout(timer);
    tip = null;
  }
</script>

<Tile {id} {label} href="#/recipes?item={encodeURIComponent(id)}" badge={qty > 1 ? `×${qty}` : null} onmouseenter={enter} onmouseleave={leave} />
{#if tip}<RecipeTip {tip} />{/if}
