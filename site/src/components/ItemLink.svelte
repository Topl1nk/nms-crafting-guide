<script>
  // An item's name, linking to every recipe that touches it.
  import { name } from "../lib/data.js";

  let { id, text = undefined } = $props();
</script>

<a href="#/recipes?item={encodeURIComponent(id)}">{text ?? name(id)}</a>
