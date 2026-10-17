<script module>
  // What you typed and filtered by outlives a visit, as on the other pages.
  const st = { text: "", planet: 0, kind: "", origin: "" };

  const FIELD_NAMES = ["planet", "system", "height (Y)", "width (Z)", "length (X)"];
</script>

<script>
  // Portal addresses (#/portals?code=&kind=): a converter between glyphs and
  // galactic coordinates, a dial, and the saved list -- shipped ones from
  // data/locations.json, and the visitor's own under `nms-items:locations`.
  import Glyph from "../components/Glyph.svelte";
  import GlyphStrip from "../components/GlyphStrip.svelte";
  import List from "../components/List.svelte";
  import {
    Address, AddressError, GLYPH_FIELD, looksLikeAddress, ordinal,
  } from "../lib/core.js";
  import { D, galaxyName, REPO_URL } from "../lib/data.js";
  import { setKeys } from "../lib/keys.js";
  import { arrival } from "../lib/router.svelte.js";
  import { local } from "../lib/local.js";
  import { copy, toast } from "../lib/toast.svelte.js";
  import { debounce } from "../lib/util.js";

  const { params } = arrival();
  if (params.has("kind")) st.kind = params.get("kind");
  if (params.has("code")) st.text = params.get("code");

  const kinds = [["", "everything"], ...D.portals.kinds.map((k) => [k, k])];
  const origins = [["", "mine and shared"], ["mine", "my finds"], ["shared", "shared"]];
  const planets = [...Array(16).keys()].map((i) => [i, `${i.toString(16).toUpperCase()} - ${ordinal(i + 1)}`]);

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
  // in this browser, and Export hands them over in the same shape for the file.
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

  const rows = $derived.by(() => {
    const terms = search.toLowerCase().split(/\s+/).filter(Boolean);
    return all.filter((l) =>
      (!kind || l.kind === kind) &&
      (!origin || l.origin === origin) &&
      terms.every((t) => [l.name, l.kind, l.origin, l.detail, l.where, l.source, l.code].join(" ").toLowerCase().includes(t)));
  });

  const saved = $derived(current ? all.filter((l) => l.code === current.code) : []);
  const curAddress = $derived.by(() => {
    try { return cur ? Address.fromCode(cur.code) : null; } catch { return null; }
  });

  // A GitHub issue on the "Share a portal address" form, pre-filled. The
  // form's field ids are the query keys (.github/ISSUE_TEMPLATE/
  // portal-address.yml); a bot checks what arrives with the same rules as this
  // page and the TUI.
  function shareIssueUrl(l = {}) {
    const q = new URLSearchParams({ template: "portal-address.yml", title: `Portal: ${l.name || ""}`.trim() });
    for (const key of ["name", "code", "galaxy", "kind", "detail", "where"]) {
      if (l[key]) q.set(key, String(l[key]));
    }
    return `${REPO_URL}/issues/new?${q}`;
  }

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

  function share() {
    const row = Object.fromEntries([...new FormData(saveForm)].map(([k, v]) => [k, String(v).trim()]));
    window.open(shareIssueUrl({ ...row, code: current.code }), "_blank", "noopener");
  }

  function save(e) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const row = {
      name: f.get("name").trim() || "unnamed",
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
    toast(`Saved ${row.name}`);
  }

  function remove(index) {
    if (!confirm("Delete this saved address from this browser?")) return;
    setMine(mine.filter((_, i) => i !== index));
  }

  function exportMine() {
    if (!mine.length) { toast("Nothing saved in this browser yet"); return; }
    const blob = new Blob([`${JSON.stringify(mine, null, 1)}\n`], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "nms-locations.json";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const copyCode = (text) => copy(text, text.includes(":") ? "the galactic address" : "the portal code");

  // The dial: sixteen symbols in dial order, two rows of eight, so picking
  // here is the same motion as dialling at the portal.
  function toggleDial() {
    dialOpen = !dialOpen;
    if (dialOpen) dialled = "";
  }
  function dialPick(digit) {
    if (dialled.length < 12) dialled += digit.toUpperCase();
  }
  const next = $derived(dialled.length < 12 ? FIELD_NAMES[GLYPH_FIELD[dialled.length]] : "");

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
  {#if l.origin === "mine"}<span class="ok">mine</span>{:else}shared{/if}{#if l.local}{" "}<span class="tag">here</span>{/if}
{/snippet}

{#snippet codeCell(l)}<code>{l.code}</code>{/snippet}

{#snippet primer()}
  <h3>Paste either form above</h3>
  <p>It converts as you type.</p>
  <dl>
    <dt>portal code</dt><dd><code>40E907FF0D6B</code><div class="muted small">12 hex digits, one per glyph</div></dd>
    <dt>galactic address</dt><dd><code>056A:0086:07EF:00E9</code><div class="muted small">what a signal booster shows</div></dd>
    <dt>share link</dt><dd><span class="muted">a nmsportals.github.io URL</span></dd>
  </dl>
  <p class="muted">Type anything else and it searches the saved addresses.</p>
  <h3>What the twelve glyphs are</h3>
  <p class="code-big"><b class="f0">p</b> <b class="f1">SSS</b> <b class="f2">YY</b> <b class="f3">ZZZ</b> <b class="f4">XXX</b></p>
  <p><span class="f0">planet</span>, <span class="f1">system index</span>, then the voxel as
  <span class="f2">height</span>, <span class="f3">width</span>, <span class="f4">length</span>. Portal coordinates put
  0,0,0 at the centre of the galaxy; a galactic address counts from a corner, which is the whole reason the two do not look alike.</p>
  <h3>Dialling one</h3>
  <p>The 16 glyphs sit on the portal dial in a fixed order, 0-9 then A-F, so the hex digit <i>is</i> the position:
  <b>A</b> is the 11th symbol, every time. You need all 16 unlocked, not twelve.</p>
  <h3>Sharing one</h3>
  <p>The same twelve glyphs point at a different star in each of the 256 galaxies, so an address alone is ambiguous. Saved ones carry their galaxy.</p>
  <h3>Adding yours to the list</h3>
  <p>Convert it here, fill in the form, and press <b>Share on GitHub</b>: it opens an issue with the fields filled in.
  A bot converts the address the same way this page does and replies with the glyphs it read, or what to fix.
  Once accepted it is added to the shared list, credited to you.</p>
{/snippet}

<div class="toolbar">
  <h1 class="view-title">Portal addresses</h1>
  <input type="search" placeholder="/  portal code, galactic address, nmsportals link - or search saved" value={st.text}
    autocomplete="off" spellcheck="false" bind:this={input} oninput={(e) => typed(e.target.value)}>
  <label>Planet <select bind:value={planet} onchange={changePlanet}>
    {#each planets as [i, label] (i)}<option value={i}>{label}</option>{/each}
  </select></label>
  <button class="btn" onclick={toggleDial}>Dial by glyph</button>
</div>
{#if dialOpen}
  <div class="card dial">
    <div class="dial-head">
      <b>Dial an address</b>
      <span class="muted small">Click the symbols in order, or type the hex digit. Backspace undoes.</span>
      <button class="link" onclick={() => { dialOpen = false; }}>close</button>
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
      {#if next}<span class="muted">glyph {dialled.length + 1} of 12 - {next}</span>
      {:else}<span class="ok">all twelve</span> <button class="btn" onclick={() => { load(dialled); dialOpen = false; }}>Use it</button>{/if}
      {#if dialled}<button class="link" onclick={() => { dialled = dialled.slice(0, -1); }}>undo</button>{/if}
    </p>
    <div class="dial-grid">
      {#each D.glyphs as gl (gl.hex)}
        <button class="dial-key" title={gl.name} onclick={() => dialPick(gl.hex)}><Glyph digit={gl.hex} /><span><b>{gl.hex}</b> {gl.name}</span></button>
      {/each}
    </div>
  </div>
{/if}
<div class="split split-portals">
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
        <dt>Portal code</dt><dd><b>{a.code}</b> <button class="link" onclick={() => copyCode(a.code)}>copy</button></dd>
        <dt>Galactic</dt><dd><b>{a.galactic}</b> <button class="link" onclick={() => copyCode(a.galactic)}>copy</button></dd>
        <dt>Voxel</dt><dd>X {x >= 0 ? "+" : ""}{x} · Y {y >= 0 ? "+" : ""}{y} · Z {z >= 0 ? "+" : ""}{z} <span class="muted">from centre</span></dd>
        <dt>Planet</dt><dd>{ordinal(a.planet + 1)} of the system <span class="muted">(glyph {a.planet.toString(16).toUpperCase()})</span></dd>
        <dt>System</dt><dd>0x{a.grouped[1]} <span class="muted">({a.system})</span></dd>
        <dt>Share link</dt><dd><a href={a.shareLink} target="_blank" rel="noopener">{a.shareLink}</a></dd>
      </dl>
      {#if a.system > D.portals.max_system}
        <p class="warn">! system index 0x{a.grouped[1]} is above the 0x{D.portals.max_system.toString(16).toUpperCase()} nmsportals treats as the maximum - check the address</p>
      {/if}
      {#if saved.length}
        <h3 class="ok">Saved</h3>
        <ul>{#each saved as l}<li>{l.name} <span class="muted">{l.kind}, {l.origin}, {l.galaxy || 1}. {galaxyName(l.galaxy || 1)}</span></li>{/each}</ul>
      {/if}
      <!-- Keyed on the address and the saved count, so the form starts empty
           for each new address and after each save. -->
      {#key `${a.code}/${saved.length}`}
        <details class="save" open={!saved.length}>
          <summary>Save this address</summary>
          <form class="form" bind:this={saveForm} onsubmit={save}>
            <label>Name <input name="name" required placeholder="what you call it"></label>
            <label>Kind <select name="kind" value="other">
              {#each D.portals.kinds as k (k)}<option value={k}>{k}</option>{/each}
            </select></label>
            <label>Found <select name="origin" value="mine">
              <option value="mine">mine - I stood there</option>
              <option value="shared">shared - off a catalogue or a friend</option>
            </select></label>
            <label>Galaxy <input name="galaxy" type="number" min="1" max="256" value="1"></label>
            <label class="wide">What is there <input name="detail" placeholder="class, type, slot count"></label>
            <label class="wide">Finding it <input name="where" placeholder="how to find it once you arrive"></label>
            <label class="wide">Source <input name="source" placeholder="who shared it, or where you found it"></label>
            <div class="wide form-actions">
              <button class="btn">Save in this browser</button>
              <button class="btn" type="button" title="Open a GitHub issue with these fields filled in" onclick={share}>Share on GitHub</button>
            </div>
          </form>
        </details>
      {/key}
    {/if}
  </section>
  <section>
    <div class="toolbar sub">
      <label>Kind <select bind:value={kind} onchange={() => { st.kind = kind; }}>
        {#each kinds as [k, label] (k)}<option value={k}>{label}</option>{/each}
      </select></label>
      <label>Found <select bind:value={origin} onchange={() => { st.origin = origin; }}>
        {#each origins as [k, label] (k)}<option value={k}>{label}</option>{/each}
      </select></label>
      <button class="btn" title="Download the addresses saved in this browser, in data/locations.json's shape" onclick={exportMine}>Export mine</button>
    </div>
    <List bind:this={list} class="short" {rows} keep empty="No saved address matches."
      onSelect={(l) => { cur = l; }} onEnter={(l) => load(l.code)} columns={[
        { title: "Name", text: (l) => l.name, cls: "strong" },
        { title: "Kind", text: (l) => l.kind },
        { title: "Found", cell: found },
        { title: "Address", cell: codeCell, cls: "wide-only" },
        { title: "What is there", text: (l) => l.detail, cls: "muted wide-only" },
      ]} />
    <p class="invite">Found somewhere worth the trip? <a href={shareIssueUrl()} target="_blank" rel="noopener">Share it on GitHub</a>:
      a bot checks the address and replies, and accepted ones join this list for everyone.
      Or edit <a href="{REPO_URL}/blob/main/data/locations.json" target="_blank" rel="noopener">data/locations.json</a> in a pull request.</p>
    {#if cur && curAddress && rows.length}
      {@const l = cur}
      {@const a = curAddress}
      <aside class="detail detail-below">
        <h2>{l.name} <span class="muted small">{l.kind}</span>
          {#if l.origin === "mine"}<span class="ok small">found by me</span>{:else}<span class="hl2 small">shared</span>{/if}</h2>
        <p><code>{@render grouped(a)}</code> <span class="muted">{a.galactic}</span></p>
        <p><span class="hl2">Galaxy</span> {l.galaxy || 1}. {galaxyName(l.galaxy || 1)}</p>
        <GlyphStrip code={a.code} />
        {#if l.detail}<p><span class="hl2">There</span> {l.detail}</p>{/if}
        {#if l.where}<p><span class="hl2">Finding it</span> {l.where}</p>{/if}
        <p class="muted small">{[l.source, l.added].filter(Boolean).join(" · ")}</p>
        <div class="actions">
          <button class="btn" onclick={() => load(l.code)}>Open in converter</button>
          <button class="btn" onclick={() => copyCode(l.code)}>Copy code</button>
          {#if l.local}
            <a class="btn" href={shareIssueUrl(l)} target="_blank" rel="noopener">Share on GitHub</a>
            <button class="btn danger" onclick={() => remove(l.localIndex)}>Delete</button>
          {/if}
        </div>
      </aside>
    {/if}
  </section>
</div>

<style>
  .split-portals { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }

  .dial { margin: 0 0 12px; }
  .dial-head { display: flex; gap: 12px; align-items: baseline; flex-wrap: wrap; font-family: var(--p-mono); }
  .dial-head .link { margin-left: auto; }
  .dial-code { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 4px; max-width: 600px; margin: 10px 0 4px; }
  .slot { aspect-ratio: 1; border-bottom: 2px solid currentColor; }
  .slot.empty { opacity: 0.35; }
  .dial-grid { display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 6px; max-width: 760px; }
  .dial-key {
    background: var(--p-raised);
    border: 1px solid var(--p-outline);
    border-radius: 0;
    padding: 6px 4px 4px;
    cursor: pointer;
    color: var(--p-text);
    min-width: 0;
  }
  .dial-key:hover { border-color: var(--p-accent); color: var(--p-accent); }
  .dial-key :global(.glyph) { width: 70%; margin: 0 auto; }
  .dial-key span { display: block; font-family: var(--p-mono); font-size: 0.7rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  details.save { margin-top: 14px; border-top: 1px solid var(--p-outline); padding-top: 10px; }
  details.save summary { cursor: pointer; color: var(--p-accent); font-family: var(--p-mono); font-weight: 700; font-size: 0.9rem; }
  .form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 12px; margin-top: 10px; }
  .form label { display: flex; flex-direction: column; gap: 3px; color: var(--p-faint); font-family: var(--p-mono); font-size: 0.8em; min-width: 0; }
  .form label.wide { grid-column: 1 / -1; }
  .form input, .form select { width: 100%; font-family: var(--p-sans); font-size: 1rem; }
  .form .btn { justify-self: start; }
  .form .form-actions { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 8px; }

  /* Under the saved list: the standing invitation to add to it. */
  .invite { margin: 10px 0 0; color: var(--p-faint); font-size: 0.85rem; line-height: 1.6; }
  .invite a { color: var(--p-accent); }

  @media (max-width: 1000px) {
    .split-portals { grid-template-columns: minmax(0, 1fr); }
  }
  @media (max-width: 640px) {
    .dial-code { grid-template-columns: repeat(6, minmax(0, 1fr)); }
    .dial-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
    .form { grid-template-columns: minmax(0, 1fr); }
  }
</style>
