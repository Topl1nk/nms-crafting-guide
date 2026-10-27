<script>
  // How gettable an item is, coloured by its ease band.
  import { band, easeLabel } from "../lib/words.js";

  let { ease } = $props();
</script>

<span class="band band-{ease.band}" title={easeLabel(ease.label)}>{band(ease.band)}</span>
