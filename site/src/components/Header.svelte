<script>
  // plugii's navbar: logo and name left, links, search, theme and GitHub
  // right, all in mono; the links fold into a menu on a phone.
  import { NAV, REPO_URL } from "../lib/data.js";
  import ThemeMenu from "./ThemeMenu.svelte";

  let { section, onsearch } = $props();
  let menuOpen = $state(false);

  // The chain planner is a page under Recipes.
  const isOn = (key) => key === section || (section === "chain" && key === "recipes");
</script>

<svelte:window onhashchange={() => { menuOpen = false; }} />

<header class="top" class:menu-open={menuOpen}>
  <div class="top-in">
    <a class="brand" href="#/"><img src="favicon.svg" alt="" width="26" height="26">NMSii</a>
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
    <nav id="nav" class="nav" aria-label="Sections" onclick={() => { menuOpen = false; }}>
      {#each NAV as [key, label], i (key)}
        <a href="#/{key}" class:on={isOn(key)} aria-current={isOn(key) ? "page" : undefined}
          title={i < 7 ? `key ${i + 1}` : "key ?"}>{label}</a>
      {/each}
    </nav>
    <button class="search-btn" type="button" aria-label="Search items, sections and addresses" onclick={onsearch}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/></svg>
      <span>Search…</span><kbd>CTRL K</kbd>
    </button>
    <ThemeMenu />
    <a class="icon-btn" href={REPO_URL} aria-label="GitHub">
      <svg class="fill" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>
    </a>
    <button class="icon-btn menu-btn" type="button" aria-label="Sections" aria-expanded={menuOpen} aria-controls="nav"
      onclick={() => { menuOpen = !menuOpen; }}>
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
    </button>
  </div>
</header>

<style>
  .top {
    position: sticky;
    top: 0;
    z-index: 5;
    background: var(--p-bg);
    box-shadow: inset 0 -1px 0 var(--p-outline);
    font-family: var(--p-mono);
  }
  .top-in {
    display: flex;
    align-items: center;
    gap: 4px;
    height: var(--nav-h);
    padding: 0 var(--gutter);
    max-width: var(--wrap);
    margin: 0 auto;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-right: auto;
    font-weight: 700;
    font-size: 0.95rem;
    color: var(--p-text);
    text-decoration: none;
    white-space: nowrap;
  }
  .brand img { display: block; }
  .brand:hover { color: var(--p-accent); }

  .nav { display: flex; align-items: center; gap: 2px; }
  .nav a {
    color: var(--p-muted);
    text-decoration: none;
    font-size: 0.88rem;
    padding: 6px 9px;
  }
  .nav a:hover, .nav a.on { color: var(--p-accent); }

  .search-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 6px 0 10px;
    padding: 5px 8px;
    min-width: 190px;
    background: var(--p-panel);
    border: 1px solid transparent;
    color: var(--p-faint);
    font-family: var(--p-mono);
    font-size: 0.85rem;
    cursor: pointer;
  }
  .search-btn:hover { border-color: var(--p-outline); color: var(--p-muted); }
  .search-btn span { flex: 1; text-align: left; }
  .search-btn kbd { font-size: 0.65rem; border-bottom-width: 1px; padding: 2px 5px; color: var(--p-faint); background: transparent; }
  /* The icons in ThemeMenu.svelte share this look, hence :global. */
  .top :global(svg) { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
  .top svg.fill { fill: currentColor; stroke: none; }
  .search-btn svg { width: 16px; height: 16px; }

  .top :global(.icon-btn) {
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    background: none;
    border: 0;
    color: var(--p-muted);
    cursor: pointer;
  }
  .top :global(.icon-btn:hover) { color: var(--p-accent); }
  .top .menu-btn { display: none; }

  @media (max-width: 1180px) {
    .top .menu-btn { display: grid; }
    .nav {
      display: none;
      position: absolute;
      top: var(--nav-h);
      left: 0;
      right: 0;
      flex-direction: column;
      align-items: stretch;
      gap: 0;
      padding: 6px 0;
      background: var(--p-bg);
      box-shadow: inset 0 -1px 0 var(--p-outline);
    }
    .menu-open .nav { display: flex; }
    .nav a { padding: 9px var(--gutter); font-size: 0.95rem; }
    .nav a.on { background: var(--p-accent); color: var(--p-on-accent); font-weight: 700; }
  }
  @media (max-width: 640px) {
    .top-in { gap: 0; }
    .search-btn { min-width: 0; margin: 0; padding: 0; width: 36px; height: 36px; justify-content: center; background: none; color: var(--p-muted); }
    .search-btn span, .search-btn kbd { display: none; }
    .search-btn svg { width: 20px; height: 20px; }
  }
</style>
