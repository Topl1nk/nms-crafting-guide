<script>
  // What to do with one item, from the storage guide: put it in a container, or sell, junk or use it. Shared by the
  // Wiki's card and the card of "My items". With `at` (the place a row of the save lies in) it says where the item
  // lies, whether that is right, and where it belongs; `onfindall` adds "Find all" (the item has other places).
  //
  // One scale of text (14px, labels 12px), one tag per fact: the place it lies in, the place it goes to, once each.
  import Action from "./Action.svelte";
  import Icon from "./Icon.svelte";
  import PlaceTag from "./PlaceTag.svelte";
  import { CONSUMED, D, ENGLISH, PRODUCED } from "../lib/data.js";
  import { t } from "../lib/i18n.js";
  import { lineOf, wikiStore } from "../lib/store.js";

  let { id, recipes = true, at = null, onfindall = null, others = 0, links = true } = $props(); // `links`: the tag of the place leads to the Wiki's filter (not in the Wiki itself)

  const item = $derived(D.items[id]);
  const p = $derived(item ? D.storage.outcomes[item.store] : null);
  const home = $derived(p ? D.storage.homes.find((h) => h.key === p.home) : null);
  // "Named in the guide" says nothing: that reason is left out; any other is shown (in the page's language).
  const why = $derived(p && ENGLISH.storage.outcomes[item.store]?.why !== "Named in the guide" ? p.why : "");
  const target = $derived(p ? wikiStore(lineOf(p)) : "");
  const showGoes = $derived(!at || at.fit !== "ok");
  const hasButtons = $derived((recipes && (PRODUCED[id] || CONSUMED[id])) || onfindall);
</script>

{#if p}
  {#if at?.fit}
    <p class="status {at.fit}"><b class="badge">{at.fit === "ok" ? "✔" : "➜"}</b>{at.fit === "ok" ? t("It lies in its place") : t("It lies in the wrong place")}</p>
  {/if}
  <div class="rows">
    {#if at}
      <div class="row"><span class="lbl">{t("Where it lies")}</span><PlaceTag {...at.place} size={36} /></div>
    {/if}
    {#if showGoes}
      <div class="row">
        <span class="lbl">{t("Where to put it")}</span>
        <span class="val"><Action placement={p} size={36} href={links ? target : ""} />{#if home?.container}<span class="n">{t("Container {n}", { n: home.key })}</span>{/if}</span>
      </div>
    {/if}
  </div>
  {#if (home && home.key !== "none") || why}
    <div class="about">
      {#if home && home.key !== "none"}<span>{home.note}</span>{/if}
      {#if why}<span>{why}</span>{/if}
    </div>
  {/if}
  {#if home?.container}
    <p class="hint"><Icon name="bolt" size={16} /><span>{t("Once one of these lies in a container, the rest go to the same one by themselves when sent to storage.")}</span></p>
  {/if}
  {#if hasButtons}
    <div class="btns">
      {#if recipes && (PRODUCED[id] || CONSUMED[id])}<a class="btn" href="#/recipes?item={encodeURIComponent(id)}">{t("Recipes")}</a>{/if}
      {#if onfindall}<button type="button" class="btn" onclick={onfindall} title={t("Show in the table every place this item lies in")}>{t("Find all")}<i>{others}</i></button>{/if}
    </div>
  {/if}
{/if}

<style>
  /* The state of the item, as the table says it: the same frame (✔ green, ➜ yellow), then the words. */
  .status { display: flex; align-items: center; gap: 8px; margin: 10px 0 4px; font-size: 0.875rem; font-weight: 600; }
  .status.ok { color: var(--p-green); }
  .status.wrong { color: var(--p-yellow); }
  .badge {
    display: inline-flex; align-items: center; justify-content: center; flex: none; width: 34px; height: 24px; box-sizing: border-box;
    border: 1px solid currentColor; border-radius: 8px; font-size: 0.95rem; line-height: 1;
  }
  .status.wrong .badge { font-weight: 900; }
  /* A label above its tag: the whole width of the card is the tag's, so a long name is never cut. */
  .rows { display: grid; gap: 6px; margin: 8px 0; }
  .row { display: grid; gap: 2px; min-width: 0; }
  .lbl { font-size: 0.75rem; letter-spacing: 0.04em; text-transform: uppercase; color: var(--p-faint); }
  .val { display: flex; flex-wrap: nowrap; align-items: center; gap: 8px; min-width: 0; }
  .n { flex: none; font-size: 0.875rem; color: var(--p-muted); white-space: nowrap; }
  /* What the place is: a grey block. */
  .about {
    display: grid; gap: 6px; margin: 10px 0; padding: 10px 12px; border-radius: 12px; font-size: 0.875rem; line-height: 1.4;
    border: 1px solid var(--p-outline); background: var(--p-raised); color: var(--p-muted);
  }
  /* A tip: no box, a bar and a picture, so it does not compete with the grey block above it. */
  .hint { display: flex; align-items: flex-start; gap: 8px; margin: 10px 0; padding: 2px 0 2px 10px; border-left: 3px solid var(--p-edge-accent); font-size: 0.8125rem; line-height: 1.4; color: var(--p-muted); }
  .hint :global(.ic) { flex: none; margin-top: 1px; color: var(--p-accent-ink); }
  /* The card's buttons stay in view at the bottom while the rest scrolls. */
  .btns { position: sticky; bottom: 0; display: flex; flex-wrap: wrap; gap: 8px; margin: 12px -2px -2px; padding: 10px 2px 2px; background: var(--p-panel); }
  .btns i { font-style: normal; font-weight: 400; color: var(--p-faint); margin-left: 6px; }
</style>



