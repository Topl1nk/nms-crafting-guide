<script>
  // The game's own sign for units, the currency: every price and profit on the site is in these.
  // Put it before a number, as the game does (<Units />{fmtInt(n)}).
  import { t } from "../lib/i18n.js";
  let { size = 16 } = $props();
</script>

<img class="units" src="icons/UNITS.webp" alt={t("units")} title={t("units")} width={size} height={size} draggable="false">

<style>
  .units { display: inline-block; flex: none; vertical-align: middle; margin-right: 0.2em; -webkit-user-drag: none; user-select: none; }
</style>
