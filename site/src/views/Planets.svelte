<script module>
  import { N_ } from "../lib/i18n.js";

  // What you typed and the filters outlive a visit, as on the other pages (a link brings its own).
  const st = { text: "", filters: null };
  const DEFAULTS = { type: "any", star: "any", weather: "any", sentinel: "any", flora: "any", fauna: "any", resource: "any", bases: false, found: false };

  // The planet types as the game's tables name them, and the star colours; English keys for t().
  const TYPES = {
    Lush: N_("Lush"), Toxic: N_("Toxic"), Scorched: N_("Scorched"), Radioactive: N_("Radioactive"), Frozen: N_("Frozen"),
    Barren: N_("Barren"), Dead: N_("Dead"), Weird: N_("Weird planet"), Swamp: N_("Swamp"), Lava: N_("Lava"), Waterworld: N_("Waterworld"),
  };
  const STARS = { Yellow: N_("Yellow"), Green: N_("Green"), Blue: N_("Blue"), Red: N_("Red"), Purple: N_("Purple") };
  const STAR_NAMES = ["Yellow", "Green", "Blue", "Red", "Purple"]; // a star's number is the game's order of colours
</script>

<script>
  // The planets you have been to (#/planets), read from the game save: a list, and the card of the chosen one. The save keeps a
  // planet's address, the day it was found, its type (a number in the discovery record, read by the desktop program), what you
  // found on it and your bases there; it does not keep its resources (the game works those out from the planet's seed), and the
  // card says plainly that they are not known. A name is kept only if one was given: the desktop program works
  // the others out from the seed and the address (name_source "generated"), and the card says so.
  import Check from "../components/Check.svelte";
  import GlyphStrip from "../components/GlyphStrip.svelte";
  import ItemIcon from "../components/ItemIcon.svelte";
  import List from "../components/List.svelte";
  import Reset from "../components/Reset.svelte";
  import Select from "../components/Select.svelte";
  import { fmtDate } from "../lib/dates.js";
  import { D, galaxyName } from "../lib/data.js";
  import { applyFacets, FLAG, facets, flag } from "../lib/facets.js";
  import { gamesave } from "../lib/gamesave.svelte.js";
  import { collate, ordinal, t, tn } from "../lib/i18n.js";
  import { setKeys } from "../lib/keys.js";
  import { capture, swap } from "../lib/motion.js";
  import { hintsOf, resOf, subOf } from "../lib/planetres.js";
  import { arrival } from "../lib/router.svelte.js";
  import { copy } from "../lib/toast.svelte.js";
  import { debounce } from "../lib/util.js";
  import { typeLabel } from "../lib/words.js";

  // A link may bring a resource (`resource`: an item's id, from the Wiki card), and the list is then of the planets that have it.
  const { params } = arrival();
  const linked = params.size > 0;

  let search = $state(linked ? "" : st.text);
  let f = $state(linked ? { ...DEFAULTS, resource: params.get("resource") ?? "any" } : { ...DEFAULTS, ...st.filters });
  let cur = $state.raw(null);
  let list = $state();
  let input = $state();
  $effect(() => { const now = { ...f }; if (!linked) st.filters = now; });

  const all = $derived(gamesave.report?.planets ?? []);
  const base = $derived.by(() => {
    const terms = search.toLowerCase().split(/\s+/).filter(Boolean);
    return terms.length ? all.filter((p) => terms.every((w) => [shown(p), p.name, p.system_name, p.code, hex3(p.system), galaxyName(p.galaxy)].join(" ").toLowerCase().includes(w))) : all;
  });

  // The filters: each lists only the choices that the other filters leave something for (lib/facets.js).
  const choices = (get, label) => {
    const seen = new Map();
    for (const p of all) { const v = get(p); if (v != null && v !== "" && !seen.has(v)) seen.set(v, label(v)); }
    return [...seen].sort((a, b) => collate(String(a[1]), String(b[1])));
  };
  const resourceIcon = (id) => (D.items[id] ? id : HINT_ICON[id] ?? id);
  const resourceName = (id) => D.items[id]?.name ?? (textOf(id) || id);
  const defs = $derived([
    { key: "type", options: [["any", t("any kind")], ...choices((p) => (p.planet ? p.biome : null), (v) => typeName(v))], neutral: "any", test: (p, v) => v === "any" || p.biome === v },
    { key: "star", options: [["any", t("any colour")], ...STAR_NAMES.map((n, i) => [i, t(STARS[n])]).filter(([i]) => all.some((p) => p.star === i))], neutral: "any", test: (p, v) => v === "any" || p.star === v },
    { key: "weather", options: [["any", t("any")], ...choices((p) => textOf(p.weather_key), (v) => v)], neutral: "any", test: (p, v) => v === "any" || textOf(p.weather_key) === v },
    { key: "sentinel", options: [["any", t("any")], ...choices((p) => textOf(p.sentinel_key), (v) => v)], neutral: "any", test: (p, v) => v === "any" || textOf(p.sentinel_key) === v },
    { key: "flora", options: [["any", t("any")], ...choices((p) => textOf(p.flora_key), (v) => v)], neutral: "any", test: (p, v) => v === "any" || textOf(p.flora_key) === v },
    { key: "fauna", options: [["any", t("any")], ...choices((p) => textOf(p.fauna_key), (v) => v)], neutral: "any", test: (p, v) => v === "any" || textOf(p.fauna_key) === v },
    { key: "resource", options: [["any", t("any")], ...resourceChoices()], neutral: "any", test: (p, v) => v === "any" || resOf(p).includes(v) },
    { key: "bases", options: FLAG, neutral: false, test: (p, v) => flag(v, p.bases.length > 0) },
    { key: "found", options: FLAG, neutral: false, test: (p, v) => flag(v, p.flora + p.fauna + p.minerals > 0) },
  ]);
  const resourceChoices = () => {
    const seen = new Set(all.flatMap((p) => resOf(p)));
    return [...seen].map((id) => [id, resourceName(id), resourceIcon(id)]).sort((a, b) => collate(a[1], b[1]));
  };
  const fx = $derived(facets(base, defs, f));
  const rows = $derived(applyFacets(base, defs, fx.effective));
  const filtered = $derived(Object.keys(DEFAULTS).some((k) => f[k] !== DEFAULTS[k]) || search !== "");
  const reset = () => { f = { ...DEFAULTS }; st.text = search = ""; if (input) input.value = ""; };

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
  // The globe of a planet as the game lays it up (desktop/planet_globe.py: which pictures, in which colours; the launcher draws it from the
  // player's own game pictures). Gas giants and planets the generator does not agree on have none.
  const hex = (c) => c.map((x) => Math.max(0, Math.min(255, Math.round(x * 255))).toString(16).padStart(2, "0")).join("");
  const globeUrl = (p) => {
    const g = p.globe;
    if (!g) return "";
    const rings = `&r=${g.rings ? 1 : 0}&s=192`;
    return g.gas ? `/globe?g=${hex(g.gas)}${rings}`
      : `/globe?t=${g.terrain[0]}&tc=${hex(g.terrain[1])}&w=${g.water ? g.water[0] : 0}&wc=${hex(g.water ? g.water[1] : [0, 0, 0])}&ww=${g.waterworld ? 1 : 0}&c=${g.clouds[0]}&ca=${Math.round(g.clouds[1] * 100)}${rings}`;
  };
  // The colour of a system's text is its star's (the game's order: yellow, green, blue, red, purple).
  const STAR = ["yellow", "green", "cyan", "red", "purple"];
  // (what a planet has: lib/planetres.js)
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
  <Reset active={filtered} onclick={reset} />
  <input class="search" style="max-width:520px" type="search" placeholder={t("Name, system or portal code")} value={search}
    autocomplete="off" spellcheck="false" bind:this={input} oninput={(e) => typed(e.target.value)}>
  <Select hidden={!fx.show.type} label={t("Type")} value={fx.effective.type} options={fx.options.type} all={fx.all.type} neutral={fx.neutral.type} onchange={(v) => { f.type = v; }} title={t("Planet type")} />
  <Select hidden={!fx.show.star} label={t("Star")} value={fx.effective.star} options={fx.options.star} all={fx.all.star} neutral={fx.neutral.star} onchange={(v) => { f.star = v; }} title={t("The colour of the system's star")} />
  <Select hidden={!fx.show.weather} label={label("WEATHER_L", "Weather")} value={fx.effective.weather} options={fx.options.weather} all={fx.all.weather} neutral={fx.neutral.weather} onchange={(v) => { f.weather = v; }} />
  <Select hidden={!fx.show.sentinel} label={label("SENTINELS_L", "Sentinels")} value={fx.effective.sentinel} options={fx.options.sentinel} all={fx.all.sentinel} neutral={fx.neutral.sentinel} onchange={(v) => { f.sentinel = v; }} />
  <Select hidden={!fx.show.flora} label={label("FLORA_L", "Flora")} value={fx.effective.flora} options={fx.options.flora} all={fx.all.flora} neutral={fx.neutral.flora} onchange={(v) => { f.flora = v; }} />
  <Select hidden={!fx.show.fauna} label={label("FAUNA_L", "Fauna")} value={fx.effective.fauna} options={fx.options.fauna} all={fx.all.fauna} neutral={fx.neutral.fauna} onchange={(v) => { f.fauna = v; }} />
  <Select hidden={!fx.show.resource} label={label("RESOURCES_L", "Resources")} value={fx.effective.resource} options={fx.options.resource} all={fx.all.resource} neutral={fx.neutral.resource} onchange={(v) => { f.resource = v; }} title={t("Planets that have this on them")} />
  <Check hidden={!fx.show.bases} label={t("Bases")} value={fx.effective.bases} onchange={(v) => { f.bases = v; }} title={t("Only planets with your bases")} />
  <Check hidden={!fx.show.found} label={t("Found by you")} value={fx.effective.found} onchange={(v) => { f.found = v; }} title={t("Only planets where you found something")} />
</div>
{#if gamesave.report?.planets?.length}<div class="count">{tn(rows.length, "{n} planet|{n} planets")}{rows.length !== all.length ? ` ${t("of {n}", { n: all.length })}` : ""}</div>{/if}

{#if !gamesave.available || !gamesave.report}
  <section class="card">
    <p class="muted">{gamesave.error || (gamesave.available ? t("No game saves found.") : t("This page reads your game save through the desktop program, and there is none to read here."))}</p>
  </section>
{:else if !gamesave.report.planets?.length}
  <section class="card"><p class="muted">{t("The save shows no planets you have visited.")}</p></section>
{:else}
  <div class="split split-planets">
    <div class="main">
      <List bind:this={list} {rows} keep {keyOf} empty={t("No planets match this search.")} onSelect={(p) => { capture(); cur = p; }} columns={[
        { title: t("Planet"), cell: nameCell, cls: "strong", sort: shown },
        { title: t("System"), ghost: true, sort: (p) => p.system_name || hex3(p.system) },
        { title: t("Planet type"), cell: typeCell, cls: "clip w190", sort: kindOf },
        { title: label("WEATHER_L", "Weather"), text: (p) => unknown(p) ? t("Data not determined") : textOf(p.weather_key), cls: "wide-only clip w170 muted", sort: (p) => textOf(p.weather_key) },
        { title: label("SENTINELS_L", "Sentinels"), text: (p) => textOf(p.sentinel_key), cls: "wide-only clip w150 muted", sort: (p) => textOf(p.sentinel_key) },
        { title: label("FAUNA_L", "Fauna"), text: (p) => textOf(p.fauna_key), cls: "wide-only clip w130 muted", sort: (p) => p.fauna_key },
        { title: t("Found by you"), cell: foundCell, cls: "wide-only", sort: (p) => p.fauna + p.flora + p.minerals },
        { title: label("RESOURCES_L", "Resources"), cell: hintCell, cls: "wide-only", sort: (p) => hintsOf(p).length },
        { title: typeLabel("Substance"), cell: subsCell, cls: "wide-only", sort: (p) => subName(p, 0) },
        { title: t("Bases"), cell: baseCell, cls: "wide-only", sort: (p) => p.bases.length },
        { title: t("Last seen"), cell: dates, cls: "num muted", sort: (p) => p.seen },
      ]} />
    </div>
    <aside class="detail" use:swap={{ key: cur ? keyOf(cur) : "", peel: true }}>
      {#if cur}
        {@const p = cur}
        <div class="head">
          <div class="who">
            <h2>{nameOf(p)}</h2>
            <p class="muted sub">{t("{ordinal} in the system", { ordinal: ordinal(p.planet), n: p.planet })}{#if p.system_name}{" · "}<span style:color={p.star != null ? `var(--p-${STAR[p.star]})` : undefined}>{p.system_name}</span>{/if}</p>
            {#if kindOf(p)}<div class="ic-chips"><span class="pill">{#if EMBLEM[p.biome]}<span class="ti"><ItemIcon id="BIOME_{EMBLEM[p.biome]}" size={24} /></span>{/if}{kindOf(p)}</span></div>{/if}
          </div>
          {#if globeUrl(p)}<div class="globe"><img src={globeUrl(p)} alt="" width="170" height="170" /></div>{/if}
        </div>

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
  .cnt b { position: absolute; right: -6px; bottom: -4px; padding: 0 5px; border-radius: 999px; font-size: 0.72rem; font-weight: 600; line-height: 1.4; white-space: nowrap; font-variant-numeric: tabular-nums; color: #fff; background: rgb(8 12 24 / 0.78); }
  .two { display: flex; flex-direction: column; line-height: 1.2; min-width: 0; }
  .two small { font-size: 0.74rem; font-weight: 400; }
  /* narrow text columns: a long text is cut with an ellipsis (the whole of it is in the tooltip) */
  .main :global(td.w130) { max-width: 130px; }
  .main :global(td.w150) { max-width: 150px; }
  .main :global(td.w170) { max-width: 170px; }
  .main :global(td.w190) { max-width: 190px; }
  /* the name and its lines on the left, the globe on the right */
  .head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 4px; }
  .who { min-width: 0; flex: 1 1 auto; }
  .who h2 { margin: 0; overflow-wrap: anywhere; }
  /* the picture has room around the globe for its rings: the planet is 61% of it (104 px of 170), the rest hangs over its box */
  .globe { position: relative; flex: none; width: 104px; height: 104px; margin: 0 14px 0 0; line-height: 0; }
  .globe img { position: absolute; left: -33px; top: -33px; width: 170px; height: 170px; }
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
