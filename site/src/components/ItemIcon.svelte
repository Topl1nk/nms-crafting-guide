<script>
  // An item's picture, taken from the game's own icon files (icons/ID.webp),
  // on a glow in the colour the game tints that item with (Appearance ->
  // glowing icons). Items without a picture leave a blank square, so rows align.
  import { D } from "../lib/data.js";
  import { glow } from "../lib/icontone.js";

  let { id, size = 28, color: tint = "", lazy = true } = $props(); // a picture far from the screen waits until it is near (a table of hundreds)
  let missing = $state(false);
  const color = $derived(tint || D?.items[id]?.color || "#131b3a");
  // The chemical symbol the game prints in the corner ("Fe", "O2"), when the picture is big enough to carry it.
  // The glow of the picture is the item's colour fitted to the surface it lies on (lib/icontone.js): never lost in it, whatever the panel.
  const tone = $derived(glow(color));
  const sym = $derived(size >= 26 ? D?.items[id]?.sym : "");
</script>

<span class="ico" style="--s:{size}px; --c:{tone}" class:none={missing}>
  {#if !missing}
    <img src="icons/{encodeURIComponent(id)}.webp" alt="" width={size} height={size} decoding="async" loading={lazy ? "lazy" : "eager"} draggable="false"
      onerror={() => { missing = true; }}>
  {/if}
  {#if sym}<i class="sym" style="font-size:{Math.max(8, Math.round(size * 0.25))}px">{sym}</i>{/if}
</span>

<style>
  .ico { position: relative; isolation: isolate; display: inline-block; flex: none; width: var(--s); height: var(--s); vertical-align: middle; border-radius: 24%; }
  .ico img { position: relative; display: block; width: 100%; height: 100%; object-fit: contain; -webkit-user-drag: none; user-select: none; }
  .sym {
    position: absolute; left: -4px; top: -2px; max-width: 100%; padding: 0 0.3em; border-radius: 999px; overflow: hidden;
    font-style: normal; font-weight: 600; line-height: 1.35; white-space: nowrap; text-overflow: ellipsis;
    color: #fff; background: rgb(8 12 24 / 0.62); pointer-events: none;
  }
  :global(html[data-sym="0"]) .sym { display: none; }
  .none { background: var(--p-raised); opacity: 0.5; }
  /* The glow is a square in the item's colour whose edge fades out on all four sides: nothing is cut off at the box. */
  :global(html:not([data-glow="0"])) .ico:not(.none)::before {
    content: ""; position: absolute; inset: 0; border-radius: 24%; background: color-mix(in srgb, var(--c) 42%, transparent);
    -webkit-mask-image: linear-gradient(to right, transparent, #000 24%, #000 76%, transparent), linear-gradient(to bottom, transparent, #000 24%, #000 76%, transparent);
    -webkit-mask-composite: source-in;
    mask-image: linear-gradient(to right, transparent, #000 24%, #000 76%, transparent), linear-gradient(to bottom, transparent, #000 24%, #000 76%, transparent);
    mask-composite: intersect;
  }  /* The picture is a piece of glass: one straight glare across the upper left, not strong, with a clean edge; and the piece lifts a
     little when it is pointed at, with a soft shadow under it. */
  .ico:not(.none)::after {
    content: ""; position: absolute; inset: 7%; border-radius: 26%; pointer-events: none;
    background: linear-gradient(128deg, rgb(255 255 255 / 0.2) 0%, rgb(255 255 255 / 0.1) 30%, rgb(255 255 255 / 0) 30.8%);
  }
  /* In a tile the glass is the tile itself: it has the glare and it is the tile that lifts (Tile.svelte). A picture alone does not move. */
  :global(.itile) .ico::after { display: none; }
</style>






