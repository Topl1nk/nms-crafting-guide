<script>
  // What to do with an item -- keep, store, sell, junk, use -- in its colour.
  let { placement } = $props();
</script>

<span class="act act-{placement.action}">{placement.label}</span>
