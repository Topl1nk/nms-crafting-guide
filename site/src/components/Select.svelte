<script>
  // A filter of a page's bar: a small label, then the choice, and a list under it that opens from the field and is
  // as wide as its widest line. `options` is [[value, text, itemId?], ...] (an itemId puts the game's picture in front);
  // `value` binds; `onchange` gets the new value. `hidden`: the filter is not offered now; it leaves a marker (.gone) in the bar,\n  // so that its two neighbours, and only they, take its room (app.css).
  //
  // The field keeps one width: that of the longest of `all` (every choice there could ever be; the page gives it when it
  // lists only some at a time) and of every choice seen so far, so choosing, or a list that gets shorter, never moves what
  // stands beside it. The list is right-aligned to the field.
  import ItemIcon from "./ItemIcon.svelte";
  import { bloom, collapse } from "../lib/bar.js";
  import { closeOutside } from "../lib/util.js";

  let { label, value = $bindable(), options, all = undefined, neutral = undefined, title = "", disabled = false, hidden = false, onchange = undefined } = $props();
  let box = $state();
  let shown = false; // set once the filter has been drawn: only a filter that comes back later grows in
  $effect(() => { shown = true; });
  let width = $state(0);
  let last = 0; // the width the field had, for the marker that takes its place
  $effect(() => { if (width > 0) last = width; });
  let seen = $state([]);

  $effect.pre(() => {
    const known = new Set(seen.map(([v]) => v));
    const fresh = [...(all ?? []), ...options].filter(([v]) => !known.has(v));
    if (fresh.length) seen = [...seen, ...fresh.filter(([v], i, a) => a.findIndex(([w]) => w === v) === i)];
  });
  const current = $derived(options.find(([v]) => v === value) ?? seen.find(([v]) => v === value) ?? options[0]);
  const active = $derived(neutral !== undefined && value !== neutral); // a filter (it has a neutral choice, "any …") is on when it is not at it
  const withIcon = $derived(seen.some(([, , icon]) => icon));
  function pick(v) {
    if (box) box.open = false;
    value = v;
    onchange?.(v);
  }
  // Up and down move along the list, Esc closes it.
  function key(e) {
    const items = [...box.querySelectorAll(".menu button")];
    const i = items.indexOf(document.activeElement);
    if (e.key === "ArrowDown") { e.preventDefault(); items[Math.min(items.length - 1, i + 1)]?.focus(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); items[Math.max(0, i - 1)]?.focus(); }
    else if (e.key === "Escape") { box.open = false; box.querySelector("summary").focus(); }
  }
</script>

{#if hidden}<i class="gone" aria-hidden="true" use:collapse={last}></i>{:else}
<details class="drop sel" bind:this={box} bind:clientWidth={width} in:bloom={{ skip: !shown }} use:closeOutside class:disabled>
  <summary class="fsel" class:on={active} {title} onclick={(e) => { if (disabled) e.preventDefault(); }}>
    <span class="lab">{label}</span>
    <b class="cur">
      {#each seen as [v, text] (v)}<span class="ghost" aria-hidden="true">{#if withIcon}<span class="pad"></span>{/if}{text}</span>{/each}
      <span class="now">{#if current?.[2]}<ItemIcon id={current[2]} size={32} />{:else if withIcon}<span class="pad"></span>{/if}{current?.[1] ?? ""}</span>
    </b>
    <i class="chev" aria-hidden="true"></i>
  </summary>
  <div class="drop-pop menu" role="listbox" tabindex="-1" onkeydown={key}>
    {#each options as [v, text, icon] (v)}
      <button type="button" role="option" aria-selected={v === value} class:on={v === value} onclick={() => pick(v)}>
        {#if icon}<ItemIcon id={icon} size={44} />{:else if withIcon}<span class="none"></span>{/if}<span class="t">{text}</span>
      </button>
    {/each}
  </div>
</details>
{/if}

<style>
  .lab { color: var(--p-faint); }
  /* Every line of every choice stacked in one cell, hidden: the cell is as wide as the widest, whatever is shown. */
  .cur { display: inline-grid; flex: 1; margin-left: -4px; font-weight: 400; color: var(--p-text); font-size: 0.9rem; }
  .cur > * { grid-area: 1 / 1; display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; min-width: 0; overflow: hidden; text-overflow: ellipsis; }
  .ghost { visibility: hidden; height: 0; max-width: 34ch; }
  .pad { width: 32px; flex: none; }
  .chev { flex: none; width: 8px; height: 8px; margin: 0 12px 0 2px; border-radius: 50%; background: var(--p-faint); }
  .on .chev { background: var(--p-accent-ink); }
  .on .cur { color: var(--p-accent-ink); }
  .disabled { opacity: 0.5; }
  .menu { left: auto; right: 0; width: max-content; min-width: 100%; max-width: min(90vw, 480px); max-height: 70vh; overflow: auto; padding: 6px; display: grid; gap: 2px; }
  .menu button {
    display: flex; align-items: center; gap: 10px; height: 36px; padding: 0 12px; border: 0; border-radius: 8px; overflow: hidden;
    background: none; color: var(--p-text); font: inherit; font-size: 0.9rem; text-align: left; cursor: pointer; white-space: nowrap;
  }
  .menu button:has(:global(.ico)), .menu button:has(.none) { height: 44px; padding-left: 0; }
  .menu button:hover, .menu button:focus-visible { background: var(--p-raised); outline: none; }
  .menu button.on { color: var(--p-accent-ink); }
  .none { width: 44px; flex: none; }
</style>






