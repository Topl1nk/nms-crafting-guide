<script>
  // The frame every view sits in, and the hand-off from the URL to a view.
  import Footer from "./components/Footer.svelte";
  import Header from "./components/Header.svelte";
  import Palette from "./components/Palette.svelte";
  import Toast from "./components/Toast.svelte";
  import UpdateToast from "./components/UpdateToast.svelte";
  import { gameRelease, load, NAV } from "./lib/data.js";
  import { onKey } from "./lib/keys.js";
  import { markdownFor } from "./lib/markdown.js";
  import { route } from "./lib/router.svelte.js";
  import Chain from "./views/Chain.svelte";
  import Cooking from "./views/Cooking.svelte";
  import Help from "./views/Help.svelte";
  import Home from "./views/Home.svelte";
  import Inventory from "./views/Inventory.svelte";
  import Multitools from "./views/Multitools.svelte";
  import Nanites from "./views/Nanites.svelte";
  import Portals from "./views/Portals.svelte";
  import Recipes from "./views/Recipes.svelte";
  import Storage from "./views/Storage.svelte";

  const VIEWS = {
    home: Home, recipes: Recipes, chain: Chain, nanites: Nanites, cooking: Cooking,
    multitools: Multitools, portals: Portals, storage: Storage, inventory: Inventory,
    help: Help,
  };

  let ready = $state(false);
  let failed = $state("");
  let palette;

  load().then(() => { ready = true; }, (exc) => { failed = exc.message; });

  const View = $derived(VIEWS[route.section] ?? Home);
  // Item pages need the item list, so they wait for data.json.
  const markdown = $derived(ready ? markdownFor(route.section, route.arg, route.params) : "llms.txt");

  // The alternate link lives in index.html's head, outside what Svelte draws.
  $effect(() => { document.getElementById("md-alt")?.setAttribute("href", markdown); });

  // Each visit starts at the top, with the title of the section it is in.
  $effect(() => {
    route.visit;
    window.scrollTo(0, 0);
    const known = route.section !== "home" && VIEWS[route.section];
    document.title = known
      ? `${NAV.find(([k]) => k === route.section)?.[1] ?? "Chain"} · NMSii`
      : "NMSii - No Man's Sky recipes, nanites, portals";
  });
</script>

<svelte:window onkeydown={(e) => onKey(e, () => ready && palette.open())} />

<Header section={route.section} onsearch={() => ready && palette.open()} />
<Palette bind:this={palette} />
<main>
  {#if failed}
    <p class="pad err">Could not load data.json ({failed}). Run <code>mise run web:data</code>.</p>
  {:else if !ready}
    <p class="pad muted">Loading the recipe book…</p>
  {:else}
    {#key route.visit}
      <View />
    {/key}
  {/if}
</main>
<Footer {markdown} release={ready ? gameRelease() : null} />
<Toast />
<UpdateToast />
