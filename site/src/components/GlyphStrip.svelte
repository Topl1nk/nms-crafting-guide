<script>
  // A portal code as the twelve glyphs you dial, each in its field's colour,
  // with the hex digit under it -- and the glyph's name, when there is room.
  import { GLYPH_FIELD } from "../lib/core.js";
  import { D } from "../lib/data.js";
  import { t } from "../lib/i18n.js";
  import Glyph from "./Glyph.svelte";

  let { code, names = false } = $props();
</script>

<div class="glyphs">
  {#each [...code] as digit, i (i)}
    <figure class="f{GLYPH_FIELD[i]}">
      <Glyph {digit} />
      <figcaption><b>{digit}</b>{#if names}{" "}<span>{t(D.glyphs[parseInt(digit, 16)].name)}</span>{/if}</figcaption>
    </figure>
  {/each}
</div>

<style>
  .glyphs {
    display: grid;
    grid-template-columns: repeat(12, minmax(0, 1fr));
    gap: 4px;
    margin: 10px 0;
    max-width: 720px;
  }
  figure { margin: 0; text-align: center; min-width: 0; }
  figcaption { font-family: var(--p-mono); font-size: 0.7rem; line-height: 1.25; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  figcaption b { font-family: var(--p-mono); }
  figcaption span { display: block; color: var(--p-faint); }

  @media (max-width: 640px) {
    .glyphs { grid-template-columns: repeat(6, minmax(0, 1fr)); }
  }
</style>
