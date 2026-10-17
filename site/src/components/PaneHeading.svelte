<script>
  // A pane title, `┌─ Title ─────`: the h3 skin from global.css. A note, as
  // the install panes carry, goes past the rule and wraps under it when the
  // pane is narrow.
  let { title, note = "", class: cls = "" } = $props();
</script>

<h3 class={cls} class:noted={note}><span>{title}</span>{#if note}<em>{note}</em>{/if}</h3>

<style>
  .noted { flex-wrap: wrap; row-gap: 2px; }
  .noted::after { order: 2; }
  .noted span { flex: none; }
  em { order: 3; flex: none; font-style: normal; font-weight: 400; color: var(--p-faint); font-size: 0.8rem; }
</style>
