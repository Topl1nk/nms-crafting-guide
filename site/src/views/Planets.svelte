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
  import List from "../components/List.svelte";
  import { Address } from "../lib/core.js";
  import { D, galaxyName } from "../lib/data.js";
  import { gamesave } from "../lib/gamesave.svelte.js";
  import { ordinal, t, tn, ui } from "../lib/i18n.js";
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
    return all.filter((p) => terms.every((w) => [p.name, p.system_name, p.code, hex3(p.system), galaxyName(p.galaxy)].join(" ").toLowerCase().includes(w)));
  });

  const hex3 = (n) => `0x${n.toString(16).toUpperCase().padStart(3, "0")}`;
  const when = (ts) => (ts ? new Date(ts * 1000).toLocaleDateString(ui.locale, { year: "numeric", month: "short", day: "numeric" }) : "");
  // Planet 0 of an address is a place in the system (a base can stand there), not one of its planets.
  const nameOf = (p) => p.name || (p.planet ? t("Unnamed planet") : t("A place in the system"));
  const keyOf = (p) => `${p.galaxy}/${p.code}`;
  const typeName = (id) => (TYPES[id] ? t(TYPES[id]) : t("{colour} type", { colour: t(STARS[id] ?? id) }));

  const chosen = $derived(cur?.planet && cur.biome ? D.biomes.types.find((b) => b.id === cur.biome) : null); // a type the game's table lists
  const address = $derived.by(() => { try { return cur ? Address.fromCode(cur.code) : null; } catch { return null; } });

  const typed = debounce((value) => { st.text = value; search = value; });

  setKeys({
    get list() { return list; },
    get search() { return input; },
    escape: () => { st.text = search = ""; if (input) input.value = ""; },
  });
</script>

{#snippet dates(p)}{when(p.seen)}{/snippet}
{#snippet nameCell(p)}{p.name || ""}{#if !p.name}<span class="muted">{nameOf(p)}</span>{/if}{/snippet}

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
        { title: t("Name"), cell: nameCell, cls: "strong", sort: (p) => p.name },
        { title: t("System"), text: (p) => p.system_name || hex3(p.system), sort: (p) => p.system_name || hex3(p.system) },
        { title: t("Galaxy"), text: (p) => galaxyName(p.galaxy), cls: "wide-only", sort: (p) => p.galaxy },
        { title: t("Last seen"), cell: dates, cls: "muted", sort: (p) => p.seen },
      ]} />
    </div>
    <section class="readout">
      {#if cur}
        {@const p = cur}
        <h2>{nameOf(p)}</h2>
        {#if p.name_source === "generated" || p.system_name_source === "generated"}<p class="muted small">{t("The names the save does not hold are calculated from the planet's seed and address, the way the game makes them up. A name you gave in the game, or a change in how the game names things, may make them differ.")}</p>{/if}
        <p class="muted">{p.planet ? t("{ordinal} in the system", { ordinal: ordinal(p.planet), n: p.planet }) : t("A place in the system, not a planet")}{p.system_name ? ` · ${p.system_name}` : ""} · {p.galaxy}. {galaxyName(p.galaxy)}</p>
        <GlyphStrip code={p.code} />
        <dl>
          <dt>{t("Portal code")}</dt><dd><b>{p.code}</b> <button class="link" onclick={() => copy(p.code, t("portal code"))}>{t("copy")}</button> · <a href="#/portals?code={p.code}">{t("To the converter")}</a></dd>
          {#if address}<dt>{t("Galactic")}</dt><dd><b>{address.galactic}</b></dd>{/if}
          <dt>{t("System")}</dt><dd>{hex3(p.system)}</dd>
          {#if p.found}<dt>{t("First found")}</dt><dd>{when(p.found)}</dd>{/if}
          <dt>{t("Last seen")}</dt><dd>{when(p.seen)}</dd>
        </dl>

        <h3>{t("What you found here")}</h3>
        <p>{t("Flora")}: <b>{p.flora}</b> · {t("Fauna")}: <b>{p.fauna}</b> · {t("Minerals")}: <b>{p.minerals}</b></p>
        <h3>{t("Bases")}</h3>
        {#if p.bases.length}
          <ul>{#each p.bases as name}<li>{name || t("Unnamed base")}</li>{/each}</ul>
        {:else}<p class="muted">—</p>{/if}

        {#if p.planet}
        <h3>{t("Planet type")}</h3>
        {#if chosen}
          <p><b>{typeName(chosen.id)}</b> <span class="muted small">{t("Read from the save.")}</span></p>
          <p>{tn(chosen.variants, "{n} terrain variant|{n} terrain variants")}</p>
          <p class="muted small">{t("Share of the planets around a star of each colour, by the game's weights:")}</p>
          <ul class="shares">
            {#each D.biomes.stars.filter((s) => chosen.stars[s]) as star (star)}<li><span>{t(STARS[star] ?? star)}</span> <b>{chosen.stars[star]}%</b></li>{/each}
          </ul>
        {:else}<p class="muted">—</p>{/if}
        {/if}

        <h3>{t("Resources")}</h3>
        <p class="warn">{t("The game files do not say which resources a planet has. The game works them out from the planet's seed, and the save does not keep them, so none are listed here.")}</p>
      {/if}
    </section>
  </div>
{/if}

<style>
  .split-planets { grid-template-columns: minmax(0, 1fr) clamp(340px, 32%, 460px); }
  .main { min-width: 0; min-height: 0; align-self: stretch; display: flex; flex-direction: column; }
  .main :global(.list) { flex: 1 1 0; height: auto; max-height: none; overflow: auto; min-height: 160px; }
  .readout { align-self: stretch; }
  .readout h2 { margin: 0 0 4px; font-size: 1.1rem; }
  .readout h3 { margin: 16px 0 6px; font-size: 0.95rem; }
  dl { display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: 4px 12px; margin: 10px 0 0; }
  dt { color: var(--p-faint); }
  dd { margin: 0; }
  .shares { display: flex; flex-wrap: wrap; gap: 6px 16px; list-style: none; padding: 0; margin: 4px 0 0; }
  .shares li { margin: 0; }
  @media (max-width: 1000px) { .split-planets { grid-template-columns: minmax(0, 1fr); } }
</style>
