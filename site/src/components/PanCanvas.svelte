<script>
  // The canvas of the craft tree, for every page that draws pyramids: a dotted board that is moved by dragging anywhere on
  // it, zoomed with Ctrl + wheel or the page's panel (ZoomBar), and on which nothing is selected or picked up (text, pictures).
  // A press that moved is a pan, never the click of the tile it started on.
  // `onpan`: called when a drag starts (a card over a tile goes away).
  import { tick } from "svelte";
  import { t } from "../lib/i18n.js";
  import { swap } from "../lib/motion.js";
  let { zoom = $bindable(1), onpan = undefined, children } = $props();
  let scroller = $state();
  let drag = null;

  const setZoom = (z) => { zoom = Math.min(1.6, Math.max(0.2, +z.toFixed(2))); };
  /** The zoom at which the chain nearest to the left edge that is in view (not just a sliver of it) just fills the height of the
   *  canvas; it is then brought to the left, top at the top. */
  export async function fit() {
    const edge = scroller.getBoundingClientRect();
    const chains = [...scroller.firstElementChild.children].map((el) => ({ el, rect: el.getBoundingClientRect() })).filter(({ rect }) => rect.height > 50);
    const lead = chains.find(({ rect }) => rect.right > edge.left + 40) ?? chains[0];
    if (!lead) return;
    setZoom(Math.floor(((scroller.clientHeight - 2) / (lead.rect.height / zoom)) * 100) / 100); // rounded down: never a hair too high
    await tick();
    const now = lead.el.getBoundingClientRect();
    scroller.scrollBy({ left: now.left - edge.left - 14 * zoom, top: now.top - edge.top - 1 });
  }
  /** Is a drag going on (so a card over a tile must not open)? */
  export const moved = () => Boolean(drag?.moved);

  function down(e) {
    if (e.button !== 0 || e.target.closest("button, input, select, label, summary")) return;
    drag = { x: e.clientX, y: e.clientY, l: scroller.scrollLeft, t: scroller.scrollTop, id: e.pointerId, moved: false };
  }
  function move(e) {
    if (!drag) return;
    const dx = e.clientX - drag.x;
    const dy = e.clientY - drag.y;
    if (!drag.moved) {
      if (Math.hypot(dx, dy) < 5) return;
      drag.moved = true;
      onpan?.();
      scroller.setPointerCapture(drag.id); // only now: a plain press still clicks its tile
      scroller.classList.add("grab");
    }
    scroller.scrollLeft = drag.l - dx;
    scroller.scrollTop = drag.t - dy;
  }
  function up() {
    if (drag?.moved) scroller.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); }, { capture: true, once: true });
    drag = null;
    scroller?.classList.remove("grab");
  }
  function wheel(e) {
    if (!e.ctrlKey) return;
    e.preventDefault();
    setZoom(zoom + (e.deltaY < 0 ? 0.1 : -0.1));
  }
</script>

<div class="pan" use:swap={{ initial: true, edge: "left" }}>
  <div class="canvas" role="application" aria-label={t("Canvas")} bind:this={scroller} onpointerdown={down} onpointermove={move}
    onpointerup={up} onpointercancel={up} onwheel={wheel} ondragstart={(e) => e.preventDefault()} onselectstart={(e) => e.preventDefault()}>
    <div class="inner" style="zoom:{zoom}">{@render children()}</div>
  </div>
</div>

<style>
  .pan { position: relative; height: 100%; min-height: 240px; display: flex; flex-direction: column; }
  .canvas {
    position: relative; isolation: isolate; z-index: 0; overflow: auto; cursor: grab; touch-action: none; flex: 1 1 auto;
    min-height: 240px;
    border: 1px solid var(--p-outline); border-radius: 14px;
    background: transparent; /* only its edge and its shadow are drawn: what lies behind shows through */
    user-select: none; -webkit-user-select: none;
  }
  .canvas:global(.grab) { cursor: grabbing; }
  .canvas :global(img) { -webkit-user-drag: none; user-select: none; pointer-events: none; }
  .inner { display: flex; align-items: flex-start; gap: 14px; padding: 14px; width: max-content; min-width: 100%; }
</style>



