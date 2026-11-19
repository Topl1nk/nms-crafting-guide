<script>
  // "Look": light or dark, the accent colour, glowing icons, chemical symbols, text size.
  import { onMount } from "svelte";
  import { fmtStamp } from "../lib/dates.js";
  import { gamesave } from "../lib/gamesave.svelte.js";
  import { t } from "../lib/i18n.js";
  import { language, setLanguage } from "../lib/language.svelte.js";
  import { checkUpdate, installUpdate, setAuto, update } from "../lib/update.svelte.js";
  import { installPictures, pictures, probePictures } from "../lib/pictures.svelte.js";
  import { ACCENTS, applyTheme, look, setLook, themeChoice, THEMES } from "../lib/theme.js";
  import { toast } from "../lib/toast.svelte.js";

  let choice = $state(themeChoice());
  let accent = $state(look.accent());
  let glow = $state(look.glow());
  let fs = $state(look.fs());
  let sym = $state(look.sym());
  let open = $state(false);
  let button;
  onMount(probePictures);
  const stepText = $derived(
    pictures.step === "pictures" ? t("Taking the pictures: {done} of {total}", { done: pictures.done, total: pictures.total })
      : pictures.step === "listing" ? t("Listing the game's files…") : t("Reading the game's tables…"));
  const pictureError = $derived(/game not found/.test(pictures.error) ? t("The game was not found") : pictures.error);

  const percent = $derived(update.total ? Math.round((100 * update.done) / update.total) : 0);
  const busy = $derived(update.state !== "idle");

  const toggle = (e) => { e.stopPropagation(); open = !open; };
  const pickTheme = (k) => { choice = k; applyTheme(k); };
  const pickAccent = (k) => { accent = k; setLook("accent", k); };
  const pickLanguage = async (e) => {
    try { await setLanguage(e.target.value); } catch (exc) {
      e.target.value = language.code;
      toast(t("Could not load the language ({error})", { error: exc.message }));
    }
  };
</script>

<svelte:document onclick={(e) => { if (!e.target.closest(".theme-wrap")) open = false; }}
  onkeydown={(e) => { if (e.key === "Escape" && open) { open = false; button.focus(); } }} />

<div class="theme-wrap">
  <button class="icon-btn" id="theme" type="button" aria-label={t("Appearance")} aria-haspopup="dialog"
    aria-expanded={open} bind:this={button} onclick={toggle} title={update.newer ? t("New version {n} is available", { n: update.latest }) : t("Appearance")}>
    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/></svg>
    {#if update.newer}<i class="mark" aria-hidden="true"></i>{/if}
  </button>
  <div class="panel" role="dialog" aria-label={t("Appearance")} hidden={!open}>
    <section class="grp">
    <h4>{t("Theme")}</h4>
    <div class="seg">
      {#each THEMES as [k, label] (k)}
        <button type="button" class:on={choice === k} onclick={() => pickTheme(k)}>{t(label)}</button>
      {/each}
    </div>
    <h4>{t("Accent colour")}</h4>
    <div class="swatches">
      {#each ACCENTS as [k, label, hex] (k)}
        <button type="button" class="sw" class:on={accent === k} style="--c:{hex}" title={t(label)} aria-label={t(label)} onclick={() => pickAccent(k)}></button>
      {/each}
    </div>
    <h4>{t("Show")}</h4>
    <label class="opt"><input type="checkbox" checked={glow} onchange={(e) => { glow = e.target.checked; setLook("glow", glow); }}>
      <span>{t("Glow icons in the game's own colour")}</span></label>
    <label class="opt"><input type="checkbox" checked={sym} onchange={(e) => { sym = e.target.checked; setLook("sym", sym); }}>
      <span>{t("Chemical symbols on icons")}</span></label>
    <h4>{t("Text size")} <b>{fs}</b></h4>
    <input class="range" type="range" min="14" max="22" step="1" value={fs} aria-label={t("Text size")}
      oninput={(e) => { fs = Number(e.target.value); setLook("fs", fs); }}>
    </section>
    <section class="grp">
    {#if language.list.length > 1}
      <h4>{t("Language")}</h4>
      <select class="lang" value={language.code} onchange={pickLanguage} aria-label={t("Language")}>
        {#each language.list as l (l.code)}<option value={l.code}>{l.name}</option>{/each}
      </select>
      {#if language.building}<span class="hint" aria-busy="true">…</span>{/if}
    {/if}
    </section>
    <section class="grp">
    {#if gamesave.available}
      <h4>{t("Game save")}</h4>
      <label class="opt" title={t("Take the items from your game save, not from a list typed in by hand")}>
        <input type="checkbox" checked={gamesave.on} onchange={(e) => { gamesave.on = e.target.checked; }}><span>{t("From the save")}</span></label>
      {#if gamesave.on && gamesave.slots.length}
        <select class="lang" value={gamesave.slot} onchange={(e) => { gamesave.slot = e.target.value; }} aria-label={t("Slot")} title={t("Which save to take the items from")}>
          {#each gamesave.slots as s (gamesave.slotKey(s))}<option value={gamesave.slotKey(s)}>{s.file} · {fmtStamp(s.saved * 1000)}</option>{/each}
        </select>
      {/if}
    {/if}
    {#if pictures.available}
      <h4>{t("Game pictures")}</h4>
      <div class="pics">
        {#if pictures.state === "running"}
          <span class="bar"><i style="width:{pictures.total ? Math.round((100 * pictures.done) / pictures.total) : 6}%"></i></span>
          <span class="hint">{stepText}</span>
        {:else if pictures.state === "done"}
          <span class="hint">{t("Done, reloading…")}</span>
        {:else}
          <button type="button" class="install" disabled={!pictures.game} onclick={installPictures}>{pictures.have ? t("Update from my game") : t("Install from my game")}</button>
          <span class="hint">{pictures.game ? `${t("{n} pictures installed", { n: pictures.have })} · ${t("{n} save slots found", { n: pictures.saves })}` : t("The game was not found")}</span>
          {#if pictures.state === "error"}<span class="hint err">{pictureError}</span>{/if}
        {/if}
      </div>
    {/if}
    </section>
    <section class="grp">
    {#if update.available && update.current}
      <h4>{t("Updates")}</h4>
      <div class="upd">
        {#if update.state === "downloading"}
          <span class="bar"><i style="width:{percent}%"></i></span>
          <span class="hint">{t("Downloading… {n}%", { n: percent })}</span>
        {:else if update.state === "installing"}
          <span class="hint">{t("Installing… the program will restart")}</span>
        {:else}
          <span class="hint">{t("Version {n}", { n: update.current })}</span>
          {#if update.newer}
            <span class="new">{t("New version {n} is available", { n: update.latest })}</span>
            {#if update.supported}<button type="button" class="install" disabled={busy} onclick={installUpdate}>{t("Update now")}</button>{/if}
          {:else if update.state === "checking"}
            <span class="hint">{t("Checking…")}</span>
          {:else}
            {#if update.asked && !update.error}<span class="hint">{t("You have the latest version")}</span>{/if}
            <button type="button" class="check" disabled={busy} onclick={() => checkUpdate(true)}>{t("Check for updates")}</button>
          {/if}
          {#if update.error}<span class="hint err">{update.error}</span>{/if}
        {/if}
        {#if update.supported}
          <label class="opt" title={t("Installs a new version by itself when one is found")}>
            <input type="checkbox" checked={update.auto} onchange={(e) => setAuto(e.target.checked)}><span>{t("Update automatically")}</span></label>
        {/if}
      </div>
    {/if}
    </section>
  </div>
</div>

<style>
  .theme-wrap { position: relative; }
  #theme { position: relative; }
  /* Four groups, each its own block under a line: how it looks, the language, the game's save and pictures, the program's updates.
     A group with nothing to show (no launcher, no update to speak of) is not drawn at all. */
  .grp:not(:first-of-type) { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--p-outline); }
  .grp:not(:has(h4)) { display: none; }
  .grp h4:first-child { margin-top: 0; }
  /* a new version is waiting: a dot on the button's corner, in the accent's own colour */
  .mark { position: absolute; top: 5px; right: 5px; width: 9px; height: 9px; border-radius: 50%; background: var(--p-red); box-shadow: 0 0 0 2px var(--p-bg); }
  .upd, .pics { display: grid; gap: 8px; }
  .new { font-size: 0.9rem; font-weight: 700; color: var(--p-text); }
  .check { height: 34px; border-radius: 10px; border: 1px solid var(--p-outline); background: var(--p-raised); color: var(--p-text); font: inherit; cursor: pointer; }
  .check:disabled { opacity: 0.5; cursor: default; }
  .check:not(:disabled):hover { border-color: var(--p-edge-accent); }
  .install { height: 36px; border-radius: 10px; border: 1px solid var(--p-edge-accent); background: var(--p-accent); color: var(--p-on-accent); font: inherit; font-weight: 700; cursor: pointer; }
  .install:disabled { opacity: 0.5; cursor: default; }
  .install:not(:disabled):hover { filter: brightness(1.08); }
  .hint { font-size: 0.82rem; color: var(--p-faint); }
  .hint.err { color: var(--p-red); }
  .bar { display: block; height: 8px; border-radius: 999px; background: var(--p-raised); overflow: hidden; }
  .bar i { display: block; height: 100%; background: var(--p-accent); transition: width 0.3s; }
  .panel {
    position: absolute; right: 0; top: calc(100% + 8px); z-index: 30; width: 330px; padding: 16px 18px 14px;
    background: var(--p-panel); border: 1px solid var(--p-outline); border-radius: 16px;
    max-height: calc(100vh - 80px); overflow-y: auto;
    box-shadow: 0 16px 40px rgb(0 0 0 / 0.45);
  }
  .panel[hidden] { display: none; }
  h4 { margin: 14px 0 8px; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--p-faint); }
  h4:first-child { margin-top: 0; }
  .seg { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; padding: 4px; background: var(--p-raised); border-radius: 12px; }
  .seg button {
    height: 34px; border: 0; border-radius: 9px; background: none; color: var(--p-muted); cursor: pointer; font: inherit; font-size: 0.9rem;
  }
  .seg button.on { background: var(--p-accent); color: var(--p-on-accent); font-weight: 700; }
  .swatches { display: flex; gap: 10px; }
  .sw {
    width: 34px; height: 34px; border-radius: 50%; border: 2px solid transparent; background: var(--c); cursor: pointer;
    outline: 2px solid transparent; outline-offset: 2px; padding: 0;
  }
  .sw.on { outline-color: var(--p-text); }
  .sw:hover { transform: scale(1.08); }
  .lang { width: 100%; height: 34px; }
  h4 b { margin-left: 6px; color: var(--p-text); font-size: 0.8rem; }
  .range { width: 100%; height: 24px; padding: 0; border: 0; background: none; accent-color: var(--p-accent-ink); cursor: pointer; }
  .opt { display: flex; align-items: center; gap: 10px; padding: 6px 0; font-size: 0.92rem; color: var(--p-muted); cursor: pointer; }
</style>

