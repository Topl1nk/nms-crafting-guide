<script>
  // The start page: one big question ("what do you want to make?") and a
  // picture for every section.
  import ItemIcon from "../components/ItemIcon.svelte";
  import RecipeNode from "../components/RecipeNode.svelte";
  import { craftableNow, fmtInt } from "../lib/core.js";
  import { D, PRODUCED, RECIPES } from "../lib/data.js";
  import { gamesave } from "../lib/gamesave.svelte.js";
  import { collate, t, tn } from "../lib/i18n.js";
  import { inventory } from "../lib/inventory.svelte.js";
  import { ICONS } from "../lib/icons.js";
  import { go } from "../lib/router.svelte.js";

  // Every section, the same as the menu; the line under each is what it is for.
  const TILES = [
    ["recipes", t("Craft"), t("Refining, cooking and nanites: what turns into what, what a dish gives"), "recipes", () => tn(D.recipes.length, "{n} recipe|{n} recipes", { n: fmtInt(D.recipes.length) })],
    ["tree", t("Tree"), t("Every way to make an item, each as a pyramid of tiles"), "chain", () => tn(Object.keys(PRODUCED).length, "{n} item|{n} items", { n: fmtInt(Object.keys(PRODUCED).length) })],
    ["wiki", t("Wiki"), t("Every item in the game: type, rarity, price and where it is needed"), "data", () => tn(Object.keys(D.items).length, "{n} item|{n} items", { n: fmtInt(Object.keys(D.items).length) })],
    ["multitools", t("Multi-tools"), t("Types, weapons, where to get them and how to upgrade"), "multitools", () => tn(D.multitools.types.length, "{n} type|{n} types")],
    ["portals", t("Portals"), t("Place addresses: code, glyphs, galactic coordinates"), "portals", () => tn(D.portals.locations.length, "{n} address|{n} addresses")],
    ["inventory", t("My items"), t("What you have and where to put it: a card for every item"), "inventory", () => (inventory.fromSave ? t("from the save") : tn(Object.keys(inventory.items).length, "{n} kind|{n} kinds"))],
    ["help", t("Help"), t("Where things are, the keys and what the words in the tables mean"), "keys", () => t("guide")],
  ];

  // What the bag makes right now, richest first: the answer to "what can I do with this?".
  const now = $derived.by(() => {
    if (!Object.keys(inventory.items).length) return [];
    return craftableNow(D.recipes, inventory.items, ["refine", "cook"])
      .map(([i]) => RECIPES[i]).sort((a, b) => b.profit - a.profit)
      .filter((r, i, all) => all.findIndex((o) => o.out[0] === r.out[0]) === i).slice(0, 10);
  });
  const total = $derived(Object.keys(inventory.items).length ? craftableNow(D.recipes, inventory.items, ["refine", "cook"]).length : 0);
  // Items people look for first: shown by the game's own name, in the chosen language.
  const POPULAR = ["TECHFRAG", "STELLAR2", "ASTEROID1", "ALLOY3", "ASTEROID2", "FUEL1"].filter((id) => PRODUCED[id]);

  let q = $state("");
  let sel = $state(0);

  const hits = $derived.by(() => {
    const text = q.trim().toLowerCase();
    if (!text) return [];
    const starts = [];
    const contains = [];
    for (const [id, item] of Object.entries(D.items)) {
      const n = item.name.toLowerCase();
      if (n.startsWith(text)) starts.push(id);
      else if (n.includes(text)) contains.push(id);
    }
    const byName = (a, b) => collate(D.items[a].name, D.items[b].name);
    return [...starts.sort(byName), ...contains.sort(byName)].slice(0, 8);
  });

  const choose = (id) => { if (id) go(`#/recipes?path=${encodeURIComponent(id)}`); };

  function key(e) {
    if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(hits.length - 1, sel + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); }
    else if (e.key === "Enter") { e.preventDefault(); choose(hits[sel]); }
  }
</script>

<section class="hero">
  <h1>{t("What do you want to make?")}</h1>
  <p class="lead">{t("Type an item's name and I will show what to make it from and what to gather for it.")}</p>
  <div class="ask">
    <input type="search" placeholder={t("For example: {item}", { item: D.items.TECHFRAG?.name ?? "" })} autocomplete="off" spellcheck="false"
      bind:value={q} oninput={() => { sel = 0; }} onkeydown={key}>
    {#if hits.length}
      <ul class="hits">
        {#each hits as id, i (id)}
          <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
          <li class:sel={i === sel} onclick={() => choose(id)} onmouseenter={() => { sel = i; }}>
            <ItemIcon {id} size={36} /><span class="nm">{D.items[id].name}</span><span class="muted sub">{D.items[id].sub}</span>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
  <p class="popular">
    <span class="muted">{t("Often searched:")}</span>
    {#each POPULAR as id (id)}
      <a class="chip-item" href="#/recipes?path={id}"><ItemIcon {id} size={26} />{D.items[id].name}</a>
    {/each}
  </p>
</section>

{#if now.length}
  <section class="now">
    <h3>{t("You can make right now")} <span class="muted">· {fmtInt(total)}{#if gamesave.active}, {t("from your save")}{/if}</span> <a href="#/inventory">{t("all")}</a></h3>
    <div class="row">{#each now as r (r.index)}<RecipeNode id={r.out[0]} qty={r.out[1]} ri={r.index} />{/each}</div>
  </section>
{/if}
<section class="tiles">
  {#each TILES as [key, title, text, icon, count] (key)}
    <a class="tile" href="#/{key}">
      <span class="top"><svg viewBox="0 0 24 24" aria-hidden="true">{@html ICONS[icon]}</svg><i>{count()}</i></span>
      <b>{title}</b>
      <span>{text}</span>
    </a>
  {/each}
</section>

<style>
  .hero { padding: 36px 0 12px; text-align: center; }
  .hero h1 { font-size: 2.4rem; margin: 0 0 6px; color: var(--p-text); }
  .lead { font-size: 1.15rem; color: var(--p-muted); margin: 0 auto 18px; max-width: 40rem; }
  .ask { position: relative; max-width: 40rem; margin: 0 auto; text-align: left; }
  .ask input {
    width: 100%; font-size: 1.3rem; padding: 16px 20px;
    border-radius: 18px; border: 2px solid var(--p-outline); background: var(--p-panel);
  }
  .ask input:focus { border-color: var(--p-edge-accent); outline: none; box-shadow: 0 0 0 4px color-mix(in srgb, var(--p-accent) 25%, transparent); }
  .hits {
    list-style: none; margin: 6px 0 0; padding: 6px; position: absolute; left: 0; right: 0; z-index: 4;
    background: var(--p-panel); border: 1px solid var(--p-outline); border-radius: 16px;
    box-shadow: 0 14px 40px rgb(0 0 0 / 0.35);
  }
  .hits li { display: flex; align-items: center; gap: 12px; padding: 6px 12px; border-radius: 10px; cursor: pointer; font-size: 1.05rem; }
  .hits li.sel { background: var(--p-sel); }
  .hits .nm { font-weight: 700; }
  .hits .sub { margin-left: auto; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .popular { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; align-items: center; margin: 18px 0 0; }
  .chip-item {
    display: inline-flex; align-items: center; gap: 6px; padding: 4px 14px 4px 6px;
    background: var(--p-panel); border: 1px solid var(--p-outline); border-radius: 999px;
    color: var(--p-text); text-decoration: none;
  }
  .chip-item:hover { border-color: var(--p-edge-accent); color: var(--p-accent-ink); }

  .now { width: 100%; max-width: 1280px; margin: 18px auto 0; padding: 14px 18px 16px; background: var(--p-panel); border: 1px solid var(--p-outline); border-radius: 20px; }
  .now h3 { margin: 0 0 12px; }
  .now h3 a { margin-left: 8px; color: var(--p-accent-ink); text-transform: none; letter-spacing: 0; }
  .now .row { display: flex; flex-wrap: wrap; gap: 12px; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; padding: 18px 0 24px; }
  .tile .top { display: flex; align-items: center; justify-content: space-between; }
  .tile .top i { font-style: normal; font-size: 0.78rem; color: var(--p-faint); padding: 3px 10px; border-radius: 999px; background: var(--p-raised); }
  .tile {
    display: flex; flex-direction: column; gap: 6px; padding: 20px;
    background: var(--p-panel); border: 1px solid var(--p-outline); border-radius: 20px;
    color: var(--p-text); text-decoration: none; transition: transform 0.45s var(--spring), border-color 0.12s;
  }
  .tile:hover { transform: translateY(-3px); border-color: var(--p-edge-accent); }
  .tile svg { width: 40px; height: 40px; fill: none; stroke: var(--p-accent-ink); stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
  .tile b { font-size: 1.25rem; }
  .tile span { color: var(--p-muted); font-size: 0.95rem; line-height: 1.4; }
</style>



