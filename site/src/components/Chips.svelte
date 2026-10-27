<script>
  // What kind of thing an item is and how rare it is, as small coloured tags in
  // the game's own words (type) and the colours its HUD uses for them. Items the
  // recipe data does not hold (the Wiki's) bring their own `type` and `rar`.
  import { D } from "../lib/data.js";
  import { ITEM_TYPES, RARITIES, rarityLabel, typeLabel } from "../lib/words.js";
  import { t } from "../lib/i18n.js";

  // `show`: "both" (type and rarity), "type" only, or "rarity" only -- the last is a column of its own, so it says
  // "Common" too, where beside the type a common item carries no tag.
  // `typeHref` / `rarHref` turn that tag into a link.
  let { id, show = "both", type: typeIn = "", rar: rarIn = "", typeHref = "", rarHref = "" } = $props();

  const item = $derived(D.items[id]);
  const key = $derived(typeIn || item?.type);
  const type = $derived(show !== "rarity" ? (ITEM_TYPES[key] ? [typeLabel(key), ITEM_TYPES[key][1]] : key ? [key, "#94aac8"] : null) : null);
  const level = $derived(rarIn || item?.rar);
  const rar = $derived(show !== "type" && RARITIES[level] ? [rarityLabel(level), RARITIES[level][1]] : null);
  const common = $derived(show === "rarity" && level === "Common");
</script>

{#snippet tag(href, cls, color, text)}
  {#if href}<a class="chip2 {cls}" {href} style="--c:{color}">{text}</a>{:else}<span class="chip2 {cls}" style="--c:{color}">{text}</span>{/if}
{/snippet}

{#if type}{@render tag(typeHref, "", type[1], type[0])}{/if}
{#if rar}{@render tag(rarHref, "r", rar[1], rar[0])}{:else if common}{@render tag(rarHref, "", "#94aac8", t("Common"))}{/if}

<style>
  .chip2 {
    display: inline-flex; align-items: center; height: 24px; padding: 0 10px; margin-right: 6px;
    border-radius: 999px; font-size: 0.78rem; font-weight: 600; white-space: nowrap;
    color: color-mix(in srgb, var(--c) 82%, var(--p-text)); background: color-mix(in srgb, var(--c) 16%, transparent);
    border: 1px solid color-mix(in srgb, var(--c) 50%, transparent);
  }
  a.chip2 { text-decoration: none; }
  /* A tag that is a link lights up, its text is never underlined (a table's own `a:hover` would). */
  a.chip2:hover { text-decoration: none; background: color-mix(in srgb, var(--c) 30%, transparent); border-color: var(--c); }
  .r::before { content: "◆"; margin-right: 5px; font-size: 0.65em; }
</style>
