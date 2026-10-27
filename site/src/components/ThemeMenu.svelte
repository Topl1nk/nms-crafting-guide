<script>
  // "Look": light or dark, the accent colour, glowing icons, chemical symbols, text size.
  import { t } from "../lib/i18n.js";
  import { language, setLanguage } from "../lib/language.svelte.js";
  import { ACCENTS, applyTheme, look, setLook, themeChoice, THEMES } from "../lib/theme.js";
  import { toast } from "../lib/toast.svelte.js";

  let choice = $state(themeChoice());
  let accent = $state(look.accent());
  let glow = $state(look.glow());
  let fs = $state(look.fs());
  let sym = $state(look.sym());
  let open = $state(false);
  let button;

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
    aria-expanded={open} bind:this={button} onclick={toggle} title={t("Appearance")}>
    <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/></svg>
  </button>
  <div class="panel" role="dialog" aria-label={t("Appearance")} hidden={!open}>
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
    {#if language.list.length > 1}
      <h4>{t("Language")}</h4>
      <select class="lang" value={language.code} onchange={pickLanguage} aria-label={t("Language")}>
        {#each language.list as l (l.code)}<option value={l.code}>{l.name}</option>{/each}
      </select>
    {/if}
    <h4>{t("Show")}</h4>
    <label class="opt"><input type="checkbox" checked={glow} onchange={(e) => { glow = e.target.checked; setLook("glow", glow); }}>
      <span>{t("Glow icons in the game's own colour")}</span></label>
    <label class="opt"><input type="checkbox" checked={sym} onchange={(e) => { sym = e.target.checked; setLook("sym", sym); }}>
      <span>{t("Chemical symbols on icons")}</span></label>
    <h4>{t("Text size")} <b>{fs}</b></h4>
    <input class="range" type="range" min="14" max="22" step="1" value={fs} aria-label={t("Text size")}
      oninput={(e) => { fs = Number(e.target.value); setLook("fs", fs); }}>
  </div>
</div>

<style>
  .theme-wrap { position: relative; }
  .panel {
    position: absolute; right: 0; top: calc(100% + 8px); z-index: 30; width: 300px; padding: 16px 18px 14px;
    background: var(--p-panel); border: 1px solid var(--p-outline); border-radius: 16px;
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

