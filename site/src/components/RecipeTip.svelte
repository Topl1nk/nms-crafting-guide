<script>
  // The small card that follows the pointer over a tile of the craft tree: the
  // recipe of that step, with the numbers for the amount asked, never a scrap
  // of text. It is fixed to the window (the canvas scrolls and zooms under it)
  // and lets the pointer through, so it cannot get in the way of the tile.
  import Icon from "./Icon.svelte";
  import ItemIcon from "./ItemIcon.svelte";
  import { fmtInt, fmtSigned } from "../lib/core.js";
  import { buffOf, CONSUMED, D, easeOf, name, PRODUCED, RECIPES } from "../lib/data.js";
  import { t, tn } from "../lib/i18n.js";
  import { easeDescribe, easeLabel, machine } from "../lib/words.js";
  import Units from "./Units.svelte";

  let { tip } = $props();
  const makes = $derived((PRODUCED[tip.id] || []).length);
  const uses = $derived((CONSUMED[tip.id] || []).length);

  // Moved to <body>: a table or a card around the tile would otherwise be the window it is fixed to.
  function portal(node) {
    document.body.appendChild(node);
    return { destroy() { node.remove(); } };
  }

  const r = $derived(tip.ri === undefined || tip.ri === null ? null : RECIPES[tip.ri]);
  const buff = $derived(buffOf(tip.id));
  const ease = $derived(easeOf(tip.id));

  const W = 300;
  let box = $state();
  let x = $state(0);
  let y = $state(0);
  // Right of the tile if it fits, else left of it; level with the tile, kept inside the window.
  $effect(() => {
    const { rect } = tip;
    const h = box?.offsetHeight ?? 220;
    x = rect.right + 12 + W <= innerWidth ? rect.right + 12 : Math.max(8, rect.left - 12 - W);
    y = Math.max(8, Math.min(rect.top, innerHeight - h - 8));
  });
</script>

<div class="tip" use:portal bind:this={box} style="left:{x}px; top:{y}px; width:{W}px">
  <div class="top">
    <ItemIcon id={tip.id} size={40} />
    <div>
      <b>{name(tip.id)}</b>
      <small class="muted">{#if tip.need}{t("need {n}", { n: fmtInt(tip.need) })}{#if r && tip.batches} · {t("batches {n}, yields {yield}", { n: fmtInt(tip.batches), yield: fmtInt(tip.yield) })}{/if}{:else}{D.items[tip.id]?.sub ?? ""}{/if}</small>
    </div>
  </div>
  {#if r}
    <div class="box">{#each r.in as [ing, n], i}{#if i}<span class="plus">+</span>{/if}<span class="ing"><ItemIcon id={ing} size={28} />{#if n > 1}<b>{n}×</b>{/if}<span>{name(ing)}</span></span>{/each}<span class="arrow">→</span><b>{r.outLabel}</b></div>
    <div class="nums">
      <span title={t("Time of one cycle")}><Icon name="clock" size={14} />{r.timeLabel}</span>
      <span title={t("Yield")}><Icon name="times" size={14} />{r.mult}</span>
      <span title={t("Per hour")}><Icon name="gauge" size={14} />{fmtInt(r.rate)}</span>
      <span title={t("Gain per cycle, in units")}><Units size={14} />{fmtSigned(r.profit)}</span>
    </div>
    <div class="line"><Icon name="flask" size={14} /><span>{r.op} · {machine(r.machine)}</span></div>
    {#if buff}<div class="line"><Icon name="bolt" size={14} /><span><b>{buff.effect}</b>, {t("strength {n}", { n: buff.potency.toFixed(2) })}</span></div>{/if}
  {:else}
    {#if !PRODUCED[tip.id]}<div class="line"><Icon name="bag" size={14} /><span>{t("cannot be crafted:")} {easeLabel(ease.label)}</span></div>{:else}<div class="line"><Icon name="bag" size={14} /><span>{easeLabel(ease.label)}</span></div>{/if}
    {#if ease.where}<div class="line muted"><span>{easeDescribe(ease.where)}</span></div>{/if}
    <div class="line"><Icon name="bag" size={14} /><span>{t("price each")} <Units />{fmtInt(D.items[tip.id]?.value ?? 0)}</span></div>
    {#if makes}<div class="line"><Icon name="make" size={14} /><span>{tn(makes, "Made in {n} way|Made in {n} ways")}</span></div>{/if}
    {#if uses}<div class="line"><Icon name="need" size={14} /><span>{tn(uses, "Needed for {n} recipe|Needed for {n} recipes")}</span></div>{/if}
  {/if}
</div>

<style>
  .tip {
    position: fixed; z-index: 60; pointer-events: none; padding: 12px;
    background: var(--p-panel); border: 1px solid var(--p-edge-accent); border-radius: 14px;
    box-shadow: 0 16px 40px rgb(0 0 0 / 0.5); font-size: 0.88rem; line-height: 1.3;
  }
  .top { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .top div { display: grid; min-width: 0; }
  .top b { font-size: 1rem; overflow-wrap: anywhere; }
  .box { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 10px; padding: 8px 10px; margin-bottom: 8px; background: var(--p-raised); border-radius: 10px; }
  .box b { color: var(--p-text); }
  .arrow { color: var(--p-accent-ink); font-size: 1.2rem; }
  .ing { display: inline-flex; align-items: center; gap: 4px; }
  .ing b { color: var(--p-accent-ink); }
  .plus { color: var(--p-faint); }
  .nums { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 4px; margin-bottom: 8px; }
  .nums span { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 6px 2px; border-radius: 8px; background: var(--p-raised); font-weight: 700; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .nums :global(.ic) { color: var(--p-accent-ink); }
  .line { display: flex; align-items: flex-start; gap: 8px; color: var(--p-muted); margin-top: 4px; }
  .line :global(.ic) { margin-top: 2px; color: var(--p-faint); }
  .line b { color: var(--p-text); }
</style>


