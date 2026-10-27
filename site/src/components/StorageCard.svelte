<script>
  // The card of one row of "My items" (an item, and the place it lies in when the save is read), built like the card of
  // the Craft and Wiki pages (picture and name, tags, the four figures), then where it lies and where it goes.
  // Every tag leads somewhere: the type and the rarity to the Wiki filtered by them, the places to the Wiki.
  import Chips from "./Chips.svelte";
  import Icon from "./Icon.svelte";
  import ItemIcon from "./ItemIcon.svelte";
  import StorageNote from "./StorageNote.svelte";
  import Units from "./Units.svelte";
  import { fmtInt } from "../lib/core.js";
  import { CONSUMED, D, PRODUCED } from "../lib/data.js";
  import { t } from "../lib/i18n.js";
  import { inventory } from "../lib/inventory.svelte.js";
  import { swap } from "../lib/motion.js";
  import { wikiRar, wikiType } from "../lib/store.js";

  let { id, at = null, onfindall = null, others = 0 } = $props();

  const item = $derived(D.items[id]);
  const have = $derived(at ? at.n : inventory.items[id] ?? 0);
</script>

<aside class="detail" use:swap={{ key: `${id}|${at?.place?.name ?? ""}`, drop: true }}>
  <div class="ic-head">
    <ItemIcon {id} size={60} />
    <div><h2>{item.name}</h2><p class="muted">{item.sub}</p></div>
  </div>
  <div class="ic-chips"><Chips {id} typeHref={wikiType(id)} rarHref={wikiRar(id)} /></div>

  <div class="stats">
    <div class="stat" title={t("Price each")}><Units size={18} /><b>{fmtInt(item.value)}</b><small>{t("price")}</small></div>
    <div class="stat" title={t("How many recipes make this")}><Icon name="make" /><b>{(PRODUCED[id] || []).length}</b><small>{t("how to make")}</small></div>
    <div class="stat" title={t("How many recipes need this")}><Icon name="need" /><b>{(CONSUMED[id] || []).length}</b><small>{t("where needed")}</small></div>
    <div class="stat" title={at ? t("How many lie in this place") : t("How many you have")}><Icon name="bag" /><b>{fmtInt(have)}</b><small>{at ? t("here") : t("you have")}</small></div>
  </div>

  <StorageNote {id} {at} {onfindall} {others} />
</aside>


