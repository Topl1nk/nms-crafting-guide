<script>
  // What every page is for and how to use it, how to move around, and what the
  // words in the tables mean.
  import { t } from "../lib/i18n.js";
  import { ICONS } from "../lib/icons.js";

  const PAGES = [
    ["recipes", t("Craft"), "recipes",
      t("Every recipe in one table. “Kind” picks refining, cooking, nanites or a type of item; “Effect” finds dishes with the buff you need; “My items” keeps only what your items are enough for. Click a row for its card on the right: the scheme, time, gain and other ways. A column heading sorts the table.")],
    ["tree", t("Tree"), "chain",
      t("Pick an item to see every way to make it, each as a pyramid: the item on top, below it what it is made from, at the bottom what is only gathered. Hover a tile for its recipe, click it to open it in Craft. The canvas moves with the mouse, Ctrl + wheel zooms. “Batches” multiplies the numbers.")],
    ["chain", t("Short path"), "chain",
      t("A button in the card of a recipe (Craft) and of an item (Wiki). In Craft the pyramid of the shortest path takes the table's place: one way from raws to the item that keeps the refiner busy the least, with a count of what to gather. “Available” is which raws you can reach: from the planet only, with asteroids, or with the atmosphere harvester. The red “Close” button (or Esc) brings the table back.")],
    ["wiki", t("Wiki"), "data",
      t("Every item in the game with its picture: type, rarity, price, how many ways there are to make it and where it is needed. On the right a card with the description and buttons to Craft, Tree and “Where to put it”.")],
    ["multitools", t("Multi-tools"), "multitools",
      t("The kinds of multi-tool, the weapons, where to get each kind and the order to upgrade in. The rows of the tables open into a card under them.")],
    ["portals", t("Portals"), "portals",
      t("Paste a portal code, a galactic address or a link and get all the rest, with the glyphs to dial. The list of saved addresses can be searched and added to: they are kept only on this computer.")],
    ["inventory", t("My items"), "inventory",
      t("Items from the game save (the program reads it without changing anything and refreshes by itself) or a list you type in by hand. On the right the card of the item under the cursor: where to put it (which container, or sell, or throw away) and why. An item's name opens the Wiki, the “Type” and “Rarity” tags open the Wiki with that filter. “Where it lies” leaves out places (containers, ships, exocraft) that should not be counted.")],
  ];
  const KEYS = [
    [["↓", "↑"], t("move along the list (or J and K)")],
    [["/"], t("go to the search; Esc or Enter leaves it")],
    [["Enter"], t("in Craft, everything about the item; in Portals, open the address")],
    [["Esc"], t("clear the search or the filter")],
    [["Ctrl", "K"], t("quick search over items and sections")],
    [["1", "–", "7"], t("go to a section by its number")],
  ];
  const WORDS = [
    [t("Yield"), t("How many times more you get than you put in. “1→6” is a recipe where one of the ingredients is also in the result: 1 chlorine + 2 oxygen → 6 chlorine. The chlorine multiplies, but it is no perpetual motion machine: every run also spends oxygen, which is taken from elsewhere. Real loops are found in the background and added to the table as rows “… per turn” (the “Loops” box keeps only those): several recipes that feed one another and leave more after a turn than they took.")],
    [t("Time"), t("One cycle, by the game's data. The time the game itself shows is often wrong.")],
    [t("Where"), t("A portable or personal refiner takes 1 ingredient, a medium one 2, a large one 3.")],
    [t("Per hour, gain"), t("How many pieces an hour one machine that is never idle gives, and by how much the price grows per cycle. For nanites the gain says nothing: their ways are collected under Craft → Kind → nanites.")],
    [t("Effect"), t("What a dish gives when it is eaten, and how strongly.")],
    [t("Raws"), t("Easy — from what is on any planet. Fair and Takes work — asteroids, the atmosphere harvester or many steps are needed. Hard — a rare item that can only be found.")],
    [t("Letters on an icon"), t("The chemical symbol of the substance, as in the game. It can be turned off in the appearance menu.")],
  ];
</script>

<div class="fbar"><h1><span>{t("Help")}</span></h1></div>
<div class="help">
  <div class="pages">
    {#each PAGES as [key, title, icon, text] (key)}
      <a class="card page" href="#/{key}">
        <span class="head"><svg viewBox="0 0 24 24" aria-hidden="true">{@html ICONS[icon]}</svg><b>{title}</b></span>
        <span class="text">{text}</span>
      </a>
    {/each}
  </div>
  <div class="side">
    <section class="card"><h3>{t("Appearance and language")}</h3>
      <p>{t("The cog at the top right: light or dark theme, accent colour, language (names and descriptions come from the game's files, and the page's own words follow it), glowing icons, chemical symbols on icons and text size.")}</p></section>
    <section class="card"><h3>{t("Keys")}</h3>
      <div class="keys">
        {#each KEYS as [keys, text]}
          <span class="k">{#each keys as k}<kbd>{k}</kbd>{/each}</span><span>{text}</span>
        {/each}
      </div></section>
    <section class="card"><h3>{t("What the words mean")}</h3>
      <dl class="words">
        {#each WORDS as [term, text]}<dt>{term}</dt><dd>{text}</dd>{/each}
      </dl></section>
    <section class="card"><h3>{t("Where all this comes from")}</h3>
      <p>{t("Recipes, names, glyphs and pictures were extracted from the files of your installed game (Cosmos 7.06, build 180836). The captions for portals, storage and multi-tools were written by hand by the project's author. No Man's Sky and its data belong to Hello Games. The project is open source: github.com/Topl1nk/nms-crafting-guide.")}</p></section>
  </div>
</div>

<style>
  .help { display: grid; grid-template-columns: minmax(0, 7fr) minmax(0, 5fr); gap: 16px; align-items: start; padding-bottom: 8px; }
  .pages { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; min-width: 0; }
  .side { display: grid; gap: 16px; min-width: 0; }
  .card p { margin: 0; color: var(--p-muted); line-height: 1.55; }
  .page { display: flex; flex-direction: column; gap: 8px; padding: 16px 18px; color: inherit; text-decoration: none; transition: border-color 0.12s; }
  .page:hover { border-color: var(--p-edge-accent); }
  .head { display: flex; align-items: center; gap: 10px; }
  .head svg { width: 28px; height: 28px; fill: none; stroke: var(--p-accent-ink); stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; flex: none; }
  .head b { font-size: 1.05rem; color: var(--p-text); }
  .text { color: var(--p-muted); line-height: 1.5; font-size: 0.92rem; }
  .keys { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 10px 16px; align-items: center; color: var(--p-muted); }
  .k { display: inline-flex; gap: 4px; justify-content: flex-end; }
  .words { display: grid; grid-template-columns: 8em minmax(0, 1fr); gap: 12px 16px; margin: 0; }
  .words dt { color: var(--p-accent-ink); font-weight: 700; padding: 0; }
  .words dd { margin: 0; color: var(--p-muted); line-height: 1.5; }
  @media (max-width: 1100px) { .help { grid-template-columns: minmax(0, 1fr); } }
  @media (max-width: 640px) { .pages { grid-template-columns: minmax(0, 1fr); } }
</style>



