<script>
  // Light / Dark / System, as a small menu under the moon-or-sun button.
  import { applyTheme, themeChoice, THEMES } from "../lib/theme.js";

  let choice = $state(themeChoice());
  let open = $state(false);
  let button;
  let menu;

  function toggle(e) {
    e.stopPropagation();
    open = !open;
  }

  function pick(next) {
    choice = next;
    applyTheme(next);
    open = false;
    button.focus();
  }

  function keydown(e) {
    const items = [...menu.querySelectorAll("button")];
    const i = items.indexOf(document.activeElement);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      items[(i + (e.key === "ArrowDown" ? 1 : items.length - 1)) % items.length].focus();
    } else if (e.key === "Escape") {
      e.stopPropagation();
      open = false;
      button.focus();
    }
  }

  // Opening it puts focus on the current choice, for the arrow keys.
  $effect(() => {
    if (open) menu.querySelector('[aria-checked="true"]')?.focus();
  });
</script>

<svelte:document onclick={(e) => { if (!e.target.closest(".theme-wrap")) open = false; }} />

<div class="theme-wrap">
  <button class="icon-btn" id="theme" type="button" aria-label="Theme" aria-haspopup="menu"
    aria-expanded={open} aria-controls="theme-menu" bind:this={button} onclick={toggle}>
    <svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>
    <svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
  </button>
  <div class="theme-menu" id="theme-menu" role="menu" tabindex="-1" hidden={!open} bind:this={menu} onkeydown={keydown}>
    {#each THEMES as [key, label] (key)}
      <button type="button" role="menuitemradio" aria-checked={choice === key} onclick={() => pick(key)}>{label}</button>
    {/each}
  </div>
</div>

<style>
  /* The icon shows the theme in effect, whoever chose it. */
  .sun, :global(:root[data-theme="light"]) .moon { display: none; }
  :global(:root[data-theme="light"]) .sun { display: block; }
  @media (prefers-color-scheme: light) {
    :global(:root:not([data-theme])) .moon { display: none; }
    :global(:root:not([data-theme])) .sun { display: block; }
  }

  .theme-wrap { position: relative; }
  .theme-menu {
    position: absolute;
    right: 0;
    top: calc(100% + 6px);
    z-index: 6;
    min-width: 9rem;
    padding: 4px 0;
    background: var(--p-panel);
    border: 1px solid var(--p-outline);
    box-shadow: 0 8px 24px rgb(0 0 0 / 0.3);
  }
  .theme-menu[hidden] { display: none; }
  .theme-menu button {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    padding: 6px 12px;
    background: none;
    border: 0;
    color: var(--p-muted);
    font-family: var(--p-mono);
    font-size: 0.85rem;
    text-align: left;
    cursor: pointer;
  }
  .theme-menu button::before { content: " "; width: 1ch; color: var(--p-accent); }
  .theme-menu button[aria-checked="true"] { color: var(--p-text); }
  .theme-menu button[aria-checked="true"]::before { content: "●"; }
  .theme-menu button:hover, .theme-menu button:focus-visible { background: var(--p-accent); color: var(--p-on-accent); outline: none; }
  .theme-menu button:hover::before, .theme-menu button:focus-visible::before { color: var(--p-on-accent); }
</style>
