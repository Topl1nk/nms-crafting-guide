<script module>
  import { N_ } from "../lib/i18n.js";

  // What you typed and filtered by outlives a visit, as on the other pages.
  const st = { text: "", planet: 0, kind: "", origin: "" };

  const FIELD_NAMES = [N_("planet"), N_("system"), N_("height (Y)"), N_("width (Z)"), N_("length (X)")]; // English keys for t()
  const KINDS = {
    "multi-tool": N_("multi-tool"), starship: N_("starship"), exotic: N_("exotic starship"), freighter: N_("freighter"),
    base: N_("base"), planet: N_("planet"), other: N_("other"),
  };
</script>

<script>
  // Portal addresses (#/portals?code=&kind=): a converter between glyphs and
  // galactic coordinates, a dial, and the saved list -- shipped ones from
  // data/locations.json, and the visitor's own under `nms-items:locations`.
  import Glyph from "../components/Glyph.svelte";
  import Reset from "../components/Reset.svelte";
  import Select from "../components/Select.svelte";
  import { applyFacets, facets } from "../lib/facets.js";
  import GlyphStrip from "../components/GlyphStrip.svelte";
  import List from "../components/List.svelte";
  import {
    Address, AddressError, GLYPH_FIELD, looksLikeAddress,
  } from "../lib/core.js";
  import { D, galaxyName } from "../lib/data.js";
  import { ordinal, t } from "../lib/i18n.js";
  import { setKeys } from "../lib/keys.js";
  import { arrival } from "../lib/router.svelte.js";
  import { local } from "../lib/local.js";
  import { copy, toast } from "../lib/toast.svelte.js";
  import { debounce } from "../lib/util.js";

  const { params } = arrival();
  // A link opens its own view (its kind, its code), not one narrowed by what was set last time.
  const linked = params.size > 0;
  if (linked) { st.kind = params.get("kind") ?? ""; st.origin = ""; st.text = params.get("code") ?? ""; }

  const kindName = (k) => t(KINDS[k] ?? k);
  const kinds = [["", t("everything")], ...D.portals.kinds.map((k) => [k, kindName(k)])];
  const origins = [["", t("mine and others'")], ["mine", t("my finds")], ["shared", t("others'")]];
  const planets = [...Array(16).keys()].map((i) => [i, `${i.toString(16).toUpperCase()} — ${t("{ordinal} in the system", { ordinal: ordinal(i + 1), n: i + 1 })}`]);

  $effect(() => { Object.assign(st, { kind, origin }); });
  let planet = $state(st.planet);
  let kind = $state(st.kind);
  let origin = $state(st.origin);
  let current = $state.raw(null);
  let error = $state("");
  let search = $state("");
  let cur = $state.raw(null);
  let dialOpen = $state(false);
  let dialled = $state("");
  let list = $state();
  let input = $state();
  let saveForm = $state();

  // Shipped addresses come from data/locations.json; the ones saved here live
  // in this browser.
  let mine = $state.raw(local.get("locations", []));
  function setMine(rows) {
    mine = rows;
    local.set("locations", rows);
  }

  const all = $derived.by(() => {
    const clean = (l) => ({ kind: "other", origin: "mine", galaxy: 1, ...l, code: l.code.replace(/[^0-9A-Fa-f]/g, "").toUpperCase() });
    const shipped = D.portals.locations.map((l) => ({ ...clean(l), local: false }));
    return [...shipped, ...mine.map((l, i) => ({ ...clean(l), local: true, localIndex: i }))];
  });

  const base = $derived.by(() => {
    const terms = search.toLowerCase().split(/\s+/).filter(Boolean);
    return all.filter((l) => terms.every((w) => [l.name, t(l.name), l.kind, kindName(l.kind), l.origin, l.detail, t(l.detail), l.where, t(l.where), l.source, t(l.source), l.code].join(" ").toLowerCase().includes(w)));
  });
  const defs = $derived([
    { key: "kind", options: kinds, neutral: "", test: (l, v) => !v || l.kind === v },
    { key: "origin", options: origins, neutral: "", test: (l, v) => !v || l.origin === v },
  ]);
  const fx = $derived(facets(base, defs, { kind, origin }));
  const rows = $derived(applyFacets(base, defs, fx.effective));
  const saved = $derived(current ? all.filter((l) => l.code === current.code) : []);
  const curAddress = $derived.by(() => {
    try { return cur ? Address.fromCode(cur.code) : null; } catch { return null; }
  });

  // A colon means a galactic address, twelve hex digits a portal code;
  // anything that is neither searches the saved list instead.
  function convert() {
    const text = st.text.trim();
    current = null; error = ""; search = "";
    if (!text) return;
    try {
      current = Address.parse(text, planet);
      planet = st.planet = current.planet;
    } catch (exc) {
      if (!(exc instanceof AddressError)) throw exc;
      if (looksLikeAddress(text)) error = exc.message; else search = text;
    }
  }

  function setText(text) {
    st.text = text;
    if (input) input.value = text;
    convert();
  }

  function load(code) {
    setText(code);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const typed = debounce((value) => { st.text = value; convert(); });

  function changePlanet() {
    st.planet = planet;
    if (current) setText(current.withPlanet(planet).code);
    else convert();
  }

  function save(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const row = {
      name: f.get("name").trim() || t("untitled"),
      code: current.code,
      kind: f.get("kind"),
      origin: f.get("origin"),
      galaxy: Math.min(256, Math.max(1, Number(f.get("galaxy")) || 1)),
      detail: f.get("detail").trim(),
      where: f.get("where").trim(),
      source: f.get("source").trim(),
      added: new Date().toISOString().slice(0, 10),
    };
    setMine([...mine, row]);
    toast(t("Saved: {name}", { name: row.name }));
  }

  function remove(index) {
    if (!confirm(t("Delete this address from the saved ones?"))) return;
    setMine(mine.filter((_, i) => i !== index));
  }

  const copyCode = (text) => copy(text, text.includes(":") ? t("galactic address") : t("portal code"));

  // The dial: sixteen symbols in dial order, two rows of eight, so picking
  // here is the same motion as dialling at the portal.
  function toggleDial() {
    dialOpen = !dialOpen;
    if (dialOpen) dialled = "";
  }
  function dialPick(digit) {
    if (dialled.length < 12) dialled += digit.toUpperCase();
  }
  const next = $derived(dialled.length < 12 ? t(FIELD_NAMES[GLYPH_FIELD[dialled.length]]) : "");

  setKeys({
    get list() { return list; },
    get search() { return input; },
    enter: () => { const l = list?.current(); if (l) load(l.code); },
    escape: () => setText(""),
    key: (e) => {
      if (!dialOpen) return false;
      if (/^[0-9a-fA-F]$/.test(e.key)) { dialPick(e.key); return true; }
      if (e.key === "Backspace") { dialled = dialled.slice(0, -1); return true; }
      return false;
    },
  });

  convert();
</script>

{#snippet grouped(a)}
  {#each a.grouped as part, i (i)}{i ? " " : ""}<b class="f{i}">{part}</b>{/each}
{/snippet}

{#snippet found(l)}
  {#if l.origin === "mine"}<span class="ok">{t("mine")}</span>{:else}{t("others'")}{/if}
{/snippet}

{#snippet codeCell(l)}<code>{l.code}</code>{/snippet}

{#snippet primer()}
  <h3>{t("Paste an address into the field above")}</h3>
  <div class="fmts">
    <button class="fmt" onclick={() => setText("40E907FF0D6B")}><span class="muted small">{t("portal code")}</span><code>40E907FF0D6B</code></button>
    <button class="fmt" onclick={() => setText("056A:0086:07EF:00E9")}><span class="muted small">{t("galactic address")}</span><code>056A:0086:07EF:00E9</code></button>
    <div class="fmt"><span class="muted small">{t("link")}</span><code>nmsportals.github.io/…</code></div>
  </div>
  <h3>{t("What the twelve glyphs mean")}</h3>
  <p class="code-big"><b class="f0">p</b> <b class="f1">SSS</b> <b class="f2">YY</b> <b class="f3">ZZZ</b> <b class="f4">XXX</b></p>
  <p><span class="f0">{t("planet")}</span>, <span class="f1">{t("system")}</span>, {t("then a point in the galaxy:")}
  <span class="f2">{t("height")}</span>, <span class="f3">{t("width")}</span>, <span class="f4">{t("length")}</span>. {t("In a portal code 0,0,0 is the centre of the galaxy, in a galactic address the count starts from a corner, so two addresses of one place do not look alike.")}</p>
  <h3>{t("How to dial")}</h3>
  <p>{t("On a portal the glyphs always stand in the same order: 0–9, then A–F.")} {t("A digit is a place on the disc: A is the 11th glyph.")} {t("The same twelve glyphs lead to different stars in each of the 256 galaxies, so saved addresses name the galaxy.")}</p>
{/snippet}

<div class="fbar">
  <h1><span>{t("Portals")}</span></h1>
  <Reset active={Boolean(kind || origin)} onclick={() => { kind = ""; origin = ""; }} />
  <input class="search" style="max-width:520px" type="search" placeholder={t("Portal code, galactic address, link — or search the saved ones")} value={st.text}
    autocomplete="off" spellcheck="false" bind:this={input} oninput={(e) => typed(e.target.value)}>
  <Select label={t("Planet")} bind:value={planet} options={planets} onchange={changePlanet} title={t("Which planet of the system, by count")} />
  <Select hidden={!(fx.show.kind)} label={t("What")} value={fx.effective.kind} options={fx.options.kind} all={fx.all.kind} neutral={fx.neutral.kind} onchange={(v) => { kind = v; }} />
  <Select hidden={!(fx.show.origin)} label={t("Whose")} value={fx.effective.origin} options={fx.options.origin} all={fx.all.origin} neutral={fx.neutral.origin} onchange={(v) => { origin = v; }} />
  <button class="btn" onclick={toggleDial}>{t("Dial by glyphs")}</button>
</div>
{#if dialOpen}
  <div class="card dial">
    <div class="dial-head">
      <b>{t("Dialling an address")}</b>
      <span class="muted small">{t("Click the glyphs in order or type the digits. Backspace undoes.")}</span>
      <button class="link" onclick={() => { dialOpen = false; }}>{t("close")}</button>
    </div>
    <div class="dial-code">
      {#each Array(12) as _, i (i)}
        {#if i < dialled.length}
          <span class="slot f{GLYPH_FIELD[i]}"><Glyph digit={dialled[i]} /></span>
        {:else}
          <span class="slot empty f{GLYPH_FIELD[i]}"></span>
        {/if}
      {/each}
    </div>
    <p class="small">
      {#if next}<span class="muted">{t("glyph {n} of 12 — {field}", { n: dialled.length + 1, field: next })}</span>
      {:else}<span class="ok">{t("all twelve")}</span> <button class="btn" onclick={() => { load(dialled); dialOpen = false; }}>{t("Done")}</button>{/if}
      {#if dialled}<button class="link" onclick={() => { dialled = dialled.slice(0, -1); }}>{t("undo")}</button>{/if}
    </p>
    <div class="dial-grid">
      {#each D.glyphs as gl (gl.hex)}
        <button class="dial-key" title={t(gl.name)} onclick={() => dialPick(gl.hex)}><Glyph digit={gl.hex} /><span><b>{gl.hex}</b> {t(gl.name)}</span></button>
      {/each}
    </div>
  </div>
{/if}
<div class="split split-portals">
  <div class="main">
    <List bind:this={list} {rows} keep empty={t("No saved addresses match this search.")}
      onSelect={(l) => { cur = l; }} onEnter={(l) => load(l.code)} columns={[
        { title: t("Name"), text: (l) => t(l.name), cls: "strong", sort: (l) => l.name },
        { title: t("What"), text: (l) => kindName(l.kind), sort: (l) => kindName(l.kind) },
        { title: t("Whose"), cell: found, sort: (l) => l.origin },
        { title: t("Address"), cell: codeCell, cls: "wide-only", sort: (l) => l.code },
        { title: t("What is there"), text: (l) => t(l.detail), cls: "muted wide-only clip", sort: (l) => l.detail },
      ]} />
    {#if cur && curAddress && rows.length}
      {@const l = cur}
      {@const a = curAddress}
      <aside class="detail pick">
        <div class="pick-head">
          <h2>{t(l.name)}</h2>
          <span class="muted small">{kindName(l.kind)}</span>
          {#if l.origin === "mine"}<span class="ok small">{t("my find")}</span>{:else}<span class="hl2 small">{t("someone else's address")}</span>{/if}
          <span class="pick-acts">
            <button class="btn" onclick={() => load(l.code)}>{t("To the converter")}</button>
            <button class="btn" onclick={() => copyCode(l.code)}>{t("Copy")}</button>
            {#if l.local}<button class="btn danger" onclick={() => remove(l.localIndex)}>{t("Delete")}</button>{/if}
          </span>
        </div>
        <div class="pick-body">
          <div class="pick-glyphs">
            <p class="pick-code"><code>{@render grouped(a)}</code> <span class="muted">{a.galactic}</span> <span class="muted">· {l.galaxy || 1}. {galaxyName(l.galaxy || 1)}</span></p>
            <GlyphStrip code={a.code} />
          </div>
          <div class="pick-text">
            {#if l.detail}<p><span class="hl2">{t("What is there")}</span> {t(l.detail)}</p>{/if}
            {#if l.where}<p><span class="hl2">{t("How to find it")}</span> {t(l.where)}</p>{/if}
            <p class="muted small">{[t(l.source), l.added].filter(Boolean).join(" · ")}</p>
          </div>
        </div>
      </aside>
    {/if}
  </div>
  <section class="readout">
    {#if !current}
      {#if error}<p class="err">{error}</p>{/if}
      {@render primer()}
    {:else}
      {@const a = current}
      {@const [x, y, z] = a.voxel}
      <p class="code-big">{@render grouped(a)}</p>
      <GlyphStrip code={a.code} names />
      <dl>
        <dt>{t("Portal code")}</dt><dd><b>{a.code}</b> <button class="link" onclick={() => copyCode(a.code)}>{t("copy")}</button></dd>
        <dt>{t("Galactic")}</dt><dd><b>{a.galactic}</b> <button class="link" onclick={() => copyCode(a.galactic)}>{t("copy")}</button></dd>
        <dt>{t("Point")}</dt><dd>X {x >= 0 ? "+" : ""}{x} · Y {y >= 0 ? "+" : ""}{y} · Z {z >= 0 ? "+" : ""}{z} <span class="muted">{t("from the centre")}</span></dd>
        <dt>{t("Planet")}</dt><dd>{t("{ordinal} in the system", { ordinal: ordinal(a.planet + 1), n: a.planet + 1 })} <span class="muted">({t("glyph {glyph}", { glyph: a.planet.toString(16).toUpperCase() })})</span></dd>
        <dt>{t("System")}</dt><dd>0x{a.grouped[1]} <span class="muted">({a.system})</span></dd>
        <dt>{t("Link")}</dt><dd><a href={a.shareLink} target="_blank" rel="noopener">{a.shareLink}</a></dd>
      </dl>
      {#if a.system > D.portals.max_system}
        <p class="warn">! {t("The system number 0x{system} is above the maximum 0x{max} — check the address", { system: a.grouped[1], max: D.portals.max_system.toString(16).toUpperCase() })}</p>
      {/if}
      {#if saved.length}
        <h3 class="ok">{t("Already saved")}</h3>
        <ul>{#each saved as l}<li>{t(l.name)} <span class="muted">{kindName(l.kind)}, {l.origin === "mine" ? t("mine") : t("others'")}, {t("galaxy")} {l.galaxy || 1}. {galaxyName(l.galaxy || 1)}</span></li>{/each}</ul>
      {/if}
      <!-- Keyed on the address and the saved count, so the form starts empty
           for each new address and after each save. -->
      {#key `${a.code}/${saved.length}`}
        <details class="save" open={!saved.length}>
          <summary>{t("Save this address")}</summary>
          <form class="form" bind:this={saveForm} onsubmit={save}>
            <label>{t("Name")} <input name="name" required placeholder={t("what you will call it")}></label>
            <label>{t("What is it")} <select name="kind" value="other">
              {#each D.portals.kinds as k (k)}<option value={k}>{kindName(k)}</option>{/each}
            </select></label>
            <label>{t("Where the address is from")} <select name="origin" value="mine">
              <option value="mine">{t("mine — I was there")}</option>
              <option value="shared">{t("someone else's — from a catalogue or a friend")}</option>
            </select></label>
            <label>{t("Galaxy")} <input name="galaxy" type="number" min="1" max="256" value="1"></label>
            <label class="wide">{t("What is there")} <input name="detail" placeholder={t("class, type, number of slots")}></label>
            <label class="wide">{t("How to find it")} <input name="where" placeholder={t("how to find it on the spot")}></label>
            <label class="wide">{t("Source")} <input name="source" placeholder={t("who told you or where you found it")}></label>
            <div class="wide form-actions">
              <button class="btn primary">{t("Save")}</button>
            </div>
          </form>
        </details>
      {/key}
    {/if}
  </section>
</div>

<style>
  .split-portals { grid-template-columns: minmax(0, 1fr) clamp(400px, 28%, 480px); }
  /* The saved list takes the height with the card of the chosen address under it; the converter has the same width as the cards of Craft. */
  .main { display: flex; flex-direction: column; gap: 12px; min-width: 0; min-height: 0; align-self: stretch; }
  .main :global(.list) { flex: 1 1 0; height: auto; max-height: none; overflow: auto; min-height: 160px; }
  .readout { align-self: stretch; }
  .pick { flex: none; padding: 10px 14px 12px; }
  .pick-head { display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 10px; margin-bottom: 4px; }
  .pick-head h2 { margin: 0; font-size: 1.05rem; }
  .pick-acts { margin-left: auto; display: flex; gap: 6px; align-self: center; }
  .pick-acts .btn { height: 30px; padding: 0 12px; font-size: 0.82rem; border-radius: 9px; }
  .pick-body { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 4px 18px; align-items: start; }
  .pick-code { margin: 0; font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .pick-glyphs :global(.glyphs) { margin: 4px 0 0; gap: 2px; }
  .pick-glyphs :global(figcaption) { font-size: 0.62rem; }
  .pick-text p { margin: 0 0 3px; font-size: 0.88rem; line-height: 1.35; }
  @media (max-width: 1000px) { .split-portals { grid-template-columns: minmax(0, 1fr); } }
  @media (max-width: 1300px) { .pick-body { grid-template-columns: minmax(0, 1fr); } }
  .fmts { display: grid; gap: 6px; margin-bottom: 8px; }
  .fmt {
    display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 44px; padding: 0 14px; text-align: left;
    background: var(--p-raised); border: 1px solid var(--p-outline); border-radius: 12px; color: var(--p-text); font: inherit;
  }
  button.fmt { cursor: pointer; }
  button.fmt:hover { border-color: var(--p-edge-accent); }
  .fmt code { color: var(--p-accent-ink); background: none; padding: 0; }

  .dial { margin: 0 0 12px; }
  .dial-head { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; }
  .dial-head .link { margin-left: auto; }
  .dial-code { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 4px; max-width: 600px; margin: 10px 0 4px; }
  .slot { aspect-ratio: 1; border-bottom: 2px solid currentColor; }
  .slot.empty { opacity: 0.35; }
  .dial-grid { display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 6px; max-width: 760px; }
  .dial-key {
    background: var(--p-raised);
    border: 1px solid var(--p-outline);
    border-radius: 10px;
    padding: 6px 4px 4px;
    cursor: pointer;
    color: var(--p-text);
    min-width: 0;
  }
  .dial-key:hover { border-color: var(--p-edge-accent); color: var(--p-accent-ink); }
  .dial-key :global(.glyph) { width: 70%; margin: 0 auto; }
  .dial-key span { display: block; font-size: 0.7rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  details.save { margin-top: 14px; border-top: 1px solid var(--p-outline); padding-top: 10px; }
  details.save summary { cursor: pointer; color: var(--p-accent-ink); font-weight: 700; font-size: 0.95rem; }
  .form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 12px; margin-top: 10px; }
  .form label { display: flex; flex-direction: column; gap: 3px; color: var(--p-faint); font-size: 0.85em; min-width: 0; }
  .form label.wide { grid-column: 1 / -1; }
  .form input, .form select { width: 100%; font-size: 1rem; }
  .form .btn { justify-self: start; }
  .form .form-actions { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 8px; }

  @media (max-width: 1000px) {
    .split-portals { grid-template-columns: minmax(0, 1fr); }
  }
  @media (max-width: 640px) {
    .dial-code { grid-template-columns: repeat(6, minmax(0, 1fr)); }
    .dial-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .form { grid-template-columns: minmax(0, 1fr); }
  }
</style>





