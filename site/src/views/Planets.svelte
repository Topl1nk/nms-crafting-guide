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
  import { fmtDate } from "../lib/dates.js";
  import { D, galaxyName } from "../lib/data.js";
  import { gamesave } from "../lib/gamesave.svelte.js";
  import { ordinal, t } from "../lib/i18n.js";
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
  const when = (ts) => fmtDate(ts * 1000);
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
  // A name of the game's planet page, as the game words it in the chosen language (the page's own word where the game has none).
  const label = (key, english) => textOf(key) || t(english);
  // The resource list is the hints (plant, bones, salvage ...) and then the rare, the uncommon and the common substance.
  // The emblem of each type (pictures.py: the game's pets' biome pictures, eight of them). The types the game has no picture for take
  // the one of the type they belong to: swamp and waterworld are lush, lava is scorched, red, green and blue are the exotic (weird) ones.
  // That is our reading of how they belong, not something the game files say. Gas giants have none.
  const EMBLEM = { Lush: "Lush", Toxic: "Toxic", Scorched: "Scorched", Radioactive: "Radioactive", Frozen: "Frozen", Barren: "Barren", Dead: "Dead", Weird: "Weird",
    Swamp: "Lush", Waterworld: "Lush", Lava: "Scorched", Red: "Weird", Green: "Weird", Blue: "Weird" };
  // The colour of a system's text is its star's (the game's order: yellow, green, blue, red, purple).
  const STAR = ["yellow", "green", "cyan", "red", "purple"];
  // The plant comes first (its hint is an item's id, the others' are the game's UI texts), then the rest in the game's order.
  const hintsOf = (p) => {
    const hints = p.resources?.length >= 3 ? p.resources.slice(0, -3) : [];
    return [...hints.filter((id) => !id.startsWith("UI_")), ...hints.filter((id) => id.startsWith("UI_"))];
  };
  const resOf = (p) => [...hintsOf(p), ...(p.resources?.length >= 3 ? p.resources.slice(-3) : p.resources ?? [])];
  const subOf = (p, i) => (p.resources?.length >= 3 ? p.resources[p.resources.length - 3 + i] : "");
  const subName = (p, i) => { const id = subOf(p, i); return id ? D.items[id]?.name ?? textOf(id) ?? id : ""; };
  // A planet whose weather, sentinels, flora and fauna are not worked out (the save's record and the generator disagree on its type).
  const unknown = (p) => p.planet && !(p.weather_key || p.sentinel_key || p.flora_key || p.fauna_key);

  // What the game shows beside a hint that is not an item (the bones, the salvage, the bugs, the swarm): a picture of an item that is the same.
  const HINT_ICON = { UI_BONES_HINT: "HINT_bones", UI_SCRAP_HINT: "BP_SALVAGE", UI_BUGS_HINT: "HINT_bugs", UI_B_SWARM_HINT: "HINT_swarm" };

  const typed = debounce((value) => { st.text = value; search = value; });

  setKeys({
    get list() { return list; },
    get search() { return input; },
    escape: () => { st.text = search = ""; if (input) input.value = ""; },
  });
</script>

{#snippet typeCell(p)}{#if p.planet && EMBLEM[p.biome]}<span class="ti"><ItemIcon id="BIOME_{EMBLEM[p.biome]}" size={32} /></span>{/if}{kindOf(p)}{/snippet}
{#snippet dates(p)}{when(p.seen)}{/snippet}
<!-- what you found: a picture and a figure for each kind, the fauna out of how many there are -->
{#snippet foundCell(p)}<span class="res-row">{#each [["flora", p.flora, null, "#6fdc8c", label("UI_DISC_FLORA", "Flora")], ["fauna", p.fauna, p.fauna_total, "#f3b878", label("UI_DISC_FAUNA", "Fauna")], ["mineral", p.minerals, null, "#be96f6", label("UI_DISC_MINERALS", "Minerals")]] as [icon, n, total, tone, name]}{#if n || total}<span class="cnt" title={name}><ItemIcon id="FIND_{icon}" size={32} color={tone} /><b>{n}{#if total}/{total}{/if}</b></span>{/if}{/each}</span>{/snippet}
{#snippet baseCell(p)}{#if p.bases.length}<span class="cnt" title={p.bases.map((n) => n || t("Unnamed base")).join(", ")}><ItemIcon id="PLANET_base" size={32} color="#8fb6ff" />{#if p.bases.length > 1}<b>{p.bases.length}</b>{/if}</span>{/if}{/snippet}
{#snippet hintCell(p)}<span class="res-row">{#each hintsOf(p) as id}<ItemIcon id={D.items[id] ? id : HINT_ICON[id] ?? id} size={32} />{/each}</span>{/snippet}
{#snippet subsCell(p)}<span class="res-row">{#each [0, 1, 2] as i}{@const id = subOf(p, i)}{#if id}<ItemIcon id={D.items[id] ? id : HINT_ICON[id] ?? id} size={32} />{/if}{/each}</span>{/snippet}
<!-- the name over its system (and galaxy, outside the first): one column instead of three -->
{#snippet nameCell(p)}<span class="two"><span>{#if shown(p)}{shown(p)}{:else}<span class="muted">{nameOf(p)}</span>{/if}</span><small class="muted" style:color={p.star != null ? `var(--p-${STAR[p.star]})` : undefined}>{p.system_name || hex3(p.system)}{p.galaxy > 1 ? ` · ${galaxyName(p.galaxy)}` : ""}</small></span>{/snippet}

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
        { title: t("Planet"), cell: nameCell, cls: "strong", sort: shown },
        { title: t("System"), ghost: true, sort: (p) => p.system_name || hex3(p.system) },
        { title: t("Planet type"), cell: typeCell, cls: "clip w190", sort: kindOf },
        { title: label("WEATHER_L", "Weather"), text: (p) => unknown(p) ? t("Data not determined") : textOf(p.weather_key), cls: "wide-only clip w170 muted", sort: (p) => textOf(p.weather_key) },
        { title: label("SENTINELS_L", "Sentinels"), text: (p) => textOf(p.sentinel_key), cls: "wide-only clip w150 muted", sort: (p) => textOf(p.sentinel_key) },
        { title: label("FAUNA_L", "Fauna"), text: (p) => textOf(p.fauna_key), cls: "wide-only clip w130 muted", sort: (p) => p.fauna_key },
        { title: t("Found by you"), cell: foundCell, cls: "wide-only", sort: (p) => p.fauna + p.flora + p.minerals },
        { title: label("RESOURCES_L", "Resources"), cell: hintCell, cls: "wide-only", sort: (p) => hintsOf(p).length },
        { title: `${label("RESOURCES_L", "Resources")} 2`, cell: subsCell, cls: "wide-only", sort: (p) => subName(p, 0) },
        { title: t("Bases"), cell: baseCell, cls: "wide-only", sort: (p) => p.bases.length },
        { title: t("Last seen"), cell: dates, cls: "num muted", sort: (p) => p.seen },
      ]} />
    </div>
    <aside class="detail">
      {#if cur}
        {@const p = cur}
        {#if p.planet && p.biome}<div class="globe"><ItemIcon id="GLOBE_{p.biome}" size={96} /></div>{/if}
        <h2>{nameOf(p)}</h2>
        <p class="muted sub">{t("{ordinal} in the system", { ordinal: ordinal(p.planet), n: p.planet })}{p.system_name ? ` · ${p.system_name}` : ""}</p>
        {#if kindOf(p)}<div class="ic-chips"><span class="pill">{#if EMBLEM[p.biome]}<span class="ti"><ItemIcon id="BIOME_{EMBLEM[p.biome]}" size={24} /></span>{/if}{kindOf(p)}</span></div>{/if}

        <div class="portal">
          <GlyphStrip code={p.code} />
          <p class="code"><b>{p.code}</b> <button class="link" onclick={() => copy(p.code, t("portal code"))}>{t("copy")}</button> · <a href="#/portals?code={p.code}">{t("To the converter")}</a></p>
        </div>

        {#if p.weather_key || p.sentinel_key || p.flora_key || p.fauna_key}
          <dl>
            {#each [["weather", "WEATHER_L", "Weather", p.weather_key], ["sentinels", "SENTINELS_L", "Sentinels", p.sentinel_key], ["flora", "FLORA_L", "Flora", p.flora_key], ["fauna", "FAUNA_L", "Fauna", p.fauna_key]] as [icon, loc, english, key]}
              {#if key}<dt><ItemIcon id="PLANET_{icon}" size={32} color="#8fb6ff" />{label(loc, english)}</dt><dd>{textOf(key)}</dd>{/if}
            {/each}
          </dl>
        {:else if unknown(p)}
          <p class="muted small">{t("Data not determined")}</p>
        {/if}

        {#if p.resources?.length}
          <h3>{label("RESOURCES_L", "Resources")}</h3>
          <div class="res">
            {#each resOf(p) as id}<span><ItemIcon id={D.items[id] ? id : HINT_ICON[id] ?? id} size={24} />{D.items[id]?.name ?? (textOf(id) || id)}</span>{/each}
          </div>
        {:else}
          <p class="muted small">{t("The game files do not say which resources a planet has. The game works them out from the planet's seed, and the save does not keep them, so none are listed here.")}</p>
        {/if}

        {#if p.flora || p.fauna || p.minerals || p.fauna_total}
          <h3>{t("Found by you")}</h3>
          {@render foundCell(p)}
        {/if}
        {#if p.bases.length}
          <h3>{t("Bases")}</h3>
          <div class="res">{#each p.bases as name}<span><ItemIcon id="PLANET_base" size={24} color="#8fb6ff" />{name || t("Unnamed base")}</span>{/each}</div>
        {/if}
      {/if}
    </aside>
  </div>
{/if}

<style>
  .res-row { display: inline-flex; gap: 8px; align-items: center; }
  /* a find: the picture, with its figure on its lower edge like a stack's count */
  .cnt { position: relative; display: inline-flex; margin-right: 6px; }
  .cnt b { position: absolute; right: -6px; bottom: -4px; padding: 0 5px; border-radius: 999px; font-size: 0.72rem; font-weight: 600; line-height: 1.4; font-variant-numeric: tabular-nums; color: #fff; background: rgb(8 12 24 / 0.78); }
  .two { display: flex; flex-direction: column; line-height: 1.2; min-width: 0; }
  .two small { font-size: 0.74rem; font-weight: 400; }
  /* narrow text columns: a long text is cut with an ellipsis (the whole of it is in the tooltip) */
  .main :global(td.w130) { max-width: 130px; }
  .main :global(td.w150) { max-width: 150px; }
  .main :global(td.w170) { max-width: 170px; }
  .main :global(td.w190) { max-width: 190px; }
  .globe { display: flex; justify-content: center; margin: 4px 0 10px; line-height: 0; }
  .ti { display: inline-block; margin-right: 8px; vertical-align: middle; line-height: 0; }
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
  h3 { display: flex; align-items: center; gap: 8px; }
  dl { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 12px 16px; align-items: center; margin: 0; }
  dt { display: flex; align-items: center; gap: 8px; color: var(--p-faint); }
  dd { margin: 0; }
  @media (max-width: 1000px) { .split-planets { grid-template-columns: minmax(0, 1fr); } }
</style>
