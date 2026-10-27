<script>
  // The tile of an item, the one every scheme of the site is built of (a recipe card's scheme, a pyramid of the craft tree,
  // the steps of a cycle, the list of things to break down): the picture on its colour, the name under it, a count over it.
  // One size for all (--tile, a square) and one look; nothing about it depends on the text it carries. A page puts it in
  // place (`style`), says what it is (`mark`) and what the count is (`badge`), and adds the events it needs.
  import ItemIcon from "./ItemIcon.svelte";
  import { D, name } from "../lib/data.js";

  // `mark`: "apex" (the item a scheme is about), "leaf" (only gathered: a dashed edge), or "".
  // `tone`: the count's colour: "" (the accent), "enough" (green: you hold that many), "some" (orange: you hold part).
  let { id, href, badge = null, tone = "", mark = "", dim = false, label = "", style = "", ...rest } = $props();
</script>

<a class="itile {mark}" class:dim {href} style="--c:color-mix(in srgb, {D.items[id]?.color || '#131b3a'} var(--item-tone), #5b73a7); {style}" draggable="false" {...rest}>
  {#if badge !== null}<b class="ib {tone}">{badge}</b>{/if}
  <ItemIcon {id} size={44} />
  <span class="in">{label || name(id)}</span>
</a>

<style>
  /* The tile takes its tone from the surface it lies on (--surface, set by the pane or the box that holds it): the glass sits IN that
     surface, a little deeper at the foot, never a hole in it. */
  .itile {
    position: relative; flex: none; box-sizing: border-box; display: flex; flex-direction: column; align-items: center; gap: 4px;
    width: var(--tile); height: var(--tile); padding: 14px 6px 6px; overflow: visible;
    border-radius: 12px; text-align: center; text-decoration: none; color: var(--p-text);
    background: var(--suede), linear-gradient(180deg, color-mix(in srgb, var(--c) 17%, var(--surface, var(--p-bg))), color-mix(in srgb, var(--surface, var(--p-bg)) 90%, black) 76%);
    background-size: 192px 192px, auto;
    border: 1px solid var(--p-outline); border-bottom: 3px solid color-mix(in srgb, var(--c) 80%, var(--p-outline));
    font-size: 0.78rem; line-height: 1.15; font-weight: 500;
  }
  .itile:hover, .itile:focus-visible { border-color: var(--p-edge-accent); }
  .itile.apex { border-color: var(--p-edge-accent); background: var(--suede), color-mix(in srgb, var(--p-accent) 16%, var(--p-raised)); background-size: 192px 192px, auto; font-weight: 700; }
  .itile.leaf { border-style: dashed; }
  .itile.dim { opacity: 0.3; }
  /* The name has room for two lines, whatever it says. */
  .in { display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; overflow-wrap: break-word; hyphens: auto; max-width: 100%; min-height: 2.3em; }
  .ib {
    position: absolute; top: -9px; left: 50%; transform: translateX(-50%); min-width: 32px; height: 20px; padding: 0 8px;
    display: grid; place-items: center; border-radius: 10px; font-size: 0.75rem; font-weight: 700; white-space: nowrap;
    background: var(--p-accent); color: var(--p-on-accent); box-shadow: 0 0 0 2px var(--p-panel);
  }
  .ib.enough { background: var(--p-green); }
  .ib.some { background: var(--p-orange); }
  /* The tile is a pane of glass: one straight, not strong glare across its upper left, with a clean edge. Pointed at, the whole piece
     (glass and picture) lifts a little, a soft shadow falls under it, and the glare brightens a hair. */
  .itile::after {
    content: ""; position: absolute; inset: 0; border-radius: inherit; pointer-events: none;
    background: linear-gradient(128deg, rgb(255 255 255 / 0.13) 0%, rgb(255 255 255 / 0.06) 34%, rgb(255 255 255 / 0) 34.8%);
    transition: opacity 0.16s;
  }
  .itile { transition: transform 0.5s var(--spring), box-shadow 0.3s ease; }
  .itile:hover { transform: translateY(-3px); box-shadow: 0 11px 12px -8px rgb(6 8 17 / 0.75); }
  .itile:hover::after { background: linear-gradient(128deg, rgb(255 255 255 / 0.2) 0%, rgb(255 255 255 / 0.09) 34%, rgb(255 255 255 / 0) 34.8%); }
  @media (prefers-reduced-motion: reduce) { .itile { transition: none; } .itile:hover { transform: none; } }</style>











