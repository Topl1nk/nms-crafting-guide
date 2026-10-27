<script>
  // "Reset filters": a square button with an icon, the same on every page that has filters. It is always there: when there is nothing
  // to reset it is dimmed (#293161) and does nothing.
  import Icon from "./Icon.svelte";
  import { t } from "../lib/i18n.js";

  let { active = false, onclick, title = t("Reset filters") } = $props();
</script>

<button class="reset" class:off={!active} {onclick} {title} aria-label={title} disabled={!active}><Icon name="reset" size={18} /></button>
