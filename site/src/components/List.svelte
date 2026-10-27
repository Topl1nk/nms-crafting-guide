<script>
  // A table with one highlighted row. Views hand it columns and rows; it owns
  // the cursor, the header-click sorting, and calls `onSelect` when the cursor
  // lands somewhere -- with `user` false when it landed there because the rows
  // changed, not because anyone moved it.
  //
  // `keyOf`: the identity of a row (default: the row itself), for lists that make their rows anew on every update.
  // `start`: the row the cursor lands on (and is scrolled to); with `atTop` it is brought to the top of the table.
  //
  // A column is { title, cls, text: (row) => string } or, for anything with
  // markup in it, { title, cls, cell: snippet } with the snippet taking the row.
  // Give it `sort: (row) => number | string` and its header sorts the table:
  // click once for ascending, again for descending, a third time to go back to
  // the view's own order.
  //
  // The keyboard reaches it through lib/keys.js: bind:this and hand the
  // instance to setKeys() as `list`.
  import { tick, untrack } from "svelte";
  import { t } from "../lib/i18n.js";
  import { springAt } from "../lib/spring.js";

  let {
    rows, columns, onSelect, onEnter, empty = t("Nothing found."),
    start = 0, atTop = false, keep = false, keyOf = (row) => row, class: cls = "",
  } = $props();

  // Only the first rows are drawn at once (a list of two thousand drawn whole stalls the page for a second); the rest are
  // added as the end of the list comes near, and for a row the cursor is sent to.
  const FIRST = 80;
  const STEP = 120;
  let shown = $state(FIRST);
  let sel = $state(-1);
  let sortCol = $state(-1);
  let sortDir = $state(1);
  let box;

  const view = $derived.by(() => {
    const c = columns[sortCol];
    if (!c?.sort) return rows;
    const key = c.sort;
    return [...rows].sort((a, b) => {
      const x = key(a);
      const y = key(b);
      const cmp = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), "ru");
      return cmp * sortDir;
    });
  });

  function sortBy(i) {
    if (!columns[i].sort) return;
    if (sortCol !== i) { sortCol = i; sortDir = 1; }
    else if (sortDir === 1) sortDir = -1;
    else { sortCol = -1; sortDir = 1; }
  }

  // `top`: bring the row to the top of the table, under the header (a row the view was opened on), not just into view.
  export function select(i, scroll = true, user = true, top = false) {
    if (!view.length) { sel = -1; return; }
    i = Math.max(0, Math.min(i, view.length - 1));
    sel = i;
    if (i >= shown) shown = i + STEP / 2; // the row has to be there to be scrolled to
    if (scroll) tick().then(() => {
      const tr = box?.querySelector(`tr[data-i="${i}"]`);
      if (!tr) return;
      if (!top) { tr.scrollIntoView({ block: "nearest" }); return; }
      const head = box.querySelector("thead")?.getBoundingClientRect().height ?? 0;
      box.scrollTop += tr.getBoundingClientRect().top - box.getBoundingClientRect().top - head;
    });
    onSelect?.(view[i], i, user);
  }

  export const move = (delta) => select(sel + delta);
  export const current = () => view[sel];
  export const count = () => view.length;

  // New rows, or a new order, put the cursor back at the top (or where `start`
  // says), unless the view asked to `keep` it where it was. The same rows again, in the same order (the list was built
  // anew from something that was read again and found unchanged), are no new rows: the cursor and the scroll stay.
  // `keyOf` says which rows are the same one when a view makes them anew each time (an array per row, say).
  let was = [];
  $effect.pre(() => {
    view;
    untrack(() => {
      const keys = view.map(keyOf);
      const unchanged = sel >= 0 && keys.length === was.length && keys.every((k, i) => k === was[i]);
      was = keys;
      if (unchanged) return;
      shown = FIRST;
      select(keep && sel > 0 ? sel : start, start > 0, false, atTop && start > 0);
    });
  });

  function click(event) {
    if (event.target.closest("a, button, input, select")) return;
    const tr = event.target.closest("tr[data-i]");
    if (tr) select(Number(tr.dataset.i));
  }

  function dblclick(event) {
    const tr = event.target.closest("tr[data-i]");
    if (tr && onEnter) onEnter(view[Number(tr.dataset.i)]);
  }

  // Every column is as wide as its longest value (up to a limit, in the CSS
  // below); what is left over goes to one column: the one the view marks
  // `fill: true`, or else the last of the long-text (`clip`) ones.
  // A text column with nothing in any row is left out, header and all.
  const cols = $derived(columns.map((c, i) => ({ c, i }))
    .filter(({ c }) => c.cell || !rows.length || rows.some((r) => String(c.text(r) ?? "").trim() !== "")));
  const fill = $derived(cols.some(({ c }) => c.fill) ? cols.find(({ c }) => c.fill).i
    : cols.findLast(({ c }) => c.cls?.includes("clip"))?.i ?? -1);
  const klass = (c, i) => `${c.cls || ""}${i === fill ? " fill" : ""}`;

  // The end of what is drawn: when it comes within a screen or two of the list's window, the next rows are drawn.
  function nearEnd(node) {
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) shown = Math.min(view.length, shown + STEP); }, { root: box, rootMargin: "900px 0px" });
    io.observe(node);
    return { destroy: () => io.disconnect() };
  }

  const ariaSort = (i) => (sortCol === i ? (sortDir === 1 ? "ascending" : "descending") : columns[i].sort ? "none" : undefined);

  // The columns are as wide as their longest value, so a filter changes them all at once. They do not jump: the widths
  // the table had are put back for a moment (a fixed layout with a <col> for each) and each <col> grows or shrinks
  // to its new width.
  const MS = 450;
  let widths = null; // column index -> width, as the table last stood
  let settle = null; // puts a table that is moving back to its own layout at once
  $effect(() => {
    view; cols; shown;
    untrack(() => {
      settle?.();
      const table = box?.querySelector("table");
      if (!table) { widths = null; return; }
      const keys = cols.map(({ i }) => i);
      const now = new Map([...table.querySelectorAll("thead th")].map((th, k) => [keys[k], th.getBoundingClientRect().width]));
      const was = widths;
      widths = now;
      if (!was || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      const sum = (m) => [...m.values()].reduce((s, w) => s + w, 0);
      if (Math.abs(sum(was) - sum(now)) > 2 || ![...now].some(([k, w]) => Math.abs(w - (was.get(k) ?? 0)) > 2)) return; // another size of table, or nothing moved
      const group = document.createElement("colgroup");
      const cs = keys.map((k) => { const col = document.createElement("col"); col.style.width = `${was.get(k) ?? 0}px`; group.append(col); return col; });
      table.prepend(group);
      table.style.tableLayout = "fixed";
      table.style.width = `${sum(now)}px`;
      box.classList.add("moving");
      // A <col> does not animate by css: every frame sets the widths a step further on the way.
      const from = keys.map((k) => was.get(k) ?? 0);
      const to = keys.map((k) => now.get(k));
      const t0 = performance.now();
      const timer = setTimeout(() => settle?.(), MS + 250); // a hidden tab draws no frames: never stay half way
      let frame = requestAnimationFrame(function step(t) {
        const p = Math.min(1, Math.max(0, (t - t0) / MS)); // (the frame's own time can be older than t0)
        const e = springAt(p); // the one spring of the site: it overshoots a little and settles
        cs.forEach((col, n) => { col.style.width = `${from[n] + (to[n] - from[n]) * e}px`; });
        if (p < 1) frame = requestAnimationFrame(step); else settle?.();
      });
      settle = () => {
        clearTimeout(timer);
        cancelAnimationFrame(frame);
        group.remove();
        table.style.tableLayout = "";
        table.style.width = "";
        box.classList.remove("moving");
        settle = null;
      };    });
  });</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="list {cls}" bind:this={box} onclick={click} ondblclick={dblclick}>
  {#if view.length}
    <table>
      <thead><tr>
        {#each cols as { c, i: ci } (ci)}
          <th class={klass(c, ci)} aria-sort={ariaSort(ci)}>
            {#if c.sort}
              <button type="button" class="th" onclick={() => sortBy(ci)} title={t("Sort by this column")}>
                <span>{c.title}</span><i class="arrow" class:on={sortCol === ci}>{sortCol === ci ? (sortDir === 1 ? "▲" : "▼") : "↕"}</i>
              </button>
            {:else}{c.title}{/if}
          </th>
        {/each}
      </tr></thead>
      <tbody>
        {#each view.slice(0, shown) as row, i (i)}
          <tr data-i={i} class:sel={i === sel}>
            {#each cols as { c, i: ci } (ci)}
              <td class={klass(c, ci)} title={c.text && String(c.text(row)).length > 28 ? c.text(row) : undefined}>{#if c.cell}{@render c.cell(row)}{:else}{c.text(row)}{/if}</td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
    {#if shown < view.length}<div class="more" use:nearEnd></div>{/if}
  {:else}
    <p class="muted pad empty">{empty}</p>
  {/if}
</div>

<style>
  table { border-collapse: separate; border-spacing: 0; width: 100%; font-size: 1rem; }
  th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: var(--p-head);
    box-shadow: 0 7px 9px -7px rgb(6 8 17 / 0.6); /* the head lifts a little off the rows under it */
    text-align: left;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--p-muted);
    border-bottom: 1px solid var(--p-outline);
    white-space: nowrap;
  }
  th.muted { color: var(--p-faint); }
  th, td { padding: 0 12px; vertical-align: middle; }
  th { height: 40px; }
  td { height: 48px; border-bottom: 1px solid var(--p-outline); white-space: nowrap; }
  tbody tr:last-child td { border-bottom: 0; }
  /* Scrolling a row into view leaves room for the sticky header, so row one is never left under it. */
  tbody tr { cursor: pointer; scroll-margin-top: 44px; }
  tbody tr:hover td { background: color-mix(in srgb, var(--p-accent) 6%, transparent); }
  tbody tr.sel td { background: var(--p-sel); }
  tbody tr.sel td:first-child { box-shadow: inset 3px 0 0 var(--p-accent-ink); }
  /* One line per row, always: long text is cut with an ellipsis (full text in the tooltip). */
  td.clip { max-width: 420px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  /* The one column that takes the room the others leave: width 100% with max-width 0 is the table's "rest of the row". */
  th.fill, td.fill { width: 100%; max-width: 0; }
  th.fill { overflow: hidden; }
  td.fill { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  td.num, th.num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
  th.num .th { margin-left: auto; }
  .th {
    display: inline-flex; align-items: center; gap: 6px; padding: 0; height: 100%;
    background: none; border: 0; color: inherit; font: inherit; letter-spacing: inherit;
    text-transform: inherit; cursor: pointer;
  }
  .th:hover { color: var(--p-text); }
  .arrow { font-style: normal; font-size: 0.7em; width: 1em; text-align: center; color: var(--p-faint); opacity: 0.6; }
  .arrow.on { color: var(--p-accent-ink); opacity: 1; }
  /* Links in cells come from the views' snippets, hence :global. */
  td :global(a) { text-decoration: none; }
  td :global(a:hover) { text-decoration: underline; }
  .empty { padding: 28px 16px; text-align: center; }
  .more { height: 1px; }
  /* While the columns move, a cell shows only what fits in it. */
  .list.moving :global(td), .list.moving :global(th) { overflow: hidden; text-overflow: clip; }
  /* The widths are fixed while they move, so the rows out of view need not be laid out on every frame. */
  .list.moving :global(tbody tr) { content-visibility: auto; contain-intrinsic-size: auto 48px; }

  @media (max-width: 640px) {
    th, td { padding: 0 8px; }
  }
</style>








