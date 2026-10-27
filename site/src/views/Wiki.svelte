<script module>
  // The search and the filters outlive a visit, as on the other pages (a link brings its own).
  const st = { q: "", filters: null };
  const DEFAULTS = { type: "any", rar: "any", store: "any", makes: false, mine: false };
</script>

<script>
  // Every item the game has, built like the Recipes page: a list, filters, and a
  // card for the item in place of the recipe's.
  import Action from "../components/Action.svelte";
  import Check from "../components/Check.svelte";
  import Chips from "../components/Chips.svelte";
  import { capture, swap } from "../lib/motion.js";
  import Icon from "../components/Icon.svelte";
    import ItemIcon from "../components/ItemIcon.svelte";
  import Units from "../components/Units.svelte";
  import List from "../components/List.svelte";
  import Reset from "../components/Reset.svelte";
  import Select from "../components/Select.svelte";
  import StorageNote from "../components/StorageNote.svelte";
  import { fmtInt } from "../lib/core.js";
  import { D, placement } from "../lib/data.js";
  import { applyFacets, FLAG, facets, flag } from "../lib/facets.js";
  import { collate, t } from "../lib/i18n.js";
  import { inventory } from "../lib/inventory.svelte.js";
  import { setKeys } from "../lib/keys.js";
  import { arrival, go } from "../lib/router.svelte.js";
  import { inStore, storeLines } from "../lib/store.js";
  import { toast } from "../lib/toast.svelte.js";
  import { debounce } from "../lib/util.js";
  import { loadWiki } from "../lib/wiki.js";
  import { RARITIES, rarityLabel, rarityRank, typeLabel } from "../lib/words.js";

  const { params } = arrival();
  // A link opens its own view, not one narrowed by what was set last time.
  const linked = params.size > 0;

  let all = $state.raw(null);
  let failed = $state("");
  loadWiki().then((r) => { all = r.map((x) => ({ ...x, key: `${x.name} ${x.sub}`.toLowerCase() })); }, (e) => { failed = e.message; });

  // A link may bring a filter (`type`, `rar`, `store`: a line of the storage scheme, lib/store.js) and an item whose card is to be open (`item`: its row is under the cursor).
  let f = $state(linked
    ? { ...DEFAULTS, type: params.get("type") ?? "any", rar: params.get("rar") ?? "any", store: params.get("store") ?? "any" }
    : { ...DEFAULTS, ...st.filters });
  let q = $state(params.get("q") ?? (linked ? "" : st.q));
  let want = $state(params.get("item") ?? ""); // dropped as soon as the list is changed by hand
  const start = $derived(want ? Math.max(0, rows.findIndex((x) => x.id === want)) : 0);
  let cur = $state.raw(null);
  let list = $state();
  let search = $state();
  $effect(() => { const now = { ...f }; if (!linked) st.filters = now; });

  const types = $derived(all ? [...new Set(all.map((x) => x.type))].sort((a, b) => collate(typeLabel(a), typeLabel(b))) : []);
  const rarityChoices = [["any", t("any rarity")], ["Common", t("common")], ...Object.keys(RARITIES).map((k) => [k, rarityLabel(k).toLowerCase()])];
  const defs = $derived([
    { key: "type", options: [["any", t("any kind")], ...types.map((type) => [type, typeLabel(type)])], neutral: "any", test: (x, v) => v === "any" || x.type === v },
    { key: "rar", options: rarityChoices, neutral: "any", test: (x, v) => v === "any" || x.rar === v },
    { key: "store", options: [["any", t("any number")], ...storeLines().map((l) => [l.key, l.name, l.icon])], neutral: "any", test: (x, v) => v === "any" || inStore(x.id, v) },
    { key: "makes", options: FLAG, neutral: false, test: (x, v) => flag(v, x.makes > 0) },
    { key: "mine", options: FLAG, neutral: false, test: (x, v) => flag(v, inventory.items[x.id] > 0) },
  ]);
  const base = $derived.by(() => {
    if (!all) return [];
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    return terms.length ? all.filter((x) => terms.every((w) => x.key.includes(w))) : all;
  });
  const fx = $derived(facets(base, defs, f));
  const rows = $derived(applyFacets(base, defs, fx.effective));
  const filtered = $derived(Object.keys(DEFAULTS).some((k) => f[k] !== DEFAULTS[k]) || q !== "" || want !== "");

  const typed = debounce((v) => { want = ""; q = v; st.q = v; });
  const reset = () => { want = ""; f = { ...DEFAULTS }; q = st.q = ""; if (search) search.value = ""; };
  function addToInventory(id) {
    const n = inventory.add(id);
    toast(t("{item}: now {n} in my items", { item: D.items[id].name, n }));
  }

  setKeys({
    get list() { return list; },
    get search() { return search; },
    enter: () => { const r = list?.current(); if (r) go(`#/recipes?item=${encodeURIComponent(r.id)}`); },
    escape: () => { search.value = ""; q = st.q = ""; },
  });
</script>

{#snippet itemCell(x)}<span class="mk"><ItemIcon id={x.id} size={32} color={x.color} lazy /><span class="t">{x.name}</span></span>{/snippet}
{#snippet priceCell(x)}<span class="gold"><Units />{fmtInt(x.value)}</span>{/snippet}
{#snippet typeCell(x)}<Chips id={x.id} type={x.type} show="type" />{/snippet}
{#snippet rarCell(x)}<Chips id={x.id} rar={x.rar} show="rarity" />{/snippet}
{#snippet goesCell(x)}{#if placement(x.id)}<Action placement={placement(x.id)} />{/if}{/snippet}

<div class="fbar">
  <h1><span>{t("Wiki")}</span></h1>
  <Reset active={filtered} onclick={reset} />
  <input class="search" type="search" placeholder={t("Search by name…")} value={q} autocomplete="off"
    bind:this={search} oninput={(e) => typed(e.target.value)}>
  <Select hidden={!(fx.show.type)} label={t("Type")} value={fx.effective.type} options={fx.options.type} all={fx.all.type} neutral={fx.neutral.type} onchange={(v) => { want = ""; f.type = v; }} title={t("What sort of item it is: substance, component, technology…")} />
  <Select hidden={!(fx.show.rar)} label={t("Rarity")} value={fx.effective.rar} options={fx.options.rar} all={fx.all.rar} neutral={fx.neutral.rar} onchange={(v) => { want = ""; f.rar = v; }} />
  <Select hidden={!(fx.show.store)} label={t("Where to put it")} value={fx.effective.store} options={fx.options.store} all={fx.all.store} neutral={fx.neutral.store} onchange={(v) => { want = ""; f.store = v; }} title={t("Where to put it: which container, or sell, throw away or use")} />
  <Check hidden={!(fx.show.makes)} label={t("Can be made")} value={fx.effective.makes} onchange={(v) => { f.makes = v; }} title={t("Only what can be made")} />
  <Check hidden={!(fx.show.mine)} label={t("My items")} value={fx.effective.mine} onchange={(v) => { f.mine = v; }} title={t("Only what you have")} />
</div><div class="count">{#if all}{t("Items:")} <b>{fmtInt(rows.length)}</b>{rows.length !== all.length ? ` ${t("of {n}", { n: fmtInt(all.length) })}` : ""} · {t("everything in the game's tables")}{:else if failed}<span class="err">{t("Could not load: {error}", { error: failed })}</span>{:else}{t("Loading…")}{/if}</div>

<div class="split">
  <List bind:this={list} {rows} {start} atTop columns={[
    { title: t("Item"), cell: itemCell, cls: "strong", sort: (x) => x.name },
    { title: t("Type"), cell: typeCell, cls: "wide-only", sort: (x) => x.type },
    { title: t("Rarity"), cell: rarCell, cls: "wide-only", sort: (x) => rarityRank(x.rar) },
    { title: t("Where to put it"), cell: goesCell, cls: "wide-only", sort: (x) => placement(x.id)?.label ?? "" },
    { title: t("What it is"), text: (x) => x.sub, cls: "muted wide-only clip", sort: (x) => x.sub },
    { title: t("Price"), cell: priceCell, cls: "num", sort: (x) => x.value },
    { title: t("How to make"), text: (x) => x.makes || "·", cls: "num wide-only", sort: (x) => x.makes },
    { title: t("Where it is needed"), text: (x) => x.needs || "·", cls: "num wide-only", sort: (x) => x.needs },
  ]} onSelect={(x) => { capture(); cur = x; }} onEnter={(x) => go(`#/recipes?item=${encodeURIComponent(x.id)}`)} empty={all ? t("Nothing found.") : t("Loading…")} />

  {#if !rows.length}
    <aside class="detail"><p class="muted">{t("Nothing found.")}</p></aside>
  {:else if cur}
    {@const x = cur}
    {@const id = encodeURIComponent(x.id)}
    {@const carry = D.items[x.id]}
    {@const got = inventory.items[x.id] ?? 0}
    <aside class="detail" use:swap={{ key: x.id, peel: true }}>
      <div class="ic-head">
        <ItemIcon id={x.id} size={60} color={x.color} />
        <div><h2>{x.name}</h2><p class="muted">{x.sub}</p></div>
        {#if carry && !inventory.fromSave}<button class="ic-add" title={t("Add to my items")} aria-label={t("Add to my items")} onclick={() => addToInventory(x.id)}><Icon name="plus" size={18} /></button>{/if}
      </div>
      <div class="ic-chips">
        <Chips id={x.id} type={x.type} rar={x.rar} />
      </div>

      <div class="stats">
        <div class="stat" title={t("Price each")}><Units size={18} /><b>{fmtInt(x.value)}</b><small>{t("price")}</small></div>
        <div class="stat" title={t("How many recipes make this")}><Icon name="make" /><b>{x.makes}</b><small>{t("how to make")}</small></div>
        <div class="stat" title={t("How many recipes need this")}><Icon name="need" /><b>{x.needs}</b><small>{t("where needed")}</small></div>
        <div class="stat" title={t("How many you have")}><Icon name="bag" /><b>{fmtInt(got)}</b><small>{t("you have")}</small></div>
      </div>

      {#if x.desc}<p class="desc">{x.desc}</p>{/if}

      {#if carry}<StorageNote id={x.id} recipes={false} links={false} />{/if}

      <nav class="acts2">
        {#if x.makes}<a class="primary half" href="#/tree/{id}"><Icon name="tree" />{t("Craft tree")}</a>{/if}
        {#if x.makes}<a href="#/recipes?path={id}"><Icon name="route" />{t("Short path")}</a>{/if}
        {#if x.makes}<a href="#/recipes?item={id}&role=output"><Icon name="make" />{t("How to make")}<i>{x.makes}</i></a>{/if}
        {#if x.needs}<a href="#/recipes?item={id}&role=input"><Icon name="need" />{t("Where it is needed")}<i>{x.needs}</i></a>{/if}
      </nav>
    </aside>
  {/if}
</div>

<style>
  .desc { margin: 4px 0 8px; white-space: pre-line; color: var(--p-muted); font-size: 0.92rem; line-height: 1.5; }
</style>










