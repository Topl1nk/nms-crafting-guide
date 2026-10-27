<script>
  import { tick } from "svelte";
  // The frame every view sits in, and the hand-off from the URL to a view.
  import Footer from "./components/Footer.svelte";
  import Header from "./components/Header.svelte";
  import Palette from "./components/Palette.svelte";
  import Toast from "./components/Toast.svelte";
  import UpdateToast from "./components/UpdateToast.svelte";
  import { gameRelease, load, NAV } from "./lib/data.js";
  import { startSave } from "./lib/gamesave.svelte.js";
  import { t } from "./lib/i18n.js";
  import { language, startLanguage } from "./lib/language.svelte.js";
  import { onKey } from "./lib/keys.js";
  import { markdownFor } from "./lib/markdown.js";
  import { enterView, hold, snapshot } from "./lib/motion.js";
  import { route } from "./lib/router.svelte.js";
  import Help from "./views/Help.svelte";
  import Home from "./views/Home.svelte";
  import Inventory from "./views/Inventory.svelte";
  import Multitools from "./views/Multitools.svelte";
  import Portals from "./views/Portals.svelte";
  import Recipes from "./views/Recipes.svelte";
  import Tree from "./views/Tree.svelte";
  import Wiki from "./views/Wiki.svelte";

  const VIEWS = {
    home: Home, recipes: Recipes,
    multitools: Multitools, portals: Portals, inventory: Inventory,
    help: Help, tree: Tree, wiki: Wiki,
  };

  let ready = $state(false);
  let failed = $state("");
  let palette;

  // The language is chosen before the first view is drawn, so it never flashes in the other one.
  load().then(startLanguage).then(() => { ready = true; startSave(); }, (exc) => { failed = exc.message; });

  const View = $derived(VIEWS[route.section] ?? Home);
  // Item pages need the item list, so they wait for data.json.
  const markdown = $derived(ready ? markdownFor(route.section, route.arg, route.params) : "llms.txt");

  // The alternate link lives in index.html's head, outside what Svelte draws.
  $effect(() => { document.getElementById("md-alt")?.setAttribute("href", markdown); });

  // The page changes by sliding: the old panes leave behind their edges, the new ones come in from theirs. The new page
  // comes from the right when its tab is further along the bar than the last one, from the left when it is before it.
  const place = (section) => { const i = NAV.findIndex(([k]) => k === section); return i >= 0 ? i : section === "tree" ? NAV.findIndex(([k]) => k === "recipes") + 0.5 : -1; };
  let was = place(route.section);
  let snap = null;
  $effect.pre(() => { // before the page is replaced: the old one is copied where it stands
    route.visit; language.code;
    const main = document.querySelector("main");
    snap = ready ? snapshot(main) : null;
    if (ready) hold(main);
  });
  $effect(() => {
    route.visit; language.code;
    if (!ready) return;
    const now = place(route.section);
    const dir = now >= was ? "right" : "left";
    was = now;
    const old = snap;
    snap = null;
    tick().then(() => enterView(document.querySelector("main"), dir, old));
  });
  // Each visit starts at the top, with the title of the section it is in.
  $effect(() => {
    route.visit; language.code;
    window.scrollTo(0, 0);
    const known = route.section !== "home" && VIEWS[route.section];
    document.title = known
      ? `${t(NAV.find(([k]) => k === route.section)?.[1] ?? "How to make")} · NMSii`
      : t("NMSii — a No Man's Sky reference");
  });
</script>

<svelte:window onkeydown={(e) => onKey(e, () => ready && palette.open())} />

<!-- Everything is drawn again when the language changes, so no word of the page is left in the old one. -->
{#key language.code}
  <Header section={route.section} onsearch={() => ready && palette.open()} />
  <Palette bind:this={palette} />
{/key}
<main>
  {#if failed}
    <p class="pad err">{t("Could not load the data ({error}).", { error: failed })}</p>
  {:else if !ready}
    <p class="pad muted">{t("Loading the reference…")}</p>
  {:else}
    {#key `${route.visit}|${language.code}`}
      <View />
    {/key}
  {/if}
</main>
<!-- The footer waits for the page above it: drawn under the one-line
     "Loading" it would be pushed down a screen when data.json lands, the
     whole of Lighthouse's layout shift (CLS 0.25 desktop, 0.52 mobile). -->
{#key language.code}
  {#if ready || failed}
    <Footer {markdown} release={ready ? gameRelease() : null} />
  {/if}
  <Toast />
  <UpdateToast />
{/key}




