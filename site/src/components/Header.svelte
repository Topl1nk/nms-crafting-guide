<script>
  // plugii's navbar: logo and name left, links, search, theme and GitHub
  // right, all in mono; the links fold into a menu on a phone.
  import { NAV } from "../lib/data.js";
  import { t } from "../lib/i18n.js";
  import ThemeMenu from "./ThemeMenu.svelte";
  import { search } from "../lib/search.svelte.js";

  let { section, onsearch } = $props();
  let menuOpen = $state(false);

  // The search is one loupe, and a character. Pressed, a square of its field appears under it; the loupe darts left in it and hits the
  // left wall hard, pushing the wall out; the wall gives, overshoots, and the loupe recoils off it and settles; only then, in a hurry,
  // does the word come. Closed, it all goes back the way it came.
  const CELL = 36;
  let field, loupe, input, nav;
  let width = $state(240);
  let seen = false;
  let anims = [];

  const room = () => Math.max(CELL + 80, Math.min(240, innerWidth - 150));

  $effect(() => {
    const open = search.open;
    if (!seen) { seen = true; if (!open) return; }
    for (const a of anims) a.cancel();
    anims = [];
    const w = room();
    width = w;
    const reach = w - CELL;
    const still = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (open) input?.focus();
    if (still || !field) return;
    const go = (el, frames, o) => anims.push(el.animate(frames, { fill: "both", ...o }));
    if (open) {
      go(field, [{ opacity: 0, width: CELL + "px" }, { opacity: 1, width: CELL + "px" }], { duration: 120, easing: "ease-out" });
      // the wall is pushed by the loupe: it moves with it, a hair behind, gives way past its place and springs back
      go(field, [{ width: CELL + "px" }, { width: reach + CELL + 15 + "px", offset: 0.62, easing: "cubic-bezier(.2,.6,.4,1)" },
        { width: reach + CELL - 3 + "px", offset: 0.82 }, { width: w + "px" }],
        { duration: 400, delay: 108, easing: "cubic-bezier(.55,0,.35,1)", composite: "replace" });
      // the loupe: a dart, the knock on the wall, the recoil
      // the tabs are pushed along by the wall, as far as it goes, and give back with it
      go(nav, [{ transform: "translateX(0)" }, { transform: `translateX(${-reach - 15}px)`, offset: 0.62, easing: "cubic-bezier(.2,.6,.4,1)" },
        { transform: `translateX(${-reach + 3}px)`, offset: 0.82 }, { transform: `translateX(${-reach}px)` }],
        { duration: 400, delay: 108, easing: "cubic-bezier(.55,0,.35,1)" });
      go(nav, [{ filter: "blur(0)" }, { filter: "blur(1.4px)", offset: 0.35 }, { filter: "blur(0)" }], { duration: 400, delay: 108 });
      go(loupe, [{ filter: "blur(0)" }, { filter: "blur(2.4px)", offset: 0.35 }, { filter: "blur(0)" }], { duration: 400, delay: 110 });
      go(loupe, [{ transform: "translateX(0)" }, { transform: `translateX(${-reach - 7}px)`, offset: 0.62, easing: "cubic-bezier(.2,.6,.4,1)" },
        { transform: `translateX(${-reach + 4}px)`, offset: 0.82 }, { transform: `translateX(${-reach}px)` }],
        { duration: 400, delay: 110, easing: "cubic-bezier(.55,0,.35,1)" });
      go(input, [{ opacity: 0, transform: "translateX(-8px)" }, { opacity: 1, transform: "translateX(0)" }], { duration: 150, delay: 470, easing: "ease-out" });
    } else {
      go(input, [{ opacity: 1 }, { opacity: 0 }], { duration: 80 });
      go(nav, [{ transform: `translateX(${-reach}px)` }, { transform: "translateX(0)" }], { duration: 300, delay: 40, easing: "cubic-bezier(.4,0,.2,1)" });
      go(loupe, [{ filter: "blur(0)" }, { filter: "blur(1.8px)", offset: 0.4 }, { filter: "blur(0)" }], { duration: 300, delay: 40 });
      go(loupe, [{ transform: `translateX(${-reach}px)` }, { transform: "translateX(0)" }], { duration: 300, delay: 40, easing: "cubic-bezier(.4,0,.2,1)" });
      go(field, [{ width: w + "px", opacity: 1 }, { width: CELL + "px", opacity: 1, offset: 0.85 }, { width: CELL + "px", opacity: 0 }], { duration: 340, delay: 40, easing: "cubic-bezier(.4,0,.2,1)" });
    }
  });

  // The chain planner is a page under Recipes.
  const isOn = (key) => key === section || (section === "chain" && key === "recipes");
</script>

<svelte:window onhashchange={() => { menuOpen = false; }} />

<header class="top" class:menu-open={menuOpen} class:searching={search.open} style="--w: {width}px">
  <div class="top-in">
    <a class="brand" href="#/"><img src="favicon.svg" alt="" width="26" height="26">NMSii</a>
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
    <nav id="nav" class="nav" bind:this={nav} aria-label={t("Sections")} onclick={() => { menuOpen = false; }}>
      {#each NAV as [key, label], i (key)}
        <a href="#/{key}" class:on={isOn(key)} aria-current={isOn(key) ? "page" : undefined}
          title={i < 7 ? t("key {n}", { n: i + 1 }) : ""}>{t(label)}</a>
      {/each}
    </nav>
    <div class="sf">
      <div class="field" bind:this={field}></div>
      <button class="loupe" bind:this={loupe} type="button" aria-label={t("Search items and sections")} aria-expanded={search.open}
        onclick={() => { if (search.open) search.open = false; else onsearch(); }}>
        <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/></svg>
      </button>
      <input class="q" bind:this={input} bind:value={search.q} type="search" placeholder={t("Search…")} autocomplete="off" spellcheck="false"
        aria-label={t("Search items and sections")} tabindex={search.open ? 0 : -1} onkeydown={(e) => search.keydown?.(e)}>
    </div>
    <ThemeMenu />
    <button class="icon-btn menu-btn" type="button" aria-label={t("Sections")} aria-expanded={menuOpen} aria-controls="nav"
      onclick={() => { menuOpen = !menuOpen; }}>
      <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
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
  .brand:hover { color: var(--p-accent-ink); }

  .nav { display: flex; align-items: center; gap: 2px; }
  .nav a {
    color: var(--p-muted);
    text-decoration: none;
    font-size: 0.88rem;
    padding: 6px 9px;
  }
  .nav a:hover, .nav a.on { color: var(--p-accent-ink); }

  .sf { position: relative; flex: none; width: 36px; height: 36px; margin: 0 6px 0 10px; }
  .field {
    position: absolute; right: 0; top: 0; width: 36px; height: 36px; opacity: 0; border-radius: 10px;
    background: var(--p-panel); border: 1px solid var(--p-outline); box-sizing: border-box; pointer-events: none;
  }
  .loupe {
    position: absolute; left: 0; top: 0; z-index: 1; display: grid; place-items: center; width: 36px; height: 36px; padding: 0;
    background: none; border: 0; color: var(--p-muted); cursor: pointer;
  }
  .loupe:hover { color: var(--p-accent-ink); }
  .top .sf .q {
    position: absolute; top: 4px; bottom: 4px; right: 8px; width: calc(var(--w) - 52px); height: auto; min-height: 0; opacity: 0; pointer-events: none;
    background: none; border: 0; border-radius: 0; outline: none; box-shadow: none; padding: 0; font: inherit; font-size: 0.88rem; color: var(--p-text);
  }
  .top .sf .q::-webkit-search-cancel-button { display: none; }
  .sf.on .field { width: var(--w); opacity: 1; }
  .searching .nav { transform: translateX(calc(36px - var(--w))); }
  .sf.on .loupe { transform: translateX(calc(36px - var(--w))); }
  .top .sf.on .q { opacity: 1; pointer-events: auto; }
  /* The icons in ThemeMenu.svelte share this look, hence :global. */
  .top :global(svg) { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
  .loupe svg { width: 16px; height: 16px; }

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
  .top :global(.icon-btn:hover) { color: var(--p-accent-ink); }
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
    .sf { margin: 0; }
    .loupe svg { width: 20px; height: 20px; }
  }
</style>



