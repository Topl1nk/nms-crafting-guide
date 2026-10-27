<script>
  // The card of one recipe, for refining and cooking alike: what it makes, what
  // it needs, the numbers, and a way to every other page about the item.
  import Action from "./Action.svelte";
  import { swap } from "../lib/motion.js";
  import Band from "./Band.svelte";
  import Chips from "./Chips.svelte";
  import Icon from "./Icon.svelte";
  import Ingredients from "./Ingredients.svelte";
  import RecipeNode from "./RecipeNode.svelte";
  import ItemIcon from "./ItemIcon.svelte";
  import ItemLink from "./ItemLink.svelte";
  import Units from "./Units.svelte";
  import { fmtInt, fmtSigned } from "../lib/core.js";
  import { buffOf, CONSUMED, D, easeOf, easeOfRecipe, name, placement, PRODUCED, RECIPES } from "../lib/data.js";
  import { inventory } from "../lib/inventory.svelte.js";
  import { list, t, tn } from "../lib/i18n.js";
  import { lineOf, wikiRar, wikiStore, wikiType } from "../lib/store.js";
  import { toast } from "../lib/toast.svelte.js";
  import { band, easeDescribe, machine } from "../lib/words.js";

  // `onpath`: opens the short path of the item in place (Craft's canvas over its table); without it the button is a link.
  let { r, onpath = null, oncycle = null } = $props();

  const out = $derived(r.out[0]);
  const id = $derived(encodeURIComponent(out));
  const p = $derived(placement(out));
  const buff = $derived(buffOf(out));
  // A loop (r.cycle): the recipes that make it up, with how many times each is run in a turn.
  const parts = $derived(r.cycle ? r.cycle.parts.map((p) => ({ ...p, r: RECIPES[p.recipe] })) : []);
  const others = $derived(r.cycle ? [] : (PRODUCED[out] || []).filter((o) => o.index !== r.index)
    .sort((a, b) => Math.max(b.loop, b.ratio) - Math.max(a.loop, a.ratio)));
  const uses = $derived((CONSUMED[out] || []).length);
  // "1→6": the result is also an ingredient (1 Chlorine + 2 Oxygen -> 6 Chlorine). It multiplies that one item; it is no cycle
  // that runs by itself, every run spends the other ingredients too and they have to be got from elsewhere.
  const loopNote = $derived.by(() => {
    const own = r.in.find(([i]) => i === out);
    if (!(r.loop > 1 && own)) return null;
    const rest = list(r.in.filter(([i]) => i !== out).map(([i, n]) => `${n} ${name(i)}`));
    return t("{item}: put in {in}, got {out}. Each run also spends {rest}: you have to get those elsewhere", { item: name(out), in: own[1], out: r.out[1], rest });
  });

  function addToInventory() {
    toast(t("{item}: now {n} in my items", { item: name(out), n: inventory.add(out) }));
  }
</script>

<aside class="detail" use:swap={{ key: r.index, drop: true }}>
  <div class="ic-head">
    <ItemIcon id={out} size={60} />
    <div>
      <h2>{r.outLabel}</h2>
      <p class="muted">{D.items[out]?.sub ?? ""}</p>
    </div>
    {#if !inventory.fromSave}<button class="ic-add" title={t("Add to my items")} aria-label={t("Add to my items")} onclick={addToInventory}><Icon name="plus" size={18} /></button>{/if}
  </div>
  <div class="ic-chips">
    <Chips id={out} typeHref={wikiType(out)} rarHref={wikiRar(out)} />
    <span title={t("How easy the rarest ingredient is to get")}><Band ease={easeOfRecipe(r)} /></span>
    {#if p}<Action placement={p} size={32} href={wikiStore(lineOf(p))} />{/if}
  </div>

  {#if !r.cycle}
  <div class="recipe-box">
    <Ingredients recipe={r} tiles />
    <span class="arrow" aria-hidden="true">➜</span>
    <RecipeNode id={out} qty={r.out[1]} ri={r.index} />
  </div>
  {/if}

  <div class="stats">
    <div class="stat" title={r.cycle ? t("Time of one turn: all the runs in order") : t("Time of one cycle")}><Icon name="clock" /><b>{r.timeLabel}</b><small>{r.cycle ? t("turn") : t("time")}</small></div>
    {#if r.cycle}
      <div class="stat" title={t("What is left after one turn")}><Icon name="times" /><b>{r.mult}</b><small>{t("per turn")}</small></div>
      <div class="stat" title={t("How many different recipes are in the loop")}><Icon name="flask" /><b>{parts.length}</b><small>{t("recipes")}</small></div>
      <div class="stat" title={t("How many runs are in one turn")}><Icon name="gauge" /><b>{r.cycle.order.length}</b><small>{t("runs")}</small></div>
    {:else}
    <div class="stat" title={loopNote ?? t("How many times more you get than you put in")}><Icon name="times" /><b>{r.mult}</b><small>{t("yield")}</small></div>
    <div class="stat" title={t("Pieces an hour from one machine that is never idle")}><Icon name="gauge" /><b>{fmtInt(r.rate)}</b><small>{t("per hour")}</small></div>
    <div class="stat" title={t("By how many units the result is worth more than the ingredients, per cycle")}><Units size={18} /><b>{fmtSigned(r.profit)}</b><small>{t("gain")}</small></div>
    {/if}
  </div>
  <div class="ic-meta">
    <div><Icon name="flask" size={16} /><span>{r.op}</span></div>
    <div><Icon name="box" size={16} /><span>{machine(r.machine)}</span></div>
    {#if buff}
      <div title={buff.use}><Icon name="bolt" size={16} /><span><b>{buff.effect}</b>, {t("strength {n}", { n: buff.potency.toFixed(2) })}{#if buff.use}<span class="muted"> · {buff.use}</span>{/if}</span></div>
    {/if}
  </div>

  <nav class="acts2">
    {#if r.cycle}<button type="button" class="primary" onclick={() => oncycle?.(r)}><Icon name="route" />{t("Full loop")}</button>
    <a href="#/tree/{id}"><Icon name="tree" />{t("Craft tree")}</a>
    {:else}<a class="primary half" href="#/tree/{id}"><Icon name="tree" />{t("Craft tree")}</a>{/if}
    {#if onpath}<button type="button" onclick={() => onpath(out)}><Icon name="route" />{t("Short path")}</button>
    {:else}<a href="#/recipes?path={id}"><Icon name="route" />{t("Short path")}</a>{/if}
    <a href="#/recipes?item={id}&role=output"><Icon name="make" />{t("How to make")}<i>{(PRODUCED[out] || []).length}</i></a>
    <a href="#/recipes?item={id}&role=input"><Icon name="need" />{t("Where it is needed")}<i>{uses}</i></a>
  </nav>

  <h3>{r.cycle ? t("Start with") : t("Ingredients")}</h3>
  <ul class="lines">
    {#each r.in as [ing, n]}
      <li>
        <span class="n">{n}×</span>
        <span class="who"><ItemLink id={ing} size={30} /></span>
        {#if inventory.items[ing]}<span class="have" title={t("You have it")}><Icon name="bag" size={13} />{fmtInt(inventory.items[ing])}</span>{/if}
        <span class="val" title={t("Price each, in units. Getting it: {band} — {how}", { band: band(easeOf(ing).band).toLowerCase(), how: easeDescribe(easeOf(ing).describe) })}><span class="gold"><Units />{fmtInt(D.items[ing]?.value ?? 0)}</span></span>
      </li>
    {/each}
  </ul>
  {#if parts.length}
    <h3>{t("Recipes of the loop")} · {parts.length}</h3>
    <ul class="lines">
      {#each parts as p (p.recipe)}
        <li>
          <a class="way" href="#/recipes?item={encodeURIComponent(p.r.out[0])}&role=output&r={p.recipe}" title={p.r.inputs}>
            <Ingredients recipe={p.r} size={26} compact />
            <span class="what">{p.r.inputs} → {p.r.outLabel}</span>
            <span class="val" title={t("How many times to run it per turn")}>{tn(p.runs, "{n} time|{n} times")}</span>
          </a>
        </li>
      {/each}
    </ul>
    <p class="muted note">{t("Order of runs:")} {r.cycle.order.map((i) => RECIPES[i].outName).join(" → ")}</p>
  {/if}
  {#if others.length}
    <h3>{t("Other ways")} · {others.length}</h3>
    <ul class="lines">
      {#each others.slice(0, 5) as o (o.index)}
        <li>
          <a class="way" href="#/recipes?item={id}&role=output&r={o.index}" title={o.inputs}>
            <Ingredients recipe={o} size={26} compact />
            <span class="what">{o.inputs}</span>
            <span class="val">{o.mult}</span>
          </a>
        </li>
      {/each}
    </ul>
  {/if}
</aside>

<style>
  .recipe-box {
    display: flex; flex-wrap: wrap; align-items: center; gap: 24px 12px;
    padding: 20px 12px 12px; margin: 0 0 4px;
    background: var(--p-raised); border-radius: 14px;
  }
  .arrow { font-size: 1.4rem; font-weight: 900; color: var(--p-accent-ink); } /* U+279C, a heavy arrow */
  .ic-meta b { color: var(--p-text); }

  .lines { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
  .lines li { display: flex; align-items: center; gap: 10px; min-height: 38px; padding: 0 6px; border-radius: 8px; }
  .lines li:hover { background: var(--p-raised); }
  .n { min-width: 2.4em; text-align: right; color: var(--p-accent-ink); font-weight: 700; font-variant-numeric: tabular-nums; }
  .who { flex: 1; min-width: 0; }
  .val { color: var(--p-faint); font-size: 0.85rem; font-variant-numeric: tabular-nums; white-space: nowrap; }
  /* The name is underlined only while the pointer is over its row, even if it is not on the text itself. */
  .who :global(a) { text-decoration: none; }
  .lines li:hover .who :global(a) { text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 0.2em; }
  .way { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; min-height: 38px; color: inherit; text-decoration: none; }
  .what { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--p-muted); font-size: 0.88rem; }
  .way:hover .what { color: var(--p-accent-ink); }
  .note { font-size: 0.85rem; margin: 8px 6px 0; }
</style>









