<script module>
  import { N_ } from "../lib/i18n.js";

  // What you typed and which planet was chosen outlives a visit, as on the other pages.
  const st = { text: "" };

  // The planet types as the game's tables name them, and the star colours; English keys for t().
  const TYPES = {
    Lush: N_("Lush"), Toxic: N_("Toxic"), Scorched: N_("Scorched"), Radioactive: N_("Radioactive"), Frozen: N_("Frozen"),
    Barren: N_("Barren"), Dead: N_("Dead"), Weird: N_("Weird planet"), Swamp: N_("Swamp"), Lava: N_("Lava"), Waterworld: N_("Waterworld"),
  };
  const STARS = { Yellow: N_("Yellow"), Green: N_("Green"), Blue: N_("Blue"), Red: N_("Red"), Purple: N_("Purple") };
</script>

<script>
  // The planets you have been to (#/planets), read from the game save: a list, and the card of the chosen one. The save keeps a
  // planet's address, the day it was found, its type (a number in the discovery record, read by the desktop program), what you
  // found on it and your bases there; it does not keep its resources (the game works those out from the planet's seed), and the
  // card says plainly that they are not known. A name is kept only if one was given: the desktop program works
  // the others out from the seed and the address (name_source "generated"), and the card says so.
  import GlyphStrip from "../components/GlyphStrip.svelte";
  import ItemIcon from "../components/ItemIcon.svelte";
  import List from "../components/List.svelte";
  import { D, galaxyName } from "../lib/data.js";
  import { gamesave } from "../lib/gamesave.svelte.js";
  import { ordinal, t, ui } from "../lib/i18n.js";
  import { setKeys } from "../lib/keys.js";
  import { copy } from "../lib/toast.svelte.js";
  import { debounce } from "../lib/util.js";

  let search = $state(st.text);
  let cur = $state.raw(null);
  let list = $state();
  let input = $state();

  const rows = $derived.by(() => {
    const all = gamesave.report?.planets ?? [];
    const terms = search.toLowerCase().split(/\s+/).filter(Boolean);
    return all.filter((p) => terms.every((w) => [shown(p), p.name, p.system_name, p.code, hex3(p.system), galaxyName(p.galaxy)].join(" ").toLowerCase().includes(w)));
  });

  const hex3 = (n) => `0x${n.toString(16).toUpperCase().padStart(3, "0")}`;
  const when = (ts) => (ts ? new Date(ts * 1000).toLocaleDateString(ui.locale, { year: "numeric", month: "short", day: "numeric" }) : "");
  // A name the save does not hold is put together the way the game does it, from its own texts in the chosen language: the
  // template (NAMEGEN_PLANET_STYLE_n) and the word added to it (Delta becomes Дельта). A name from the save is shown as it is.
  const shown = (p) => {
    const w = D.biomes.words, n = p.name_parts, template = n && w[`NAMEGEN_PLANET_STYLE_${n.style}`];
    if (!template) return p.name;
    return template.replace("%ADORN%", w[`NAMEGEN_PLANET_ADORN_${n.adorn}`] || "").replace(/%([A-Z]+)%/g, (m, key) => n[key] ?? m);
  };
  const nameOf = (p) => shown(p) || t("Unnamed planet");
  const keyOf = (p) => `${p.galaxy}/${p.code}`;
  const typeName = (id) => (TYPES[id] ? t(TYPES[id]) : t("{colour} type", { colour: t(STARS[id] ?? id) }));

  // The word the game puts before "Planet" in its own language: the text under the planet's loc key, ending in the word for the planet.
  const wordOf = (p) => (D.biomes.words[p.word_key] || "").replace("%PLANETCLASS%", D.biomes.words[p.class_key || "PLANETCLASS1"] || "").trim();
  // What the table and the card call the planet's type: the game's own word, else the type's name (Weird planets have no word).
  const kindOf = (p) => (p.planet ? wordOf(p) || (TYPES[p.biome] ? t(TYPES[p.biome]) : "") : "");
  // The game's text under a loc key (weather, sentinels, flora), without the planet-word placeholders.
  const textOf = (key) => (D.biomes.words[key] || "").replace(/%[A-Z]+%/g, "").trim();

  const typed = debounce((value) => { st.text = value; search = value; });

  setKeys({
    get list() { return list; },
    get search() { return input; },
    escape: () => { st.text = search = ""; if (input) input.value = ""; },
  });
</script>

{#snippet dates(p)}{when(p.seen)}{/snippet}
{#snippet nameCell(p)}{shown(p) || ""}{#if !shown(p)}<span class="muted">{nameOf(p)}</span>{/if}{/snippet}

<div class="fbar">
  <h1><span>{t("Planets")}</span></h1>
  <input class="search" style="max-width:520px" type="search" placeholder={t("Name, system or portal code")} value={st.text}
    autocomplete="off" spellcheck="false" bind:this={input} oninput={(e) => typed(e.target.value)}>
</div>

{#if !gamesave.available || !gamesave.report}
  <section class="card">
    <p class="muted">{gamesave.error || (gamesave.available ? t("No game saves found.") : t("This page reads your game save through the desktop program, and there is none to read here."))}</p>
  </section>
{:else if !gamesave.report.planets?.length}
  <section class="card"><p class="muted">{t("The save shows no planets you have visited.")}</p></section>
{:else}
  <div class="split split-planets">
    <div class="main">
      <List bind:this={list} {rows} keep {keyOf} empty={t("No planets match this search.")} onSelect={(p) => { cur = p; }} columns={[
        { title: t("Name"), cell: nameCell, cls: "strong", sort: shown },
        { title: t("System"), text: (p) => p.system_name || hex3(p.system), sort: (p) => p.system_name || hex3(p.system) },
        { title: t("Planet type"), text: kindOf, sort: kindOf },
        { title: t("Galaxy"), text: (p) => galaxyName(p.galaxy), cls: "wide-only", sort: (p) => p.galaxy },
        { title: t("Last seen"), cell: dates, cls: "muted", sort: (p) => p.seen },
      ]} />
    </div>
    <aside class="detail">
      {#if cur}
        {@const p = cur}
        <h2>{nameOf(p)}</h2>
        <p class="muted sub">{t("{ordinal} in the system", { ordinal: ordinal(p.planet), n: p.planet })}{p.system_name ? ` · ${p.system_name}` : ""}</p>
        {#if kindOf(p)}<div class="ic-chips"><span class="pill">{kindOf(p)}</span></div>{/if}

        <div class="portal">
          <GlyphStrip code={p.code} />
          <p class="code"><b>{p.code}</b> <button class="link" onclick={() => copy(p.code, t("portal code"))}>{t("copy")}</button> · <a href="#/portals?code={p.code}">{t("To the converter")}</a></p>
        </div>

        {#if p.weather_key || p.sentinel_key || p.flora_key || p.fauna_key}
          <dl>
            {#if p.weather_key}<dt>{t("Weather")}</dt><dd>{textOf(p.weather_key)}</dd>{/if}
            {#if p.sentinel_key}<dt>{t("Sentinels")}</dt><dd>{textOf(p.sentinel_key)}</dd>{/if}
            {#if p.flora_key}<dt>{t("Flora")}</dt><dd>{textOf(p.flora_key)}</dd>{/if}
            {#if p.fauna_key}<dt>{t("Fauna")}</dt><dd>{textOf(p.fauna_key)}</dd>{/if}
          </dl>
        {/if}

        {#if p.resources?.length}
          <h3>{t("Resources")}</h3>
          <div class="res">
            {#each p.resources as id}<span>{#if D.items[id]}<ItemIcon {id} size={20} />{D.items[id].name}{:else}{textOf(id) || id}{/if}</span>{/each}
          </div>
        {:else}
          <p class="muted small">{t("The game files do not say which resources a planet has. The game works them out from the planet's seed, and the save does not keep them, so none are listed here.")}</p>
        {/if}

        {#if p.flora || p.fauna || p.minerals}
          <p class="muted small finds">{p.flora} {t("Flora")} · {p.fauna} {t("Fauna")} · {p.minerals} {t("Minerals")}</p>
        {/if}
        {#if p.bases.length}
          <h3>{t("Bases")}</h3>
          <ul>{#each p.bases as name}<li>{name || t("Unnamed base")}</li>{/each}</ul>
        {/if}
      {/if}
    </aside>
  </div>
{/if}

<style>
  .split-planets { grid-template-columns: minmax(0, 1fr) clamp(340px, 32%, 460px); }
  .main { min-width: 0; min-height: 0; align-self: stretch; display: flex; flex-direction: column; }
  .main :global(.list) { flex: 1 1 0; height: auto; max-height: none; overflow: auto; min-height: 160px; }
  .split-planets .detail { align-self: stretch; }
  .sub { margin: 2px 0 10px; }
  .portal { margin: 4px 0 14px; }
  .code { margin: 6px 0 0; font-size: 0.9rem; }
  h3 { margin: 18px 0 8px; font-size: 0.78rem; letter-spacing: 0.06em; text-transform: uppercase; color: var(--p-faint); font-weight: 600; }
  .res { display: flex; flex-wrap: wrap; gap: 6px; }
  .res span { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; background: var(--p-raised); white-space: nowrap; font-size: 0.9rem; }
  .finds { margin-top: 16px; }
  dl { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 6px 16px; margin: 0; }
  dt { color: var(--p-faint); }
  dd { margin: 0; }
  @media (max-width: 1000px) { .split-planets { grid-template-columns: minmax(0, 1fr); } }
</style>
