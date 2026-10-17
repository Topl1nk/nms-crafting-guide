<script>
  // One portal glyph, from the outlines traced into data/glyphs.json.
  import { D } from "../lib/data.js";

  let { digit } = $props();
  const gl = $derived(D.glyphs[parseInt(digit, 16)]);
</script>

<svg class="glyph" viewBox={gl.viewbox} role="img" aria-label={gl.name}>
  <g transform={gl.transform}>{#each gl.paths as d, i (i)}<path {d} />{/each}</g>
</svg>

<style>
  .glyph { width: 100%; height: auto; fill: currentColor; display: block; aspect-ratio: 1; }
</style>
