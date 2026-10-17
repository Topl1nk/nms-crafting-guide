<script>
  // Installing the site as an app, beside the ways to run the terminal one:
  // the browser's own prompt behind a button where it offers one, the Share
  // menu on iOS Safari, which never does. Nothing at all inside the installed
  // app. Shown on the start page and in Help.
  import { install, pwa } from "../lib/pwa.svelte.js";
  import PaneHeading from "./PaneHeading.svelte";
</script>

{#if !pwa.standalone}
  <section class="pane app">
    <PaneHeading title="as an app" note="this site, offline" />
    <p>Install this site and it opens in its own window, from the home screen or the app list, and keeps working with
      no signal: every screen, with the data from your last visit.</p>
    {#if pwa.ios}
      <p class="hint">On iPhone or iPad: <b>Share</b> → <b>Add to Home Screen</b>.</p>
    {:else if pwa.canInstall}
      <p><button type="button" class="install" onclick={install}>Install app</button></p>
    {:else}
      <p class="hint">From the browser's menu: <b>Install app</b>, or <b>Add to Home screen</b> on a phone.</p>
    {/if}
  </section>
{/if}

<style>
  .pane { background: var(--p-panel); border: 1px solid var(--p-outline); padding: 4px 18px 14px; margin-top: 12px; }
  .pane p { font-size: 0.92rem; line-height: 1.6; color: var(--p-muted); max-width: 80ch; }
  .hint { font-family: var(--p-mono); font-size: 0.85rem; color: var(--p-faint); }
  .hint b { color: var(--p-text); font-weight: 400; }
  /* The start page's primary action, `[ Install app ]`. */
  .install {
    font-family: var(--p-mono);
    font-weight: 700;
    padding: 8px 20px;
    border: 0;
    border-radius: 0;
    background: var(--p-accent);
    color: var(--p-on-accent);
    cursor: pointer;
  }
  .install::before { content: "[ "; }
  .install::after { content: " ]"; }
  .install:hover { filter: brightness(1.08); }
  /* Inside Help's card the pane inverts, as InstallPanes' do. */
  :global(.card) .pane { background: var(--p-bg); }
</style>
