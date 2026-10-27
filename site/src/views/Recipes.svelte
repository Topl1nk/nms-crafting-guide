<script module>
  import { N_ } from "../lib/i18n.js";

  // The search, the filters and the sort outlive a visit: going to an item's recipes and back keeps them
  // (but a link brings its own, see `linked`).
  const st = { q: "", filters: null, sort: "mult" };

  const SORTS = [ // English keys for t()
    ["mult", N_("by yield")], ["time", N_("by time")], ["rate", N_("by yield per hour")],
    ["profit", N_("by gain")], ["potency", N_("by strength of effect")], ["ease", N_("by how easy the raws are")], ["name", N_("alphabetically")],
    ["color", N_("by colour")], ["type", N_("by kind")], ["rar", N_("by rarity")],
  ];
  const MAX_ROWS = 400;
</script>

<script>
  // Craft: every recipe, refining and cooking alike, searchable, or the ones
  // touching one item (?item=&role=). A dish's buff is a filter and a column
  // here (?effect=), so cooking is not a place of its own.
  import ChainBar from "../components/ChainBar.svelte";
  import ChainCanvas from "../components/ChainCanvas.svelte";
  import Check from "../components/Check.svelte";
  import Ingredients from "../components/Ingredients.svelte";
  import ItemIcon from "../components/ItemIcon.svelte";
  import List from "../components/List.svelte";
  import RecipeCard from "../components/RecipeCard.svelte";
  import Reset from "../components/Reset.svelte";
  import Select from "../components/Select.svelte";
  import { craftableNow } from "../lib/core.js";
  import { cycles, findLoopsInBackground } from "../lib/cycles.svelte.js";
  import { buffOf, CONSUMED, D, easeOfRecipe, name, PRODUCED, RECIPES } from "../lib/data.js";
  import { applyFacets, facets } from "../lib/facets.js";
  import { collate, t, tn } from "../lib/i18n.js";
  import { inventory } from "../lib/inventory.svelte.js";
  import { setKeys } from "../lib/keys.js";
  import { byColor, byRarity, byType } from "../lib/sortkeys.js";
  import { DEFAULTS, recipeDefs } from "../lib/recipefacets.js";
  import { arrival, go, replace, trapBack } from "../lib/router.svelte.js";
  import { debounce } from "../lib/util.js";
  import { machineShort } from "../lib/words.js";

  const { params } = arrival();
  const item = params.get("item");
  const role = params.get("role") || "any";
  let want = $state(params.has("r") ? Number(params.get("r")) : null); // a recipe to start on (a tree tile's, or the one that was picked before a path was opened)

  // The short path of an item (?path=): the canvas of the Tree in the place of the table, until it is closed.
  const known = (id) => Boolean(id && (D.items[id] || PRODUCED[id]));
  let path = $state(known(params.get("path")) ? params.get("path") : "");
  let tier = $state(Math.min(Number(params.get("tier") || 0), D.tiers.length - 1));
  let qty = $state(Math.max(1, Number(params.get("qty") || 1)));
  let cook = $state(params.get("cook") === "1");
  let rootRecipe = $state.raw(null); // the recipe at the top of the path drawn: the card beside it is that one, not the table's
  let zoom = $state(1); // the scale of the canvas, kept by its panel in the bar
  let canvasRef = $state();
  let cyc = $state.raw(null); // a loop drawn whole in the same place (its row of the table); no address, a loop has none
  const open = $derived(Boolean(path || cyc));
  // The address as it is, with the row the table stands on: what Back comes back to shows that row, not the first.
  const withRow = (index) => {
    const [at, qs = ""] = location.hash.slice(1).split("?");
    const q = new URLSearchParams(qs);
    q.set("r", index);
    return `#${at}?${q}`;
  };
  // A path or a loop drawn whole takes a step of the history: Back closes it and shows the table with its buttons.
  let pushPath = false; // the next write of the path address is a new step, not a rewrite
  let pathPushed = false;
  let releaseCycle = null;
  const openPath = (id) => {
    want = cur?.index ?? want;
    if (cur && cur.index >= 0) replace(withRow(cur.index));
    pushPath = true;
    path = id;
  };
  const openCycle = (row) => {
    want = row.index;
    qty = 1;
    cyc = row;
    releaseCycle = trapBack(() => { cyc = null; releaseCycle = null; });
  };
  const closePath = () => {
    if (cyc) { (releaseCycle ?? (() => { cyc = null; }))(); return; }
    if (path && pathPushed) { pathPushed = false; history.back(); return; } // the view is rebuilt on the table it came from
    path = "";
  };  // The path is a link: its settings are kept in the address, and closing it takes them out.
  let pathShown = false;
  $effect(() => {
    const q = new URLSearchParams();
    if (path) { q.set("path", path); if (tier) q.set("tier", tier); if (qty !== 1) q.set("qty", qty); if (cook) q.set("cook", "1"); }
    if (item) q.set("item", item);
    if (role !== "any" && item) q.set("role", role);
    if (!path && !pathShown) return;
    pathShown = Boolean(path);
    const hash = `#/recipes${q.size ? `?${q}` : ""}`;
    if (path && pushPath) { pushPath = false; pathPushed = true; history.pushState(null, "", hash); } else replace(hash);
  });

  // A link says everything about the view it opens: its own filters on top of the defaults, never on top of what
  // was set last time (which could leave the table it points to empty). Without a link, the last ones come back.
  const linked = [...params.keys()].some((k) => k !== "r"); // the row alone (what Back comes back to) is no link
  function initial() {
    if (!linked) return { ...DEFAULTS, ...st.filters };
    const o = { ...DEFAULTS };
    if (item) o.domain = "all"; // an item's page lists every recipe it is in
    if (params.has("domain")) o.domain = params.get("domain");
    if (params.has("effect")) o.effect = D.cooking.find((g) => g.id === params.get("effect") || g.effect === params.get("effect"))?.id ?? "any";
    return o;
  }
  let f = $state(initial());
  let q = $state(linked ? "" : st.q);
  let sort = $state(params.has("effect") ? "potency" : st.sort);
  // What was set stays set for the next visit.
  $effect(() => { const now = { ...f }; if (!linked) { st.filters = now; st.sort = sort; } });

  findLoopsInBackground();

  const carried = $derived(Object.keys(inventory.items).length);
  const makeable = $derived(new Set(craftableNow(D.recipes, inventory.items, ["refine", "cook"]).map(([i]) => i)));

  const defs = $derived(recipeDefs({ makeable, held: inventory.items }));
  function scope() {
    if (!item) return cycles.rows.length ? [...RECIPES, ...cycles.rows] : RECIPES;
    if (role === "output") return PRODUCED[item] || [];
    if (role === "input") return CONSUMED[item] || [];
    return [...new Set([...(PRODUCED[item] || []), ...(CONSUMED[item] || [])])];
  }
  const base = $derived.by(() => {
    const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
    return terms.length ? scope().filter((r) => terms.every((w) => r.key.includes(w))) : scope();
  });
  const fx = $derived(facets(base, defs, f));
  // "Reset": every filter, whoever set it (a link too: the item the page was opened on, its role), and the search.
  const filtered = $derived(Object.keys(DEFAULTS).some((k) => f[k] !== DEFAULTS[k]) || Boolean(item) || q !== "");
  const resetFilters = () => {
    f = { ...DEFAULTS };
    q = st.q = "";
    st.filters = { ...DEFAULTS };
    if (search) search.value = "";
    if (item) go("#/recipes");
  };

  // How much a recipe gives for what it takes, for the order: a real loop is the best there is; "1→6" (the result is also an
  // ingredient) gives nothing the others do not.
  const gain = (r) => (r.cycle ? 1e9 : r.loop > 1 ? 1 : r.ratio);
  const power = (r) => D.items[r.out[0]]?.potency ?? 0;
  const BY = {
    mult: (a, b) => gain(b) - gain(a) || a.time - b.time,
    time: (a, b) => (a.time || 1e9) - (b.time || 1e9) || b.ratio - a.ratio,
    rate: (a, b) => b.rate - a.rate || a.time - b.time,
    profit: (a, b) => b.profit - a.profit || a.time - b.time,
    potency: (a, b) => power(b) - power(a) || b.profit - a.profit,
    ease: (a, b) => easeOfRecipe(b).score - easeOfRecipe(a).score || a.time - b.time,
    name: (a, b) => collate(a.outName, b.outName) || collate(a.inputs, b.inputs),
    color: (a, b) => byColor(a.out[0], b.out[0]) || BY.name(a, b),
    type: (a, b) => byType(a.out[0], b.out[0]) || BY.name(a, b),
    rar: (a, b) => byRarity(a.out[0], b.out[0]) || BY.name(a, b),
  };
  const left = $derived(applyFacets(base, defs, fx.effective));
  // A sort that has nothing to sort by (strength of effect, with no dish among the rows) is not offered.
  const sortList = SORTS.map(([k, label]) => [k, t(label)]);
  const sorts = $derived(sortList.filter(([k]) => k !== "potency" || left.some((r) => power(r) > 0)));
  const order = $derived(sorts.some(([k]) => k === sort) ? sort : "mult");
  // An item's page (?item=) opens on the recipes that make it, then the ones that use it; its first row is selected,
  // at the top of the table.
  const makes = (r) => (item && role === "any" && r.out[0] === item ? 0 : 1);
  const matches = $derived([...left].sort(BY[order]).sort((a, b) => makes(a) - makes(b)));
  const rows = $derived(matches.slice(0, MAX_ROWS));
  const start = $derived(Math.max(0, rows.findIndex((r) => r.index === want)));
  const buffText = $derived(D.cooking.find((g) => g.id === fx.effective.effect));
  const verb = { output: t("how to make"), input: t("where needed"), any: t("everything about") }[role];

  function pickDomain(v) {
    f.domain = v;
    if (v === "nanites") sort = "rate"; // nanites an hour, best first
  }
  function pickEffect(v) {
    f.effect = v;
    if (v === "any") return;
    // A buff belongs to dishes: show them, strongest first.
    f.domain = "cook";
    sort = "potency";
  }

  let cur = $state.raw(null);
  let list = $state();
  let search = $state();
  const typed = debounce((value) => { q = value; st.q = value; });
  const enter = (r) => { if (r) go(`#/recipes?item=${encodeURIComponent(r.out[0])}`); };

  setKeys({
    get list() { return list; },
    get search() { return search; },
    enter: () => enter(list?.current()),
    escape: () => {
      if (open) { closePath(); return; }
      if (item) { go("#/recipes"); return; }
      search.value = "";
      q = st.q = "";
    },
  });

  const buffCell = (r) => { const b = buffOf(r.out[0]); return b ? `${b.effect} · ${b.potency.toFixed(2)}` : ""; };
</script>
{#snippet make(r)}<span class="mk"><ItemIcon id={r.out[0]} size={32} /><span class="t">{r.outLabel}</span></span>{/snippet}
{#snippet from(r)}<div class="cellclip" title={r.inputs}><Ingredients recipe={r} /></div>{/snippet}
{#snippet mult(r)}<span class:cyc={r.cycle}>{r.mult}</span>{/snippet}

{#if open}
  <ChainBar target={cyc ? cyc.out[0] : path} cycle={Boolean(cyc)} bind:tier bind:qty bind:cook bind:zoom onfit={() => canvasRef?.fit()} onclose={closePath} />
{:else}
<div class="fbar one">
  <h1><span>{t("Craft")}</span></h1>
  <Reset active={filtered} onclick={resetFilters} />
  <input class="search" type="search" placeholder={t("Search…")} value={q}
    autocomplete="off" bind:this={search} oninput={(e) => typed(e.target.value)}>
  <Select hidden={!(fx.show.domain)} label={t("Kind")} value={fx.effective.domain} options={fx.options.domain} all={fx.all.domain} neutral={fx.neutral.domain} onchange={pickDomain} title={t("What to show: refining, cooking, ways to get nanites, or items of one type")} />
  <Select hidden={!(fx.show.effect)} label={t("Effect")} value={fx.effective.effect} options={fx.options.effect} all={fx.all.effect} neutral={fx.neutral.effect} onchange={pickEffect} title={t("What a dish gives when it is eaten")} />
  <Select hidden={!(fx.show.refiner)} label={t("Refiner")} value={fx.effective.refiner} options={fx.options.refiner} all={fx.all.refiner} neutral={fx.neutral.refiner} onchange={(v) => { f.refiner = v; }} title={t("The biggest refiner you have: recipes that need a bigger one are hidden")} />
  <Select hidden={!(fx.show.source)} label={t("Source")} value={fx.effective.source} options={fx.options.source} all={fx.all.source} neutral={fx.neutral.source} onchange={(v) => { f.source = v; }} title={t("How easy the rarest ingredient of the recipe is to get")} />
  <Select hidden={!(fx.show.owned)} label={t("My items")} value={fx.effective.owned} options={fx.options.owned} all={fx.all.owned} neutral={fx.neutral.owned} onchange={(v) => { f.owned = v; }} title={t("Whether you have enough items for the recipe")} />
  <Select label={t("Order")} value={order} options={sorts} all={sortList} onchange={(v) => { sort = v; }} />
  <Check hidden={!(fx.show.loops)} label={t("Loops")} value={fx.effective.loops} onchange={(v) => { f.loops = v; }} title={t("Only real loops: recipes that feed one another and give more than they took. They are searched for in the background, rows appear as they are found")} />
</div>
{/if}
{#if open}
  <!-- Empty while the path is open: it only keeps the row's height, so the canvas and the card stay where the table and the card were. -->
  <div class="count" aria-hidden="true">&nbsp;</div>
{:else}
<div class="count">
  {#if !cycles.done && !item}<span class="muted" title={t("Loops are searched for in the background")}>{t("looking for loops… found {n}", { n: cycles.rows.length })}{" · "}</span>{/if}{#if matches.length > MAX_ROWS}{t("showing {shown} of {n}", { shown: MAX_ROWS, n: matches.length })}{:else}{t("Recipes:")} {matches.length}{#if matches.length < base.length}{" "}{t("of {n}", { n: base.length })}{/if}{/if}
  {#if item}· {verb} <b>{name(item)}</b> <a href="#/recipes">{t("show all")}</a>{/if}
  {#if buffText?.use}· <b>{buffText.effect}</b>: {buffText.use}{/if}
  {#if inventory.fromSave}· {t("items from the save are counted")}{:else if carried}· <a href="#/inventory">{t("my items: {n}", { n: carried })}</a>{/if}
</div>
{/if}
<div class="split split-craft">
  {#if open}
    <ChainCanvas bind:this={canvasRef} bind:zoom target={cyc ? cyc.out[0] : path} cycle={cyc?.cycle ?? null} {tier} {qty} {cook} bind:rootRecipe />
  {:else}
  <List bind:this={list} {rows} {start} atTop columns={[
    { title: t("Makes"), cell: make, cls: "strong", sort: (r) => r.outName },
    { title: t("From"), cell: from, fill: true, sort: (r) => r.inputs },
    { title: t("Effect"), text: buffCell, cls: "wide-only", sort: (r) => power(r) },
    { title: t("Yield"), cell: mult, cls: "num", sort: gain },
    { title: t("Time"), text: (r) => r.timeLabel, cls: "num", sort: (r) => r.time || 1e9 },
    { title: t("Where"), text: (r) => machineShort(r.machine), cls: "wide-only", sort: (r) => r.machine },
  ]} onSelect={(r) => { cur = r; }} onEnter={enter} empty={t("No such recipes.")} />
  {/if}
  {#if open}
    {#if (cyc ? cyc : rootRecipe ?? cur)}<RecipeCard r={cyc ?? rootRecipe ?? cur} onpath={openPath} oncycle={openCycle} />{/if}
  {:else if !matches.length}
    <aside class="detail"><p class="muted">{t("No such recipes.")}</p></aside>
  {:else if cur}
    <RecipeCard r={cur} onpath={openPath} oncycle={openCycle} />
  {/if}
</div>

<style>
  .split-craft { grid-template-columns: minmax(0, 1fr) clamp(400px, 28%, 480px); }
  @media (max-width: 1000px) { .split-craft { grid-template-columns: minmax(0, 1fr); } }
  .cyc { color: var(--p-green); font-weight: 700; }
</style>

















