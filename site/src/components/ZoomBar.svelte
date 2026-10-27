<script>
  // The scale panel of a canvas: "−", the percentage, "+", and "Fit height".
  import { t } from "../lib/i18n.js";
  let { zoom = $bindable(1), onfit } = $props();
  const set = (z) => { zoom = Math.min(1.6, Math.max(0.2, +z.toFixed(2))); };
</script>

<div class="zoom">
  <button type="button" onclick={() => set(zoom - 0.1)} aria-label={t("Zoom out")}>−</button>
  <span>{Math.round(zoom * 100)}%</span>
  <button type="button" onclick={() => set(zoom + 0.1)} aria-label={t("Zoom in")}>+</button>
  <button type="button" class="fit" onclick={onfit}>{t("Fit height")}</button>
</div>

<style>
  .zoom { flex: none; display: flex; align-items: center; height: 36px; border-radius: 10px; background: var(--p-panel); border: 1px solid var(--p-outline); overflow: hidden; }
  .zoom button { height: 100%; min-width: 34px; padding: 0 10px; background: none; border: 0; color: var(--p-text); font: inherit; font-size: 1.05rem; cursor: pointer; }
  .zoom button:hover { background: var(--p-raised); color: var(--p-accent-ink); }
  .zoom .fit { font-size: 0.85rem; border-left: 1px solid var(--p-outline); }
  .zoom span { min-width: 3.4em; text-align: center; font-size: 0.85rem; color: var(--p-muted); font-variant-numeric: tabular-nums; }
</style>

