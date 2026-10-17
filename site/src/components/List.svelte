<script>
  // A table with one highlighted row, the TUI's list pane. Views hand it
  // columns and rows; it owns the cursor, and calls `onSelect` when the cursor
  // lands somewhere -- with `user` false when it landed there because the rows
  // changed, not because anyone moved it.
  //
  // A column is { title, cls, text: (row) => string } or, for anything with
  // markup in it, { title, cls, cell: snippet } with the snippet taking the row.
  //
  // The keyboard reaches it through lib/keys.js: bind:this and hand the
  // instance to setKeys() as `list`.
  import { tick, untrack } from "svelte";

  let {
    rows, columns, onSelect, onEnter, empty = "Nothing matches.",
    start = 0, keep = false, class: cls = "",
  } = $props();

  let sel = $state(-1);
  let box;

  export function select(i, scroll = true, user = true) {
    if (!rows.length) { sel = -1; return; }
    i = Math.max(0, Math.min(i, rows.length - 1));
    sel = i;
    if (scroll) tick().then(() => box?.querySelector(`tr[data-i="${i}"]`)?.scrollIntoView({ block: "nearest" }));
    onSelect?.(rows[i], i, user);
  }

  export const move = (delta) => select(sel + delta);
  export const current = () => rows[sel];
  export const count = () => rows.length;

  // New rows put the cursor back at the top (or where `start` says), unless
  // the view asked to `keep` it where it was.
  $effect.pre(() => {
    rows;
    untrack(() => select(keep && sel > 0 ? sel : start, false, false));
  });

  function click(event) {
    if (event.target.closest("a, button")) return;
    const tr = event.target.closest("tr[data-i]");
    if (tr) select(Number(tr.dataset.i));
  }

  function dblclick(event) {
    const tr = event.target.closest("tr[data-i]");
    if (tr && onEnter) onEnter(rows[Number(tr.dataset.i)]);
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="list {cls}" bind:this={box} onclick={click} ondblclick={dblclick}>
  {#if rows.length}
    <table>
      <thead><tr>{#each columns as c, ci (ci)}<th class={c.cls || ""}>{c.title}</th>{/each}</tr></thead>
      <tbody>
        {#each rows as row, i (i)}
          <tr data-i={i} class:sel={i === sel}>
            {#each columns as c, ci (ci)}
              <td class={c.cls || ""}>{#if c.cell}{@render c.cell(row)}{:else}{c.text(row)}{/if}</td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  {:else}
    <p class="muted pad">{empty}</p>
  {/if}
</div>

<style>
  table { border-collapse: collapse; width: 100%; font-size: 0.92rem; }
  th {
    position: sticky;
    top: 0;
    background: var(--p-raised);
    text-align: left;
    font-family: var(--p-mono);
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--p-muted);
    box-shadow: inset 0 -1px 0 var(--p-outline);
    z-index: 1;
  }
  /* A column marked muted is muted in its header too, as the global class
     alone would have it if this scoped rule did not outrank it. */
  th.muted { color: var(--p-faint); }
  th, td { padding: 5px 10px; vertical-align: top; }
  tbody tr { cursor: pointer; border-top: 1px solid var(--p-outline); }
  tbody tr:first-child { border-top: 0; }
  tbody tr:hover { background: var(--p-raised); }
  tbody tr.sel { background: var(--p-sel); box-shadow: inset 3px 0 0 var(--p-accent); }
  td.num, th.num { text-align: right; white-space: nowrap; font-family: var(--p-mono); font-size: 0.88em; }
  /* Links in cells come from the views' snippets, hence :global. */
  td :global(a) { text-decoration: none; }
  td :global(a:hover) { text-decoration: underline; }

  @media (max-width: 640px) {
    th, td { padding: 5px 7px; }
  }
</style>
