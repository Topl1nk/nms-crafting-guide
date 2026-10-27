<script>
  // An item's name with its picture, linking to every recipe that touches it.
  import { name } from "../lib/data.js";
  import ItemIcon from "./ItemIcon.svelte";

  let { id, text = undefined, icon = true, size = 24 } = $props();
</script>

<a class="item" href="#/recipes?item={encodeURIComponent(id)}">{#if icon}<ItemIcon {id} {size} />{/if}<span>{text ?? name(id)}</span></a>

<style>
  .item { display: inline-flex; align-items: center; gap: 6px; vertical-align: middle; max-width: 100%; }
  /* A name is one line; when the place is short it is cut, never broken letter by letter. */
  .item span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
