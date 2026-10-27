<script>
  // What to do with an item -- keep, store, sell, junk, use -- as a tag in its colour, with the game's picture of the
  // place (the Storage Container with its number, the exosuit, ...) right before it. The same everywhere it is shown;
  // a link (`href`) where it leads somewhere.
  import PlaceTag from "./PlaceTag.svelte";
  import { iconOf } from "../lib/store.js";

  let { placement, size = 40, href = "" } = $props();
  // The picture carries the number of a container ("5 Progression" -> "Progression", "...in “7 Sellables”" -> "...in “Sellables”").
  const label = $derived(placement.label.replace(/(^|«)\d\s+/g, "$1"));
</script>

<PlaceTag name={label} icon={iconOf(placement)} tone={placement.action} {href} {size} />
