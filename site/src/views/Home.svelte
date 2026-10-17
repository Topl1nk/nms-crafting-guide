<script>
  // What the project is, and a card per section -- the same shape as the
  // plugii and dotfiles start pages. Every count on it is read off data.json,
  // so the page cannot claim a number the data no longer has.
  import FeatureCard from "../components/FeatureCard.svelte";
  import InstallPanes from "../components/InstallPanes.svelte";
  import { fmtInt } from "../lib/core.js";
  import { D, gameRelease, name, RECIPES } from "../lib/data.js";

  const count = (domain) => D.recipes.filter((r) => r.domain === domain).length;
  const dishes = D.cooking.reduce((n, g) => n + g.dishes.length, 0);
  const containers = D.storage.homes.filter((h) => h.container).length;
  const bestNanite = D.nanites.map((n) => RECIPES[n.recipe]).sort((a, b) => b.rate - a.rate)[0];
  const loops = RECIPES.filter((r) => r.loop > 1).length;
  const release = gameRelease();
  // The chain card shows off a real plan: the most valuable thing Tier 0 reaches.
  const showcase = Object.keys(D.tiers[0].via.refine)
    .sort((a, b) => (D.items[b]?.value ?? 0) - (D.items[a]?.value ?? 0))[0];

  let install;

  // A scroll, not a #fragment: the hash is the router's.
  function toInstall(e) {
    e.preventDefault();
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    install.scrollIntoView({ behavior: still ? "auto" : "smooth" });
  }
</script>

<section class="home">
  <a class="badge" href="https://github.com/rdlu/nms-items-interface"><i></i>No Man's Sky Items Interface (NMSii)<em>{" · Python TUI · GPL-3.0"}</em> <span>→</span></a>
  <h1 class="hero">The numbers No Man's Sky doesn't show you</h1>
  <p class="lede">
    What refines into what, the cheapest way to make it from what you can pick up,
    which dish buffs what, where every item belongs in storage, and every portal
    address drawn in glyphs. All of it computed from the game's own recipe tables,
    not copied from a wiki.
  </p>
  <p class="lede muted">
    This is the web version of a terminal app. It runs entirely in your browser,
    and works on a phone propped up next to the game.
  </p>
  {#if release}
    <p class="lede muted">Up to date with <b>{release.name}</b>{#if release.build}{" "}<span class="build">build {release.build}</span>{/if}.</p>
  {/if}
  <div class="hero-actions">
    <a class="primary" href="#/recipes">Open the recipes</a>
    <a href="#/home" onclick={toInstall}>Run it locally</a>
    <a href="pdf/nms-cheatsheet-dark.pdf">Cheat sheet (PDF)</a>
    <a href="https://github.com/rdlu/nms-items-interface">GitHub</a>
  </div>

  <figure class="demo">
    <div class="bar"><span>mise run tui</span><b>the terminal app</b></div>
    <img src="img/recipes.svg" alt="The NMSii terminal app: the recipe list searched for cobalt, with the detail pane showing the selected recipe, its ingredients and how gettable each one is." loading="lazy">
  </figure>

  <h2 class="section">What's inside</h2>
  <div class="features">
    <FeatureCard key="1" href="#/recipes" title="Recipes" icon="recipes"><b>{fmtInt(count("refine"))}</b> refining and <b>{fmtInt(count("cook"))}</b> cooking recipes, searchable by output, ingredient or operation. Sort by multiplier, speed, profit or how gettable the inputs are; {loops} recipes are loops that grow a stack from a seed.</FeatureCard>
    <FeatureCard key="c" href="#/chain/{encodeURIComponent(showcase)}" title="Chain planner" icon="chain">Works backwards from any item to what you can pick up on any planet, off asteroids, or from an atmosphere harvester, minimising refiner time. Try it on {name(showcase)}, the most valuable thing the bare planet surface refines into.</FeatureCard>
    <FeatureCard key="2" href="#/nanites" title="Nanite ladder" icon="nanites">All <b>{fmtInt(D.nanites.length)}</b> routes to nanites, ranked by nanites per hour per refiner, with where each input drops. The best is {bestNanite?.inputs ?? ""} at <b>{fmtInt(bestNanite?.rate ?? 0)}</b>/h.</FeatureCard>
    <FeatureCard key="3" href="#/cooking" title="Cooking buffs" icon="cooking"><b>{fmtInt(dishes)}</b> dishes across <b>{fmtInt(D.cooking.length)}</b> buffs: what each one does when you eat it, how strongly, and what it sells for. Cook the batch, eat one, sell the rest.</FeatureCard>
    <FeatureCard key="4" href="#/multitools" title="Multi-tools" icon="multitools">The <b>{fmtInt(D.multitools.types.length)}</b> types side by side, the weapons measured, where the free S-class ones come from, and the adjacency and supercharged-slot rules.</FeatureCard>
    <FeatureCard key="5" href="#/portals" title="Portal addresses" icon="portals">Convert between portal glyphs and galactic coordinates as you type, dial an address symbol by symbol, and browse <b>{fmtInt(D.portals.locations.length)}</b> saved places worth going.</FeatureCard>
    <FeatureCard key="6" href="#/storage" title="Where does it go?" icon="storage">Every one of <b>{fmtInt(Object.keys(D.items).length)}</b> items gets a home: one of the {containers} storage containers, Cold Storage, or sell, junk, use it now. Type "sell" to list everything to sell.</FeatureCard>
    <FeatureCard key="7" href="#/inventory" title="Inventory" icon="inventory">Type what you are carrying, and see what you can make right now and what you are one ingredient short of. Kept in this browser.</FeatureCard>
    <FeatureCard href="pdf/nms-cheatsheet.pdf" title="Cheat sheet" icon="sheet">The recipes worth memorising on five landscape A4 pages, for print. The dark version for screens is linked at the bottom of every page.</FeatureCard>
  </div>

  <h2 class="section" id="install" bind:this={install}>Run it on your machine</h2>
  <p class="lede muted">The terminal app has the same screens with vim keys, a command palette and themes, and
    saves portal addresses to a file you can share. It works offline once installed.</p>
  <InstallPanes />

  <h2 class="section">Good to know</h2>
  <div class="features">
    {#if release}
      <FeatureCard href="https://github.com/rdlu/nms-items-interface#readme" title="Straight from the game files" icon="data">Recipes, batch times and values are read from the game's own files, <b>{release.name}</b>, re-extracted after each patch, and a test suite checks the claims the written guides make.</FeatureCard>
    {:else}
      <FeatureCard href="https://github.com/ApexFatality93/NMS-Handbook" title="Straight from the game files" icon="data">Recipes, batch times and values come from the game's recipe table via NMS-Handbook, rebuilt after each patch, and a test suite checks the claims the written guides make.</FeatureCard>
    {/if}
    <FeatureCard key="?" href="#/help" title="Keys and columns" icon="keys"><kbd>j</kbd> <kbd>k</kbd> move, <kbd>/</kbd> searches, <kbd>Enter</kbd> pivots, <kbd>1</kbd>-<kbd>7</kbd> jump between sections. What Mult, Gettable and the rest mean.</FeatureCard>
    <FeatureCard href="#/portals" title="Share an address" icon="portals">Found a ship, a tool or a base worth the trip? Convert it on the portals page and share it as a GitHub issue; a bot checks the glyphs, and accepted ones join the list.</FeatureCard>
  </div>
</section>

<style>
  /* Hextra's home: 2rem under the navbar, 3rem from 768px, on the page's own
     edges -- the hero is narrowed by its line length, not by a second box. */
  .home { padding: 2rem 0 3rem; }
  @media (min-width: 768px) { .home { padding-top: 3rem; } }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: var(--p-mono);
    font-size: 0.8rem;
    color: var(--p-muted);
    text-decoration: none;
    border: 1px solid var(--p-outline);
    background: var(--p-panel);
    padding: 3px 10px;
    white-space: nowrap;
    max-width: 100%;
  }
  .badge i { flex: none; width: 8px; height: 8px; background: var(--p-accent); }
  .badge:hover { border-color: var(--p-accent); color: var(--p-accent); }
  .badge em { font-style: normal; }
  @media (max-width: 640px) {
    .badge { font-size: 0.72rem; gap: 6px; }
    .badge em { display: none; }
  }

  .hero {
    font-family: var(--p-mono);
    font-size: clamp(1.9rem, 5vw, 3.2rem);
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: -0.02em;
    margin: 1.5rem 0 1.5rem;
    max-width: 24ch;
    display: block;
    color: var(--p-text);
  }
  .hero::before { content: "> "; color: var(--p-accent); }
  /* The block cursor. */
  .hero::after {
    content: "";
    display: inline-block;
    width: 0.55em;
    height: 0.9em;
    margin-inline-start: 0.12em;
    vertical-align: -0.08em;
    background: var(--p-accent);
    animation: blink 1.1s steps(1, end) infinite;
  }
  @keyframes blink { 50% { opacity: 0; } }
  @media (prefers-reduced-motion: reduce) { .hero::after { animation: none; } }

  .lede { font-size: 1.12rem; line-height: 1.7; max-width: 80ch; color: var(--p-muted); margin: 0 0 12px; }
  .lede.muted { font-size: 1rem; color: var(--p-faint); }
  .lede b { color: var(--p-accent); font-weight: 400; }
  .build { font-family: var(--p-mono); font-size: 0.88em; }

  .hero-actions { display: flex; flex-wrap: wrap; gap: 12px; margin: 28px 0 8px; }
  .hero-actions a {
    font-family: var(--p-mono);
    padding: 10px 22px;
    text-decoration: none;
    color: var(--p-text);
    box-shadow: inset 0 0 0 1px var(--p-outline);
  }
  .hero-actions a:hover { color: var(--p-accent); box-shadow: inset 0 0 0 1px var(--p-accent); }
  .hero-actions a.primary { background: var(--p-accent); color: var(--p-on-accent); font-weight: 700; box-shadow: none; }
  .hero-actions a.primary::before { content: "[ "; }
  .hero-actions a.primary::after { content: " ]"; }
  .hero-actions a.primary:hover { color: var(--p-on-accent); filter: brightness(1.08); }

  /* The TUI screenshot in a terminal pane. Rich draws its own dark window, so
     the pane stays dark in the light theme too. */
  .demo { margin: 40px 0 8px; border: 1px solid var(--p-outline); background: #000; }
  .demo .bar {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 4px 12px;
    font-family: var(--p-mono);
    font-size: 0.8rem;
    color: #c6c6c6;
    background: #131313;
    border-bottom: 1px solid #3a3a3a;
  }
  .demo .bar b { color: #ffc857; font-weight: 400; }
  .demo img { display: block; width: 100%; height: auto; }

  /* Section titles: `┌─ What's inside ─────`, bigger than a pane's. */
  h2.section {
    scroll-margin-top: calc(var(--nav-h) + 1rem);
    display: flex;
    align-items: baseline;
    gap: 0.6ch;
    font-family: var(--p-mono);
    font-size: 1.5rem;
    color: var(--p-text);
    margin: 56px 0 20px;
  }
  h2.section::before {
    content: "";
    flex: none;
    align-self: center;
    width: 0.7em;
    height: 0.55em;
    margin-top: 0.45em;
    border-top: 2px solid var(--p-outline);
    border-left: 2px solid var(--p-outline);
  }
  h2.section::after {
    content: "";
    flex: 1 1 2rem;
    align-self: center;
    border-top: 1px solid var(--p-outline);
  }

  .features { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
  @media (max-width: 1000px) { .features { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 640px) { .features { grid-template-columns: minmax(0, 1fr); } }
</style>
