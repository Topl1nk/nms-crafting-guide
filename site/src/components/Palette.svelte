<script>
  // The TUI's Ctrl+P palette, as the site's search: sections by name, items by
  // name (exact, then prefix, then substring, like Book.search_items), and a
  // pasted portal address straight into the converter.
  import { tick } from "svelte";
  import { Address } from "../lib/core.js";
  import { CONSUMED, D, name, NAV, PRODUCED } from "../lib/data.js";
  import { collate, t } from "../lib/i18n.js";
  import { go } from "../lib/router.svelte.js";
  import { search } from "../lib/search.svelte.js";

  const TAG = { section: t("section"), item: t("recipes"), store: t("storage"), portal: t("portal") };

  let sel = $state(0);
  let listEl;

  const rows = $derived(search.open ? paletteRows(search.q) : []);

  // The field is in the header (it grows out of the loupe there and takes the focus itself); this is the list under it.
  export function open() {
    search.open = true;
    search.q = "";
    sel = 0;
  }

  function close() { search.open = false; }

  $effect(() => { search.q; sel = 0; });
  $effect(() => { search.keydown = keydown; return () => { search.keydown = null; }; });

  function choose(row) {
    if (!row) return;
    close();
    go(row.href);
  }

  function paletteRows(text) {
    text = text.trim();
    const lower = text.toLowerCase();
    const out = [];
    for (const [key, english] of [["home", "Home"], ...NAV]) {
      const label = t(english);
      if (!lower || label.toLowerCase().includes(lower)) {
        out.push({ kind: "section", label, href: `#/${key === "home" ? "" : key}` });
      }
    }
    if (!lower) return out;
    try {
      const a = Address.parse(text);
      out.unshift({ kind: "portal", label: a.code, note: a.galactic, href: `#/portals?code=${a.code}` });
    } catch { /* not an address */ }
    const starts = [];
    const contains = [];
    for (const [id, item] of Object.entries(D.items)) {
      const n = item.name.toLowerCase();
      if (n.startsWith(lower)) starts.push(id);
      else if (n.includes(lower)) contains.push(id);
    }
    const byName = (a, b) =>
      (name(a).toLowerCase() !== lower) - (name(b).toLowerCase() !== lower) || collate(name(a), name(b));
    for (const id of [...starts.sort(byName), ...contains.sort(byName)].slice(0, 30)) {
      const recipes = PRODUCED[id] || CONSUMED[id];
      out.push({
        kind: recipes ? "item" : "store",
        label: name(id),
        note: D.items[id].sub,
        // Items no recipe touches still have a storage answer.
        href: recipes ? `#/recipes?item=${encodeURIComponent(id)}` : `#/wiki?item=${encodeURIComponent(id)}`,
      });
    }
    return out;
  }

  async function move(delta) {
    sel = Math.max(0, Math.min(rows.length - 1, sel + delta));
    await tick();
    listEl?.querySelector(".sel")?.scrollIntoView({ block: "nearest" });
  }

  function keydown(e) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      move(e.key === "ArrowDown" ? 1 : -1);
    } else if (e.key === "Enter") {
      e.preventDefault();
      choose(rows[sel]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      close();
    }
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="palette" hidden={!search.open} onclick={(e) => { if (e.target === e.currentTarget) close(); }}>
  <div class="palette-box" role="dialog" aria-label={t("Search")}>
    <ul role="listbox" bind:this={listEl}>
      {#each rows as r, i (i)}
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <li role="option" class:sel={i === sel} aria-selected={i === sel} onclick={() => choose(r)}>
          <span class="pl">{r.label}</span>{#if r.note}<span class="pn">{r.note}</span>{/if}<span class="pt">{TAG[r.kind]}</span>
        </li>
      {:else}
        <li class="empty">{t("Nothing with that name.")}</li>
      {/each}
    </ul>
    <p class="palette-foot"><kbd>↑</kbd> <kbd>↓</kbd> {t("select")} · <kbd>Enter</kbd> {t("open")} · <kbd>Esc</kbd> {t("close")}</p>
  </div>
</div>

<style>
  /* The list of results, a pane under the field in the header (the header itself stays free above it). */
  .palette {
    position: fixed;
    inset: var(--nav-h) 0 0 0;
    z-index: 20;
    background: color-mix(in srgb, var(--p-bg) 55%, transparent);
    display: flex;
    justify-content: flex-end;
    align-items: flex-start;
    padding: 6px var(--gutter) 16px;
  }
  .palette[hidden] { display: none; }
  .palette-box {
    width: min(560px, 100%);
    animation: palette-in 0.22s ease 0.32s backwards;
    background: var(--p-panel);
    border: 1px solid var(--p-outline);
    box-shadow: 0 12px 40px rgb(0 0 0 / 0.4);
    font-family: var(--p-mono);
  }
  @keyframes palette-in { from { opacity: 0; transform: translateY(-6px); } }
  @media (prefers-reduced-motion: reduce) { .palette-box { animation: none; } }
  ul { list-style: none; margin: 0; padding: 4px 0; max-height: 50vh; overflow: auto; }
  li { display: flex; align-items: baseline; gap: 10px; padding: 6px 14px; cursor: pointer; font-size: 0.9rem; }
  li.sel { background: var(--p-accent); color: var(--p-on-accent); }
  li.sel .pn, li.sel .pt { color: var(--p-on-accent); }
  li.empty { color: var(--p-faint); cursor: default; }
  .pl { font-weight: 700; white-space: nowrap; }
  .pn { color: var(--p-faint); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 0.85em; }
  .pt { margin-left: auto; color: var(--p-faint); font-size: 0.75em; }
  .palette-foot { margin: 0; padding: 6px 14px; border-top: 1px solid var(--p-outline); color: var(--p-faint); font-size: 0.75rem; }
</style>
