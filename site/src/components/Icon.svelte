<script>
  // Small line icons (24px grid, 1.8 stroke) for the cards and buttons: the same
  // few pictures wherever the same thing appears, so a card can be read by
  // its icons instead of by its labels.
  let { name, size = 18 } = $props();

  const PATHS = {
    clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    times: '<path d="M6 6l12 12M18 6L6 18"/>',
    gauge: '<path d="M4.5 17a8.5 8.5 0 1 1 15 0"/><path d="M12 13l4-4"/><circle cx="12" cy="13" r="1"/>',
    coin: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v10M9.5 9.5c0-1 1-1.6 2.5-1.6s2.5.6 2.5 1.6-1 1.5-2.5 1.9-2.5.9-2.5 1.9 1 1.6 2.5 1.6 2.5-.6 2.5-1.6"/>',
    flask: '<path d="M9 3h6M10 3v6l-5 9a1.8 1.8 0 0 0 1.6 2.5h10.8A1.8 1.8 0 0 0 19 18l-5-9V3"/><path d="M7.5 15h9"/>',
    box: '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/>',
    tree: '<rect x="9" y="3" width="6" height="4"/><rect x="3" y="17" width="6" height="4"/><rect x="15" y="17" width="6" height="4"/><path d="M12 7v5M6 17v-5h12v5"/>',
    route: '<circle cx="6" cy="18" r="2"/><circle cx="18" cy="6" r="2"/><path d="M8 18h6a3 3 0 0 0 0-6h-4a3 3 0 0 1 0-6h6"/>',
    into: '<path d="M4 12h12M11 7l5 5-5 5"/><path d="M20 4v16"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    bag: '<path d="M6 10a6 6 0 0 1 12 0v10H6z"/><path d="M9.5 5V3h5v2"/>',
    make: '<path d="M4 20l8-8M13 5l6 6M15 3l6 6-3 3-6-6z"/>',
    need: '<circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/>',
    reset: '<path d="M4 12a8 8 0 1 0 2.5-5.8"/><path d="M4 4v5h5"/>',
    bolt: '<path d="M13 3L5.5 13.5H11L10 21l7.5-10.5H12z"/>',
  };
</script>

<svg class="ic" width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">{@html PATHS[name]}</svg>

<style>
  .ic { flex: none; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
</style>
