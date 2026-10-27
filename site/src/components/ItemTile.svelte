<script>
  // A thing to break down into chains, as the shared tile (Tile.svelte), with how many ways there are to make it on top.
  // Over it, the little card of the item.
  import RecipeTip from "./RecipeTip.svelte";
  import Tile from "./Tile.svelte";
  import { PRODUCED } from "../lib/data.js";

  let { id } = $props();

  let tip = $state.raw(null);
  let timer;
  function enter(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    clearTimeout(timer);
    timer = setTimeout(() => { tip = { id, ri: null, need: 0, rect }; }, 120);
  }
  function leave() {
    clearTimeout(timer);
    tip = null;
  }
  const ways = $derived((PRODUCED[id] || []).length);
</script>

<Tile {id} href="#/tree/{encodeURIComponent(id)}" badge={ways > 1 ? String(ways) : null} onmouseenter={enter} onmouseleave={leave} onfocus={enter} onblur={leave} />
{#if tip}<RecipeTip {tip} />{/if}
