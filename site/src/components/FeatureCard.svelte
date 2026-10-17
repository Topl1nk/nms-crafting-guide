<script>
  // A card on the start page: icon, title, the key that jumps there, a line.
  import { ICONS } from "../lib/icons.js";

  let { href, title, key = "", icon = "", onclick = undefined, children } = $props();
</script>

<a class="feature" {href} {onclick}>
  <h3>
    <!-- The icons are our own constant markup, from lib/icons.js. -->
    {#if ICONS[icon]}<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">{@html ICONS[icon]}</svg>{/if}<span>{title}</span>{#if key}<kbd>{key}</kbd>{/if}
  </h3>
  <p>{@render children()}</p>
</a>

<style>
  .feature {
    display: block;
    background: var(--p-panel);
    border: 1px solid var(--p-outline);
    padding: 16px 18px;
    color: var(--p-text);
    text-decoration: none;
  }
  .feature:hover { border-color: var(--p-accent); color: var(--p-text); }
  h3 { display: flex; align-items: center; gap: 10px; margin: 0 0 8px; font-size: 1.02rem; color: var(--p-text); }
  h3::before, h3::after { content: none; }
  kbd { margin-left: auto; font-weight: 400; color: var(--p-faint); }
  .ico { flex: none; width: 22px; height: 22px; fill: none; stroke: var(--p-accent); stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
  .feature:hover h3 span { color: var(--p-accent); }
  p { margin: 0; font-size: 0.92rem; line-height: 1.6; color: var(--p-muted); }
  p :global(b) { color: var(--p-text); }
  p :global(code) { color: var(--p-text); }
</style>
