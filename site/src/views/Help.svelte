<script>
  // Keys, what the columns mean, and how to run or add to it.
  import InstallApp from "../components/InstallApp.svelte";
  import InstallPanes from "../components/InstallPanes.svelte";
  import { gameRelease, REPO_URL } from "../lib/data.js";

  const release = gameRelease();

  let local;

  // A scroll, not a #fragment: the hash is the router's.
  function toLocal(e) {
    e.preventDefault();
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    local.scrollIntoView({ behavior: still ? "auto" : "smooth" });
  }
</script>

<div class="prose">
  <section class="card span"><h3>What this is</h3>
    <p>NMSii reads the numbers No Man's Sky doesn't show you out of the game's own files{#if release}, currently
    {release.name} ({release.build}){/if}. This site is one way in. The same data is a
    <a href="#/help" onclick={toLocal}>terminal app</a>, an <a href="{REPO_URL}#for-ai-assistants-mcp">MCP server</a>
    for AI assistants, and <a href="llms.txt">markdown</a>, one page per item. Below: the keys, what the columns
    mean, and how to run it or add to it.</p></section>
  <section class="card"><h3>Keys</h3>
    <dl class="rows keys">
      <dt><kbd>j</kbd> <kbd>k</kbd> / <kbd>↓</kbd> <kbd>↑</kbd></dt><dd>move through the list</dd>
      <dt><kbd>/</kbd></dt><dd>search - <kbd>Esc</kbd> or <kbd>Enter</kbd> leaves the box</dd>
      <dt><kbd>Enter</kbd></dt><dd>recipes: everything touching the item · portals: load the address</dd>
      <dt><kbd>Esc</kbd></dt><dd>clear the search or the item filter</dd>
      <dt><kbd>p</kbd> <kbd>r</kbd></dt><dd>recipes that produce / consume the highlighted item</dd>
      <dt><kbd>c</kbd></dt><dd>chain plan for the highlighted item</dd>
      <dt><kbd>1</kbd>-<kbd>7</kbd></dt><dd>jump to a section</dd>
    </dl></section>
  <section class="card"><h3>Reading the columns</h3>
    <dl class="rows">
      <dt>Mult</dt><dd>Units out per unit in. <code>x6 loop</code> means the recipe feeds itself:
        1 Chlorine + 2 Oxygen → 6 Chlorine multiplies the seed six times.</dd>
      <dt>Time</dt><dd>One batch, from the game files. The in-game display is often wrong.</dd>
      <dt>Machine</dt><dd>Portable/Personal (1 input), Medium (2), Large (3).</dd>
      <dt>Rate / Profit</dt><dd>Units per hour with one machine kept fed, and the base-value difference across one batch.
        Profit is in units and says nothing about nanites; those get their own page.</dd>
      <dt>Gettable</dt><dd><code>T0/T1/T2 +n</code>: refinable from surface materials / asteroids / an atmosphere harvester,
        n refining steps away. <code>needs seed</code>: refinable, but wanting a material none of those tiers contain.
        <code>loot (…)</code>: no recipe makes it.</dd>
    </dl></section>
  <section class="card"><h3>The chain planner</h3>
    <p>It works backwards to a source set - by default the five things you can pick up on any planet - and minimises
    <b>refiner-seconds per unit</b>, so the plan is the one that ties up a machine for the least time.</p></section>
  <section class="card span" bind:this={local}><h3>Running it locally</h3>
    <p>The terminal app reads the same data as this site, and adds vim keys, a command palette, themes, and saving
    portal addresses to <code>data/locations.json</code>.</p>
    <InstallPanes />
    <p class="muted small">On Windows, use WSL or the podman route. The app is a Textual program: any modern terminal draws it.</p>
    <InstallApp /></section>
  <section class="card"><h3>Sharing a portal address</h3>
    <p>Convert it on the <a href="#/portals">portals page</a>, fill in the form there, and press <b>Share on GitHub</b>.
    It opens an issue on the <i>Share a portal address</i> form with the fields filled in.</p>
    <p>A bot reads it within a minute, converts the address the same way this page does, and replies with the glyphs
    and coordinates it got, or a list of what to fix. Edit the issue and it checks again. When a maintainer accepts it,
    the bot opens the pull request that adds it, crediting you.</p>
    <p>Comfortable with git? Edit <a href="{REPO_URL}/blob/main/data/locations.json">data/locations.json</a> in a pull
    request instead; the same checks run on it. Locally, <code>mise run contrib:validate</code>.</p></section>
  <section class="card"><h3>Where this comes from</h3>
    <p>Every number is read from the game's own files{#if release}: {release.name} ({release.build}), extracted {release.extracted}{/if}.
    Earlier builds read the same tables via
    <a href="https://github.com/ApexFatality93/NMS-Handbook">NMS-Handbook</a>, still the fallback source. The site, the terminal app,
    the MCP server and the markdown all read the same data; the source, the cheat-sheet PDFs and the full README are on
    <a href="https://github.com/rdlu/nms-items-interface">GitHub</a>. Portal glyphs are traced from
    <a href="https://nmsportals.github.io/">nmsportals</a>. No Man's Sky and its data belong to Hello Games.</p></section>
</div>
