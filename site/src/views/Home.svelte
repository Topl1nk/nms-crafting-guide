<script module>
  // The intro (from the project's name) plays once per page load; coming back
  // to the start page picks the rotation up at the tagline, already typed.
  let typed = false;
</script>

<script>
  // What the project is, and a card per section -- the same shape as the
  // plugii and dotfiles start pages. Every count on it is read off data.json,
  // so the page cannot claim a number the data no longer has.
  import FeatureCard from "../components/FeatureCard.svelte";
  import InstallApp from "../components/InstallApp.svelte";
  import InstallPanes from "../components/InstallPanes.svelte";
  import { fmtInt } from "../lib/core.js";
  import { D, gameRelease, name, RECIPES, REPO_URL } from "../lib/data.js";
  import { install as installApp, pwa } from "../lib/pwa.svelte.js";
  import { untrack } from "svelte";

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

  // The hero, typed like a prompt, round and round: each line typed, held,
  // backspaced, then the next. A new line is one more entry here, with how
  // long it stays up (ms): the name and the tagline longer than the jokes.
  // Screen readers get the h1's aria-label (the tagline), never the typing,
  // and reduced motion gets the tagline alone, still.
  const PHRASES = [
    { text: "NMSii: No Man's Sky Items Interface", hold: 4500 },
    { text: "The numbers No Man's Sky doesn't show you", hold: 5000 },
    { text: "The Atlas counts in 16. So do we.", hold: 2500 },
    { text: "Six-teen. Not six-seven. :x", hold: 2500 }, // the 6-7 meme: drop this line when it ages
  ];
  const HERO = PHRASES[1].text;
  const animate = !matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fresh = !typed;
  typed = true;

  let h1;
  let shown = $state(animate && fresh ? "" : HERO);
  let busy = $state(animate && fresh);
  // The toggle's state. The rest of what stops the clock -- a mouse over the
  // line, keyboard focus on the toggle, a hidden tab, the hero scrolled away
  // -- is plain flags, read by sync().
  let paused = $state(false);
  let held = false, hovered = false, hidden = false, away = false;

  // The phrase on screen, how much of it, typing/holding/erasing, and the ms
  // until the next key.
  let p = fresh ? 0 : 1;
  let len = fresh ? 0 : HERO.length;
  let phase = fresh ? "type" : "hold";
  let wait = fresh ? 500 : PHRASES[1].hold;
  let timer = null;
  const key = () => 35 + Math.random() * 35; // a human's 35-70 ms a key

  function act() {
    const { text, hold } = PHRASES[p];
    if (phase === "type") {
      shown = text.slice(0, ++len);
      if (len < text.length) wait = key();
      else { phase = "hold"; wait = hold; }
    } else {
      phase = "erase";
      shown = text.slice(0, --len);
      wait = 18; // a quick backspace
      if (len === 0) { p = (p + 1) % PHRASES.length; phase = "type"; wait = 350; }
    }
  }

  // Start or stop the clock to match the flags. A pause keeps its place in
  // the line; the cursor blinks whenever it is not moving.
  function sync() {
    const run = animate && !paused && !held && !hovered && !hidden && !away;
    busy = run && phase !== "hold";
    if (run && timer === null) {
      timer = setTimeout(() => { timer = null; act(); sync(); }, wait);
    } else if (!run && timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  }

  // The pause control (WCAG 2.2.2). Resuming also lifts the focus hold, or
  // it would only move again once focus left the button.
  function toggle() {
    paused = !paused;
    if (!paused) held = false;
    sync();
  }
  const hover = (on) => (e) => { if (e.pointerType === "mouse") { hovered = on; sync(); } };
  function focus(e) { held = e.currentTarget.matches(":focus-visible"); sync(); }
  function blur() { held = false; sync(); }

  $effect(() => {
    if (!animate) return;
    const io = new IntersectionObserver(([e]) => { away = !e.isIntersecting; sync(); });
    io.observe(h1);
    const vis = () => { hidden = document.hidden; sync(); };
    document.addEventListener("visibilitychange", vis);
    untrack(vis);
    return () => {
      clearTimeout(timer);
      timer = null;
      io.disconnect();
      document.removeEventListener("visibilitychange", vis);
    };
  });

  // A scroll, not a #fragment: the hash is the router's.
  function toInstall(e) {
    e.preventDefault();
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    install.scrollIntoView({ behavior: still ? "auto" : "smooth" });
  }
</script>

<section class="home">
  <a class="badge" href="https://github.com/rdlu/nms-items-interface"><i></i>No Man's Sky Items Interface (NMSii)<em>{" · web · terminal · MCP · GPL-3.0"}</em> <span>→</span></a>
  <!-- Every line sits invisibly in the same grid cell, so the box is the
       tallest one's height and the typing never moves the page. -->
  <div class="hero-box">
    <h1 class="hero" class:busy aria-label={HERO} bind:this={h1}
        onpointerenter={hover(true)} onpointerleave={hover(false)}>
      {#each animate ? PHRASES.map((l) => l.text) : [HERO] as line}
        <span class="sizer" aria-hidden="true">{line}</span>
      {/each}
      <span class="typed" aria-hidden="true">{shown}</span>
    </h1>
    {#if animate}
      <button type="button" class="hero-pause" onclick={toggle} onfocus={focus} onblur={blur}
              aria-label={paused ? "Resume the title animation" : "Pause the title animation"}
        ><span aria-hidden="true">{paused ? "▶" : "‖"}</span> {paused ? "resume" : "pause"}</button>
    {/if}
  </div>
  <p class="lede">
    What refines into what, the cheapest way to make it from what you can pick up,
    which dish buffs what, where every item belongs in storage, and every portal
    address drawn in glyphs. All of it computed from the game's own recipe tables,
    not copied from a wiki.
  </p>
  {#if release}
    <p><a class="badge" href="{REPO_URL}/blob/main/docs/cosmos-changes.md"><i></i>Up to date with {release.name}<em>{` · ${release.build} · read from the game files`}</em> <span>→</span></a></p>
  {/if}
  <p class="lede muted">
    The same data is this site, a terminal app, an MCP server for AI assistants,
    and plain markdown. The site runs entirely in your browser, and works on a
    phone propped up next to the game.
  </p>
  <div class="hero-actions">
    <a class="primary" href="#/recipes">Open the recipes</a>
    {#if pwa.canInstall && !pwa.standalone}
      <button type="button" onclick={installApp}>Install app</button>
    {/if}
    <a href="#/home" onclick={toInstall}>Run it locally</a>
    <a href="pdf/nms-cheatsheet-dark.pdf">Cheat sheet (PDF)</a>
    <a href="https://github.com/rdlu/nms-items-interface">GitHub</a>
  </div>

  <figure class="demo">
    <div class="bar"><span>mise run tui</span><b>the terminal app</b></div>
    <img src="img/recipes.svg" width="1848" height="1075" alt="The NMSii terminal app: the recipe list searched for cobalt, with the detail pane showing the selected recipe, its ingredients and how gettable each one is." loading="lazy">
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
    <FeatureCard href="pdf/nms-cheatsheet.pdf" title="Cheat sheet" icon="sheet">The recipes worth memorising on six landscape A4 pages, for print. The dark version for screens is linked at the bottom of every page.</FeatureCard>
  </div>

  <h2 class="section">Other ways in</h2>
  <div class="features">
    {#if !pwa.standalone}
      <FeatureCard href="#/home" onclick={toInstall} title="As an app" icon="app">Install this site from the browser, or <b>Share → Add to Home Screen</b> on an iPhone, and it opens in its own window and works with no signal, data included.</FeatureCard>
    {/if}
    <FeatureCard href="#/home" onclick={toInstall} title="In a terminal" icon="terminal"><code>nms</code> has the same screens with vim keys, a command palette and themes, and saves portal addresses to a file you can share. <code>uv run nms</code> in a checkout, or <code>podman compose run --rm tui</code> with nothing else installed.</FeatureCard>
    <FeatureCard href="{REPO_URL}#for-ai-assistants-mcp" title="For AI assistants" icon="ai"><code>nms mcp</code> serves the chain planner, inventory matching, storage rules and portal arithmetic over MCP, so an assistant looks them up instead of guessing from a wiki. <code>mise run mcp:install-claude</code>, or Codex, pi, opencode, goose.</FeatureCard>
    <FeatureCard href="llms.txt" title="As markdown" icon="markdown">Every section and every item as plain markdown, for crawlers and language models: <code>llms.txt</code>, <code>llms-full.txt</code>, and a page per item. Each page's footer links its own twin.</FeatureCard>
  </div>

  <h2 class="section" id="install" bind:this={install}>Run it on your machine</h2>
  <p class="lede muted">The terminal app has the same screens with vim keys, a command palette and themes, and
    saves portal addresses to a file you can share. It works offline once installed.</p>
  <InstallPanes />
  <InstallApp />

  <h2 class="section">Good to know</h2>
  <div class="features">
    <FeatureCard href="{REPO_URL}#where-the-data-comes-from" title="Straight from the game files" icon="data">Recipes, batch times and values are read from the game's own files{#if release}, currently {release.name} ({release.build}){/if}, re-extracted after each patch. NMS-Handbook, the original source, is the fallback. A test suite checks the claims the written guides make.</FeatureCard>
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
    display: grid;
    color: var(--p-text);
  }
  /* Both lines in one grid cell: the hidden sizer sets the height, the typed
     one is drawn over it. */
  .hero > span { grid-area: 1 / 1; }
  .hero .sizer { visibility: hidden; }
  .hero > span::before { content: "> "; color: var(--p-accent); }
  /* The block cursor, steady while it types and blinking once it rests. */
  .hero > span::after {
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
  .hero.busy > span::after { animation: none; }
  /* The pause toggle hangs in the h1's bottom margin, out of the flow, so it
     takes no room and never shifts anything. 24px tall: the minimum target. */
  .hero-box { position: relative; }
  .hero-pause {
    position: absolute;
    top: 100%;
    left: 0;
    height: 24px;
    padding: 0 6px;
    font-family: var(--p-mono);
    font-size: 0.75rem;
    line-height: 1;
    color: var(--p-faint);
    background: none;
    border: 0;
    border-radius: 0;
    cursor: pointer;
  }
  .hero-pause span { display: inline-block; width: 1ch; color: var(--p-accent); }
  .hero-pause:hover { color: var(--p-accent); }
  @media (prefers-reduced-motion: reduce) { .hero > span::after { animation: none; } }

  .lede { font-size: 1.12rem; line-height: 1.7; max-width: 80ch; color: var(--p-muted); margin: 0 0 12px; }
  .lede.muted { font-size: 1rem; color: var(--p-faint); }

  .hero-actions { display: flex; flex-wrap: wrap; gap: 12px; margin: 28px 0 8px; }
  .hero-actions a, .hero-actions button {
    font-family: var(--p-mono);
    padding: 10px 22px;
    text-decoration: none;
    color: var(--p-text);
    box-shadow: inset 0 0 0 1px var(--p-outline);
  }
  .hero-actions button { background: none; border: 0; border-radius: 0; cursor: pointer; font-size: inherit; }
  .hero-actions a:hover, .hero-actions button:hover { color: var(--p-accent); box-shadow: inset 0 0 0 1px var(--p-accent); }
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
  /* width/height in the markup (the SVG's viewBox) and the ratio here keep
     its box the right size before the lazy image arrives. */
  .demo img { display: block; width: 100%; height: auto; aspect-ratio: 1848 / 1075; }

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
