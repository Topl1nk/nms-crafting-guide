<script>
  import { bloom, collapse } from "../lib/bar.js";
  import { t } from "../lib/i18n.js";
  // A yes/no filter of a page's bar, the same box everywhere (.chk in app.css). It has three states, as filters do:
  //   empty   no opinion: everything is shown;
  //   ✔       only what has it (`true`);
  //   −       none of what has it, it is left out (`"not"`).
  // A click goes round them. `tri={false}`: a plain on/off (a setting, not a filter).
  let { label, value = $bindable(false), tri = true, title = "", disabled = false, hidden = false, onchange = undefined } = $props();

  let shown = false; // set once the filter has been drawn: only a filter that comes back later grows in
  $effect(() => { shown = true; });
  let width = $state(0);
  let last = 0; // the width the box had, for the marker that takes its place
  $effect(() => { if (width > 0) last = width; });

  function click() {
    value = value === false ? true : value === true && tri ? "not" : false;
    onchange?.(value);
  }
</script>

{#if hidden}<i class="gone" aria-hidden="true" use:collapse={last}></i>{:else}<button type="button" class="chk" bind:clientWidth={width} in:bloom={{ skip: !shown }} class:on={value === true} class:not={value === "not"} role="checkbox" aria-checked={value === "not" ? "mixed" : value === true}
  title={value === "not" ? t("{title} (these are hidden now)", { title }) : title} {disabled} onclick={click}>
  <span class="cbx" aria-hidden="true">{value === true ? "✔" : ""}</span><span>{label}</span></button>{/if}




