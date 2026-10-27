<script>
  // The bar of the short path, in the place of Craft's filters while the path is open: what is allowed, how many, with
  // cooking or not, the way on to the Tree, and a plain, large "Close" that gives the table back.
  import Check from "./Check.svelte";
  import Icon from "./Icon.svelte";
  import ItemIcon from "./ItemIcon.svelte";
  import Select from "./Select.svelte";
  import ZoomBar from "./ZoomBar.svelte";
  import { D, name } from "../lib/data.js";
  import { t } from "../lib/i18n.js";
  import { debounce } from "../lib/util.js";
  import { tier as tierName } from "../lib/words.js";

  // `cycle`: the bar of a full cycle (a loop of lib/cycles.js): no raw materials to choose, qty is a multiplier of the whole scheme.
  let { target, tier = $bindable(0), qty = $bindable(1), cook = $bindable(false), cycle = false, zoom = $bindable(1), onfit, onclose } = $props();

  const TIER_TEXT = [t("from the planet only"), t("with asteroids"), t("with the atmosphere harvester")];
  const tiers = D.tiers.map((tr, i) => [i, TIER_TEXT[i] ?? tierName(tr.name)]);
  const typedQty = debounce((value) => {
    const n = Math.floor(Number(value));
    if (n >= 1) qty = Math.min(n, 9999);
  });
</script>

<div class="fbar one">
  <h1><ItemIcon id={target} size={32} /><span>{cycle ? t("Full loop") : t("Path")}: {name(target)}</span></h1>
  {#if !cycle}<Select label={t("Available")} bind:value={tier} options={tiers} title={D.tiers[tier].sources.map(name).sort().join(", ")} />{/if}
  <label class="fsel"><span>{cycle ? t("Multiplier") : t("How many")}</span><input type="number" min="1" max="9999" value={qty} oninput={(e) => typedQty(e.target.value)}></label>
  {#if !cycle}<Check label={t("Cooking")} tri={false} bind:value={cook} title={t("Count cooking recipes too")} />{/if}
  <a class="btn" href="#/tree/{encodeURIComponent(target)}"><Icon name="tree" size={16} />{t("All chains")}</a>
  <span class="zoomwrap"><ZoomBar bind:zoom {onfit} /></span>
  <button type="button" class="close" onclick={onclose} title={t("Close and return to the table (Esc)")} aria-label={t("Close")}><span aria-hidden="true">✕</span>{t("Close")}</button>
</div>

<style>
  /* At the far end of the bar, in the colour of a way out, never to be missed. */
  .close {
    display: inline-flex; align-items: center; gap: 8px; height: 36px; padding: 0 16px 0 12px; flex: none;
    border-radius: 10px; border: 1px solid var(--p-red); background: color-mix(in srgb, var(--p-red) 12%, transparent);
    color: var(--p-red); font: inherit; font-weight: 700; cursor: pointer;
  }
  .zoomwrap { margin-left: auto; flex: none; }
  .close span { font-size: 1.1rem; line-height: 1; }
  .close:hover { background: color-mix(in srgb, var(--p-red) 24%, transparent); }
</style>




