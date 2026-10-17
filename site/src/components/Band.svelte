<script>
  // How gettable an item is, coloured by its ease band.
  let { ease } = $props();
</script>

<span class="band band-{ease.band}">{ease.label}</span>
