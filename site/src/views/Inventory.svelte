<script>
  // What you carry, and the card of the item picked in the list: the right half is that card and nothing else.
  // Kept in this browser (lib/inventory.svelte.js).
  import Action from "../components/Action.svelte";
  import Chips from "../components/Chips.svelte";
  import Icon from "../components/Icon.svelte";
  import ItemIcon from "../components/ItemIcon.svelte";
  import List from "../components/List.svelte";
  import PlaceTag from "../components/PlaceTag.svelte";
  import Select from "../components/Select.svelte";
  import StorageCard from "../components/StorageCard.svelte";
  import Units from "../components/Units.svelte";
  import { fmtInt } from "../lib/core.js";
  import { D, ENGLISH, ITEM_NAMES, name, placement } from "../lib/data.js";
  import { gamesave, refresh } from "../lib/gamesave.svelte.js";
  import { collate, t, ui } from "../lib/i18n.js";
  import { inventory } from "../lib/inventory.svelte.js";
  import { setKeys } from "../lib/keys.js";
  import { arrival, go, trapBack } from "../lib/router.svelte.js";
  import { storeLines, wikiRar, wikiStore, wikiType } from "../lib/store.js";
  import { toast } from "../lib/toast.svelte.js";
  import { closeOutside, debounce } from "../lib/util.js";
  import { placeLabel, rarityRank, typeLabel } from "../lib/words.js";

  let adding = $state("");
  let count = $state(1);
  let table = $state();
  let search = $state(); // the field that adds an item by hand
  let find = $state(); // the search over the rows
  // The card is the one of the row the cursor is on: a row is an item and, from the save, the place it lies in.
  // #/inventory?item= opens the card of that item (held or not) and keeps it until a row is picked by hand.
  const { params } = arrival();
  const linked = D.items[params.get("item")] ? params.get("item") : "";
  let cardRow = $state.raw(linked ? [linked, 0, null] : null); // [item, how many, place]
  let pinned = $state(Boolean(linked));
  let only = $state(""); // "Find all": only the rows of this item are listed
  // "Find all" takes a step of the history: Back shows the whole list again.
  let releaseOnly = null;
  const showOnly = (id) => { if (!releaseOnly) releaseOnly = trapBack(() => { only = ""; releaseOnly = null; }); only = id; };
  const clearOnly = () => { if (releaseOnly) releaseOnly(); else only = ""; };
  const showRow = (row) => { cardRow = row; pinned = false; };
  // A place the save reads (lib/gamesave: suit, freighter, food, chest0-9, ship0.., vehicle0..), named and pictured
  // as the filter "Where to put it" of the Wiki does it: a chest is its line of the scheme with the game's chest picture.
  const lines = Object.fromEntries(storeLines().map((l) => [l.key, l]));
  function place(c) {
    const chest = /^chest(\d)$/.exec(c.key);
    if (chest) return { name: lines[chest[1]].name, icon: lines[chest[1]].icon };
    const own = { suit: lines.exosuit, food: lines.processor }[c.key];
    if (own) return { name: own.name, icon: own.icon };
    if (c.key === "freighter") return { name: placeLabel(c.label), icon: "STORE_freighter" };
    if (c.key.startsWith("ship")) return { name: placeLabel(c.label), icon: "STORE_ship" };
    return { name: placeLabel(c.label), icon: lines.exocraft.icon }; // exocraft
  }
  // The places in the order of the Wiki's list: the ten containers, the suit, the Nutrient Processor, then what the
  // scheme has no line for (exocraft, ships, the freighter), each kind in the order the save gives it.
  const RANK = { suit: 10, food: 11, vehicle: 13, ship: 14, freighter: 15 };
  const rank = (c) => (/^chest(\d)$/.test(c.key) ? Number(c.key.slice(5)) : RANK[c.key.replace(/\d+$/, "")] ?? 16);
  const slotChoices = $derived(gamesave.slots.map((s) => [gamesave.slotKey(s), `${s.file} · ${new Date(s.saved * 1000).toLocaleString(ui.locale, { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}`]));
  const places = $derived([...(gamesave.report?.containers ?? [])].sort((a, b) => rank(a) - rank(b)));
  // The column "Where it lies" is there when the items are read from the save. No column is cut then: tags are never
  // clipped; a table wider than its pane scrolls sideways instead.
  const withWhere = $derived(Boolean(inventory.fromSave && gamesave.report));
  // Where an item lies, among the places counted (the ones not left out of "Where it lies"), in that order.
  const whereOf = (id) => places.filter((c) => c.items[id] && !gamesave.skipped.includes(c.key));
  // The place of the scheme a place of the save is: its home key (lib/store.js). A ship and the freighter are no home of the
  // scheme (nothing is to be kept there): "ship", which is never what an item is given.
  const homeOf = (c) => (/^chest\d$/.test(c.key) ? c.key.slice(5) : { suit: "exosuit", food: "processor" }[c.key] ?? (c.key.startsWith("vehicle") ? "exocraft" : "ship"));
  /** Is the item of a row where the scheme puts it? "ok": yes; "wrong": no; "": the scheme says nothing about it (or no place). */
  function fit([id, , c]) {
    const p = placement(id);
    if (!p || !c || ENGLISH.storage.outcomes[D.items[id]?.store]?.why === "No rule yet - sort it by hand") return "";
    return p.home === homeOf(c) ? "ok" : "wrong";
  }
  const tone = (c) => (c.key.startsWith("chest") ? "store" : "keep"); // the colour of a place's tag, as "Where to put it" has it
  const placeHref = (c) => (homeOf(c) === "ship" ? "" : wikiStore(homeOf(c))); // a ship is no line of the scheme

  const byName = Object.fromEntries(Object.entries(D.items).map(([id, i]) => [i.name.toLowerCase(), id]));
  // A row is [item, how many, place]. From the save, an item lying in several places has a row for each, never two
  // places in one row: the count and the price are that place's. By hand there is no place (null).
  const carried = $derived(Object.entries(inventory.items).sort((a, b) => collate(name(a[0]), name(b[0])))
    .flatMap(([id, n]) => {
      const at = withWhere ? whereOf(id) : [];
      return at.length ? at.map((c) => [id, c.items[id], c]) : [[id, n, null]];
    }));
  // The search: every word is in the name, the type or the place of the row.
  let q = $state("");
  const typed = debounce((value) => { q = value; });
  const keyOfRow = ([id, , c]) => `${name(id)} ${typeLabel(D.items[id]?.type)} ${c ? place(c).name : ""}`.toLowerCase();
  const terms = $derived(q.toLowerCase().split(/\s+/).filter(Boolean));
  const shown = $derived(terms.length ? carried.filter((r) => { const k = keyOfRow(r); return terms.every((w) => k.includes(w)); }) : carried);
  const rows = $derived(only ? shown.filter(([id]) => id === only) : shown);
  const start = $derived(Math.max(0, rows.findIndex(([id]) => id === linked)));
  // The row of the card now: the same item in the same place if it is still listed, else the item's first row, else
  // (a link to an item not held) the item alone.
  const current = $derived.by(() => {
    if (!cardRow) return null;
    const [id, , c] = cardRow;
    return carried.find((r) => r[0] === id && r[2]?.key === c?.key) ?? carried.find((r) => r[0] === id) ?? (pinned ? cardRow : null);
  });
  const others = $derived(current ? carried.filter((r) => r[0] === current[0]).length : 0);
  const at = $derived.by(() => {
    const c = current?.[2];
    if (!c) return null;
    return { n: current[1], fit: fit(current), place: { name: place(c).name, icon: place(c).icon, tone: tone(c), href: placeHref(c) } };
  });

  function add(e) {
    e.preventDefault();
    const id = byName[adding.trim().toLowerCase()];
    if (!id) { toast(t("There is no such item: pick one from the hint")); return; }
    const n = inventory.add(id, Math.max(1, Number(count) || 1));
    adding = "";
    count = 1;
    toast(`${name(id)}: ${n}`);
  }

  function setCount(id, value) {
    const next = { ...inventory.items };
    const n = Math.floor(Number(value));
    if (n > 0) next[id] = n; else delete next[id];
    inventory.save(next);
  }

  function drop(id) {
    const next = { ...inventory.items };
    delete next[id];
    inventory.save(next);
  }

  function clear() {
    if (Object.keys(inventory.items).length && confirm(t("Clear all items?"))) inventory.save({});
  }

  setKeys({
    get list() { return table; },
    get search() { return find; },
    enter: () => { const row = table?.current(); if (row) go(`#/wiki?item=${encodeURIComponent(row[0])}`); },
  });
</script>

{#snippet priceCell([id, n])}<span class="gold"><Units />{fmtInt((D.items[id]?.value ?? 0) * n)}</span>{/snippet}
{#snippet typeCell([id])}<Chips {id} show="type" typeHref={wikiType(id)} />{/snippet}
{#snippet rarCell([id])}<Chips {id} show="rarity" rarHref={wikiRar(id)} />{/snippet}
{#snippet itemCell([id])}<a class="nm" href="#/wiki?item={encodeURIComponent(id)}" title={t("Description in the Wiki")}><ItemIcon {id} size={24} /><span>{name(id)}</span></a>{/snippet}
{#snippet countCell([id, n])}
  {#if inventory.fromSave}<span class="have"><Icon name="bag" size={13} />{fmtInt(n)}</span>{:else}
  <input type="number" class="count have" min="0" value={n} aria-label={t("count")} onchange={(e) => setCount(id, e.target.value)}>
  {/if}
{/snippet}
{#snippet whereCell([, , c])}{#if c}<PlaceTag name={place(c).name} icon={place(c).icon} tone={tone(c)} size={40} />{/if}{/snippet}
{#snippet fitCell(row)}{#if fit(row) === "ok"}<b class="fit ok" title={t("It lies in its place")}>✔</b>{:else if fit(row) === "wrong"}<b class="fit wrong" title={t("It lies in the wrong place: see “Where to put it”")}>➜</b>{/if}{/snippet}
{#snippet goesTo(row)}{#if placement(row[0]) && fit(row) !== "ok"}<Action placement={placement(row[0])} />{/if}{/snippet}
{#snippet dropCell([id])}{#if !inventory.fromSave}<button class="x" title={t("remove")} onclick={() => drop(id)}>×</button>{/if}{/snippet}

<div class="fbar">
  <h1><span>{t("My items")}</span></h1>
  <input class="search" type="search" placeholder={t("Search my items…")} value={q} autocomplete="off" bind:this={find} oninput={(e) => typed(e.target.value)}>
  {#if gamesave.available}
    <label class="chk" title={t("Take the items from your game save, not from a list typed in by hand")}>
      <input type="checkbox" checked={gamesave.on} onchange={(e) => { gamesave.on = e.target.checked; }}><span>{t("From the save")}</span></label>
  {/if}
  {#if inventory.fromSave}
    <Select label={t("Slot")} value={gamesave.slot} options={slotChoices} onchange={(v) => { gamesave.slot = v; }} title={t("Which save to take the items from")} />    {#if gamesave.report}
      <details class="drop" use:closeOutside>
        <summary class="btn">{t("Where it lies")}: {gamesave.report.containers.length - gamesave.skipped.filter((k) => gamesave.report.containers.some((c) => c.key === k)).length} {t("of {n}", { n: gamesave.report.containers.length })}</summary>
        <div class="drop-pop">
          <p class="pophead">
            <span class="muted small">{t("Untick a place that should not be counted.")}</span>
            <button class="btn" onclick={() => gamesave.setAll(gamesave.skipped.length > 0)}>{gamesave.skipped.length ? t("Select all") : t("Clear all")}</button>
          </p>
          <div class="places">
            {#each places as c (c.key)}
              <label class="place"><input type="checkbox" checked={!gamesave.skipped.includes(c.key)} onchange={() => gamesave.toggle(c.key)}>
                <ItemIcon id={place(c).icon} size={44} /><span class="t">{place(c).name}</span><span class="muted n">{Object.keys(c.items).length}</span></label>
            {/each}
          </div>
        </div>
      </details>
    {/if}
    <button class="btn" onclick={refresh} disabled={gamesave.loading}>{gamesave.loading ? t("Reading…") : t("Refresh")}</button>
  {:else}
    <form class="addform" onsubmit={add}>
      <input class="search" list="item-names" placeholder={t("What do you have? Start typing a name")} autocomplete="off"
        bind:this={search} bind:value={adding}>
      <input class="num" type="number" min="1" bind:value={count} aria-label={t("how many")}>
      <button class="btn primary">{t("Add")}</button>
    </form>
    <button class="btn danger" onclick={clear}>{t("Clear")}</button>
  {/if}
</div>
<datalist id="item-names">{#each ITEM_NAMES as n}<option value={n}></option>{/each}</datalist>
<div class="count">
  {#if gamesave.error}<span class="err">{gamesave.error}</span>
  {:else if inventory.fromSave}{t("Items from the save")} · {t("read at {time}", { time: gamesave.readAt ? new Date(gamesave.readAt).toLocaleTimeString(ui.locale) : "—" })} · {t("refreshes by itself")}
  {:else}{gamesave.available ? t("The save is turned off.") : t("The page cannot see your save.")} {t("Type in what is in your backpack, and how many — the list is kept only on this computer.")}{/if}
</div>
{#if only}<div class="count">{t("Showing every place of “{item}”", { item: name(only) })} · <button class="link" onclick={clearOnly}>{t("show all items")}</button></div>{/if}
<div class="grid3">
  <section>
    <List bind:this={table} {rows} {start} keyOf={([id, , c]) => `${id}|${c?.key ?? ""}`} onSelect={(row, i, user) => { if (user || !pinned) showRow(row); }} onEnter={([id]) => go(`#/wiki?item=${encodeURIComponent(id)}`)} empty={q ? t("Nothing found.") : t("Nothing here yet. Add items above.")} columns={[
      { title: t("Item"), cell: itemCell, cls: "strong", fill: !withWhere, sort: ([id]) => name(id) },
      { title: t("Type"), cell: typeCell, cls: "wide-only", sort: ([id]) => D.items[id]?.type ?? "" },
      { title: t("Rarity"), cell: rarCell, cls: "wide-only", sort: ([id]) => rarityRank(D.items[id]?.rar) },
      { title: t("How many"), cell: countCell, cls: "num", sort: ([, n]) => n },
      { title: t("Price"), cell: priceCell, cls: "num", sort: ([id, n]) => (D.items[id]?.value ?? 0) * n },
      ...(withWhere ? [{ title: t("Where it lies"), cell: whereCell, cls: "wide-only", sort: ([, , c]) => (c ? rank(c) : 99) }] : []),
      ...(withWhere ? [{ title: t("Fit"), cell: fitCell, cls: "wide-only fitcol", sort: (row) => fit(row) }] : []),
      { title: t("Where to put it"), cell: goesTo, cls: "wide-only", sort: ([id]) => placement(id)?.label ?? "" },
      { title: "", cell: dropCell },
    ]} /></section>
  <!-- No headings on either half: the table and the card both start at the top and fill the page. -->
  <section class="cardside">
    <div class="cardbody">
      {#if current}
        <StorageCard id={current[0]} {at} {others} onfindall={others > 1 && only !== current[0] ? () => showOnly(current[0]) : null} />
      {:else}
        <aside class="detail"><p class="muted">{t("Pick an item on the left: its card will be here.")}</p></aside>
      {/if}
    </div>
  </section>
</div>

<style>
  .addform { display: flex; gap: 8px; flex: 1 1 360px; max-width: 560px; min-width: 0; }
  .addform .search { flex: 1 1 auto; max-width: none; }
  .addform .num { width: 76px; }
  .grid3 {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(340px, 400px); /* the card as narrow as on the Craft page (.split) */
    gap: var(--s5);
    padding: 0 0 12px;
    align-items: stretch; /* a list pane fills its column; "start" would leave it no height */
  }
  .cardside { min-width: 0; }
  .cardbody { flex: 1 1 0; min-height: 0; overflow: auto; display: flex; flex-direction: column; }
  .cardbody :global(.detail) { flex: 0 1 auto; } /* as tall as its content, the rest of the pane is the page's */
  /* The name opens the item in the Wiki, in the table's own white, not the link yellow. */
  .nm { display: inline-flex; align-items: center; gap: 6px; max-width: 100%; vertical-align: middle; color: var(--p-text); }
  .nm:hover { color: var(--p-text); }
  .nm span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .goes { padding: 0; border: 0; background: none; font: inherit; cursor: pointer; }
  .goes:hover { filter: brightness(1.25); }
  /* The count wears the same green pill as the "have" figure of a recipe card, as wide as its own figure. */
  input.count {
    field-sizing: content; min-width: 3em; height: 22px; padding: 0 10px; border: 0; border-radius: 999px; text-align: right;
    font-size: 0.78rem; font-weight: 700; color: var(--p-green); background: color-mix(in srgb, var(--p-green) 14%, transparent);
  }
  .pophead { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .pophead .btn { height: 32px; padding: 0 12px; font-size: 0.85rem; }
  /* A list like the Wiki's "Where to put it": a row per place, its picture the height of the row, the checkbox kept. */
  .places { display: grid; gap: 2px; max-height: 60vh; overflow: auto; }
  .place { display: flex; align-items: center; gap: 10px; height: 44px; padding: 0 12px 0 10px; border-radius: 8px; overflow: hidden; cursor: pointer; }
  .place:hover { background: var(--p-raised); }
  .place .t { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .place .n { font-variant-numeric: tabular-nums; }
  /* The column "Fit": a green check where it lies right, a yellow bold arrow where it should go elsewhere. */
  .fit {
    display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 24px; box-sizing: border-box;
    border: 1px solid currentColor; border-radius: 8px; font-size: 0.95rem; line-height: 1; vertical-align: middle;
  }
  .fit.ok { color: var(--p-green); }
  .fit.wrong { color: var(--p-yellow); font-weight: 900; }
  :global(td.fitcol), :global(th.fitcol) { text-align: center; }
  .chk { display: inline-flex; align-items: center; gap: 6px; }
  .x { background: none; border: 0; color: var(--p-faint); cursor: pointer; font-size: 1.1em; padding: 0 4px; }
  .x:hover { color: var(--p-red); }
  /* Narrow: the table over the card, each with a height of its own. (With the rows of the wide grid left, the table was
     given no height at all and the page showed nothing.) */
  @media (max-width: 1000px) {
    .grid3 { grid-template-columns: minmax(0, 1fr); grid-template-rows: none; }
    .grid3 :global(.list) { flex: none; height: 60vh; }
    .cardbody { flex: none; overflow: visible; }
  }
</style>






